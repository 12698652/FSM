import json, collections, os

d = json.load(open(os.path.join(os.environ['TEMP'], 'gjn_24h.json'), encoding='utf-8'))
rows = d if isinstance(d, list) else d.get('data')
agg = collections.OrderedDict()
for r in rows:
    h = r['timestamp'][:13]
    agg.setdefault(h, []).append(
        (float(r['nh3_adc']), float(r['voc']), float(r['temperature']),
         float(r['tvoc']), float(r['co2eq']), float(r['humidity'])))

hdr = "%-14s %3s %7s %6s %5s %5s %5s %5s %5s" % ('hour','n','nh3avg','rng','voc','temp','humi','tvoc','co2')
print(hdr)
for h, v in agg.items():
    nh = [x[0] for x in v]
    print("%-14s %3d %7.1f %6.0f %5.1f %5.1f %5.1f %5.1f %5.0f" % (
        h, len(v), sum(nh)/len(nh), max(nh)-min(nh),
        sum(x[1] for x in v)/len(v), sum(x[2] for x in v)/len(v),
        sum(x[5] for x in v)/len(v), sum(x[3] for x in v)/len(v),
        sum(x[4] for x in v)/len(v)))

last12 = list(agg.items())[-12:]
means = [sum(x[0] for x in v)/len(v) for _, v in last12]
overall = sum(means)/len(means)
print()
print('=== last 12h criterion ===')
print('hourly means:', ' '.join('%.0f' % m for m in means))
print('overall: %.1f   max hourly swing: %.1f%%   (criterion <5%%)' % (
    overall, (max(means)-min(means))/overall*100))
half = len(means)//2
first, second = sum(means[:half])/half, sum(means[half:])/(len(means)-half)
trend = 'DOWN' if first > second*1.02 else ('UP' if second > first*1.02 else 'FLAT')
print('first half %.1f vs second half %.1f -> trend %s' % (first, second, trend))
