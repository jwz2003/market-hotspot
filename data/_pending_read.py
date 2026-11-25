import json, os, datetime

base = os.path.expanduser('~/market-hotspot/data')
lp = os.path.join(base, 'last_pushed.txt')
last = open(lp).read().strip() if os.path.exists(lp) else ''

items = json.load(open(os.path.join(base, 'alerts_pending.json')))
new = [a for a in items if str(a.get('time', '')) > last]
new.sort(key=lambda x: {'🔴': 0, '🟡': 1}.get(x.get('level'), 2))

print('LAST:', last or '(first)')
print('COUNT:', len(new))

# first run: only keep last 3 hours
if not last:
    cutoff = datetime.datetime.now() - datetime.timedelta(hours=3)
    kept = []
    for a in new:
        try:
            t = datetime.datetime.strptime(str(a.get('time')), '%Y-%m-%d %H:%M')
        except Exception:
            continue
        if t >= cutoff:
            kept.append(a)
    new = kept
    print('FIRST_RUN_FILTERED:', len(new))

print('---')
for a in new[:10]:
    print(json.dumps(a, ensure_ascii=False))
print('---TAIL---')
for a in items[-8:]:
    print(json.dumps(a, ensure_ascii=False))
