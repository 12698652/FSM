# -*- coding: utf-8 -*-
"""实验编排器：样品台账（建样 / 结束 / 编号打印 / 查询）

为什么需要它
------------
旧流程靠两条「时间魔法」维持：
  1. preprocess.detect_sessions()：只有采样间隔 > SESSION_GAP_MIN 才切新场次，
     样品衔接紧凑时会被并成同一场次，按场次切分训练/测试就失真；
  2. preprocess 里硬编码的 EMPTY_CHAMBER / SPIKE_WINDOWS / BASELINE_WINDOWS /
     FIRMWARE_TRANSITION / UNLABELED_GAP：靠人工回忆维护，写错就把脏段喂进训练。

新流程把「哪个样品、什么存放条件、何时开始与结束」落库（experiments 表），
采集桥逐条把 sample_id 打到 measurements 上，事后按样品取数、按样品出标注模板。

表结构
------
experiments(id, code, category, batch, packaging, storage, plan_hours,
            interval_s, start_ts, end_ts, status, note, created_at)
  status: running 采集中 / done 已结束 / aborted 作废（训练时按需剔除）
measurements 新增列 sample_id（历史数据为 NULL，不影响已有训练）

用法（在 soft/ 目录执行）
------------------------
  python server/experiments.py new --code PORK-A-001 --category 猪肉 --batch B1
  python server/experiments.py list
  python server/experiments.py stop --code PORK-A-001
  python server/experiments.py codes --prefix PORK --n 3 --base-url http://主机/gjn
"""
import argparse
import os
import sqlite3
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (DEFAULT_PLAN_HOURS, DEFAULT_SAMPLE_INTERVAL_S, DB_PATH,
                    SAMPLE_BASE_URL)

TS_FMT = "%Y-%m-%d %H:%M:%S"

EXPERIMENTS_DDL = """CREATE TABLE IF NOT EXISTS experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,        -- 样品编号（贴在样品/气室上，扫码用）
    category TEXT NOT NULL,           -- 品类：猪肉/牛肉/牛奶/面包/熟鸡蛋…
    batch TEXT,                       -- 批次号
    packaging TEXT,                   -- 包装：敞口/保鲜膜/真空/原包装
    storage TEXT,                     -- 存放条件：常温25℃/冷藏4℃/冷冻-18℃
    plan_hours REAL,                  -- 计划采集时长(h)
    interval_s INTEGER,               -- 采样间隔(s)，仅台账记录，固件另有实现
    start_ts DATETIME NOT NULL,       -- 开始时间（数据归属起点）
    end_ts DATETIME,                   -- 结束时间（NULL 表示仍在采集）
    status TEXT DEFAULT 'running',    -- running / done / aborted
    note TEXT,
    created_at DATETIME
)"""


def now_ts():
    return datetime.now().strftime(TS_FMT)


