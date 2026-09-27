# -*- coding: utf-8 -*-
"""数据预处理：SQLite → 标签对齐 → 场次切分 → 仅训练集归一化 → 滑动窗口

相比旧版的关键修正：
  1. 标签来源分离
     - 真实标签：data/labels.csv（TVB-N / pH 实测 或 0-3 级人工评分）
     - 伪标签  ：NH₃ 阈值法（仅演示/管线验证用，属循环论证，不可作为答辩结论）
  2. 数据来源隔离：DEMO_BEFORE 之前的模拟数据不会混入真实训练集
  3. 防泄漏：多场次时按「场次」切分（训练 A 场、测试 B 场）；
     单场次时按标签分层切分，保证每类都进训练集
  4. 归一化参数只在训练集上拟合，两个集合用同一套参数

输出: data/processed.npz + data/processed_meta.json
运行:
  python preprocess.py                # 默认 real: 只用真实数据
  python preprocess.py --source demo   # 只用模拟数据跑通管线(管线验证)
  python preprocess.py --source real   # 只用真实数据
"""
import argparse
import json
import os
import sqlite3
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from config import (DEMO_BEFORE, LABELS_PATH, PSEUDO_FRESH_MAX,
                    PSEUDO_SLIGHT_MAX, PSEUDO_WARNING_MAX, SESSION_GAP_MIN,
                    TVBN_FRESH_MAX, TVBN_SLIGHT_MAX, TVBN_WARNING_MAX, DB_PATH)

# ============ 可调参数 ============
WINDOW_SIZE = 60        # 滑动窗口: 60 个采样点(60分钟)
STRIDE = 2              # 窗口步长(重叠采样)
TEST_RATIO = 0.3        # 单场次时的测试比例
FEATURES = ["voc", "co2eq", "tvoc", "temperature", "humidity", "nh3_adc"]
STAGE_NAMES = ["Fresh", "Warning", "Slight", "Spoiled"]   # 新鲜/预警/轻微变质/腐坏
N_CLASSES = 4
SEED = 42


