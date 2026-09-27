# -*- coding: utf-8 -*-
"""全局配置文件（巴法云 MQTT / 数据存储 / Web 服务）"""

# ===== 巴法云 MQTT =====
MQTT_HOST = "bemfa.com"                              # 巴法云 MQTT 服务器
MQTT_PORT = 9501                                     # MQTT TCP 端口
MQTT_USER = "afc373d147d6af88a41f607133a292de"       # 巴法云私钥（设备端认证用，勿公开分享）
TOPIC = "food001"                                    # 数据主题（巴法云主题仅支持字母数字）

# 方式二认证（PC 接收端用，与设备端身份隔离）
# 注意：发布用「主题名/set」才会推送给订阅者（官方 /set 指令规则）
MQTT_APPID = "beid_ycTO5IzM3gzNx8VOxADN4MD"
MQTT_SECRETKEY = "132WClCh3QWGrJqyaYt8FN28a55S9xD6"

# 客户端 ID（各端保持唯一，避免互踢）
CLIENT_ID_BRIDGE = "pc_bridge_001"      # PC 接收端
CLIENT_ID_SIM = "sim_001"               # 模拟设备（调试用）
CLIENT_ID_ESP32 = "esp32_food_001"      # ESP32 固件端（firmware 中保持一致）

# ===== 数据存储路径 =====
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "food.db")
CSV_PATH = os.path.join(BASE_DIR, "data", "measurements.csv")

# ===== Flask Web 服务 =====
WEB_HOST = "0.0.0.0"    # 监听所有网卡（手机 / Tailscale 远程均可访问）
WEB_PORT = 5000

# ===== 数据来源切分 =====
# 此时间点之前的数据由 backfill_demo_data.py 生成（模拟数据，仅用于管线验证），
# 之后的数据才是 ESP32 实测数据。训练时默认只用真实数据，避免污染。
DEMO_BEFORE = "2026-09-01 00:00:00"

# ===== 标签配置 =====
# 真实标签文件（TVB-N / pH 实测，或 0-3 级人工腐败评分），格式见文件表头
LABELS_PATH = os.path.join(BASE_DIR, "data", "labels.csv")

# 相邻两条采样间隔超过该分钟数 → 视为新实验场次（用于按场次切分，防数据泄漏）
SESSION_GAP_MIN = 30

# TVB-N 分级阈值（mg/100g，参照 GB 2707 鲜肉一级鲜度 ≤15）
TVBN_FRESH_MAX = 15.0
TVBN_WARNING_MAX = 25.0

# 伪标签（NH₃ 阈值）——仅用于演示/管线验证，属循环论证，不可作为答辩结论
PSEUDO_FRESH_MAX = 700
PSEUDO_WARNING_MAX = 1200
