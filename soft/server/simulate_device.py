# -*- coding: utf-8 -*-
"""模拟设备：无硬件时模拟 ESP32 向巴法云上报传感器 JSON（调试/演示用）。
数据模拟"食品缓慢腐败"趋势：VOC/eCO2/NH3 随时间缓慢上升。
运行: python simulate_device.py
"""
import json
import math
import random
import time
from datetime import datetime

import paho.mqtt.client as mqtt

from config import CLIENT_ID_SIM, MQTT_HOST, MQTT_PORT, MQTT_USER, TOPIC

INTERVAL = 5  # 上报间隔（秒）


def build_payload(t):
    """t: 已运行秒数 → 构造一条模拟传感器数据"""
    voc = 150 + 40 * math.sin(t / 300) + 0.02 * t + random.uniform(-8, 8)
    co2eq = int(400 + 0.6 * t + random.uniform(-20, 20))
    tvoc = int(200 + 0.4 * t + random.uniform(-15, 15))
    temp = round(25 + 1.5 * math.sin(t / 600) + random.uniform(-0.2, 0.2), 1)
    humi = round(60 + 5 * math.sin(t / 700) + random.uniform(-1, 1), 1)
    nh3_adc = int(512 + 0.25 * t + random.uniform(-10, 10))
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "voc": round(voc),
        "co2eq": co2eq,
        "tvoc": tvoc,
        "temp": temp,
        "humi": humi,
        "nh3_adc": nh3_adc,
    }


def main():
    # 方式一认证：clientId = 私钥（与 ESP32 设备端一致；巴法云设备端唯一有效方式）
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=MQTT_USER)
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()
    print(f"[sim] 已连接巴法云，每 {INTERVAL} 秒向主题 {TOPIC}/set 上报模拟数据，Ctrl+C 退出")
    t0 = time.time()
    try:
        while True:
            payload = build_payload(time.time() - t0)
            client.publish(f"{TOPIC}/set", json.dumps(payload))   # /set 才会推送给订阅者
            print(f"[sim] 上报: {json.dumps(payload, ensure_ascii=False)}")
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()
        print("[sim] 已退出")


if __name__ == "__main__":
    main()
