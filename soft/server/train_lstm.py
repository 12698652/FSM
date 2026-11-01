# -*- coding: utf-8 -*-
"""LSTM + Attention 分类模型训练（按技术文档架构）

架构: LSTM(64) → LSTM(32) → Dropout(0.2) → Attention → Softmax(类别数自适应, 4级分类)
训练: Adam lr=0.001, batch=32, 早停(验证集 loss 不再下降则停)
输出: server/model.pth + metrics.json

相比旧版的修正:
  - 类别不均衡 → 加 class_weight 到 CrossEntropyLoss
  - 从训练集尾部切 15% 作验证集做早停（不再盲跑 50 epoch）
  - 归一化参数(norm_lo/hi)与元信息一并存进 checkpoint，
    推理端可直接复用，保证「训练怎么归一化、推理就怎么归一化」

运行: python train_lstm.py
"""
import json

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

# ============ 超参数 ============
BATCH = 32
EPOCHS = 200          # 上限，实际由早停决定
PATIENCE = 20         # 验证集 loss 连续 20 轮不降 → 停
LR = 0.001
HIDDEN1, HIDDEN2 = 64, 32
DROPOUT = 0.2
VAL_RATIO = 0.15
SEED = 42


class LSTMAttention(nn.Module):
    """LSTM 双层编码 + 加性注意力聚合 + 全连接分类"""

    def __init__(self, n_features, n_classes=4, h1=HIDDEN1, h2=HIDDEN2, dropout=DROPOUT):
        super().__init__()
        self.lstm1 = nn.LSTM(n_features, h1, batch_first=True)
        self.lstm2 = nn.LSTM(h1, h2, batch_first=True)
        self.dropout = nn.Dropout(dropout)
        self.attn = nn.Linear(h2, 1)
        self.fc = nn.Linear(h2, n_classes)

    def forward(self, x):
        out, _ = self.lstm1(x)
        out, _ = self.lstm2(out)
        out = self.dropout(out)
        weights = torch.softmax(self.attn(out), dim=1)   # (B,T,1)
        context = (out * weights).sum(dim=1)             # (B,h2)
        return self.fc(context)


