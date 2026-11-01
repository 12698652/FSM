# -*- coding: utf-8 -*-
"""导出清洁空气参考基线数据集（原始 CSV + 逐通道统计摘要）。

默认导出一段稳定无事件的清洁空气基线，用于定义「正常值」参考范围：
    时间范围: 2026-10-01 17:00:00 ~ 23:00:00
    剔除尖峰: 直接取自 server/preprocess.py 的 SPIKE_WINDOWS（清洗规则唯一来源）

产出:
    data/baseline_clean_20261001.csv        原始逐条数据
    data/baseline_clean_20261001_stats.csv  逐通道统计摘要

用法:
    python data/export_baseline.py
    python data/export_baseline.py --start "2026-10-01 17:00:00" --end "2026-10-01 23:00:00"
    python data/export_baseline.py --prefix baseline_clean_20261002
    python data/export_baseline.py --exclude "2026-10-01 19:02:00" "2026-10-01 19:07:00"
    python data/export_baseline.py --no-exclude
"""
import argparse
import os
import sqlite3
import sys

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "server")
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from preprocess import SPIKE_WINDOWS  # 清洗规则唯一来源：server/preprocess.py

DEFAULT_DB = os.path.join(SCRIPT_DIR, "food.db")
DEFAULT_START = "2026-10-01 17:00:00"
DEFAULT_END = "2026-10-01 23:00:00"
DEFAULT_PREFIX = "baseline_clean_20261001"
CHANS = ["voc", "co2eq", "tvoc", "temperature", "humidity", "nh3_adc"]


def parse_args():
    p = argparse.ArgumentParser(description="导出清洁空气参考基线数据集")
    p.add_argument("--db", default=DEFAULT_DB, help="SQLite 数据库路径")
    p.add_argument("--start", default=DEFAULT_START, help="起始时间（含）")
    p.add_argument("--end", default=DEFAULT_END, help="结束时间（不含）")
    p.add_argument("--prefix", default=DEFAULT_PREFIX, help="输出文件名前缀")
    p.add_argument("--out-dir", default=SCRIPT_DIR, help="输出目录")
    p.add_argument("--exclude", nargs=2, action="append", metavar=("START", "END"),
                   help="额外剔除的尖峰时段，可重复；区间为 [START, END)")
    p.add_argument("--no-exclude", action="store_true", help="不剔除任何尖峰段")
    return p.parse_args()


def main():
    args = parse_args()

    spikes = []
    if not args.no_exclude:
        spikes = [tuple(x) for x in args.exclude] if args.exclude else list(SPIKE_WINDOWS)

    conn = sqlite3.connect(args.db)
    df = pd.read_sql_query("SELECT * FROM measurements ORDER BY timestamp ASC", conn)
    conn.close()

    ts = pd.to_datetime(df["timestamp"], errors="coerce")
    mask = (ts >= args.start) & (ts < args.end)
    for a, b in spikes:
        mask &= ~((ts >= a) & (ts < b))
    seg = df[mask].copy()[["timestamp"] + CHANS].reset_index(drop=True)

    if seg.empty:
        raise SystemExit(f"[错误] 该时间范围内无数据：{args.start} ~ {args.end}")

    out_raw = os.path.join(args.out_dir, f"{args.prefix}.csv")
    out_stats = os.path.join(args.out_dir, f"{args.prefix}_stats.csv")
    seg.to_csv(out_raw, index=False, encoding="utf-8-sig")

    rows = []
    for c in CHANS:
        s = pd.to_numeric(seg[c], errors="coerce")
        rows.append({
            "channel": c,
            "count": int(s.count()),
            "mean": round(float(s.mean()), 3),
            "std": round(float(s.std()), 3),
            "min": round(float(s.min()), 3),
            "p01": round(float(s.quantile(0.01)), 3),
            "p50": round(float(s.median()), 3),
            "p99": round(float(s.quantile(0.99)), 3),
            "max": round(float(s.max()), 3),
        })
    st = pd.DataFrame(rows)
    st.to_csv(out_stats, index=False, encoding="utf-8-sig")

    print(f"[导出] 清洁基线 {len(seg)} 条 -> {out_raw}")
    print(f"[导出] 统计摘要      -> {out_stats}")
    print(f"[范围] {seg['timestamp'].iloc[0]}  ->  {seg['timestamp'].iloc[-1]}")
    print(f"[剔除] 尖峰段 {len(spikes)} 个" if spikes else "[剔除] 无")
    print("\n=== 逐通道统计 ===")
    print(st.to_string(index=False))


if __name__ == "__main__":
    main()
