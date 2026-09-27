# -*- coding: utf-8 -*-
"""巴法云多客户端共存测试：两个客户端都用 clientId=私钥，验证是否互踢 + 消息回环"""
import time

import paho.mqtt.client as mqtt

from config import MQTT_HOST, MQTT_PORT, MQTT_USER, TOPIC

KEY = MQTT_USER


def make_client(name):
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=KEY)
    st = {"name": name, "connected": None, "log": [], "received": None}

    def on_connect(cl, u, flags, rc, properties=None):
        st["connected"] = (not rc.is_failure)
        st["log"].append(f"{name} 连接: {rc}")

    def on_disconnect(cl, u, flags, rc, properties=None):
        if st["connected"]:
            st["connected"] = False
            st["log"].append(f"{name} 被断开!!! rc={rc}")

    def on_message(cl, u, m):
        st["received"] = m.payload.decode("utf-8", "replace")
        st["log"].append(f"{name} 收到消息: {st['received']}")

    c.on_connect = on_connect
    c.on_disconnect = on_disconnect
    c.on_message = on_message
    return c, st


def main():
    print(f"测试: 两个客户端同时使用 clientId=私钥 连接 {MQTT_HOST}:{MQTT_PORT}")

    a, sa = make_client("客户端A(订阅端)")
    a.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    a.loop_start()
    time.sleep(2)
    print(f"A 状态: connected={sa['connected']}")

    b, sb = make_client("客户端B(发布端)")
    b.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    b.loop_start()
    time.sleep(2)
    print(f"B 连接后 -> A connected={sa['connected']}, B connected={sb['connected']}")

    a.subscribe(TOPIC)
    time.sleep(1)
    b.publish(TOPIC, "coexist_test_789")
    time.sleep(3)

    print(f"\n结果:")
    print(f"  A 仍在线: {sa['connected']}")
    print(f"  B 仍在线: {sb['connected']}")
    print(f"  A 收到消息: {sa['received']!r}")
    ok = (sa["connected"] and sb["connected"] and sa["received"] == "coexist_test_789")
    print(f"\n  ==> {'多客户端共存 + 回环 全部成功!' if ok else '存在互踢或消息不通，需调整架构'}")
    print("  日志:", "; ".join(sa["log"] + sb["log"]))

    a.loop_stop(); a.disconnect()
    b.loop_stop(); b.disconnect()


if __name__ == "__main__":
    main()
