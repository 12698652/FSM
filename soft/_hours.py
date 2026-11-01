import os, sqlite3
os.chdir(r'c:\Users\Administrator\Desktop\FSM\soft')
import pandas as pd

c = sqlite3.connect('data/food_cloud.db')
d = pd.read_sql_query("SELECT * FROM measurements ORDER BY timestamp ASC", c)
c.close()
d['ts'] = pd.to_datetime(d['timestamp'], errors='coerce')
sub = d[(d['ts'] >= '2026-10-04 17:30') & (d['ts'] <= '2026-10-04 19:40')]
agg = sub.set_index('ts')[['voc','co2eq','tvoc','nh3_adc','temperature','humidity']].resample('5min').agg(['mean','count'])
print('=== 10-04 17:30 ~ 19:40 五分钟均值/计数 ===')
print(agg.round(2).to_string())
