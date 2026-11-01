# -*- coding: utf-8 -*-
"""数据质量自动审计：采完立刻出报告，训练前按标记自动剔除异常段

检测项
------
  adc_saturation  NH₃ 通道打满(≥4090) —— 气室饱和/接线错，连续 ≥3 点判异常
  adc_zero        NH₃ 读数恒为 0 —— 传感器断线/未供电
  frozen          通道长时间完全不变 —— 传感器卡死（默认检查 nh3_adc / voc）
  spike           单点跳变超过「绝对阈值 + 8 倍中位差」—— 人员靠近/静电/重启瞬态
  gap             采样间隔超过 3 倍标称间隔且 ≥180s —— 掉线/断采
  ts_dup / ts_neg 时间戳重复 / 倒序 —— 入库异常
  env_range       温度或湿度超出物理范围 —— BME 读数异常
  humi_stuck      湿度长期卡在 ≈100% —— BME 常见故障（冷凝/结露）
  sgp_sat         co2eq / tvoc 打满 59990 —— SGP30 量程上限

severity：error 参与剔除（训练时会自动过滤）；warn 只记录不剔除

产出
----
  1. data/quality/<样品编号或区间>_quality.md  人工复核用报告
  2. quality_flags 表（同库）供 preprocess 自动读取剔除

用法（在 soft/ 目录执行）
------------------------
  python server/audit.py --running                    # 审计正在采集的样品
  python server/audit.py --code PORK-A-001            # 审计指定样品（结束时会自动跑）
  python server/audit.py --from "2026-10-02" --to "2026-10-05"   # 按时间段审计历史数据
  python server/audit.py --all --no-write             # 只看报告，不写标记
"""
import argparse
import os
import sqlite3
import sys
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import BASE_DIR, DB_PATH

TS_FMT = "%Y-%m-%d %H:%M:%S"
QUALITY_DIR = os.path.join(BASE_DIR, "data", "quality")

# ===== 判定阈值（改这里即可，不散落在逻辑里）=====
ADC_FULL = 4095
ADC_SAT = 4090                  # 高于此视为接近饱和
ADC_SAT_MIN_RUN = 3             # 连续点数
ADC_ZERO_MIN_RUN = 3
FREEZE_MIN_RUN = 20             # 连续 20 点完全不变（60s 采样≈20 分钟；实测数据最长 18 点）
FREEZE_CHANNELS = ("nh3_adc", "voc")   # co2eq/tvoc 在洁净空气下天然恒定，不做卡死判定
SPIKE_ABS = 300                 # 相邻两点 NH₃ 跳变的绝对下限
SPIKE_MAD_K = 8.0               # 同时要求超过 8 倍中位差，避免把真实快速腐败当异常
GAP_FACTOR = 3.0                # 间隔超过标称的 3 倍
GAP_MIN_S = 180                 # 且至少 180s 才算断点
TEMP_RANGE = (-20.0, 60.0)
HUMI_RANGE = (0.0, 100.0)
HUMI_STUCK_MAX = 99.5
HUMI_STUCK_MIN_RUN = 10
SGP_SAT = 59990

FLAGS_DDL = """CREATE TABLE IF NOT EXISTS quality_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_id INTEGER,
    kind TEXT,                -- 检测项标识
    channel TEXT,             -- 涉及通道
    severity TEXT,            -- error 剔除 / warn 仅记录
    start_ts DATETIME,
    end_ts DATETIME,
    n_points INTEGER,
    detail TEXT,
    created_at DATETIME
)"""

SEVERITY_CN = {"error": "剔除", "warn": "记录"}


def ensure_tables(conn):
    conn.execute(FLAGS_DDL)
    conn.commit()


def _runs(mask, min_len):
    """返回连续 True 段的 (start_idx, end_idx) 列表（含首尾）"""
    out, start = [], None
    m = np.asarray(mask, dtype=bool)
    for i, v in enumerate(m):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= min_len:
                out.append((start, i - 1))
            start = None
    if start is not None and len(m) - start >= min_len:
        out.append((start, len(m) - 1))
    return out


def _flag(kind, channel, severity, start, end, n, detail):
    return {"kind": kind, "channel": channel, "severity": severity,
            "start_ts": start, "end_ts": end, "n_points": int(n), "detail": detail}


