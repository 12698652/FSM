# -*- coding: utf-8 -*-
"""随机森林 / 梯度提升 基线模型（对比用）

为什么要有这个基线：
  - 本项目样本量小（单场次实验仅数千条），树模型往往比 LSTM 更稳、更不易过拟合
  - 答辩时可对比「LSTM+Attention vs 树模型」，证明选 LSTM 是有依据的，而不是硬凑
  - 树模型无需归一化、训练秒级，适合做快速 sanity check

输入: data/processed.npz（由 preprocess.py 生成）
输出: data/metrics_rf.json + data/model_rf.joblib

运行: python train_rf.py
"""
import json

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

SEED = 42


def load():
    d = np.load("data/processed.npz", allow_pickle=True)
    Xtr = d["X_train"].reshape(len(d["X_train"]), -1)
    Xte = d["X_test"].reshape(len(d["X_test"]), -1)
    return Xtr, d["y_train"], Xte, d["y_test"], [str(s) for s in d["stage_names"]]


def evaluate(name, model, Xtr, ytr, Xte, yte, stages):
    model.fit(Xtr, ytr)
    pred = model.predict(Xte)
    acc = accuracy_score(yte, pred)
    f1 = f1_score(yte, pred, average="macro", zero_division=0)
    all_labels = list(range(len(stages)))
    cm = confusion_matrix(yte, pred, labels=all_labels).tolist()
    print(f"\n=== {name} ===")
    print(f"准确率 {acc:.4f} | macro-F1 {f1:.4f}")
    print(f"混淆矩阵(行=真实 列=预测, 顺序 {'/'.join(stages)}):")
    for s, row in zip(stages, cm):
        print(f"  {s:8s} {row}")
    print(classification_report(yte, pred, labels=all_labels,
                                target_names=stages, zero_division=0))
    return {"name": name, "accuracy": round(acc, 4), "macro_f1": round(f1, 4),
            "confusion_matrix": cm}


def main():
    Xtr, ytr, Xte, yte, stages = load()
    n_classes = len(set(ytr.tolist()) | set(yte.tolist()))
    print(f"训练 {Xtr.shape} | 测试 {Xte.shape} | 出现的类别数 {n_classes}")
    if n_classes < 2:
        raise SystemExit("标签只有 1 类，无法训练分类模型（真实数据尚未进入腐败阶段）")

    results = []
    rf = RandomForestClassifier(n_estimators=300, max_depth=None,
                                class_weight="balanced", random_state=SEED, n_jobs=-1)
    results.append(evaluate("RandomForest", rf, Xtr, ytr, Xte, yte, stages))

    gb = GradientBoostingClassifier(random_state=SEED)
    results.append(evaluate("GradientBoosting", gb, Xtr, ytr, Xte, yte, stages))

    best = max(results, key=lambda r: r["macro_f1"])
    print(f"\n基线最佳: {best['name']} (macro-F1={best['macro_f1']})")

    joblib.dump(rf, "data/model_rf.joblib")
    with open("data/metrics_rf.json", "w", encoding="utf-8") as f:
        json.dump({"results": results, "best": best["name"], "stages": stages},
                  f, ensure_ascii=False, indent=2)
    print("已保存 → data/model_rf.joblib + data/metrics_rf.json")


if __name__ == "__main__":
    main()
