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
                    TVBN_FRESH_MAX, TVBN_SLIGHT_MAX, TVBN_WARNING_MAX,
                    TRAIN_DB_PATH, USE_DB_QUALITY_FLAGS)

# ============ 可调参数 ============
WINDOW_SIZE = 60        # 滑动窗口: 60 个采样点(60分钟)
STRIDE = 2              # 窗口步长(重叠采样)
TEST_RATIO = 0.3        # 单场次时的测试比例
# 模型输入特征：仅气味类通道，不含温度/湿度。
#   温度/湿度受环境影响极大（密闭盒 vs 开放空气、昼夜温差），与腐败无直接因果，
#   纳入后模型会把「潮湿/偏冷的环境」误关联为变质（2026-10-04 洁净空气被误判为
#   Warning 即因此）。故从模型输入中移除，仅保留与腐败直接相关的挥发物信号。
#   温湿度仍在 OLED/网页展示，只是不再喂给模型。
FEATURES = ["voc", "co2eq", "tvoc", "nh3_adc"]
DELTA_FEATURES = ["d_nh3", "d_voc"]   # 派生特征：末尾追加的窗口首末变化率
# voc 通道方向修正：BME680 的 voc = gas_resistance/1000(kΩ)，是「电阻」——
#   洁净空气电阻大、污染气体电阻小，方向与其它通道相反。建模前逐通道乘此符号，
#   使「数值越大=污染越重」全通道一致；ΔVOC 派生特征随之自动正确。
#   该符号随训练集一并存入产物，推理端必须用同一套（见 inference.py）。
FEAT_SIGN = np.array([-1, 1, 1, 1], dtype=np.float32)
STAGE_NAMES = ["Fresh", "Warning", "Slight", "Spoiled"]   # 新鲜/预警/轻微变质/腐坏
N_CLASSES = 4
SEED = 42

# 空舱段（无样品在舱）：该区间实测数据阶段不可信，训练/测试一律剔除
EMPTY_CHAMBER = [("2026-09-27 16:52:00", "2026-09-27 21:33:00")]

# 独立抽查段（隔日回舱）：整段留出，不进训练/测试，仅作跨条件一致性抽查
HOLDOUT_CHECK = ("2026-09-27 21:33:00", "2026-09-28 01:03:00")

# 清洁空气基线段：作为 Fresh 参考，强制并入训练集（不进测试, 避免作弊式准确率）
#   旧固件：10-01 下午 6 小时；新固件：10-04 19:04 起（升级后重置于洁净空气）。
#   新固件段会被 labels.csv 末条(stage=3)前向填充污染, 故在 main() 中统一按 Fresh 重打标。
BASELINE_WINDOWS = [("2026-10-01 17:00:00", "2026-10-01 23:00:00"),
                    ("2026-10-04 19:04:20", None)]

# 无标签空档段：无有效标签, 且会被标签前向填充(backward)污染, 训练/测试一律剔除
# 09-28 抽查段结束 → 10-01 基线开始；10-01 基线结束 → 10-02 重启自热瞬态结束（有界, 勿写成 None 以免吞掉后续新实验）
UNLABELED_GAP = [("2026-09-28 01:03:00", "2026-10-01 17:00:00"),
                 ("2026-10-01 23:00:00", "2026-10-02 06:00:00")]

# 人为尖峰段（人员靠近板子 / 重启自热瞬态）：非真实腐败信号，不作基线/标签/训练
# 唯一来源：data/export_baseline.py 从此处导入复用，新增尖峰只改这一处
SPIKE_WINDOWS = [("2026-10-01 19:02:00", "2026-10-01 19:07:00"),
                 ("2026-10-01 23:00:00", "2026-10-01 23:16:00")]

# 新旧固件切换过渡段：10-04 18:05 起设备重启(自热温漂) + SGP30 基线重收敛, 至 19:04 新固件生效。
#   该段温漂剧烈、气味基线不可信（既非腐坏也非洁净），训练/测试一律剔除。
FIRMWARE_TRANSITION = ("2026-10-04 18:05:00", "2026-10-04 19:04:20")


def _drop_quality_flagged(df):
    """按 audit.py 写入的 quality_flags（severity=error）剔除异常段
    训练库里没有该表（如旧的云端快照）时直接跳过，不影响已有流程
    """
    try:
        conn = sqlite3.connect(TRAIN_DB_PATH)
        rows = conn.execute(
            "SELECT start_ts, end_ts FROM quality_flags WHERE severity='error'").fetchall()
        conn.close()
    except sqlite3.Error:
        return df
    if not rows:
        return df
    ts = pd.to_datetime(df["timestamp"], errors="coerce")
    mask = pd.Series(False, index=df.index)
    for a, b in rows:
        mask |= (ts >= a) & (ts <= b)
    print(f"[清洗] 剔除质检异常段 {int(mask.sum())} 条（audit.py 自动检测，共 {len(rows)} 段）")
    return df[~mask]