def detect(df, interval_s=None):
    """对一段测量数据做全项检测，返回 (flags, stats)"""
    total = len(df)
    if total == 0:
        return [], {"n": 0, "nominal": float(interval_s or 60), "gap_thr": 0.0,
                    "gap_count": 0, "longest_gap": 0.0, "missing_s": 0.0,
                    "dup": 0, "neg": 0, "error_points": 0, "valid_points": 0,
                    "valid_pct": 0.0, "ranges": {}}

    ts = pd.to_datetime(df["timestamp"], errors="coerce")
    dt = ts.diff().dt.total_seconds()
    nominal = interval_s or (float(dt[dt.gt(0)].median()) if dt.notna().any() else 60.0)
    flags = []

    # ---- 采样间隔 / 时间戳 ----
    gap_thr = max(GAP_FACTOR * nominal, GAP_MIN_S)
    gaps = dt[dt.gt(gap_thr)]
    gap_count = int(len(gaps))
    longest_gap = float(gaps.max()) if gap_count else 0.0
    missing_s = float((gaps - nominal).sum()) if gap_count else 0.0
    if gap_count:
        # 断点逐条记录（用于报告定位；不逐点写库则合并）
        i = 1
        while i < total:
            if pd.notna(dt.iloc[i]) and dt.iloc[i] > gap_thr:
                flags.append(_flag("gap", "-", "warn", str(ts.iloc[i - 1]),
                                   str(ts.iloc[i]), 1,
                                   f"断采 {dt.iloc[i]:.0f}s（标称 {nominal:.0f}s）"))
            i += 1

    dup = int(ts.duplicated().sum())
    if dup:
        flags.append(_flag("ts_dup", "-", "warn", str(ts.iloc[0]), str(ts.iloc[0]), dup,
                           f"重复时间戳 {dup} 条（仅记录，不整段剔除）"))
    neg = int(dt.lt(0).sum())
    if neg:
        flags.append(_flag("ts_neg", "-", "warn", str(ts.iloc[0]), str(ts.iloc[0]), neg,
                           f"时间戳倒序 {neg} 处（设备时钟回拨，按 id 顺序入库）"))

    # ---- NH₃ 通道 ----
    nh3 = pd.to_numeric(df["nh3_adc"], errors="coerce")
    sat_runs = _runs(nh3.ge(ADC_SAT), ADC_SAT_MIN_RUN)
    for a, b in sat_runs:
        flags.append(_flag("adc_saturation", "nh3_adc", "error", str(ts.iloc[a]),
                           str(ts.iloc[b]), b - a + 1,
                           f"连续 {b - a + 1} 点 ≥{ADC_SAT}（满量程 {ADC_FULL}）"))
    zero_runs = _runs(nh3.eq(0), ADC_ZERO_MIN_RUN)
    for a, b in zero_runs:
        flags.append(_flag("adc_zero", "nh3_adc", "error", str(ts.iloc[a]), str(ts.iloc[b]),
                           b - a + 1, f"连续 {b - a + 1} 点恒为 0（疑似断线/未供电）"))

    # ---- 卡死（长时间完全不变）----
    for ch in FREEZE_CHANNELS:
        if ch not in df.columns:
            continue
        v = pd.to_numeric(df[ch], errors="coerce")
        same = v.eq(v.shift())
        for a, b in _runs(same, FREEZE_MIN_RUN):
            flags.append(_flag("frozen", ch, "error", str(ts.iloc[a - 1]), str(ts.iloc[b]),
                               b - a + 2, f"{ch} 连续 {b - a + 2} 点完全不变（传感器卡死）"))

    # ---- 跳变（绝对阈值 + 中位差双重条件）----
    dnh3 = nh3.diff().abs()
    mad = float(dnh3.dropna().median()) if dnh3.notna().any() else 0.0
    spike_thr = max(SPIKE_ABS, SPIKE_MAD_K * mad)
    bad_idx = np.zeros(total, dtype=bool)      # 已在饱和/恒零段内的点不再重复报跳变
    for a, b in sat_runs + zero_runs:
        bad_idx[a:b + 1] = True
    for i in np.flatnonzero(dnh3.gt(spike_thr).to_numpy()):
        a, b = max(int(i) - 1, 0), int(i)
        if bad_idx[a] and bad_idx[b]:
            continue
        flags.append(_flag("spike", "nh3_adc", "error", str(ts.iloc[a]), str(ts.iloc[b]),
                           b - a + 1, f"单步跳变 {dnh3.iloc[i]:.0f}（阈值 {spike_thr:.0f}）"))

    # ---- 温湿度 ----
    # 越界点按连续段记录（不能整段标记，否则会把整场数据都判为异常）
    if "temperature" in df.columns:
        t = pd.to_numeric(df["temperature"], errors="coerce")
        bad = t.lt(TEMP_RANGE[0]) | t.gt(TEMP_RANGE[1])
        for a, b in _runs(bad, 1):
            flags.append(_flag("env_range", "temperature", "error", str(ts.iloc[a]),
                               str(ts.iloc[b]), b - a + 1,
                               f"温度越界 {TEMP_RANGE}（实测 {t.iloc[a]:.1f}）"))
    if "humidity" in df.columns:
        h = pd.to_numeric(df["humidity"], errors="coerce")
        bad = h.lt(HUMI_RANGE[0]) | h.gt(HUMI_RANGE[1])
        for a, b in _runs(bad, 1):
            flags.append(_flag("env_range", "humidity", "error", str(ts.iloc[a]),
                               str(ts.iloc[b]), b - a + 1,
                               f"湿度越界 {HUMI_RANGE}（实测 {h.iloc[a]:.1f}）"))
        for a, b in _runs(h.ge(HUMI_STUCK_MAX), HUMI_STUCK_MIN_RUN):
            flags.append(_flag("humi_stuck", "humidity", "error", str(ts.iloc[a]),
                               str(ts.iloc[b]), b - a + 1,
                               f"湿度连续 {b - a + 1} 点≈100%（BME 结露/故障）"))

    # ---- SGP 通道打满 ----
    for ch in ("co2eq", "tvoc"):
        if ch not in df.columns:
            continue
        v = pd.to_numeric(df[ch], errors="coerce")
        for a, b in _runs(v.ge(SGP_SAT), 1):
            flags.append(_flag("sgp_sat", ch, "warn", str(ts.iloc[a]), str(ts.iloc[b]),
                               b - a + 1, f"{ch} 达量程上限 {SGP_SAT}（数值被截断）"))

    error_points = _count_error_points(flags, ts, total)
    stats = {
        "n": total, "nominal": nominal, "gap_thr": gap_thr, "gap_count": gap_count,
        "longest_gap": longest_gap, "missing_s": missing_s, "dup": dup, "neg": neg,
        "error_points": error_points, "valid_points": total - error_points,
        "valid_pct": (total - error_points) / total * 100 if total else 0.0,
        "ranges": {ch: (float(pd.to_numeric(df[ch], errors="coerce").min()),
                        float(pd.to_numeric(df[ch], errors="coerce").max()))
                   for ch in ("nh3_adc", "voc", "co2eq", "tvoc", "temperature", "humidity")
                   if ch in df.columns},
    }
    return flags, stats


