# -*- coding: utf-8 -*-
"""Web 可视化：实时数据看板（手机浏览器 / Tailscale 远程均可访问）
运行: python app.py  然后浏览器打开 http://<本机IP>:5000
"""
import sqlite3

from flask import Flask, jsonify, render_template, request

from config import DB_PATH, WEB_HOST, WEB_PORT

app = Flask(__name__)

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


if __name__ == "__main__":
    app.run(host=WEB_HOST, port=WEB_PORT, debug=False)
