# -*- coding: utf-8 -*-
"""生成 48 小时模拟实验数据（回放模式演示 + LSTM 管线测试用）

模拟"鸡肉 25℃ 密闭环境"腐败三阶段（参照技术文档实验设计）：
  0-16h  Fresh   新鲜：基线 + 噪声，指标平稳
  16-32h Warning 初腐：VOC/NH₃/TVOC 缓慢上升（细菌繁殖加速）
  32-48h Danger  腐败：指标快速攀升（指数增长期）

数据直接写入 SQLite measurements 表，与真实设备同表结构。
运行: python backfill_demo_data.py
"""
import math
import random
import sqlite3
from datetime import datetime, timedelta

from config import DB_PATH

random.seed(42)  # 固定种子保证可复现

SAMPLING_SEC = 60          # 采样间隔 60 秒（48h = 2880 条）
TOTAL_HOURS = 48
FOOD_NAME = "鸡肉-25℃"


def stage_weight(hours):
    """腐败程度权重: 0(新鲜) → 1(完全腐败)，按三阶段分段"""
    if hours < 16:                      # Fresh: 平稳，微小漂移
        return hours / 16 * 0.08
    elif hours < 32:                    # Warning: 缓慢上升
        return 0.08 + (hours - 16) / 16 * 0.35
    else:                               # Danger: 指数式快速攀升
        return 0.43 + (hours - 32) / 16 * 0.57


def gen_row(t_start, hours):
    """生成一条模拟传感器数据"""
    w = stage_weight(hours)
    # 传感器基线 + 腐败趋势 + 噪声（模拟 BME680/SGP30/MQ-137 真实特性）
    voc = 150 + 850 * (w ** 1.6) + random.uniform(-15, 15)          # VOC 指数 150→~1000
    co2eq = int(420 + 1800 * (w ** 1.4) + random.uniform(-25, 25))  # eCO2 420→~2200 ppm
    tvoc = int(180 + 1500 * (w ** 1.5) + random.uniform(-20, 20))   # TVOC 180→~1700 ppb
    nh3_adc = int(512 + 1400 * (w ** 1.8) + random.uniform(-12, 12))  # NH3 ADC 512→~1900
    temp = round(25.0 + 0.8 * math.sin(hours / 8 * math.pi) + random.uniform(-0.15, 0.15), 1)
    humi = round(62 + 6 * w + random.uniform(-0.8, 0.8), 1)         # 呼吸作用产湿
    ts = (t_start + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    return (ts, round(voc), co2eq, tvoc, temp, humi, nh3_adc)


def main():
    # 48h 实验从"昨天早上 8 点"开始，保证现在回放能看到完整周期
    now = datetime.now()
    end = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if end > now:
        end -= timedelta(days=1)
    start = end - timedelta(hours=TOTAL_HOURS)

    conn = sqlite3.connect(DB_PATH)
    # 清掉旧的演示数据再写入（避免叠加）
    conn.execute("DELETE FROM measurements WHERE timestamp <= ?", (end.strftime("%Y-%m-%d %H:%M:%S"),))

    rows = []
    for i in range(TOTAL_HOURS * 3600 // SAMPLING_SEC):
        rows.append(gen_row(start, i * SAMPLING_SEC / 3600))
    conn.executemany(
        "INSERT INTO measurements (timestamp, voc, co2eq, tvoc, temperature, humidity, nh3_adc) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]
    conn.close()
    print(f"已生成 {len(rows)} 条模拟数据（{FOOD_NAME}，{start} ~ {end}）")
    print(f"当前数据库总记录: {n}")
    print(f"阶段划分: 0-16h Fresh | 16-32h Warning | 32-48h Danger")


if __name__ == "__main__":
    main()
