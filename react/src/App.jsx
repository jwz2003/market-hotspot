import { useState, useEffect } from 'react'

const TABS = [
  { id: 'radar', name: '⚡ 异动雷达' },
  { id: 'ann', name: '📋 公告披露' },
  { id: 'funds', name: '💰 资金流向' },
  { id: 'market', name: '📊 行情全览' },
]
const CAT_NAME = { index: '股指', commodity: '商品', forex: '外汇', crypto: '加密' }
const LV_COLOR = { '🔴': 'text-red-400', '🟡': 'text-yellow-400', '🟢': 'text-emerald-500' }

function useData(file) {
  const [data, setData] = useState(null)
  useEffect(() => {
    fetch(`data/${file}?t=${Date.now()}`)
      .then(r => r.ok ? r.json() : null)
      .then(setData).catch(() => setData(null))
  }, [file])
  return data
}

const fmtPct = p => (p > 0 ? '+' : '') + p?.toFixed(2) + '%'
const pctCls = p => p > 0 ? 'text-term-up' : p < 0 ? 'text-term-down' : 'text-term-dim'

function Ticker({ market }) {
  if (!market) return null
  const items = [...market].sort((a, b) => Math.abs(b.pct) - Math.abs(a.pct)).slice(0, 14)
  return (
    <div className="flex gap-5 overflow-x-auto whitespace-nowrap border-b border-term-border bg-term-panel px-4 py-2 font-mono text-xs">
      {items.map(m => (
        <span key={m.symbol} className="flex gap-1.5">
          <span className="text-term-dim">{m.name}</span>
          <span className={pctCls(m.pct)}>{fmtPct(m.pct)}</span>
        </span>
      ))}
    </div>
  )
}

function Panel({ title, children, right }) {
  return (
    <div className="rounded border border-term-border bg-term-panel">
      <div className="flex items-center justify-between border-b border-term-border px-3 py-2">
        <h3 className="text-xs font-semibold tracking-wider text-term-amber">{title}</h3>
        {right}
      </div>
      <div className="p-2">{children}</div>
    </div>
  )
}