def load_frame(source):
    """读取数据库并按来源过滤（demo=模拟数据 / real=实测数据）"""
    print(f"[数据源] 训练库 = {TRAIN_DB_PATH}")
    conn = sqlite3.connect(TRAIN_DB_PATH)
    df = pd.read_sql_query("SELECT * FROM measurements ORDER BY timestamp ASC", conn)
    conn.close()
    n_all = len(df)
    if source == "demo":
        df = df[df["timestamp"] < DEMO_BEFORE]
    elif source == "real":
        df = df[df["timestamp"] >= DEMO_BEFORE]
    if source != "demo" and EMPTY_CHAMBER:
        ts = pd.to_datetime(df["timestamp"], errors="coerce")
        mask = pd.Series(False, index=df.index)
        for a, b in EMPTY_CHAMBER:
            mask |= (ts >= a) & (ts < b)
        print(f"[清洗] 剔除空舱段 {int(mask.sum())} 条（无样品在舱, 阶段不可信）")
        df = df[~mask]
    if source != "demo" and SPIKE_WINDOWS:
        ts = pd.to_datetime(df["timestamp"], errors="coerce")
        mask = pd.Series(False, index=df.index)
        for a, b in SPIKE_WINDOWS:
            mask |= (ts >= a) & (ts < b)
        print(f"[清洗] 剔除人为尖峰段 {int(mask.sum())} 条（人员靠近/重启瞬态, 不作基线/标签）")
        df = df[~mask]
    if source != "demo" and FIRMWARE_TRANSITION:
        ts = pd.to_datetime(df["timestamp"], errors="coerce")
        a, b = FIRMWARE_TRANSITION
        mask = (ts >= a) & (ts < b)
        print(f"[清洗] 剔除固件切换过渡段 {int(mask.sum())} 条（重启自热/基线重收敛, 语义不连续）")
        df = df[~mask]
    if source != "demo" and UNLABELED_GAP:
        ts = pd.to_datetime(df["timestamp"], errors="coerce")
        mask = pd.Series(False, index=df.index)
        for a, b in UNLABELED_GAP:
            sel = ts >= a
            if b:
                sel &= ts < b
            mask |= sel
        print(f"[清洗] 剔除无标签空档段 {int(mask.sum())} 条（会被标签前向填充污染）")
        df = df[~mask]
    if source != "demo" and USE_DB_QUALITY_FLAGS:
        df = _drop_quality_flagged(df)
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
    """单个场次的原始特征窗口（未归一化，已做通道方向修正）+ 标签，标签取窗口末点"""
    raw = g[FEATURES].to_numpy(dtype=np.float32) * FEAT_SIGN
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
    n, w, n_feat = norm.shape
    feats = np.concatenate([norm, np.zeros((n, w, len(DELTA_FEATURES)), dtype=np.float32)], axis=2)
    i_nh3 = FEATURES.index("nh3_adc")
    i_voc = FEATURES.index("voc")
    feats[:, :, n_feat]     = (norm[:, -1, i_nh3] - norm[:, 0, i_nh3])[:, None] / w   # ΔNH₃/步
    feats[:, :, n_feat + 1] = (norm[:, -1, i_voc] - norm[:, 0, i_voc])[:, None] / w   # ΔVOC/步
    return feats.astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["auto", "real", "demo"], default="auto")
    ap.add_argument("--window", type=int, default=WINDOW_SIZE)
    ap.add_argument("--stride", type=int, default=STRIDE)
    ap.add_argument("--split", choices=["session", "stratified", "chrono"], default="session",
                    help="训练/测试切分方式: session=按场次(默认, 最后场次做测试); "
                         "stratified=全数据按标签分层随机; chrono=按时间先后(前段训练/后段测试)")
    args = ap.parse_args()

    source = "real" if args.source == "auto" else args.source
    df = load_frame(source)
    if len(df) < args.window + 10:
        raise SystemExit(f"数据不足({len(df)}条), 至少需要 {args.window + 10} 条")

    df, label_source = attach_labels(df, load_labels(), source)
    df = df.sort_values("timestamp_dt").reset_index(drop=True)

    df_check, check_desc = None, None
    if HOLDOUT_CHECK is not None:
        a, b = HOLDOUT_CHECK
        hm = df["timestamp_dt"] >= a
        if b:
            hm &= df["timestamp_dt"] < b
        df_check = df[hm].reset_index(drop=True)
        df = df[~hm].reset_index(drop=True)
        check_desc = f"{a} ~ {b or '最新'}"
        print(f"[抽查] 独立留出 {len(df_check)} 条（{check_desc}），不参与训练/测试")

    df_base_parts = []
    if BASELINE_WINDOWS:
        for a, b in BASELINE_WINDOWS:
            bm = df["timestamp_dt"] >= a
            if b:
                bm &= df["timestamp_dt"] < b
            part = df[bm].copy()
            if len(part):
                part["stage"] = 0   # 清洁空气恒为 Fresh（覆盖标签前向填充）
                df_base_parts.append(part.reset_index(drop=True))
                print(f"[基线] 抽出清洁空气基线 {len(part)} 条（{a} ~ {b or '最新'}），并入训练集")
            df = df[~bm].reset_index(drop=True)

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

    if args.split == "stratified":
        idx = np.arange(len(X_raw))
        tr, te = train_test_split(idx, test_size=TEST_RATIO,
                                  stratify=y_all, random_state=SEED)
        split_desc = (f"全数据按标签分层随机切分({int((1 - TEST_RATIO) * 100)}/{int(TEST_RATIO * 100)})"
                      "（重叠窗口会带来乐观偏差, 不作为泛化结论）")
    elif args.split == "chrono":
        n_all = len(X_raw)
        cut = int(n_all * (1 - TEST_RATIO))
        tr, te = np.arange(0, cut), np.arange(cut, n_all)
        split_desc = (f"按时间先后切分(前{int((1 - TEST_RATIO) * 100)}%训练/后{int(TEST_RATIO * 100)}%测试)"
                      "（更贴近'预测未来腐败'场景）")
    elif n_sess >= 2:
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

    X_train_raw, y_train = X_raw[tr], y_all[tr]
    n_base_win = 0
    for part in df_base_parts:
        if len(part) >= args.window:
            Xb, yb = raw_windows(part, args.window, args.stride)
            if Xb is not None and len(Xb):
                X_train_raw = np.concatenate([X_train_raw, Xb])
                y_train = np.concatenate([y_train, yb])
                n_base_win += len(Xb)
    if n_base_win:
        print(f"[基线] 新增训练窗口 {n_base_win} 个（清洁空气 Fresh 参考）")

    lo = X_train_raw.reshape(-1, len(FEATURES)).min(axis=0)
    hi = X_train_raw.reshape(-1, len(FEATURES)).max(axis=0)
    hi = np.where(hi - lo < 1e-8, hi + 1e-8, hi)
    print("[归一化] 参数仅在训练集拟合")

    X_train, X_test = finalize(X_train_raw, lo, hi), finalize(X_raw[te], lo, hi)
    y_test = y_all[te]
    print(f"[窗口] 训练 {X_train.shape} | 测试 {X_test.shape}")
    for tag, yy in (("训练", y_train), ("测试", y_test)):
        print(f"       {tag}标签分布: " + ", ".join(
            f"{STAGE_NAMES[k]}={int((yy == k).sum())}" for k in range(N_CLASSES)))

    X_check, y_check = None, None
    if df_check is not None and len(df_check) >= args.window:
        Xc, yc = raw_windows(df_check, args.window, args.stride)
        if Xc is not None and len(Xc):
            X_check, y_check = finalize(Xc, lo, hi), yc
            print(f"[抽查] 独立抽查窗口 {X_check.shape} | 分布: " + ", ".join(
                f"{STAGE_NAMES[k]}={int((y_check == k).sum())}" for k in range(N_CLASSES)))

    os.makedirs("data", exist_ok=True)
    save_kwargs = dict(
        X_train=X_train, X_test=X_test, y_train=y_train, y_test=y_test,
        norm_lo=lo, norm_hi=hi,
        feature_names=np.array(FEATURES + DELTA_FEATURES),
        feat_sign=FEAT_SIGN,
        stage_names=np.array(STAGE_NAMES),
        window=args.window, label_source=np.array(label_source), source=np.array(source),
    )
    if X_check is not None:
        save_kwargs["X_check"] = X_check
        save_kwargs["y_check"] = y_check
    np.savez_compressed("data/processed.npz", **save_kwargs)
    meta = {"source": source, "label_source": label_source, "n_sessions": n_sess,
            "window": args.window, "stride": args.stride, "split": split_desc,
            "split_mode": args.split,
            "train": int(len(X_train)), "test": int(len(X_test)),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    if X_check is not None:
        meta["check"] = {"desc": check_desc, "n": int(len(y_check)),
                         "dist": {STAGE_NAMES[k]: int((y_check == k).sum()) for k in range(N_CLASSES)}}
    with open("data/processed_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print("已保存 → data/processed.npz + data/processed_meta.json")
    if label_source.startswith("pseudo"):
        print("\n警告: 当前为伪标签(循环论证), 模型仅用于管线验证, 不可作为科学结论。")


if __name__ == "__main__":
    main()
