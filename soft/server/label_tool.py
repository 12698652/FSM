# -*- coding: utf-8 -*-
"""真实标签采集助手：生成待填模板 / 校验 labels.csv / 查看数据范围

背景
----
preprocess.py 只认 data/labels.csv。若该文件缺失或覆盖不足，会自动降级为
NH₃ 阈值伪标签（属循环论证，仅供演示）。本工具帮你把「真实标签」这条线走通：
  1. status 看数据库时间范围，确定去哪里取样
  2. new    按实测采样时间生成待填模板（时间点已对齐，填起来快）
  3. check  校验 labels.csv：格式、覆盖率、阶段分布，避免训练时被静默降级

用法（在项目根目录 soft/ 下执行）
----
  python server/label_tool.py status
  python server/label_tool.py new --hours 72 --every 4
  python server/label_tool.py check

字段说明
----
  timestamp : 该阶段开始的时间（与数据库采样时间对齐，merge_asof 向后匹配）
  stage     : 0=Fresh 新鲜 / 1=Warning 预警 / 2=Slight 轻微变质 / 3=Spoiled 腐坏（填了它就以它为准）
  tvb_n     : TVB-N 实测值 mg/100g（未填 stage 时，由阈值自动分级）
  ph        : pH 实测值
  note      : 备注（正式训练前请删除含「示例」字样的行）
"""
import argparse
import os
import sqlite3
import sys
from datetime import timedelta

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (BASE_DIR, DB_PATH, DEMO_BEFORE, LABELS_PATH,
                    TVBN_FRESH_MAX, TVBN_SLIGHT_MAX, TVBN_WARNING_MAX)
from preprocess import WINDOW_SIZE

STAGE_NAMES = {0: "Fresh(新鲜)", 1: "Warning(预警)",
               2: "Slight(轻微变质)", 3: "Spoiled(腐坏)"}
WORK_PATH = os.path.join(BASE_DIR, "data", "labels_work.csv")


def load_readings():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT timestamp FROM measurements ORDER BY timestamp ASC", conn)
    conn.close()
    return df


def cmd_status(_args):
    print(f"数据库: {DB_PATH}")
    df = load_readings()
    if df.empty:
        print("数据库暂无数据")
        return
    ts = pd.to_datetime(df["timestamp"])
    demo = df[ts < DEMO_BEFORE]
    real = df[ts >= DEMO_BEFORE]
    print(f"总记录 {len(df)} 条 | 时间范围 {df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]}")
    print(f"模拟(演示)数据 {len(demo)} 条 | 实测数据 {len(real)} 条 (DEMO_BEFORE={DEMO_BEFORE})")
    if len(real):
        print(f"实测范围 {real['timestamp'].iloc[0]} ~ {real['timestamp'].iloc[-1]}")
    if os.path.exists(LABELS_PATH):
        lab = pd.read_csv(LABELS_PATH, encoding="utf-8-sig").dropna(how="all")
        print(f"标签文件 {LABELS_PATH}: {len(lab)} 行")
    else:
        print(f"标签文件 {LABELS_PATH}: 不存在")


def _align_to_samples(real_ts, end, step, n):
    picked = []
    for i in range(n, -1, -1):
        t = end - step * i
        idx = int(real_ts.searchsorted(t, side="right")) - 1
        if idx >= 0:
            picked.append(real_ts.iloc[idx])
    return sorted(set(picked))