def train():
    torch.manual_seed(SEED)
    np.random.seed(SEED)

    d = np.load("data/processed.npz", allow_pickle=True)
    X_all = torch.tensor(d["X_train"], dtype=torch.float32)
    y_all = torch.tensor(d["y_train"], dtype=torch.long)
    X_test = torch.tensor(d["X_test"], dtype=torch.float32)
    y_test_np = d["y_test"]
    stage_names = [str(s) for s in d["stage_names"]]
    label_source = str(d["label_source"]) if "label_source" in d else "unknown"
    n_features = X_all.shape[2]

    classes_present = sorted(set(y_all.tolist()) | set(y_test_np.tolist()))
    if len(classes_present) < 2:
        raise SystemExit("训练数据只有 1 个类别，无法训练（真实数据尚未进入腐败阶段）")

    # 训练集尾部 15% 作验证集（时间序，避免用未来预测过去之外的泄漏）
    n_val = max(1, int(len(X_all) * VAL_RATIO))
    X_tr, y_tr = X_all[:-n_val], y_all[:-n_val]
    X_val, y_val = X_all[-n_val:], y_all[-n_val:]
    print(f"数据: 训练 {tuple(X_tr.shape)} | 验证 {tuple(X_val.shape)} | "
          f"测试 {tuple(X_test.shape)} | 特征 {n_features}")

    # 类别数从数据的 stage_names 自适应（当前为 4 级分类）
    n_classes = len(stage_names)

    # 类别权重：样本少的类别给更大权重
    counts = np.bincount(y_tr.numpy(), minlength=n_classes).astype(np.float32)
    counts[counts == 0] = 1.0
    weights = torch.tensor(counts.sum() / (len(counts) * counts), dtype=torch.float32)
    print(f"类别权重: " + ", ".join(f"{stage_names[i]}={weights[i]:.2f}" for i in range(n_classes)))

    model = LSTMAttention(n_features, n_classes)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    criterion = nn.CrossEntropyLoss(weight=weights.to(device))
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)

    best_val = float("inf")
    best_state, best_epoch, wait = None, 0, 0

    for epoch in range(1, EPOCHS + 1):
        model.train()
        perm = torch.randperm(len(X_tr))
        total = 0.0
        for i in range(0, len(X_tr), BATCH):
            idx = perm[i:i + BATCH]
            xb, yb = X_tr[idx].to(device), y_tr[idx].to(device)
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            optimizer.step()
            total += loss.item() * len(idx)

        model.eval()
        with torch.no_grad():
            val_loss = criterion(model(X_val.to(device)), y_val.to(device)).item()

        if val_loss < best_val - 1e-5:
            best_val, best_epoch, wait = val_loss, epoch, 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            wait += 1
        if epoch % 10 == 0 or epoch == 1:
            print(f"epoch {epoch:3d}  训练loss={total / len(X_tr):.4f}  验证loss={val_loss:.4f}")
        if wait >= PATIENCE:
            print(f"早停于 epoch {epoch}（最佳 epoch {best_epoch}, 验证loss={best_val:.4f}）")
            break

    if best_state is not None:
        model.load_state_dict(best_state)

    model.eval()
    with torch.no_grad():
        pred = model(X_test.to(device)).argmax(dim=1).cpu().numpy()
    acc = accuracy_score(y_test_np, pred)
    f1 = f1_score(y_test_np, pred, average="macro", zero_division=0)
    cm = confusion_matrix(y_test_np, pred, labels=list(range(n_classes))).tolist()
    print(f"\n测试集准确率: {acc:.4f} | macro-F1: {f1:.4f}")
    print(f"混淆矩阵 (行=真实 列=预测, 顺序 {'/'.join(stage_names)}):")
    for name, row in zip(stage_names, cm):
        print(f"  {name:8s} {row}")
    print(classification_report(y_test_np, pred, labels=list(range(n_classes)),
                                target_names=stage_names, zero_division=0))

    check_metrics = None
    if "X_check" in d.files:
        X_check = torch.tensor(d["X_check"], dtype=torch.float32)
        y_check_np = d["y_check"]
        with torch.no_grad():
            pred_c = model(X_check.to(device)).argmax(dim=1).cpu().numpy()
        print(f"\n[独立抽查] 隔日回舱段（未参与训练/测试）共 {len(y_check_np)} 个窗口")
        print("  真实分布: " + ", ".join(
            f"{stage_names[k]}={int((y_check_np == k).sum())}" for k in range(n_classes)))
        print("  预测分布: " + ", ".join(
            f"{stage_names[k]}={int((pred_c == k).sum())}" for k in range(n_classes)))
        check_metrics = {
            "n": int(len(y_check_np)),
            "acc": round(float(accuracy_score(y_check_np, pred_c)), 4),
            "true_dist": {stage_names[k]: int((y_check_np == k).sum()) for k in range(n_classes)},
            "pred_dist": {stage_names[k]: int((pred_c == k).sum()) for k in range(n_classes)},
        }

    torch.save({"state_dict": model.state_dict(),
                "n_features": n_features, "n_classes": n_classes,
                "hidden1": HIDDEN1, "hidden2": HIDDEN2,
                "norm_lo": d["norm_lo"], "norm_hi": d["norm_hi"],
                "window": int(d["window"]),
                "feature_names": [str(x) for x in d["feature_names"]],
                "feat_sign": (d["feat_sign"] if "feat_sign" in d.files else None),
                "stage_names": stage_names,
                "label_source": label_source}, "model.pth")
    with open("metrics.json", "w", encoding="utf-8") as f:
        json.dump({"model": "LSTM+Attention",
                   "accuracy": round(acc, 4), "macro_f1": round(f1, 4),
                   "confusion_matrix": cm, "stages": stage_names,
                   "window": int(d["window"]), "best_epoch": best_epoch,
                   "label_source": label_source,
                   "independent_check": check_metrics}, f, ensure_ascii=False, indent=2)
    print("\n已保存 → model.pth / metrics.json")
    return acc


if __name__ == "__main__":
    train()