def _count_error_points(flags, ts, total):
    """把 error 级标记落到具体采样点上，统计会被剔除的点数（去重）"""
    hit = np.zeros(total, dtype=bool)
    for f in flags:
        if f["severity"] != "error":
            continue
        hit |= (ts.ge(f["start_ts"]) & ts.le(f["end_ts"])).to_numpy()
    return int(hit.sum())


def _expected_points(stats, hours):
    if not hours or not stats.get("nominal"):
        return None
    return int(hours * 3600 / stats["nominal"]) + 1


def build_report(title, meta, flags, stats, hours=None):
    """生成 markdown 报告文本"""
    n = stats["n"]
    expected = _expected_points(stats, hours) if hours else None
    missing_pct = (1 - n / expected) * 100 if expected else None

    lines = [f"# 数据质量报告：{title}", ""]
    lines.append(f"- 生成时间：{datetime.now().strftime(TS_FMT)}")
    for k, v in meta.items():
        lines.append(f"- {k}：{v}")
    lines.append("")

    lines += ["## 总览", "", "| 指标 | 数值 |", "|---|---|"]
    lines.append(f"| 采样条数 | {n} |")
    if expected:
        lines.append(f"| 期望条数（按计划时长） | {expected} |")
        lines.append(f"| 缺口占比 | {missing_pct:.1f}% |")
    lines.append(f"| 标称间隔 | {stats['nominal']:.0f} s |")
    lines.append(f"| 合格点数 | {stats['valid_points']} |")
    lines.append(f"| **有效率** | **{stats['valid_pct']:.1f}%** |")
    lines.append(f"| 断点数 | {stats['gap_count']} |")
    lines.append(f"| 最长断点 | {stats['longest_gap']:.0f} s |")
    lines.append(f"| 累计缺失 | {stats['missing_s'] / 60:.1f} min |")
    lines.append(f"| 时间戳重复/倒序 | {stats['dup']} / {stats['neg']} |")
    lines.append("")

    r = stats["ranges"]
    lines += ["## 通道范围", "", "| 通道 | 最小 | 最大 |", "|---|---|---|"]
    for ch, (lo, hi) in r.items():
        lines.append(f"| {ch} | {lo:.2f} | {hi:.2f} |")
    lines.append("")

    lines += ["## 异常明细", ""]
    if not flags:
        lines += ["未检出异常。", ""]
    else:
        by_kind = {}
        for f in flags:
            by_kind.setdefault(f["kind"], []).append(f)
        lines += ["| 检测项 | 级别 | 通道 | 次数 | 涉及点数 | 说明 |", "|---|---|---|---|---|---|"]
        for kind, items in by_kind.items():
            n_pts = sum(i["n_points"] for i in items)
            sev = items[0]["severity"]
            if kind == "gap":   # 断点用聚合描述，避免只显示第一处
                detail = (f"{len(items)} 处，最长 {stats['longest_gap'] / 60:.1f} min，"
                          f"累计缺失 {stats['missing_s'] / 60:.1f} min")
            else:
                detail = items[0]["detail"]
            lines.append(f"| {kind} | {SEVERITY_CN[sev]} | {items[0]['channel']} | "
                         f"{len(items)} | {n_pts} | {detail} |")
        lines.append("")
        # 最多列 30 条最长的异常段，便于定位
        longest = sorted(flags, key=lambda f: f["n_points"], reverse=True)[:30]
        lines += ["### 异常段（按涉及点数排序，最多 30 条）", "",
                  "| 开始 | 结束 | 检测项 | 级别 | 点数 | 说明 |", "|---|---|---|---|---|---|"]
        for f in longest:
            lines.append(f"| {f['start_ts']} | {f['end_ts']} | {f['kind']} | "
                         f"{SEVERITY_CN[f['severity']]} | {f['n_points']} | {f['detail']} |")
        lines.append("")

    # ---- 结论 ----
    err_kinds = sorted({f["kind"] for f in flags if f["severity"] == "error"})
    lines += ["## 结论", ""]
    if n == 0:
        lines += ["- 判定：**无数据**（该样品窗口内没有任何采样点）",
                  "- 检查设备是否在线、MQTT 桥是否在运行、样品起止时间是否填错", ""]
        return "\n".join(lines)
    if stats["valid_pct"] >= 90 and stats["gap_count"] <= max(3, n * 0.02):
        verdict = "可用"
    elif stats["valid_pct"] >= 70:
        verdict = "需复查"
    else:
        verdict = "不可用，建议重采"
    lines.append(f"- 判定：**{verdict}**（有效率 {stats['valid_pct']:.1f}%）")
    if err_kinds:
        lines.append(f"- 已写入剔除标记：{', '.join(err_kinds)}"
                     f"（{stats['error_points']} 点，训练时自动过滤）")
    else:
        lines.append("- 无剔除级异常")
    if stats["gap_count"]:
        lines.append(f"- 断点 {stats['gap_count']} 处（最长 {stats['longest_gap'] / 60:.1f} min），"
                     "多为断电/掉网，不参与剔除但影响时间连续性，训练时按场次切分已能隔离")
    if stats["valid_pct"] < 90:
        lines.append("- 建议先看「异常段」表定位原因（气室饱和/传感器卡死/温湿度故障），"
                     "必要时重采该样品")
    lines.append("")
    return "\n".join(lines)