def cmd_new(args):
    df = load_readings()
    ts = pd.to_datetime(df["timestamp"])
    real = df[ts >= DEMO_BEFORE].reset_index(drop=True)
    if real.empty:
        raise SystemExit(f"暂无实测数据(>= {DEMO_BEFORE})，无法生成模板")
    real_ts = pd.to_datetime(real["timestamp"])
    end = real_ts.iloc[-1]
    step = timedelta(hours=args.every)
    n = max(1, int(args.hours // args.every))
    picked = _align_to_samples(real_ts, end, step, n)

    out = pd.DataFrame({
        "timestamp": [p.strftime("%Y-%m-%d %H:%M:%S") for p in picked],
        "stage": "", "tvb_n": "", "ph": "", "note": "",
    })
    os.makedirs(os.path.dirname(WORK_PATH), exist_ok=True)
    out.to_csv(WORK_PATH, index=False, encoding="utf-8-sig")
    print(f"已生成待填模板 → {WORK_PATH}（{len(out)} 行，时间点已按实测采样对齐）")
    print("填法: stage 填 0/1/2/3（0=新鲜 1=预警 2=轻微变质 3=腐坏）；或只填 tvb_n 由阈值自动分级")
    print(f"      TVB-N 阈值: <{TVBN_FRESH_MAX} 新鲜 / {TVBN_FRESH_MAX}~{TVBN_WARNING_MAX} 预警 / "
          f"{TVBN_WARNING_MAX}~{TVBN_SLIGHT_MAX} 轻微变质 / >= {TVBN_SLIGHT_MAX} 腐坏")
    print("填好后另存为 data/labels.csv，再执行: python server/label_tool.py check")


def cmd_from_samples(args):
    """按样品台账生成待填标注模板：一个样品一段，整段确认阶段变化
    与 new 的区别：模板行自带 sample_id / category，可直接按样品回溯实验条件，
    不再依赖 preprocess 里硬编码的时间段。
    """
    from datetime import datetime

    from experiments import TS_FMT, connect as exp_connect, list_samples

    conn = exp_connect(DB_PATH)
    rows = list(list_samples(conn, limit=args.limit))[::-1]   # 按开始时间正序
    conn.close()
    if not rows:
        raise SystemExit("暂无样品记录：先用 python server/experiments.py new "
                         "或网页 /samples 新建样品")

    now = datetime.now()
    step = timedelta(hours=args.every)
    out = []
    for r in rows:
        if r["status"] == "aborted":
            continue
        t = datetime.strptime(r["start_ts"], TS_FMT)
        end = datetime.strptime(r["end_ts"], TS_FMT) if r["end_ts"] else now
        while t <= end:
            out.append({
                "sample_id": r["id"],
                "sample_code": r["code"],
                "category": r["category"],
                "timestamp": t.strftime(TS_FMT),
                "stage": "", "tvb_n": "", "ph": "", "note": "",
            })
            t += step

    df = pd.DataFrame(out, columns=["sample_id", "sample_code", "category",
                                    "timestamp", "stage", "tvb_n", "ph", "note"])
    os.makedirs(os.path.dirname(WORK_PATH), exist_ok=True)
    df.to_csv(WORK_PATH, index=False, encoding="utf-8-sig")
    n_samples = df["sample_id"].nunique()
    print(f"已生成待填模板 → {WORK_PATH}（{n_samples} 个样品 / {len(df)} 行）")
    print("填法: 同一段样品内，找出阶段切换的时间点，填 stage=0/1/2/3 "
          "（0=新鲜 1=预警 2=轻微变质 3=腐坏）；阶段不变的相邻行留空即可，"
          "preprocess 会按「向后填充」沿用上一阶段")
    print("填好后另存为 data/labels.csv，再执行: python server/label_tool.py check")


def cmd_check(_args):
    print(f"数据库: {DB_PATH}")
    df = load_readings()
    ts = pd.to_datetime(df["timestamp"])
    real_mask = ts >= DEMO_BEFORE
    n_real = int(real_mask.sum())
    print(f"实测数据(>= {DEMO_BEFORE}): {n_real} 条")

    # 样品归属统计：新流程下每条数据都带 sample_id，先确认归属没断
    try:
        conn = sqlite3.connect(DB_PATH)
        stats = conn.execute(
            "SELECT e.code, e.category, e.status, COUNT(m.id) FROM experiments e "
            "LEFT JOIN measurements m ON m.sample_id = e.id "
            "GROUP BY e.id ORDER BY e.start_ts DESC").fetchall()
        unassigned = conn.execute(
            "SELECT COUNT(*) FROM measurements WHERE sample_id IS NULL").fetchone()[0]
        conn.close()
        if stats:
            print("样品归属:")
            for code, cat, status, n in stats:
                print(f"  {code:<14} {cat:<6} {status:<8} {n:>6} 条")
            print(f"  未归属(旧数据/空舱) {unassigned} 条")
        else:
            print("样品归属: 台账为空（旧流程，按时间间隔切场次）")
    except sqlite3.Error as e:
        print(f"样品归属: 读取失败（{e}）")

    if not os.path.exists(LABELS_PATH):
        print(f"\n[未就绪] 找不到 {LABELS_PATH}")
        print("下一步: python server/label_tool.py new   生成待填模板")
        return
    raw = pd.read_csv(LABELS_PATH, encoding="utf-8-sig").dropna(how="all")
    print(f"标签文件 {LABELS_PATH}: {len(raw)} 行")
    if len(raw) == 0:
        print("\n[未就绪] 标签文件为空（仅表头）")
        print("下一步: 填入真实标签，或先 python server/label_tool.py new 生成模板")
        return

    if "note" in raw.columns:
        demo_rows = raw[raw["note"].astype(str).str.contains("示例", na=False)]
        if len(demo_rows):
            print(f"[提示] 检测到 {len(demo_rows)} 行含「示例」字样，正式训练前请删除")

    from preprocess import load_labels
    lab = load_labels()
    if lab is None:
        print("\n[未就绪] 无有效标签行（timestamp 或 stage / tvb_n 均无法解析）")
        return

    sub = df[real_mask].copy()
    sub["timestamp_dt"] = pd.to_datetime(sub["timestamp"])
    merged = pd.merge_asof(
        sub.sort_values("timestamp_dt"),
        lab.rename(columns={"timestamp": "timestamp_dt"}).sort_values("timestamp_dt"),
        on="timestamp_dt", direction="backward")
    cover = int(merged["stage"].notna().sum())
    pct = cover / n_real * 100 if n_real else 0.0
    print(f"标签覆盖: {cover}/{n_real} 条实测数据 ({pct:.1f}%)")

    dist = merged["stage"].dropna().astype(int).value_counts().sort_index()
    print("阶段分布: " + ", ".join(f"{STAGE_NAMES.get(int(k), k)}={int(v)}" for k, v in dist.items()))

    need = WINDOW_SIZE + 10
    if cover < need:
        print(f"\n[未就绪] 覆盖率不足（需要 >= {need} 条），preprocess 会降级为伪标签")
        return
    if dist.shape[0] < 2:
        print("\n[注意] 当前只有 1 个阶段，无法训练多分类模型（需至少 2 个阶段）")
        return
    print("\n[就绪] 标签可用。下一步: python server/retrain.py")


def main():
    ap = argparse.ArgumentParser(description="真实标签采集助手")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="查看数据库时间范围与标签文件状态")
    p_new = sub.add_parser("new", help="生成待填标签模板（按时间点，旧方式）")
    p_new.add_argument("--hours", type=int, default=72, help="回溯小时数（默认 72）")
    p_new.add_argument("--every", type=int, default=4, help="采样间隔小时（默认 4）")
    p_fs = sub.add_parser("from-samples", help="按样品台账生成待填模板（推荐，带 sample_id）")
    p_fs.add_argument("--every", type=int, default=4, help="采样间隔小时（默认 4）")
    p_fs.add_argument("--limit", type=int, default=200, help="最多包含多少个样品")
    sub.add_parser("check", help="校验 data/labels.csv")
    args = ap.parse_args()
    {"status": cmd_status, "new": cmd_new, "from-samples": cmd_from_samples,
     "check": cmd_check}[args.cmd](args)


if __name__ == "__main__":
    main()
