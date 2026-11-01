"""临时脚本：基于云端 food_server.db 出图 —— 10-02 23:30 ~ 10-03 16:48 六通道整合。

说明：本地 food.db 因采集端未常驻存在断采，云端 food.db 为 7x24 连续记录，以云端为准。
"""
import os
import sqlite3

import matplotlib

matplotlib.use("Agg")  # 无界面环境出图
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "PingFang SC"]
plt.rcParams["axes.unicode_minus"] = False

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "data", "food_server.db")
OUT = os.path.join(HERE, "data", "overview_1002_1003.png")

T0 = "2026-10-02 23:30:00"
T1 = "2026-10-03 16:48:59"
COLS = ["voc", "co2eq", "tvoc", "temperature", "humidity", "nh3_adc"]
UNITS = {"voc": "ppb", "co2eq": "ppm", "tvoc": "ppb",
         "temperature": "°C", "humidity": "%RH", "nh3_adc": "ADC"}

con = sqlite3.connect(DB)
df = pd.read_sql_query(
    f"SELECT timestamp, {', '.join(COLS)} FROM measurements "
    f"WHERE timestamp >= '{T0}' AND timestamp <= '{T1}' ORDER BY timestamp",
    con)
con.close()
df["ts"] = pd.to_datetime(df["timestamp"])
print(f"云端窗口 {T0} ~ {T1} 共 {len(df)} 条")

print("\n=== 断采检查（>3 分钟） ===")
gap = df["ts"].diff().dt.total_seconds() / 60
big = gap[gap > 3]
print("无断采" if big.empty else "\n".join(
    f"  {df['ts'].iloc[i-1]} -> {df['ts'].iloc[i]} 断 {gap.iloc[i]:.0f} 分钟" for i in big.index))

print("\n=== 六通道统计（min / mean / max） ===")
for c in COLS:
    print(f"  {c:12s} {df[c].min():10.2f} {df[c].mean():10.2f} {df[c].max():10.2f}")

print("\n=== 逐小时均值 ===")
df["h"] = df["ts"].dt.strftime("%m-%d %H")
print(df.groupby("h")[COLS].mean().round(1).to_string())

seg_id = (df["ts"].diff().dt.total_seconds() / 60 > 5).cumsum()
segments = [g for _, g in df.groupby(seg_id)]

fig, axes = plt.subplots(6, 1, figsize=(14, 15), sharex=True)
colors = ["#2E86AB", "#A23B72", "#F18F01", "#2A9D8F", "#E76F51", "#6A4C93"]
EVENT = pd.Timestamp("2026-10-02 23:40:00")
for ax, c, col in zip(axes, COLS, colors):
    for seg in segments:
        ax.plot(seg["ts"], seg[c], color=col, lw=1.0)
    ax.set_ylabel(f"{c}\n({UNITS[c]})", fontsize=10)
    ax.grid(alpha=0.3)
    ax.axvline(EVENT, color="#B00020", ls="--", lw=1.0, alpha=0.7)
axes[0].set_title(
    "食品安全检测仪 · 六通道数据总览   (2026-10-02 23:30 → 2026-10-03 16:48)\n"
    "红虚线 = 预计放入肉块(~23:40)   数据源：云端连续记录",
    fontsize=13)
axes[-1].set_xlabel("时间")
axes[-1].xaxis.set_major_locator(mdates.HourLocator(interval=1))
axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=45, ha="right", fontsize=8)
fig.tight_layout()
fig.savefig(OUT, dpi=150)
print(f"\n[出图] {OUT}")
