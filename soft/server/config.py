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
_here = os.path.dirname(os.path.abspath(__file__))
# 兼容两种部署布局（data 目录在哪，项目根就在哪）：
#   本地 soft/server/config.py → data 在上一级 soft/data
#   云端 gjn/config.py         → data 在同级 gjn/data
BASE_DIR = _here if os.path.isdir(os.path.join(_here, "data")) else os.path.dirname(_here)
# 数据库路径：默认本地 data/food.db；可用环境变量 FOOD_DB_PATH 覆盖（如训练切云端库 food_server.db）
#   —— 这是「实时库」：mqtt_bridge 写入、app/label_tool 读取；勿改默认，改了会断采/串库
DB_PATH = os.environ.get("FOOD_DB_PATH") or os.path.join(BASE_DIR, "data", "food.db")

# 训练数据源：默认优先用更完整的云端快照 data/food_cloud.db（7x24 连续记录）；
#   该文件不存在时（如云端服务器上）回退实时库 DB_PATH。仍可用 FOOD_DB_PATH 覆盖。
#   仅用于训练/分析，绝不能被 mqtt_bridge 写入，故与实时库分开，避免串库。
_cloud_snapshot = os.path.join(BASE_DIR, "data", "food_cloud.db")
TRAIN_DB_PATH = os.environ.get("FOOD_DB_PATH") or (_cloud_snapshot if os.path.exists(_cloud_snapshot) else DB_PATH)
CSV_PATH = os.path.join(BASE_DIR, "data", "measurements.csv")

# ===== Flask Web 服务 =====
WEB_HOST = "0.0.0.0"    # 监听所有网卡（手机 / Tailscale 远程均可访问）
# 端口可通过环境变量覆盖：本地默认 5000；云端 systemd 注入 WEB_PORT=5001
# （ngnix 将 /gjn 反代到 127.0.0.1:5001）
WEB_PORT = int(os.environ.get("WEB_PORT", "5000"))

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
# 四级分类: <15 新鲜 / 15~20 预警 / 20~25 轻微变质 / >=25 腐坏
# （20/25 两个界值为本项目约定值，若有实验室数据可再校准）
TVBN_FRESH_MAX = 15.0
TVBN_WARNING_MAX = 20.0
TVBN_SLIGHT_MAX = 25.0

# 伪标签（NH₃ 阈值）——仅用于演示/管线验证，属循环论证，不可作为答辩结论
PSEUDO_FRESH_MAX = 700
PSEUDO_WARNING_MAX = 900
PSEUDO_SLIGHT_MAX = 1200

# ===== 实验编排（样品台账，见 experiments.py）=====
# 网页/扫码新建样品时的预设选项，可自行增删（填自定值也不拦截）
CATEGORIES = ["猪肉", "牛肉", "牛奶", "面包", "熟鸡蛋"]
PACKAGING_OPTIONS = ["敞口", "保鲜膜", "真空包装", "原包装"]
STORAGE_OPTIONS = ["常温25℃", "冷藏4℃", "冷冻-18℃"]
DEFAULT_PLAN_HOURS = 72          # 默认计划采集时长(h)
DEFAULT_SAMPLE_INTERVAL_S = 60   # 默认采样间隔(s)，需与固件一致，仅作台账记录
# 扫码链接前缀（手机扫二维码打开 <base>/s/<code>）；留空则由 CLI 传入或手工拼接
SAMPLE_BASE_URL = os.environ.get("SAMPLE_BASE_URL", "")

# ===== 数据质量审计（见 audit.py）=====
# 训练前自动读取同库 quality_flags 表中 severity=error 的异常段并剔除，
# 不再依赖 preprocess 顶部硬编码的时间段
USE_DB_QUALITY_FLAGS = True
