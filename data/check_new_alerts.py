import json, os, sys

lp = os.path.expanduser('~/market-hotspot/data/last_pushed.txt')
last = open(lp).read().strip() if os.path.exists(lp) else ''
items = json.load(open(os.path.expanduser('~/market-hotspot/data/alerts_pending.json')))
new = [a for a in items if str(a.get('time', '')) > last]
new.sort(key=lambda x: {'🔴': 0, '🟡': 1}.get(x.get('level'), 2))
print('LAST:', last or '(first)')
print(json.dumps(new[:10], ensure_ascii=False))