def load_frame(source):
    """读取数据库并按来源过滤（demo=模拟数据 / real=实测数据）"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM measurements ORDER BY timestamp ASC", conn)
    conn.close()
    n_all = len(df)
    if source == "demo":
        df = df[df["timestamp"] < DEMO_BEFORE]
    elif source == "real":
        df = df[df["timestamp"] >= DEMO_BEFORE]
    df = df.reset_index(drop=True)
    print(f"[数据] 来源={source} | 全库 {n_all} 条 → 选用 {len(df)} 条")
    return df


def load_labels():
    """读取真实标签文件；不存在或无有效行返回 None"""
    if not os.path.exists(LABELS_PATH):
        return None
    # encoding="utf-8-sig" 兼容 Excel 另存的带 BOM 文件（无 BOM 时也正常）
    lab = pd.read_csv(LABELS_PATH, encoding="utf-8-sig")
    lab = lab.dropna(how="all")
    if len(lab) == 0 or "timestamp" not in lab.columns:
        return None
    lab["timestamp"] = pd.to_datetime(lab["timestamp"], errors="coerce")
    lab = lab.dropna(subset=["timestamp"]).sort_values("timestamp")

    stages = []
    for _, r in lab.iterrows():
        if "stage" in lab.columns and pd.notna(r.get("stage")):
            stages.append(int(r["stage"]))
        elif "tvb_n" in lab.columns and pd.notna(r.get("tvb_n")):
            v = float(r["tvb_n"])
            stages.append(0 if v < TVBN_FRESH_MAX else
                          (1 if v < TVBN_WARNING_MAX else
                           (2 if v < TVBN_SLIGHT_MAX else 3)))
        else:
            stages.append(np.nan)
    lab["_stage"] = stages
    lab = lab.dropna(subset=["_stage"])
    return lab[["timestamp", "_stage"]].rename(columns={"_stage": "stage"})


def pseudo_stage(nh3_adc):
    """NH₃ 阈值伪标签（仅管线验证；nh3_adc 本身是输入特征 → 循环论证）"""
    if nh3_adc < PSEUDO_FRESH_MAX:
        return 0
    if nh3_adc < PSEUDO_WARNING_MAX:
        return 1
    if nh3_adc < PSEUDO_SLIGHT_MAX:
        return 2
    return 3


def attach_labels(df, lab, source):
    """给每条测量打标签并返回 (带标签的df, label_source描述)"""
    df = df.copy()
    df["timestamp_dt"] = pd.to_datetime(df["timestamp"], errors="coerce")
    if lab is not None:
        merged = pd.merge_asof(
            df.sort_values("timestamp_dt"),
            lab.rename(columns={"timestamp": "timestamp_dt"}).sort_values("timestamp_dt"),
            on="timestamp_dt", direction="backward")
        merged = merged.dropna(subset=["stage"])
        if len(merged) >= WINDOW_SIZE + 10:
            return merged, "real(labels.csv)"
        print(f"[标签] labels.csv 覆盖不足({len(merged)}条), 降级为伪标签")
    df["stage"] = [pseudo_stage(v) for v in df["nh3_adc"]]
    desc = "pseudo(NH3阈值, 仅演示)"
    if source == "real":
        print("[标签] 警告: 真实数据使用伪标签, 且 NH₃ 未进入腐败区间, 标签可能全为 Fresh")
    return df, desc


def detect_sessions(ts_dt):
    """按时间间隔切分实验场次（间隔 > SESSION_GAP_MIN 分钟算新场次）"""
    gaps = ts_dt.diff().dt.total_seconds().fillna(0.0)
    return (gaps > SESSION_GAP_MIN * 60).cumsum().astype(int)


def raw_windows(g, window, stride):
    """单个场次的原始特征窗口（未归一化）+ 标签，标签取窗口末点"""
    raw = g[FEATURES].to_numpy(dtype=np.float32)
    X, y = [], []
    n = len(raw)
    if n < window:
        return None, None
    for i in range(0, n - window + 1, stride):
        X.append(raw[i:i + window])
        y.append(int(g["stage"].iloc[i + window - 1]))
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int64)


def finalize(X_raw, lo, hi):
    """用训练集统计量做 Min-Max 归一化，并追加增量特征 ΔNH₃ / ΔVOC"""
    norm = (X_raw - lo) / (hi - lo)
    n, w, _ = norm.shape
    feats = np.concatenate([norm, np.zeros((n, w, 2), dtype=np.float32)], axis=2)
    feats[:, :, 6] = (norm[:, -1, 5] - norm[:, 0, 5])[:, None] / w   # ΔNH₃/步
    feats[:, :, 7] = (norm[:, -1, 0] - norm[:, 0, 0])[:, None] / w   # ΔVOC/步
    return feats.astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["auto", "real", "demo"], default="auto")
    ap.add_argument("--window", type=int, default=WINDOW_SIZE)
    ap.add_argument("--stride", type=int, default=STRIDE)
    args = ap.parse_args()

    source = "real" if args.source == "auto" else args.source
    df = load_frame(source)
    if len(df) < args.window + 10:
        raise SystemExit(f"数据不足({len(df)}条), 至少需要 {args.window + 10} 条")

    df, label_source = attach_labels(df, load_labels(), source)
    df = df.sort_values("timestamp_dt").reset_index(drop=True)
    df["session"] = detect_sessions(df["timestamp_dt"])
    n_sess = int(df["session"].nunique())
    print(f"[标签] {label_source} | 覆盖 {len(df)} 条 | 阶段分布: " +
          ", ".join(f"{STAGE_NAMES[k]}={int((df['stage'] == k).sum())}" for k in range(N_CLASSES)))
    print(f"[场次] 检测到 {n_sess} 个实验场次")

    Xs, ys, sess = [], [], []
    for sid, g in df.groupby("session"):
        X, y = raw_windows(g, args.window, args.stride)
        if X is not None and len(X):
            Xs.append(X)
            ys.append(y)
            sess.append(np.full(len(X), sid))
    if not Xs:
        raise SystemExit("窗口切分后无数据, 请检查数据量或标签覆盖")
    X_raw = np.concatenate(Xs)
    y_all = np.concatenate(ys)
    sess_all = np.concatenate(sess)

    if n_sess >= 2:
        sessions = sorted(df["session"].unique())
        test_sess = sessions[-1]
        tr = np.where(sess_all != test_sess)[0]
        te = np.where(sess_all == test_sess)[0]
        split_desc = f"按场次: 场次{sessions[:-1]}训练 / 场次{test_sess}测试"
    else:
        idx = np.arange(len(X_raw))
        tr, te = train_test_split(idx, test_size=TEST_RATIO,
                                  stratify=y_all, random_state=SEED)
        split_desc = f"单场次: 按标签分层随机切分({int((1 - TEST_RATIO) * 100)}/{int(TEST_RATIO * 100)})" \
                     "（注意: 重叠窗口会带来乐观偏差, 真实实验请用多场次）"
    print(f"[切分] {split_desc}")

    lo = X_raw[tr].reshape(-1, len(FEATURES)).min(axis=0)
    hi = X_raw[tr].reshape(-1, len(FEATURES)).max(axis=0)
    hi = np.where(hi - lo < 1e-8, hi + 1e-8, hi)
    print("[归一化] 参数仅在训练集拟合")

    X_train, X_test = finalize(X_raw[tr], lo, hi), finalize(X_raw[te], lo, hi)
    y_train, y_test = y_all[tr], y_all[te]
    print(f"[窗口] 训练 {X_train.shape} | 测试 {X_test.shape}")
    for tag, yy in (("训练", y_train), ("测试", y_test)):
        print(f"       {tag}标签分布: " + ", ".join(
            f"{STAGE_NAMES[k]}={int((yy == k).sum())}" for k in range(N_CLASSES)))

    os.makedirs("data", exist_ok=True)
    np.savez_compressed(
        "data/processed.npz",
        X_train=X_train, X_test=X_test, y_train=y_train, y_test=y_test,
        norm_lo=lo, norm_hi=hi,
        feature_names=np.array(FEATURES + ["d_nh3", "d_voc"]),
        stage_names=np.array(STAGE_NAMES),
        window=args.window, label_source=np.array(label_source), source=np.array(source),
    )
    meta = {"source": source, "label_source": label_source, "n_sessions": n_sess,
            "window": args.window, "stride": args.stride, "split": split_desc,
            "train": int(len(X_train)), "test": int(len(X_test)),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    with open("data/processed_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print("已保存 → data/processed.npz + data/processed_meta.json")
    if label_source.startswith("pseudo"):
        print("\n警告: 当前为伪标签(循环论证), 模型仅用于管线验证, 不可作为科学结论。")


if __name__ == "__main__":
    main()