def load_range(conn, t_from=None, t_to=None, sample_id=None):
    sql = "SELECT * FROM measurements WHERE 1=1"
    args = []
    if t_from:
        sql += " AND timestamp >= ?"
        args.append(t_from)
    if t_to:
        sql += " AND timestamp <= ?"
        args.append(t_to)
    if sample_id is not None:
        sql += " AND sample_id = ?"
        args.append(sample_id)
    # 按入库顺序(id)读取：时间戳若被设备时钟回拨，只有按 id 才能看出倒序
    sql += " ORDER BY id ASC"
    return pd.read_sql_query(sql, conn, params=args)


def write_flags(conn, sample_id, flags):
    """写入标记：先清掉该样品旧标记，保证重复审计结果幂等"""
    ensure_tables(conn)
    if sample_id is not None:
        conn.execute("DELETE FROM quality_flags WHERE sample_id = ?", (sample_id,))
    for f in flags:
        conn.execute(
            "INSERT INTO quality_flags (sample_id, kind, channel, severity, start_ts, end_ts,"
            " n_points, detail, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (sample_id, f["kind"], f["channel"], f["severity"], f["start_ts"], f["end_ts"],
             f["n_points"], f["detail"], datetime.now().strftime(TS_FMT)))
    conn.commit()


def audit_frame(df, title, meta, hours=None):
    flags, stats = detect(df, meta.get("标称间隔(s)"))
    return flags, stats, build_report(title, meta, flags, stats, hours)


