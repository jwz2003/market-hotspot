import json, os, datetime

lp = os.path.expanduser('~/market-hotspot/data/last_pushed.txt')
last = open(lp).read().strip() if os.path.exists(lp) else ''
items = json.load(open(os.path.expanduser('~/market-hotspot/data/alerts_pending.json')))
new = [a for a in items if str(a.get('time', '')) > last]
new.sort(key=lambda x: {'🔴': 0, '🟡': 1}.get(x.get('level'), 2))
print('LAST:', last or '(first)')
print('NEWCOUNT:', len(new))
# 3-hour window check
now = datetime.datetime.now()
cutoff = (now - datetime.timedelta(hours=3)).strftime('%Y-%m-%d %H:%M')
print('CUTOFF(3h):', cutoff)
recent = [a for a in new if str(a.get('time', '')) >= cutoff]
print('RECENTCOUNT:', len(recent))
for a in recent[:10]:
    print(json.dumps(a, ensure_ascii=False))
print('---ALL NEW (last 15)---')
for a in new[-15:]:
    print(json.dumps(a, ensure_ascii=False))
