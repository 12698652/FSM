import os, sqlite3
os.chdir(r'c:\Users\Administrator\Desktop\FSM\soft')
import pandas as pd

DEMO_BEFORE = '2026-09-01 00:00:00'

def load(p):
    c = sqlite3.connect(p)
    d = pd.read_sql_query("SELECT * FROM measurements ORDER BY timestamp ASC", c)
    c.close()
    d['ts'] = pd.to_datetime(d['timestamp'], errors='coerce')
    return d

loc = load('data/food.db')
clo = load('data/food_cloud.db')

for name, d in (('LOCAL', loc), ('CLOUD', clo)):
    real = d[d['ts'] >= DEMO_BEFORE]
    print(f"--- {name} --- 全库 {len(d)} 条 | 真实期(>=09-01) {len(real)} 条 | {real['ts'].min()} ~ {real['ts'].max()}")

print()
print('=== 真实期逐日行数对比 (09-21 起) ===')
a = loc[loc['ts'] >= DEMO_BEFORE].set_index('ts').resample('1D').size().rename('local')
b = clo[clo['ts'] >= DEMO_BEFORE].set_index('ts').resample('1D').size().rename('cloud')
cmp = pd.concat([a, b], axis=1).fillna(0).astype(int)
print(cmp.tail(16).to_string())

print()
print('=== 新固件段 (>=10-04 19:04:20) 统计 (cloud) ===')
nf = clo[clo['ts'] >= '2026-10-04 19:04:20']
print('行数:', len(nf), '| 时间:', nf['ts'].min(), '~', nf['ts'].max())
print(nf[['voc','co2eq','tvoc','nh3_adc','temperature','humidity']].describe().round(2).to_string())

print()
print('=== 全库最早标签前/后 ===')
lab = pd.read_csv('data/labels.csv')
lab['timestamp'] = pd.to_datetime(lab['timestamp'])
print('标签首:', lab['timestamp'].min(), '末:', lab['timestamp'].max(), '条数:', len(lab))