def audit_sample(conn, row, write=True, out_dir=QUALITY_DIR):
    """审计一个样品（experiments 行），返回 (报告路径, 统计)"""
    from experiments import to_dict

    d = to_dict(row)
    df = load_range(conn, d["start_ts"], d["end_ts"], sample_id=d["id"])
    # 采集窗口内也可能有少量未打标的行（桥重启），按时间窗兜底
    if df.empty:
        df = load_range(conn, d["start_ts"], d["end_ts"])
    meta = {"样品编号": d["code"], "品类": d["category"],
            "批次": d["batch"] or "-", "存放": d["storage"] or "-",
            "包装": d["packaging"] or "-",
            "采集窗口": f"{d['start_ts']} ~ {d['end_ts'] or '进行中'}",
            "标称间隔(s)": d["interval_s"]}
    flags, stats, report = audit_frame(df, d["code"], meta, hours=d["hours"])
    if write:
        write_flags(conn, d["id"], flags)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{d['code']}_quality.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
    return path, stats


def audit_by_code(code=None, sid=None, running=False, write=True):
    import experiments
    conn = experiments.connect(DB_PATH)
    try:
        if running:
            row = experiments.active_sample(conn)
        elif code:
            row = experiments.get_sample(conn, code=code)
        elif sid:
            row = experiments.get_sample(conn, sid=sid)
        else:
            raise SystemExit("请指定 --code / --id / --running")
        if row is None:
            raise SystemExit("找不到对应样品")
        return audit_sample(conn, row, write=write)
    finally:
        conn.close()


def audit_range(t_from, t_to=None, label=None, write=True):
    conn = sqlite3.connect(DB_PATH)
    ensure_tables(conn)
    df = load_range(conn, t_from, t_to)
    if df.empty:
        raise SystemExit("指定区间内没有数据")
    meta = {"区间": f"{t_from} ~ {t_to or '最新'}", "来源": DB_PATH}
    flags, stats, report = audit_frame(df, label or "区间审计", meta)
    if write:
        write_flags(conn, None, flags)      # sample_id=NULL：区间级标记
    os.makedirs(QUALITY_DIR, exist_ok=True)
    name = label or f"range_{pd.Timestamp(t_from).strftime('%Y%m%d_%H%M')}"
    path = os.path.join(QUALITY_DIR, f"{name}_quality.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
    conn.close()
    return path, stats


def main():
    ap = argparse.ArgumentParser(description="数据质量自动审计")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--code", help="样品编号")
    g.add_argument("--id", type=int, help="样品 id")
    g.add_argument("--running", action="store_true", help="审计当前正在采集的样品")
    g.add_argument("--from", dest="t_from", help="区间起点（配合 --to，审计历史数据）")
    g.add_argument("--all", action="store_true", help="审计全部样品（每个出一份报告）")
    ap.add_argument("--to", dest="t_to", help="区间终点")
    ap.add_argument("--no-write", action="store_true", help="只出报告，不写剔除标记")
    args = ap.parse_args()
    write = not args.no_write

    if args.t_from:
        path, stats = audit_range(args.t_from, args.t_to, write=write)
        print(f"报告: {path}")
        print(f"有效率 {stats['valid_pct']:.1f}% | 断点 {stats['gap_count']} | "
              f"剔除点 {stats['error_points']}")
        return

    import experiments
    if args.all:
        conn = experiments.connect(DB_PATH)
        rows = experiments.list_samples(conn, limit=500)
        for row in rows:
            path, stats = audit_sample(conn, row, write=write)
            print(f"{row['code']:<14} 有效率 {stats['valid_pct']:5.1f}%  "
                  f"断点 {stats['gap_count']:3d}  报告 {os.path.basename(path)}")
        conn.close()
        return

    path, stats = audit_by_code(code=args.code, sid=args.id, running=args.running, write=write)
    print(f"报告: {path}")
    print(f"有效率 {stats['valid_pct']:.1f}% | 断点 {stats['gap_count']} | "
          f"剔除点 {stats['error_points']}")


if __name__ == "__main__":
    main()
