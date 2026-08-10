#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全球市场热点采集器（每半小时 cron 运行，no_agent 零 token）
数据源（全部已验证 2026-08-10）：
  行情异动: Yahoo Finance chart API / Binance
  公告披露: SEC EDGAR (via r.jina.ai) / 港交所披露易 / 巨潮资讯
  资金流向: 东方财富(北向/南向) / 东财龙虎榜 / Binance 资金费率
输出: data/{market,announcements,funds,alerts_pending,meta}.json
注意: 必须用 subprocess+curl（macOS 系统 Python urllib SSL 无 CA bundle）
"""
import json, subprocess, os, re, sys, time, html
from datetime import datetime, timezone, timedelta

BASE = os.path.expanduser("~/market-hotspot")
DATA = os.path.join(BASE, "data")
os.makedirs(DATA, exist_ok=True)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST)
TODAY = NOW.strftime("%Y-%m-%d")
NOWSTR = NOW.strftime("%Y-%m-%d %H:%M")

# ---------------- 基础工具 ----------------
def curl(url, timeout=25, extra=None, ua=UA):
    cmd = ["curl", "-s", "-m", str(timeout), "-A", ua]
    if extra:
        cmd += extra
    cmd.append(url)
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout + 8)
        return r.stdout.decode("utf-8", errors="replace")
    except Exception:
        return ""

def jload(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default

def jdump(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)

# ---------------- 状态（去重） ----------------
SEEN_PATH = os.path.join(DATA, "seen.json")
seen = jload(SEEN_PATH, {"ann": [], "alerts": {}})
seen_ann = set(seen.get("ann", []))
seen_alerts = seen.get("alerts", {})  # fingerprint -> expiry_ts

alerts = jload(os.path.join(DATA, "alerts_pending.json"), [])

def add_alert(level, market, title, detail, value=None, fp=None):
    """level: 🔴/🟡/🟢; 同一指纹 6 小时内不重复"""
    fp = fp or re.sub(r"\s+", " ", f"{market}|{title}")[:120]
    now_ts = time.time()
    if fp in seen_alerts and seen_alerts[fp] > now_ts:
        return
    seen_alerts[fp] = now_ts + 6 * 3600
    alerts.append({"level": level, "market": market, "title": title,
                   "detail": detail, "value": value, "time": NOWSTR})

# ---------------- 1) 行情异动 ----------------
WATCH = {
    "index": {"^GSPC": "标普500", "^IXIC": "纳斯达克", "^DJI": "道琼斯", "^HSI": "恒生指数",
              "000001.SS": "上证指数", "399001.SZ": "深证成指", "^SOX": "费城半导体", "^VIX": "VIX恐慌"},
    "commodity": {"GC=F": "黄金", "SI=F": "白银", "CL=F": "WTI原油", "HG=F": "铜", "NG=F": "天然气"},
    "forex": {"DX-Y.NYB": "美元指数", "USDCNH=X": "离岸人民币", "USDJPY=X": "美元日元", "EURUSD=X": "欧元美元"},
}
THRESH = {"index": 1.5, "commodity": 2.0, "forex": 0.8, "crypto": 5.0}

market_rows = []
for cat, symbols in WATCH.items():
    for sym, name in symbols.items():
        try:
            txt = curl(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym.replace('^','%5E')}?interval=1d&range=5d")
            res = json.loads(txt)["chart"]["result"][0]
            price = res["meta"].get("regularMarketPrice")
            closes = [c for c in res["indicators"]["quote"][0]["close"] if c]
            if not price or len(closes) < 2:
                continue
            pct = (closes[-1] - closes[-2]) / closes[-2] * 100
            row = {"cat": cat, "symbol": sym, "name": name, "price": round(price, 2),
                   "pct": round(pct, 2)}
            market_rows.append(row)
            # VIX 只在飙升时报警（下跌=风险偏好回升，非风险事件）
            if sym == "^VIX" and pct <= 0:
                continue
            if abs(pct) >= THRESH[cat]:
                lv = "🔴" if abs(pct) >= THRESH[cat] * 1.7 else "🟡"
                add_alert(lv, "行情", f"{name} {'+' if pct>0 else ''}{pct:.2f}%",
                          f"现价 {price}，{'突破' if pct>0 else '跌破'}波动阈值 {THRESH[cat]}%",
                          value=pct, fp=f"行情|{sym}|{'up' if pct>0 else 'down'}")
        except Exception:
            continue

# 加密（Binance 24h ticker）
CRYPTO = {"BTCUSDT": "BTC", "ETHUSDT": "ETH", "SOLUSDT": "SOL", "BNBUSDT": "BNB", "XRPUSDT": "XRP"}
for sym, name in CRYPTO.items():
    try:
        d = json.loads(curl(f"https://api.binance.com/api/v3/ticker/24hr?symbol={sym}"))
        pct = float(d["priceChangePercent"])
        price = float(d["lastPrice"])
        market_rows.append({"cat": "crypto", "symbol": sym, "name": name,
                            "price": round(price, 2), "pct": round(pct, 2)})
        if abs(pct) >= THRESH["crypto"]:
            lv = "🔴" if abs(pct) >= 8 else "🟡"
            add_alert(lv, "加密", f"{name} 24h {'+' if pct>0 else ''}{pct:.2f}%",
                      f"现价 {price}，24h 波动超 {THRESH['crypto']}%",
                      value=pct, fp=f"加密|{sym}|{'up' if pct>0 else 'down'}")
    except Exception:
        continue

jdump(os.path.join(DATA, "market.json"), market_rows)

# ---------------- 2) 资金流向 ----------------
funds = {"north_south": None, "lhb": [], "funding": []}
try:
    d = json.loads(curl("https://push2.eastmoney.com/api/qt/kamt.kline/get?fields1=f1,f2,f3,f4&fields2=f51,f52,f53,f54,f55,f56&klt=101&lmt=3"))
    funds["north_south"] = d.get("data")
except Exception:
    pass
try:
    txt = curl("https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_DAILYBILLBOARD_DETAILS&columns=ALL&pageSize=20&pageNumber=1&sortColumns=TRADE_DATE&sortTypes=-1")
    rows = json.loads(txt).get("result", {}).get("data", []) or []
    for r in rows[:20]:
        funds["lhb"].append({
            "code": r.get("SECURITY_CODE"), "name": r.get("SECURITY_NAME_ABBR"),
            "date": (r.get("TRADE_DATE") or "")[:10], "chg": r.get("CHANGE_RATE"),
            "amt": r.get("BILLBOARD_DEAL_AMT"), "reason": r.get("EXPLAIN", "")[:40]})
except Exception:
    pass
for sym, name in [("BTCUSDT", "BTC"), ("ETHUSDT", "ETH")]:
    try:
        d = json.loads(curl(f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={sym}"))
        rate = float(d.get("lastFundingRate", 0)) * 100
        funds["funding"].append({"symbol": name, "rate": round(rate, 4)})
        if abs(rate) >= 0.1:
            add_alert("🟡", "资金", f"{name} 资金费率 {rate:+.3f}%",
                      "永续合约资金费率极端，多空情绪失衡",
                      value=rate, fp=f"资金费率|{sym}|{'up' if rate>0 else 'down'}")
    except Exception:
        pass
jdump(os.path.join(DATA, "funds.json"), funds)

# ---------------- 3) 公告披露 ----------------
RED_KW_ZH = ["破产", "退市", "立案", "停牌", "复牌", "违约", "盈警", "警示函", "处罚", "问询函", "退市风险"]
YEL_KW_ZH = ["财报", "年报", "半年报", "并购", "收购", "增持", "减持", "回购", "分红",
             "派息", "中标", "合同", "获批", "许可", "重组", "股权激励", "业绩预告"]
RED_KW_EN = ["bankruptcy", "chapter 11", "delisting", "fraud", "default", "investigation",
             "restatement", "going concern"]
YEL_KW_EN = ["merger", "acquisition", "buyback", "dividend", "approval", "profit warning",
             "guidance", "downgrade", "upgrade"]

def classify(text):
    t = text.lower()
    for kw in RED_KW_ZH:
        if kw in t:
            return "🔴"
    for kw in RED_KW_EN:
        if re.search(r"\b" + re.escape(kw) + r"\b", t):
            return "🔴"
    for kw in YEL_KW_ZH:
        if kw in t:
            return "🟡"
    for kw in YEL_KW_EN:
        if re.search(r"\b" + re.escape(kw) + r"\b", t):
            return "🟡"
    return "🟢"

ann_rows = []

# SEC EDGAR via r.jina.ai（8-K 重大事件，HTML 版）
SEC_ITEMS = {"1.01": "重大协议", "2.02": "经营业绩", "4.01": "审计师变更", "4.02": "财报重述风险",
             "5.02": "高管/董事变动", "7.01": "RegFD披露", "8.01": "其他重大事件", "9.01": "附件"}
try:
    txt = curl("https://r.jina.ai/https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&dateb=&owner=include&count=20", timeout=40)
    # 结构: [Company (CIK) (Filer)](url)\n8-K[[html]]...Current report, items X.XX ... 2026-08-07
    blocks = re.split(r"\n(?=\[[^\]]+?\(\d+\) \(Filer\)\])", txt)
    for blk in blocks[1:25]:
        m_co = re.match(r"\[([^\]]+?) \(\d+\) \(Filer\)\]", blk)
        if not m_co:
            continue
        company = m_co.group(1).strip()
        m_items = re.search(r"Current report, items? ([\d\.,\s]+?)\s*\n", blk)
        items = []
        if m_items:
            items = [i.strip() for i in m_items.group(1).split(",") if i.strip()]
        m_date = re.search(r"(?<![\d\-])(20\d{2}-\d{2}-\d{2})(?!\d)", blk)
        cn_items = "、".join(SEC_ITEMS.get(i, i) for i in items[:3]) or "8-K"
        title = f"{company} — {cn_items}"
        key = "sec:" + company[:50] + (m_date.group(1) if m_date else "")
        if key in seen_ann:
            continue
        seen_ann.add(key)
        lv = classify(title)
        if "4.02" in items or "4.01" in items:
            lv = "🔴"
        elif any(i in ("2.02", "1.01", "5.02") for i in items):
            lv = lv if lv == "🔴" else "🟡"
        ann_rows.append({"src": "SEC 8-K", "market": "美股", "title": title[:120],
                         "time": m_date.group(1) if m_date else NOWSTR, "level": lv})
except Exception:
    pass

# 港交所披露易
HKEX_NOISE = ["daily trading report", "daily trading summary", "supplemental listing document",
              "derivative warrant", "callable bull/bear", "cbbc"]
try:
    frm = (NOW - timedelta(days=1)).strftime("%Y%m%d")
    to = NOW.strftime("%Y%m%d")
    txt = curl(f"https://www1.hkexnews.hk/search/titleSearchServlet.do?sortDir=0&sortByOptions=DateTime&category=0&market=SEHK&stockId=&documentType=-1&fromDate={frm}&toDate={to}&title=&page=1&lang=E")
    d = json.loads(txt)
    items = json.loads(d.get("result", "[]"))[:40]
    for it in items:
        stock = html.unescape(re.sub(r"<[^>]+>", " ", it.get("STOCK_NAME", ""))).strip()
        title = html.unescape(re.sub(r"<[^>]+>", " ", it.get("TITLE", "")))
        title = re.sub(r"\s+", " ", title).strip()
        tl = title.lower()
        # 过滤衍生品与发行人日报噪音（权证/牛熊证/结构化产品）
        if re.search(r"(JP#|BP#|HS#|JP-|@E[CP]\d)", stock, re.I):
            continue
        if any(n in tl for n in HKEX_NOISE) or (not stock and "trading" in tl):
            continue
        cat_m = re.search(r"\[([^\]]+)\]", it.get("SHORT_TEXT", "") or "")
        cat = html.unescape(cat_m.group(1)) if cat_m else ""
        # 英文占位标题（公告仅有中文版）
        if "has just been published by the issuer" in tl:
            title = "中文公告（见披露易中文版）"
        label = f"[{stock}] {title}" + (f" ({cat})" if cat else "")
        key = "hkex:" + it.get("NEWS_ID", title[:60])
        if key in seen_ann:
            continue
        seen_ann.add(key)
        lv = classify(title + " " + cat)
        if "Next Day Disclosure Return" in title or "Board Meeting" in title:
            lv = "🟢"
        # 时间: "10/08/2026 17:37" → "2026-08-10 17:37"
        tm = it.get("DATE_TIME", "")
        m_tm = re.match(r"(\d{2})/(\d{2})/(\d{4}) (\d{2}:\d{2})", tm)
        tstr = f"{m_tm.group(3)}-{m_tm.group(2)}-{m_tm.group(1)} {m_tm.group(4)}" if m_tm else NOWSTR
        ann_rows.append({"src": "HKEX", "market": "港股", "title": label[:140],
                         "time": tstr, "level": lv})
except Exception:
    pass

# 巨潮资讯（沪深）
try:
    se = f"{(NOW - timedelta(days=1)).strftime('%Y-%m-%d')}~{TODAY}"
    txt = curl("https://www.cninfo.com.cn/new/hisAnnouncement/query", timeout=25,
               extra=["-X", "POST", "-d",
                      f"pageNum=1&pageSize=30&column=szse&tabName=fulltext&plate=&stock=&searchkey=&secid=&category=&trade=&seDate={se}&sortName=&sortType=&isHLtitle=true"])
    for it in (json.loads(txt).get("announcements") or [])[:30]:
        title = re.sub(r"<[^>]+>", "", it.get("announcementTitle", ""))
        label = f"[{it.get('secName','')}] {title}"
        key = "cn:" + str(it.get("announcementId", title[:60]))
        if key in seen_ann:
            continue
        seen_ann.add(key)
        ts = it.get("announcementTime")
        tstr = datetime.fromtimestamp(ts / 1000, CST).strftime("%Y-%m-%d %H:%M") if ts else NOWSTR
        ann_rows.append({"src": "巨潮", "market": "A股", "title": label[:140],
                         "time": tstr, "level": classify(title)})
except Exception:
    pass

# 公告按级别排序，🔴 触发 alert
ORDER = {"🔴": 0, "🟡": 1, "🟢": 2}
ann_rows.sort(key=lambda x: ORDER.get(x["level"], 3))
for a in ann_rows:
    if a["level"] == "🔴":
        add_alert("🔴", a["market"], f"{a['src']}公告：{a['title'][:60]}", "高危关键词命中", None)
jdump(os.path.join(DATA, "announcements.json"), ann_rows[:80])

# ---------------- 收尾 ----------------
# 清理过期指纹
now_ts = time.time()
seen_alerts = {k: v for k, v in seen_alerts.items() if v > now_ts}
jdump(SEEN_PATH, {"ann": list(seen_ann)[-3000:], "alerts": seen_alerts})
jdump(os.path.join(DATA, "alerts_pending.json"), alerts)
jdump(os.path.join(DATA, "meta.json"), {
    "updated": NOWSTR,
    "counts": {"market": len(market_rows), "ann": len(ann_rows),
               "lhb": len(funds["lhb"]), "alerts_pending": len(alerts)}})

print(f"[{NOWSTR}] market={len(market_rows)} ann={len(ann_rows)} alerts_pending={len(alerts)}")
