# -*- coding: utf-8 -*-
"""把训练好的 LSTM+Attention 导出为 ONNX，供服务器轻量推理

为什么要导 ONNX：
  - 腾讯云轻量服务器内存有限，装 PyTorch 约 800MB 有 OOM 风险
  - 服务器只装 onnxruntime（约 15MB）即可跑推理

输入: model.pth（train_lstm.py 产出）
输出: data/model.onnx + data/model_meta.json（归一化参数/窗口/特征名等，推理端必须用同一套）

运行: python export_onnx.py
"""
import json
from datetime import datetime

import numpy as np
import torch

from train_lstm import LSTMAttention


def main():
    ckpt = torch.load("model.pth", map_location="cpu", weights_only=False)
    model = LSTMAttention(ckpt["n_features"], ckpt["n_classes"],
                          ckpt["hidden1"], ckpt["hidden2"])
    model.load_state_dict(ckpt["state_dict"])
    model.eval()

    window = int(ckpt["window"])
    n_features = int(ckpt["n_features"])
    dummy = torch.randn(1, window, n_features)

    onnx_path = "data/model.onnx"
    torch.onnx.export(
        model, dummy, onnx_path,
        input_names=["input"], output_names=["logits"],
        dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=17, dynamo=False)

    meta = {
        "model": "LSTM+Attention",
        "window": window,
        "n_features": n_features,
        "feature_names": [str(x) for x in ckpt["feature_names"]],
        "feat_sign": ([float(x) for x in ckpt["feat_sign"]]
                      if ckpt.get("feat_sign") is not None else None),
        "stage_names": [str(x) for x in ckpt["stage_names"]],
        "norm_lo": [float(x) for x in ckpt["norm_lo"]],
        "norm_hi": [float(x) for x in ckpt["norm_hi"]],
        "label_source": ckpt.get("label_source", "unknown"),
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open("data/model_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # 导出后自检：ONNXRuntime 推理结果应与 PyTorch 一致
    try:
        import onnxruntime as ort
        sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
        x = np.random.randn(2, window, n_features).astype(np.float32)
        with torch.no_grad():
            ref = model(torch.tensor(x)).numpy()
        got = sess.run(None, {"input": x})[0]
        diff = float(np.abs(ref - got).max())
        print(f"ONNX 自检: 与 PyTorch 最大误差 = {diff:.2e}")
    except ImportError:
        print("未装 onnxruntime，跳过自检（服务器端会用到）")

    print(f"已导出 → {onnx_path} + data/model_meta.json")


if __name__ == "__main__":
    main()
