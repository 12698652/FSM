# -*- coding: utf-8 -*-
"""Web 可视化：实时数据看板（手机浏览器 / Tailscale 远程均可访问）
运行: python app.py  然后浏览器打开 http://<本机IP>:5000
"""
import os
import sqlite3

from flask import Flask, jsonify, render_template, request

import audit
import experiments
from config import (CATEGORIES, DB_PATH, DEFAULT_PLAN_HOURS,
                    DEFAULT_SAMPLE_INTERVAL_S, PACKAGING_OPTIONS,
                    STORAGE_OPTIONS, WEB_HOST, WEB_PORT)

app = Flask(__name__)

try:
    _conn = experiments.connect(DB_PATH)
    _conn.close()
except Exception as e:      # 数据库只读/不存在时不阻塞看板启动
    print(f"[app] 样品台账初始化失败: {e}")

_predictor = None


def query(sql, args=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/latest")
def api_latest():
    """最新一条数据"""
    rows = query("SELECT * FROM measurements ORDER BY id DESC LIMIT 1")
    return jsonify(dict(rows[0])) if rows else jsonify({})


@app.route("/api/data")
def api_data():
    """最近 N 条数据（按时间正序返回，供图表使用）
    参数: limit=60（条数）、since_id=（起始 id，增量拉取）
    """
    limit = min(int(request.args.get("limit", 60)), 2000)
    since_id = request.args.get("since_id", type=int)
    if since_id is not None:
        rows = query("SELECT * FROM measurements WHERE id > ? ORDER BY id ASC LIMIT ?",
                     (since_id, limit))
    else:
        rows = query("SELECT * FROM (SELECT * FROM measurements ORDER BY id DESC LIMIT ?) "
                     "ORDER BY id ASC", (limit,))
    return jsonify([dict(r) for r in rows])


@app.route("/api/history")
def api_history():
    """时间范围查询（回放模式数据源）
    参数: from=YYYY-MM-DD HH:MM:SS、to=...、limit=5000
    返回该范围内按时间正序的数据（最多 limit 条，均匀不足时全返回）
    """
    limit = min(int(request.args.get("limit", 5000)), 20000)
    t_from = request.args.get("from")
    t_to = request.args.get("to")
    if not t_from:
        return jsonify({"error": "缺少 from 参数"}), 400
    sql = "SELECT * FROM measurements WHERE timestamp >= ?"
    args = [t_from]
    if t_to:
        sql += " AND timestamp <= ?"
        args.append(t_to)
    sql += " ORDER BY timestamp ASC LIMIT ?"
    args.append(limit)
    rows = query(sql, tuple(args))
    return jsonify([dict(r) for r in rows])


@app.route("/api/range")
def api_range():
    """数据库时间范围概览（回放模式选段用）"""
    rows = query("SELECT MIN(timestamp) AS t_min, MAX(timestamp) AS t_max, COUNT(*) AS n FROM measurements")
    return jsonify(dict(rows[0]))


@app.route("/api/predict")
def api_predict():
    """对最近 window 条数据做腐败阶段预测（模型为 ONNX 轻量推理）
    返回: {ready, stage, stage_name, probs, label_source, window}
    """
    global _predictor
    if _predictor is None:
        try:
            from inference import StagePredictor
            _predictor = StagePredictor()
        except Exception as e:
            return jsonify({"ready": False, "error": f"模型加载失败: {e}"})
    w = _predictor.window
    rows = query("SELECT id, voc, co2eq, tvoc, temperature, humidity, nh3_adc "
                 "FROM (SELECT * FROM measurements ORDER BY id DESC LIMIT ?) "
                 "ORDER BY id ASC", (w,))
    return jsonify(_predictor.predict([dict(r) for r in rows]))


# ===== 样品台账（实验编排）=====
def _samples_context(**extra):
    ctx = dict(categories=CATEGORIES, packagings=PACKAGING_OPTIONS,
               storages=STORAGE_OPTIONS, default_hours=DEFAULT_PLAN_HOURS,
               default_interval=DEFAULT_SAMPLE_INTERVAL_S, code="")
    ctx.update(extra)
    return ctx


@app.route("/samples")
def samples_page():
    """样品台账：进行中的样品 + 新建表单 + 历史列表"""
    return render_template("samples.html", **_samples_context())


@app.route("/s/<code>")
def sample_scan(code):
    """扫码落地页：手机上打开即填品类、开始采集（编号已存在时提交会返回 409）"""
    return render_template("samples.html", **_samples_context(code=code))


@app.route("/api/samples")
def api_samples():
    conn = experiments.connect()
    try:
        rows = experiments.list_samples(conn, limit=min(int(request.args.get("limit", 200)), 1000))
        return jsonify([experiments.to_dict(r) for r in rows])
    finally:
        conn.close()


@app.route("/api/samples", methods=["POST"])
def api_sample_create():
    data = request.get_json(silent=True) or request.form.to_dict()
    if not (data.get("code") or "").strip():
        return jsonify({"error": "样品编号不能为空"}), 400
    if not (data.get("category") or "").strip():
        return jsonify({"error": "品类不能为空"}), 400
    conn = experiments.connect()
    try:
        row = experiments.create_sample(
            conn, code=data.get("code"), category=data.get("category"),
            batch=data.get("batch") or None, packaging=data.get("packaging") or None,
            storage=data.get("storage") or None,
            plan_hours=data.get("plan_hours") or None,
            interval_s=data.get("interval_s") or None,
            note=data.get("note") or None)
        return jsonify(experiments.to_dict(row)), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 409
    finally:
        conn.close()


@app.route("/api/samples/<int:sid>/stop", methods=["POST"])
def api_sample_stop(sid):
    data = request.get_json(silent=True) or {}
    aborted = bool(data.get("aborted"))
    conn = experiments.connect()
    try:
        row = experiments.stop_sample(conn, sid=sid, aborted=aborted)
        payload = experiments.to_dict(row)
        if not aborted:
            # 每场采集结束自动出一份质量报告并写入剔除标记
            try:
                path, stats = audit.audit_sample(conn, row)
                payload["quality"] = {"report": os.path.basename(path),
                                      "valid_pct": round(stats["valid_pct"], 1),
                                      "gap_count": stats["gap_count"],
                                      "error_points": stats["error_points"]}
            except Exception as e:       # 审计失败不影响结束采集
                payload["quality"] = {"error": str(e)}
        return jsonify(payload)
    except ValueError as e:
        return jsonify({"error": str(e)}), 409
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(host=WEB_HOST, port=WEB_PORT, debug=False)
