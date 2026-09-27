# -*- coding: utf-8 -*-
"""验证巴法云 /set 推送机制 + 同身份是否互通"""
import time

import paho.mqtt.client as mqtt

from config import MQTT_HOST, MQTT_PORT, MQTT_USER, TOPIC

KEY = MQTT_USER


def make_client(name):
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=KEY)
    st = {"connected": None, "received": None, "log": []}

    def on_connect(cl, u, flags, rc, properties=None):
        st["connected"] = (not rc.is_failure)
        st["log"].append(f"{name}:connect={rc}")

    def on_disconnect(cl, u, flags, rc, properties=None):
        if st["connected"]:
            st["connected"] = False
            st["log"].append(f"{name}:kicked rc={rc}")

    def on_message(cl, u, m):
        st["received"] = m.payload.decode("utf-8", "replace")
        st["log"].append(f"{name}:收到 topic={m.topic} msg={st['received']}")

    c.on_connect = on_connect
    c.on_disconnect = on_disconnect
    c.on_message = on_message
    return c, st


def main():
    print(f"测试 /set 机制: 订阅 {TOPIC}，发布到 {TOPIC}/set（同一私钥身份）")
    a, sa = make_client("订阅端A")
    a.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    a.loop_start()
    time.sleep(2)
    r = a.subscribe(TOPIC, qos=1)
    print(f"订阅返回: {r}")
    time.sleep(1)

    b, sb = make_client("发布端B")
    b.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    b.loop_start()
    time.sleep(2)
    info = b.publish(f"{TOPIC}/set", "set_test_000", qos=1)
    info.wait_for_publish()
    print(f"已发布到 {TOPIC}/set")
    time.sleep(4)

    print(f"A 收到: {sa['received']!r}")
    print(f"A 在线: {sa['connected']}, B 在线: {sb['connected']}")
    if sa["received"]:
        print("==> 同身份也能收到 /set 消息！架构无需改动")
    else:
        print("==> 确认同身份互不推送（防自收机制），PC 端需用 appID/secretKey 第二身份")
    print("日志:", "; ".join(sa["log"]))
    a.loop_stop(); a.disconnect()
    b.loop_stop(); b.disconnect()


if __name__ == "__main__":
    main()
