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
        self.lo = np.array(self.meta["norm_lo"], dtype=np.float32)
        self.hi = np.array(self.meta["norm_hi"], dtype=np.float32)
        self.window = int(self.meta["window"])
        self.feats = list(self.meta["feature_names"])[:6]
        self.stages = [str(s) for s in self.meta["stage_names"]]

    def build_input(self, rows):
        """rows: 按时间正序的 dict 列表，需含 6 个原始特征"""
        if len(rows) < self.window:
            return None
        rows = rows[-self.window:]
        raw = np.array([[float(r[f]) for f in self.feats] for r in rows], dtype=np.float32)
        norm = (raw - self.lo) / (self.hi - self.lo)
        feats = np.concatenate([norm, np.zeros((self.window, 2), np.float32)], axis=1)
        feats[:, 6] = (norm[-1, 5] - norm[0, 5]) / self.window
        feats[:, 7] = (norm[-1, 0] - norm[0, 0]) / self.window
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
