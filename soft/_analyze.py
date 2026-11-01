import os, sqlite3
os.chdir(r'c:\Users\Administrator\Desktop\FSM\soft')
import pandas as pd, numpy as np

conn = sqlite3.connect('data/food_cloud.db')
df = pd.read_sql_query("SELECT * FROM measurements ORDER BY timestamp ASC", conn)
conn.close()
df['ts'] = pd.to_datetime(df['timestamp'], errors='coerce')

print('=== 2026-10-04 15:00 ~ 10-05 01:00 每30分钟均值（找新固件湿度跳变）===')
sub = df[(df['ts'] >= '2026-10-04 15:00') & (df['ts'] <= '2026-10-05 01:00')]
agg = sub.set_index('ts')[['humidity', 'temperature', 'voc', 'co2eq', 'tvoc', 'nh3_adc']].resample('30min').mean().round(2)
print(agg.to_string())

print()
print('=== 2026-10-04 18:50 ~ 19:15 逐条（定位固件分界）===')
n = df[(df['ts'] >= '2026-10-04 18:50') & (df['ts'] <= '2026-10-04 19:15')]
print(n[['timestamp', 'humidity', 'temperature', 'voc', 'nh3_adc']].to_string(index=False))

print()
print('=== 标签覆盖分析 ===')
labels = pd.read_csv('data/labels.csv')
labels['timestamp'] = pd.to_datetime(labels['timestamp'])
print('标签行数:', len(labels), '| 最后标签:', labels['timestamp'].max())
merged = pd.merge_asof(df.sort_values('ts'),
                       labels[['timestamp', 'stage']].rename(columns={'timestamp': 'ts'}).sort_values('ts'),
                       on='ts', direction='backward')
print('总测量行:', len(merged), '| 匹配到标签:', int(merged['stage'].notna().sum()),
      '| 首次标签前(丢弃):', int(merged['stage'].isna().sum()))
print('各 stage 行数:', {int(k): int(v) for k, v in merged['stage'].value_counts().items()})
after = merged[merged['ts'] > labels['timestamp'].max()]
print('最后标签之后的行数:', len(after), '→ 全部被 backward 填为 stage=',
      sorted(after['stage'].dropna().unique().astype(int)))
print('  其中属于新固件期(>=10-04 19:04)的行数:',
      int((after['ts'] >= '2026-10-04 19:04').sum()))