def connect(path=None):
    """连接数据库并保证表结构存在（只读调用也可安全复用）"""
    conn = sqlite3.connect(path or DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    return conn


def ensure_schema(conn):
    """建 experiments 表；给 measurements 补 sample_id 列（幂等，可重复调用）"""
    conn.row_factory = sqlite3.Row      # 统一行访问方式（外部传入的 conn 也一并生效）
    conn.execute(EXPERIMENTS_DDL)
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")]
    if "measurements" in tables:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(measurements)")]
        if "sample_id" not in cols:
            conn.execute("ALTER TABLE measurements ADD COLUMN sample_id INTEGER")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_m_sample ON measurements(sample_id)")
            print("[schema] measurements 已新增 sample_id 列（历史数据保持 NULL）")
    conn.commit()


def active_sample(conn, ts=None):
    """返回当前处于采集窗口内的样品行（没有则 None）
    ts 必须传服务器本地时间字符串，与 mqtt_bridge 入库口径一致
    """
    ts = ts or now_ts()
    return conn.execute(
        "SELECT * FROM experiments WHERE status='running' AND start_ts <= ? "
        "AND (end_ts IS NULL OR end_ts >= ?) ORDER BY start_ts DESC LIMIT 1",
        (ts, ts)).fetchone()


def active_sample_id(conn, ts=None):
    row = active_sample(conn, ts)
    return row["id"] if row else None


def get_sample(conn, code=None, sid=None):
    if code is not None:
        return conn.execute("SELECT * FROM experiments WHERE code=?", (code,)).fetchone()
    return conn.execute("SELECT * FROM experiments WHERE id=?", (sid,)).fetchone()


def list_samples(conn, limit=200):
    return conn.execute(
        "SELECT * FROM experiments ORDER BY start_ts DESC LIMIT ?", (limit,)).fetchall()


def create_sample(conn, code, category, batch=None, packaging=None, storage=None,
                  plan_hours=None, interval_s=None, note=None, start=True,
                  start_ts=None):
    """新建样品；start=True 表示立即开始采集（同一时间只允许一个 running 样品）
    返回新建的行；参数非法或冲突抛 ValueError（由 Web 层转 409/400）
    """
    code = (code or "").strip()
    category = (category or "").strip()
    if not code:
        raise ValueError("样品编号不能为空")
    if not category:
        raise ValueError("品类不能为空")
    if conn.execute("SELECT 1 FROM experiments WHERE code=?", (code,)).fetchone():
        raise ValueError(f"样品编号已存在: {code}")
    running = conn.execute(
        "SELECT code FROM experiments WHERE status='running'").fetchone()
    if start and running:
        raise ValueError(f"已有样品在采集中({running['code']})，请先结束它")

    start_ts = start_ts or now_ts()
    cur = conn.execute(
        "INSERT INTO experiments (code, category, batch, packaging, storage, plan_hours,"
        " interval_s, start_ts, end_ts, status, note, created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (code, category, batch, packaging, storage,
         float(plan_hours) if plan_hours else DEFAULT_PLAN_HOURS,
         int(interval_s) if interval_s else DEFAULT_SAMPLE_INTERVAL_S,
         start_ts, None, "running" if start else "done", note, now_ts()))
    conn.commit()
    return get_sample(conn, sid=cur.lastrowid)


def stop_sample(conn, code=None, sid=None, end_ts=None, aborted=False):
    """结束样品采集：写 end_ts、状态置 done/aborted。返回更新后的行"""
    row = get_sample(conn, code=code, sid=sid)
    if row is None:
        raise ValueError("样品不存在")
    if row["status"] != "running":
        raise ValueError(f"样品 {row['code']} 当前状态为 {row['status']}，无需结束")
    conn.execute("UPDATE experiments SET end_ts=?, status=? WHERE id=?",
                 (end_ts or now_ts(), "aborted" if aborted else "done", row["id"]))
    conn.commit()
    return get_sample(conn, sid=row["id"])


def sample_span(row, ts=None):
    """样品实际数据窗口 (start, end)；未结束则 end 取当前时间"""
    end = row["end_ts"] or (ts or now_ts())
    return row["start_ts"], end


def to_dict(row):
    """样品行 → 可 JSON 化字典（补已运行时长 / 计划结束 / 是否超期）"""
    if row is None:
        return None
    d = dict(row)
    start, end = sample_span(row)
    d["hours"] = round((datetime.strptime(end, TS_FMT)
                        - datetime.strptime(start, TS_FMT)).total_seconds() / 3600.0, 2)
    d["plan_end_ts"] = (
        (datetime.strptime(start, TS_FMT)
         + timedelta(hours=float(row["plan_hours"] or 0))).strftime(TS_FMT)
        if row["plan_hours"] else None)
    d["overdue"] = bool(row["status"] == "running" and d["plan_end_ts"]
                        and now_ts() > d["plan_end_ts"])
    return d


def _fmt_row(row):
    start, end = sample_span(row)
    t0 = datetime.strptime(start, TS_FMT)
    t1 = datetime.strptime(end, TS_FMT)
    hours = (t1 - t0).total_seconds() / 3600.0
    flag = "采集中" if row["status"] == "running" else row["status"]
    print(f"{row['code']:<14} {row['category']:<6} {row['batch'] or '-':<8} "
          f"{row['storage'] or '-':<10} {start} → {row['end_ts'] or '(进行中)':<20} "
          f"{hours:5.1f}h  {flag}")


