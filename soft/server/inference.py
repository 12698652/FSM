# -*- coding: utf-8 -*-
"""服务器端轻量推理：ONNX + numpy，不依赖 PyTorch

由 app.py 调用，对「最近 window 条数据」做一次阶段预测。
关键：归一化必须复用训练时的 norm_lo / norm_hi（存在 model_meta.json），
      否则训练/推理两套尺度会导致预测完全错误。
"""
import json

import numpy as np


class StagePredictor:
    def __init__(self, onnx_path="data/model.onnx", meta_path="data/model_meta.json"):
        import onnxruntime as ort
        self.sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
        with open(meta_path, encoding="utf-8") as f:
            self.meta = json.load(f)
        self.window = int(self.meta["window"])
        # 原始输入特征 = 特征名中不含派生特征(以 d_ 开头)的部分；
        # Δ 派生特征(ΔNH₃/ΔVOC)排在末尾，由窗口首末值现算，不参与归一化参数。
        names = [str(x) for x in self.meta["feature_names"]]
        self.feats = [n for n in names if not n.startswith("d_")]
        self.n_delta = len([n for n in names if n.startswith("d_")])
        self.lo = np.array(self.meta["norm_lo"], dtype=np.float32)[:len(self.feats)]
        self.hi = np.array(self.meta["norm_hi"], dtype=np.float32)[:len(self.feats)]
        # 通道方向修正：必须与训练端 preprocess.py 的 FEAT_SIGN 完全一致，
        # 否则 voc(电阻,与浓度反相关) 会被喂成反方向 → 预测整体错乱。
        sign = self.meta.get("feat_sign")
        self.sign = (np.array(sign, dtype=np.float32)[:len(self.feats)]
                     if sign is not None else np.ones(len(self.feats), np.float32))
        self.stages = [str(s) for s in self.meta["stage_names"]]

    def build_input(self, rows):
        """rows: 按时间正序的 dict 列表，需含原始气味特征（voc/co2eq/tvoc/nh3_adc）"""
        if len(rows) < self.window:
            return None
        rows = rows[-self.window:]
        raw = np.array([[float(r[f]) for f in self.feats] for r in rows], dtype=np.float32)
        raw = raw * self.sign
        norm = (raw - self.lo) / (self.hi - self.lo)
        n_raw = len(self.feats)
        feats = np.concatenate([norm, np.zeros((self.window, self.n_delta), np.float32)], axis=1)
        if self.n_delta >= 2:
            i_nh3 = self.feats.index("nh3_adc")
            i_voc = self.feats.index("voc")
            feats[:, n_raw]     = (norm[-1, i_nh3] - norm[0, i_nh3]) / self.window
            feats[:, n_raw + 1] = (norm[-1, i_voc] - norm[0, i_voc]) / self.window
        return feats[None, ...].astype(np.float32)

    def predict(self, rows):
        x = self.build_input(rows)
        if x is None:
            return {"ready": False, "need": self.window, "have": len(rows)}
        logits = self.sess.run(None, {"input": x})[0][0]
        e = np.exp(logits - logits.max())
        p = e / e.sum()
        k = int(p.argmax())
        return {
            "ready": True,
            "stage": k,
            "stage_name": self.stages[k],
            "probs": {self.stages[i]: round(float(p[i]), 4) for i in range(len(p))},
            "label_source": self.meta.get("label_source", "unknown"),
            "window": self.window,
        }
