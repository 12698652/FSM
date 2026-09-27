# -*- coding: utf-8 -*-
"""巴法云 MQTT 连通性测试：验证私钥、认证方式、订阅/发布回环。
运行: python test_bemfa.py
"""
import time

import paho.mqtt.client as mqtt

from config import MQTT_HOST, MQTT_PORT, MQTT_USER, TOPIC

KEY = MQTT_USER


def make_client(cid, user=None, pwd=None):
    """创建测试客户端，返回 (client, state)"""
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
    if user is not None:
        c.username_pw_set(user, pwd)
    state = {"connected": None, "rc": "", "received": None}

    def on_connect(cl, u, flags, rc, properties=None):
        state["connected"] = (not rc.is_failure)
        state["rc"] = str(rc)

    def on_disconnect(cl, u, flags, rc, properties=None):
        if state["connected"]:
            state["connected"] = False
            state["rc"] = f"被断开({rc})"

    def on_message(cl, u, m):
        state["received"] = m.payload.decode("utf-8", "replace")

    c.on_connect = on_connect
    c.on_disconnect = on_disconnect
    c.on_message = on_message
    return c, state


def try_connect(name, cid, user=None, pwd=None, wait=4):
    print(f"\n--- 测试 {name}: clientId={cid[:12]}... user={'有' if user else '无'} ---")
    c, st = make_client(cid, user, pwd)
    try:
        c.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        c.loop_start()
        time.sleep(wait)
        ok = st["connected"] is True
        print(f"    结果: {'连接成功' if ok else '失败'}  rc={st['rc']}")
        return c, st, ok
    except Exception as e:
        print(f"    结果: 连接异常 {e}")
        return c, st, False


def main():
    print(f"目标: {MQTT_HOST}:{MQTT_PORT}  主题: {TOPIC}")

    # 方式一：clientId = 私钥（巴法云标准方式）
    c1, st1, ok1 = try_connect("方式A(clientId=私钥)", KEY)

    # 方式二：自定义 clientId + username=私钥
    c2, st2, ok2 = try_connect("方式B(username=私钥)", "pc_test_002", user=KEY)

    # 方式三：私钥 + 后缀 作 clientId
    c3, st3, ok3 = try_connect("方式C(clientId=私钥+后缀)", KEY + "x9")

    # 回环测试：用其中一个客户端订阅，另一个发布，验证消息能否到达
    print("\n--- 回环测试（订阅+发布） ---")
    sub, sub_st, sub_ok = (c2, st2, ok2) if ok2 else (c1, st1, ok1)
    pub, pub_st, pub_ok = (c3, st3, ok3) if ok3 else ((c2, st2, ok2) if ok2 and ok1 is False else (c1, st1, ok1))
    if sub_ok:
        sub.subscribe(TOPIC)
        time.sleep(1)
        if pub_ok and pub is not sub:
            pub.publish(TOPIC, "roundtrip_test_123")
            time.sleep(3)
            print(f"    订阅端收到: {sub_st['received']}")
            if sub_st["received"] == "roundtrip_test_123":
                print("    ==> 回环成功！巴法云链路完全可用")
            else:
                print("    ==> 发布成功但订阅端未收到（同 clientId 互踢或主题问题）")
        else:
            print("    只有单客户端可用，跳过回环（可能是认证方式冲突）")
    else:
        print("    无可用连接，回环跳过")

    for c in (c1, c2, c3):
        try:
            c.loop_stop()
            c.disconnect()
        except Exception:
            pass
    print("\n测试完成")


if __name__ == "__main__":
    main()
