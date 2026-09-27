# -*- coding: utf-8 -*-
"""端到端链路测试：设备端(私钥)发布 → 巴法云 → PC端(appID/secretKey)订阅接收
模拟真实数据流向，验证完整链路。"""
import json
import time

import paho.mqtt.client as mqtt

from config import (MQTT_APPID, MQTT_HOST, MQTT_PORT, MQTT_SECRETKEY,
                    MQTT_USER, TOPIC)

results = {"sub_connected": None, "pub_connected": None, "received": None}


def on_sub_connect(cl, u, flags, rc, properties=None):
    results["sub_connected"] = (not rc.is_failure)
    print(f"[PC订阅端] 连接{'成功' if not rc.is_failure else '失败: ' + str(rc)}")
    if not rc.is_failure:
        cl.subscribe(TOPIC)


def on_pub_connect(cl, u, flags, rc, properties=None):
    results["pub_connected"] = (not rc.is_failure)
    print(f"[设备端] 连接{'成功' if not rc.is_failure else '失败: ' + str(rc)}")


def on_sub_message(cl, u, m):
    results["received"] = m.payload.decode("utf-8", "replace")
    print(f"[PC订阅端] 收到消息: {results['received']}")


def main():
    # PC 订阅端：方式二认证（appID + secretKey）
    sub = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="pc_bridge_001")
    sub.username_pw_set(MQTT_APPID, MQTT_SECRETKEY)
    sub.on_connect = on_sub_connect
    sub.on_message = on_sub_message
    sub.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    sub.loop_start()

    # 设备端：方式一认证（私钥作 clientId）
    pub = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=MQTT_USER)
    pub.on_connect = on_pub_connect
    pub.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    pub.loop_start()

    time.sleep(3)

    # 设备端发布模拟传感器数据到 /set
    payload = json.dumps({
        "timestamp": "2026-08-22 00:40:00", "voc": 155, "co2eq": 430,
        "tvoc": 210, "temp": 25.1, "humi": 60.2, "nh3_adc": 518})
    print(f"[设备端] 发布到 {TOPIC}/set: {payload}")
    pub.publish(f"{TOPIC}/set", payload)

    # 等待消息到达
    for _ in range(10):
        if results["received"]:
            break
        time.sleep(1)

    print("\n===== 测试结果 =====")
    ok = (results["sub_connected"] and results["pub_connected"] and results["received"])
    print(f"PC订阅端连接: {results['sub_connected']}")
    print(f"设备端连接: {results['pub_connected']}")
    print(f"消息到达: {results['received'] is not None}")
    print(f"\n{'==> 完整链路打通！' if ok else '==> 链路未通，检查上方日志'}")

    sub.loop_stop(); sub.disconnect()
    pub.loop_stop(); pub.disconnect()


if __name__ == "__main__":
    main()