def cmd_new(args):
    conn = connect()
    row = create_sample(conn, code=args.code, category=args.category, batch=args.batch,
                        packaging=args.packaging, storage=args.storage,
                        plan_hours=args.hours, interval_s=args.interval,
                        note=args.note, start=True, start_ts=args.start)
    print(f"[已开始采集] id={row['id']}")
    _fmt_row(row)
    print(f"扫码链接: {args.base_url}/s/{row['code']}" if args.base_url
          else f"扫码链接: <base>/s/{row['code']}（用 --base-url 或环境变量 SAMPLE_BASE_URL 指定前缀）")


def cmd_list(args):
    conn = connect()
    rows = list_samples(conn, limit=args.limit)
    if not rows:
        print("暂无样品记录")
        return
    print(f"{'编号':<14} {'品类':<6} {'批次':<8} {'存放':<10} {'开始':<20} 窗口 / 时长 / 状态")
    for r in rows:
        _fmt_row(r)


def cmd_stop(args):
    conn = connect()
    row = stop_sample(conn, code=args.code, sid=args.id, aborted=args.abort)
    print(f"[已结束] {row['code']} → {row['end_ts']} ({row['status']})")
    _fmt_row(row)
    if not args.abort:
        try:
            import audit
            path, stats = audit.audit_sample(conn, row)
            print(f"[质量报告] {path}")
            print(f"           有效率 {stats['valid_pct']:.1f}% | 断点 {stats['gap_count']} | "
                  f"剔除点 {stats['error_points']}")
        except Exception as e:
            print(f"[质量报告] 生成失败: {e}")
    conn.close()


def cmd_codes(args):
    """批量打印待贴编号的扫码链接（打印后贴在样品/气室上）"""
    base = (args.base_url or SAMPLE_BASE_URL).rstrip("/")
    codes = [f"{args.prefix}-{i + 1:03d}" for i in range(args.n)]
    for c in codes:
        print(f"{c}\t{base}/s/{c}" if base else f"{c}\t<base>/s/{c}")
    print("\n提示: 用任意二维码工具把右侧链接生成二维码打印；扫码打开网页填品类即开始采集")
    if not base:
        print("      建议加 --base-url，或在 config.py 设置 SAMPLE_BASE_URL")


def main():
    ap = argparse.ArgumentParser(description="实验编排器 / 样品台账")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("new", help="新建并开始一个样品采集")
    p.add_argument("--code", required=True, help="样品编号，如 PORK-A-001")
    p.add_argument("--category", required=True, help="品类，如 猪肉")
    p.add_argument("--batch", help="批次号")
    p.add_argument("--packaging", help="包装：敞口/保鲜膜/真空包装/原包装")
    p.add_argument("--storage", help="存放条件：常温25℃/冷藏4℃/冷冻-18℃")
    p.add_argument("--hours", type=float, help=f"计划时长(h)，默认 {DEFAULT_PLAN_HOURS}")
    p.add_argument("--interval", type=int, help=f"采样间隔(s)，默认 {DEFAULT_SAMPLE_INTERVAL_S}")
    p.add_argument("--note", help="备注")
    p.add_argument("--start", help="开始时间，默认当前时间")
    p.add_argument("--base-url", help="扫码链接前缀，如 http://主机/gjn")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("list", help="查看样品台账")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("stop", help="结束样品采集")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--code", help="样品编号")
    g.add_argument("--id", type=int, help="样品 id")
    p.add_argument("--abort", action="store_true", help="标记为作废（aborted），训练时剔除")
    p.set_defaults(func=cmd_stop)

    p = sub.add_parser("codes", help="批量打印扫码链接（编号需自行贴到样品上）")
    p.add_argument("--prefix", required=True, help="编号前缀，如 PORK / BEEF / MILK")
    p.add_argument("--n", type=int, default=3, help="生成数量")
    p.add_argument("--base-url", help="链接前缀，如 http://主机/gjn")
    p.set_defaults(func=cmd_codes)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
