# -*- coding: utf-8 -*-
"""SHAP 可解释性分析（答辩亮点：解释"模型为什么这样判断"）

对 LSTM+Attention 模型做特征贡献分析:
  1. 优先用 shap.DeepExplainer(PyTorch 深度解释器)
  2. 失败时自动降级为 Permutation Importance(逐特征打乱测准确率跌幅)
输出: data/shap_importance.png(特征贡献条形图) + 控制台排名

运行: python explain_shap.py
"""
import json

import matplotlib

matplotlib.use("Agg")  # 无界面环境出图
import matplotlib.pyplot as plt
import numpy as np
import torch

from train_lstm import LSTMAttention

N_EXPLAIN = 200   # 用于解释的测试样本数


def load_all():
    d = np.load("data/processed.npz", allow_pickle=True)
    ckpt = torch.load("model.pth", map_location="cpu", weights_only=False)
    model = LSTMAttention(ckpt["n_features"], ckpt["n_classes"],
                          ckpt["hidden1"], ckpt["hidden2"])
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    feat_names = [str(x) for x in d["feature_names"]]
    X_test = torch.tensor(d["X_test"], dtype=torch.float32)
    return model, X_test, feat_names


def shap_deep(model, X):
    """DeepExplainer: 取每个特征在时间维上的平均 |SHAP| 值"""
    import shap
    bg = X[:64]                       # 背景集(简化用测试集前64条)
    ex = shap.DeepExplainer(model, bg)
    sv = ex.shap_values(X[:N_EXPLAIN])          # list(每类) 或 array
    sv = np.array(sv)
    if sv.ndim == 4:                             # (classes, N, T, F) → 类别维取绝对值平均
        sv = np.abs(sv).mean(axis=(0, 2))        # → (F,)
    else:
        sv = np.abs(sv).mean(axis=0)
        if sv.ndim == 2:
            sv = sv.mean(axis=0)
    return sv


def permutation_importance(model, X, y, feat_names):
    """降级方案: 打乱某特征所有时间步 → 测准确率跌幅(跌幅越大越重要)"""
    with torch.no_grad():
        base = model(X[:N_EXPLAIN]).argmax(dim=1).numpy()
    base_acc = (base == y[:N_EXPLAIN]).mean()
    drops = []
    for j in range(X.shape[2]):
        Xp = X[:N_EXPLAIN].clone()
        Xp[:, :, j] = Xp[torch.randperm(len(Xp)), :, j]   # 时间步间打乱该特征
        with torch.no_grad():
            pred = model(Xp).argmax(dim=1).numpy()
        drops.append(base_acc - (pred == y[:N_EXPLAIN]).mean())
    return np.array(drops), base_acc


def plot(values, feat_names, method, out="data/shap_importance.png"):
    order = np.argsort(values)
    plt.figure(figsize=(8, 5))
    plt.barh([feat_names[i] for i in order], values[order], color="#3182ce")
    plt.xlabel("mean |SHAP value|" if method == "deep" else "accuracy drop (permutation)")
    plt.title("Feature Importance - " + ("SHAP (DeepExplainer)" if method == "deep" else "Permutation Importance"))
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    print(f"图已保存 → {out}")


def main():
    model, X, feat_names = load_all()
    d = np.load("data/processed.npz", allow_pickle=True)
    y_test = d["y_test"]

    method, values = "deep", None
    try:
        print("尝试 SHAP DeepExplainer ...")
        values = shap_deep(model, X)
        print("DeepExplainer 成功")
    except Exception as e:
        print(f"DeepExplainer 不可用({type(e).__name__}), 降级为 Permutation Importance")
        values, base_acc = permutation_importance(model, X, y_test, feat_names)
        print(f"基准准确率: {base_acc:.4f}")
        method = "perm"

    ranking = sorted(zip(feat_names, values), key=lambda kv: -kv[1])
    print("\n特征贡献排名(答辩用):")
    for name, v in ranking:
        print(f"  {name:12s} {v:+.4f}")
    plot(values, feat_names, method)
    with open("shap_result.json", "w", encoding="utf-8") as f:
        json.dump({"method": method, "ranking": [(n, float(v)) for n, v in ranking]}, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