function Radar({ market, alerts }) {
  const groups = ['index', 'commodity', 'forex', 'crypto']
  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
      <Panel title={`当前异动 ALERTS (${alerts?.length || 0})`}>
        {!alerts?.length ? (
          <div className="py-6 text-center text-xs text-term-dim">✓ 无未处理异动，市场平稳</div>
        ) : (
          <table className="w-full text-xs">
            <tbody>
              {alerts.map((a, i) => (
                <tr key={i} className="border-b border-term-border/50 last:border-0 hover:bg-white/5">
                  <td className="w-8 py-1.5">{a.level}</td>
                  <td className="w-12 text-term-dim">{a.market}</td>
                  <td className="font-medium">{a.title}</td>
                  <td className="hidden text-right text-term-dim sm:table-cell">{a.time?.slice(5, 16)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
      {groups.map(g => (
        <Panel key={g} title={`${CAT_NAME[g]} ${g.toUpperCase()}`}>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-3">
            {(market || []).filter(m => m.cat === g).map(m => (
              <div key={m.symbol} className="flex items-baseline justify-between rounded px-2 py-1.5 font-mono text-xs hover:bg-white/5">
                <span className="text-term-dim">{m.name}</span>
                <span className="text-right">
                  <span className="mr-2 text-term-text">{m.price?.toLocaleString()}</span>
                  <span className={pctCls(m.pct)}>{fmtPct(m.pct)}</span>
                </span>
              </div>
            ))}
          </div>
        </Panel>
      ))}
    </div>
  )
}

function Announcements({ ann }) {
  const [mkt, setMkt] = useState('全部')
  const markets = ['全部', ...new Set((ann || []).map(a => a.market))]
  const rows = (ann || []).filter(a => mkt === '全部' || a.market === mkt)
  return (
    <Panel title="公告披露 FILINGS" right={
      <div className="flex gap-1">
        {markets.map(m => (
          <button key={m} onClick={() => setMkt(m)}
            className={`rounded px-2 py-0.5 text-xs ${mkt === m ? 'bg-term-amber text-black' : 'text-term-dim hover:text-term-text'}`}>
            {m}
          </button>
        ))}
      </div>
    }>
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-term-border text-left text-term-dim">
            <th className="w-6 py-1"></th><th className="w-16">来源</th>
            <th>标题</th><th className="w-28 text-right">时间</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((a, i) => (
            <tr key={i} className="border-b border-term-border/40 last:border-0 hover:bg-white/5">
              <td className={`py-1.5 ${LV_COLOR[a.level]}`}>{a.level}</td>
              <td className="text-term-dim">{a.src}</td>
              <td className="pr-2">{a.title}</td>
              <td className="text-right font-mono text-term-dim">{String(a.time).slice(5, 16)}</td>
            </tr>
          ))}
          {!rows.length && <tr><td colSpan="4" className="py-6 text-center text-term-dim">暂无数据</td></tr>}
        </tbody>
      </table>
    </Panel>
  )
}

function Funds({ funds }) {
  const ns = funds?.north_south
  const parseNS = (arr) => {
    if (!arr?.length) return null
    const last = arr[arr.length - 1].split(',')
    return { date: last[0], buy: (+last[2] / 1e8).toFixed(1) }
  }
  const north = parseNS(ns?.sh2hk), south = parseNS(ns?.hk2sh)
  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
      <Panel title="沪深港通 CONNECT">
        <div className="grid grid-cols-2 gap-2 p-1">
          <div className="rounded bg-white/5 p-3 text-center">
            <div className="text-xs text-term-dim">北向买入额(亿)</div>
            <div className="mt-1 font-mono text-xl text-term-text">{north?.buy ?? '—'}</div>
            <div className="text-xs text-term-dim">{north?.date || ''}</div>
          </div>
          <div className="rounded bg-white/5 p-3 text-center">
            <div className="text-xs text-term-dim">南向买入额(亿)</div>
            <div className="mt-1 font-mono text-xl text-term-text">{south?.buy ?? '—'}</div>
            <div className="text-xs text-term-dim">{south?.date || ''}</div>
          </div>
        </div>
        <div className="mt-2 px-1">
          <div className="mb-1 text-xs text-term-dim">加密资金费率（永续）</div>
          {(funds?.funding || []).map(f => (
            <div key={f.symbol} className="flex justify-between font-mono text-xs">
              <span>{f.symbol}/USDT</span>
              <span className={Math.abs(f.rate) >= 0.1 ? 'text-term-amber' : 'text-term-dim'}>{f.rate > 0 ? '+' : ''}{f.rate}%</span>
            </div>
          ))}
        </div>
      </Panel>
      <Panel title={`龙虎榜 TOP (${funds?.lhb?.length || 0})`}>
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-term-border text-left text-term-dim">
              <th className="py-1">名称</th><th className="text-right">涨幅</th>
              <th className="text-right">上榜额</th><th className="hidden text-right sm:table-cell">解读</th>
            </tr>
          </thead>
          <tbody>
            {(funds?.lhb || []).map((r, i) => (
              <tr key={i} className="border-b border-term-border/40 last:border-0 hover:bg-white/5">
                <td className="py-1.5">{r.name} <span className="font-mono text-term-dim">{r.code}</span></td>
                <td className={`text-right font-mono ${pctCls(r.chg)}`}>{fmtPct(r.chg)}</td>
                <td className="text-right font-mono">{r.amt ? (r.amt / 1e8).toFixed(2) + '亿' : '—'}</td>
                <td className="hidden max-w-[180px] truncate text-right text-term-dim sm:table-cell">{r.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>
    </div>
  )
}

function Market({ market }) {
  const rows = [...(market || [])].sort((a, b) => Math.abs(b.pct) - Math.abs(a.pct))
  return (
    <Panel title="行情全览 OVERVIEW（按波动排序）">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-term-border text-left text-term-dim">
            <th className="w-14 py-1">类别</th><th>名称</th>
            <th className="text-right">现价</th><th className="text-right">涨跌</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((m, i) => (
            <tr key={i} className="border-b border-term-border/40 last:border-0 hover:bg-white/5">
              <td className="py-1.5 text-term-dim">{CAT_NAME[m.cat]}</td>
              <td>{m.name} <span className="font-mono text-term-dim">{m.symbol}</span></td>
              <td className="text-right font-mono">{m.price?.toLocaleString()}</td>
              <td className={`text-right font-mono ${pctCls(m.pct)}`}>{fmtPct(m.pct)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  )
}

export default function App() {
  const [tab, setTab] = useState('radar')
  const market = useData('market.json')
  const ann = useData('announcements.json')
  const funds = useData('funds.json')
  const alerts = useData('alerts_pending.json')
  const meta = useData('meta.json')

  return (
    <div className="mx-auto min-h-screen max-w-6xl">
      <header className="flex items-center justify-between border-b border-term-border bg-term-panel px-4 py-2.5">
        <div className="flex items-center gap-2">
          <span className="text-term-amber">◉</span>
          <h1 className="text-sm font-bold tracking-widest">全球热点雷达</h1>
          <span className="rounded bg-term-amber/20 px-1.5 py-0.5 font-mono text-[10px] text-term-amber">EXCHANGE-GRADE</span>
        </div>
        <div className="font-mono text-xs text-term-dim">
          更新 {meta?.updated || '—'}
          {alerts?.length > 0 && <span className="ml-2 rounded bg-red-500/20 px-1.5 py-0.5 text-red-400">{alerts.length} 异动</span>}
        </div>
      </header>
      <Ticker market={market} />
      <nav className="flex gap-1 border-b border-term-border px-4 py-2">
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`rounded px-3 py-1 text-xs ${tab === t.id ? 'bg-term-amber font-semibold text-black' : 'text-term-dim hover:text-term-text'}`}>
            {t.name}
          </button>
        ))}
      </nav>
      <main className="p-3">
        {tab === 'radar' && <Radar market={market} alerts={alerts} />}
        {tab === 'ann' && <Announcements ann={ann} />}
        {tab === 'funds' && <Funds funds={funds} />}
        {tab === 'market' && <Market market={market} />}
      </main>
      <footer className="border-t border-term-border px-4 py-2 text-center font-mono text-[10px] text-term-dim">
        数据源: SEC EDGAR · HKEXnews · 巨潮资讯 · Yahoo Finance · Binance · 东方财富 | 每30分钟自动更新
      </footer>
    </div>
  )
}
