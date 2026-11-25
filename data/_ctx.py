import json, os
base = os.path.expanduser('~/market-hotspot/data')
items = json.load(open(os.path.join(base, 'alerts_pending.json')))
for a in items:
    if str(a.get('time','')).startswith('2026-11-25') and '费城半导体' in a.get('title',''):
        print(a.get('time'), a.get('level'), a.get('title'), '|', a.get('detail'))
print('=== 11-25 all ===')
for a in items:
    if str(a.get('time','')).startswith('2026-11-24') or str(a.get('time','')).startswith('2026-11-25'):
        print(a.get('time'), a.get('level'), a.get('market'), a.get('title'))
