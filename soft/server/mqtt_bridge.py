# -*- coding: utf-8 -*-
"""MQTT 接收桥：订阅巴法云主题 → 解析 JSON → 写入 SQLite + CSV
运行: python mqtt_bridge.py（需与 simulate_device.py 或 ESP32 配合）
"""
import json
import os
import sqlite3
import time
from datetime import datetime

import paho.mqtt.client as mqtt

from config import (CLIENT_ID_BRIDGE, CSV_PATH, DB_PATH, MQTT_APPID,
                    MQTT_HOST, MQTT_PORT, MQTT_SECRETKEY, TOPIC)
import experiments

CSV_HEADER = "timestamp,voc,co2eq,tvoc,temp,humi,nh3_adc"


def init_db():
    """初始化 SQLite 数据库（表结构与技术文档一致）"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME,
        voc FLOAT,
        co2eq INT,
        tvoc INT,
        temperature FLOAT,
        humidity FLOAT,
        nh3_adc INT)""")
    conn.commit()
    experiments.ensure_schema(conn)   # 样品台账表 + measurements.sample_id 列
    return conn


def save_row(conn, data):
    """一条传感器数据 → SQLite + CSV 双写
    入库时按当前采集窗口打 sample_id（无进行中样品则为 NULL）
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")   # 统一按服务器时间入库（忽略设备端时间戳）
    sample_id = experiments.active_sample_id(conn, ts)
    row = (ts, data.get("voc"), data.get("co2eq"), data.get("tvoc"),
           data.get("temp"), data.get("humi"), data.get("nh3_adc"))
    conn.execute(
        "INSERT INTO measurements (timestamp, voc, co2eq, tvoc, temperature, humidity, "
        "nh3_adc, sample_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", row + (sample_id,))
    conn.commit()

    # CSV 保持原表头（历史文件已是 7 列，加列会变乱）；sample_id 只在数据库中
    need_header = not os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", encoding="utf-8") as f:
        if need_header:
            f.write(CSV_HEADER + "\n")
        f.write(",".join("" if v is None else str(v) for v in row) + "\n")


def on_connect(client, userdata, flags, rc, properties=None):
    if rc.is_failure:
        print(f"[bridge] 连接失败: {rc}")
    else:
        print(f"[bridge] 已连接巴法云，订阅主题: {TOPIC}")
        client.subscribe(TOPIC)


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        print(f"[bridge] JSON 解析失败: {e} 原文: {msg.payload[:100]}")
        return
    try:
        save_row(userdata["conn"], data)
        print(f"[bridge] 入库: {data}")
    except Exception as e:
        print(f"[bridge] 入库失败: {e}")


def main():
    if "填入" in MQTT_APPID or "填入" in MQTT_SECRETKEY:
        print("[bridge] 错误: 请先在 config.py 中填入巴法云 appID 和 secretKey（方式二认证）")
        print("         获取路径: 巴法云控制台 → 连接密钥页面")
        return
    conn = init_db()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID_BRIDGE)
    client.username_pw_set(MQTT_APPID, MQTT_SECRETKEY)   # 方式二：与设备端身份隔离
    client.on_connect = on_connect
    client.on_message = on_message
    client.user_data_set({"conn": conn})

    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            client.loop_forever(retry_first_connection=True)
        except Exception as e:
            print(f"[bridge] 连接异常: {e}，5 秒后重试")
            time.sleep(5)


if __name__ == "__main__":
    main()
