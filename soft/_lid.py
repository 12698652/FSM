# -*- coding: utf-8 -*-
import json, os
import pandas as pd

p = os.path.join(os.environ["TEMP"], "gjn_lid.json")
df = pd.DataFrame(json.load(open(p, encoding="utf-8")))
df["ts"] = pd.to_datetime(df["timestamp"], errors="coerce")
for c in ["voc", "co2eq", "tvoc", "temperature", "humidity", "nh3_adc"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df = df.dropna(subset=["ts"]).sort_values("ts").reset_index(drop=True)

# 2 分钟粒度
df["slot"] = df["ts"].dt.floor("2min")
g = df.groupby("slot")[["nh3_adc", "co2eq", "tvoc", "voc", "temperature", "humidity"]].agg(["mean", "min", "max"])
g.columns = [f"{a}_{b}" for a, b in g.columns]
pd.set_option("display.width", 250)
print("=== 2min 粒度（均值 / 极值）===")
print(g.round(1).to_string())
