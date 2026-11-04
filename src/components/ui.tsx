import { useEffect, useRef, useState, type ReactNode } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { api, localToday, type Insight, type Myth, type Phase, type Tip } from '../api'
import { useAuth } from '../auth'
import { CATEGORY, GRADE, PHASE, PHASES, shortCite } from '../lib'

export function Logo() {
  return (
    <svg width="30" height="30" viewBox="0 0 30 30" aria-hidden="true">
      <circle cx="15" cy="15" r="11" fill="none" stroke="#E9B49B" strokeWidth="3" />
      <path d="M15 4 A11 11 0 0 1 26 15" fill="none" stroke="#A93F57" strokeWidth="3" strokeLinecap="round" />
      <circle cx="26" cy="15" r="3" fill="#A93F57" />
    </svg>
  )
}

export function InfoIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" style={{ flex: 'none' }}>
      <circle cx="12" cy="12" r="9.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M12 11v6M12 7.5v.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )
}

export function WarnIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" style={{ flex: 'none', marginTop: 1 }}>
      <path d="M12 3.5l9.5 16.5h-19z" fill="none" stroke="#9C3A2A" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M12 10v4.5M12 17.2v.3" stroke="#9C3A2A" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )
}

export function CheckIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export function LockIcon({ color = 'currentColor' }: { color?: string }) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" style={{ flex: 'none' }}>
      <rect x="5" y="10.5" width="14" height="10" rx="2.5" fill="none" stroke={color} strokeWidth="1.8" />
      <path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5" fill="none" stroke={color} strokeWidth="1.8" />
    </svg>
  )
}

function AccountMenu() {
  const { user, signOut } = useAuth()
  const [open, setOpen] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
        setConfirming(false)
      }
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [open])

  const initial = (user?.display_name || user?.email || '?').trim()[0]?.toUpperCase()
  return (
    <div className="account" ref={ref}>
      <button type="button" className="avatar" aria-label="Account" aria-expanded={open} onClick={() => setOpen(!open)}>
        {initial}
      </button>
      {open && (
        <div className="menu">
          <p>{user?.email}</p>
          <button type="button" onClick={() => { signOut(); navigate('/') }}>Sign out</button>
          {!confirming ? (
            <button type="button" className="danger" onClick={() => setConfirming(true)}>Delete my account</button>
          ) : (
            <button
              type="button"
              className="danger"
              onClick={async () => {
                await api.deleteMe()
                signOut()
                navigate('/')
              }}
            >
              Yes, delete everything for good
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export function Layout() {
  const links: [string, string][] = [['/', 'Today'], ['/plan', 'Plan'], ['/check-in', 'Check-in'], ['/guide', 'Guide']]
  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <NavLink to="/" className="brand">
            <Logo />
            <span>femalogy</span>
          </NavLink>
          <nav aria-label="Main" className="nav">
            {links.map(([to, label]) => (
              <NavLink key={to} to={to} end className={({ isActive }) => (isActive ? 'active' : undefined)}>
                {label}
              </NavLink>
            ))}
          </nav>
          <AccountMenu />
        </div>
      </header>
      <Outlet />
    </>
  )
}

/** The cycle ring: real segment sizes from her estimates, marker on today. */
export function CycleRing({ day, length, periodLength, ovulationDay, phase }: {
  day: number; length: number; periodLength: number; ovulationDay: number; phase: Phase
}) {
  const r = 110
  const C = 2 * Math.PI * r
  const per = C / length
  const segs: [Phase, number, number][] = [
    ['menstrual', 0, periodLength],
    ['follicular', periodLength, ovulationDay - 2],
    ['ovulation', ovulationDay - 2, ovulationDay + 1],
    ['luteal', ovulationDay + 1, length],
  ]
  const cap = 10 // round caps stick out by half the stroke width
  const gap = 3
  const shown = Math.min(day, length)
  const angle = ((shown - 0.5) / length) * 2 * Math.PI
  const mx = 140 + r * Math.sin(angle)
  const my = 140 - r * Math.cos(angle)
  return (
    <div className="ring">
      <svg className="fx-ring" viewBox="0 0 280 280" role="img" aria-label={`Cycle day ${day} of about ${length}, ${PHASE[phase].name}`}>
        <g transform="rotate(-90 140 140)">
          {segs.map(([p, from, to]) => {
            const start = from * per + cap + gap
            const len = Math.max(0.1, (to - from) * per - 2 * (cap + gap))
            return (
              <circle key={p} cx="140" cy="140" r={r} fill="none" stroke={PHASE[p].color} strokeWidth="20"
                strokeLinecap="round" strokeDasharray={`${len} ${C}`} strokeDashoffset={-start} />
            )
          })}
        </g>
        <circle className="fx-halo" cx={mx} cy={my} r="13" fill={PHASE[phase].color} />
        <circle cx={mx} cy={my} r="13" fill="#fff" stroke="#3B2A30" strokeWidth="3" />
      </svg>
      <div className="ring-center">
        <span className="eyebrow">Day</span>
        <span className="big">{day}</span>
        <span className="muted">of about {length}</span>
      </div>
    </div>
  )
}

export function PhaseLegend() {
  return (
    <ul className="legend" aria-label="Phase colours">
      {PHASES.map((p) => (
        <li key={p}>
          <span className="dot" style={{ background: PHASE[p].color }} aria-hidden="true" />
          {PHASE[p].label}
        </li>
      ))}
    </ul>
  )
}

export function TipCard({ tip }: { tip: Tip }) {
  const g = GRADE[tip.grade]
  return (
    <article className="tip fx-card">
      <div className="tip-top">
        <span className="eyebrow">{CATEGORY[tip.category] ?? tip.category}</span>
        <span className="badge" style={{ background: g.bg, color: g.fg }}>{g.label}</span>
      </div>
      <p className="text">{tip.text}</p>
      <div className="cites">
        {tip.sources.map((s) => (
          <a key={s.id} href={s.url} target="_blank" rel="noreferrer" title={`${s.title}. ${s.journal}`}>
            {shortCite(s)}
          </a>
        ))}
      </div>
    </article>
  )
}

export function InsightCard({ insight }: { insight: Insight }) {
  return (
    <article className="personal fx-card">
      <span className="eyebrow">From your check-ins</span>
      <strong>{insight.text}</strong>
      <p>{insight.suggestion}</p>
    </article>
  )
}

const VERDICT_STYLE: Record<Myth['verdict'], { bg: string; fg: string; label: string }> = {
  false: { bg: '#F7DDE3', fg: '#7E2C40', label: 'False' },
  not_supported: { bg: '#FBEDD5', fg: '#7A4E0C', label: 'Not supported by research' },
  partly_true: { bg: '#E4EFE6', fg: '#2D5B3C', label: 'Partly true' },
}

export function MythCard({ myth }: { myth: Myth }) {
  const v = VERDICT_STYLE[myth.verdict]
  return (
    <article className="myth fx-card">
      <div className="tip-top">
        <span className="eyebrow">Myth check</span>
        <span className="badge" style={{ background: v.bg, color: v.fg }}>{v.label}</span>
      </div>
      <p className="claim">“{myth.claim}”</p>
      <p>{myth.text}</p>
      <div className="cites">
        {myth.sources.map((s) => (
          <a key={s.id} href={s.url} target="_blank" rel="noreferrer" title={`${s.title}. ${s.journal}`}>
            {shortCite(s)}
          </a>
        ))}
      </div>
    </article>
  )
}

export function Loading({ height = 320 }: { height?: number }) {
  return <div className="skeleton" style={{ height }} role="status" aria-label="Loading" />
}

export function ErrorBox({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div className="alert" role="alert">
      <WarnIcon />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <p>{message}</p>
        {retry && <button type="button" className="btn small quiet" onClick={retry}>Try again</button>}
      </div>
    </div>
  )
}

/** Shown wherever the API says there's no period logged yet. */
export function FirstPeriod({ onDone }: { onDone: () => void }) {
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  return (
    <section className="hero fx-up" style={{ background: '#F7DDE3' }}>
      <div className="hero-text">
        <span className="eyebrow">Let's start</span>
        <h1>When did your last period start?</h1>
        <p className="muted" style={{ maxWidth: 520 }}>
          That's all Femalogy needs to work out your phase. Add a few past periods too and the estimates get better straight away.
        </p>
        <form
          className="row"
          style={{ alignItems: 'flex-end' }}
          onSubmit={async (e) => {
            e.preventDefault()
            setBusy(true)
            setErr('')
            try {
              await api.addPeriod(start, end || null)
              onDone()
            } catch (x) {
              setErr((x as Error).message)
            } finally {
              setBusy(false)
            }
          }}
        >
          <label className="field">Started
            <input type="date" required max={localToday()} value={start} onChange={(e) => setStart(e.target.value)} />
          </label>
          <label className="field">Ended (optional)
            <input type="date" min={start || undefined} max={localToday()} value={end} onChange={(e) => setEnd(e.target.value)} />
          </label>
          <button className="btn" disabled={busy || !start}>Save</button>
        </form>
        {err && <p className="error" role="alert">{err}</p>}
      </div>
    </section>
  )
}

export function Disclaimer({ children }: { children?: ReactNode }) {
  return (
    <footer className="foot">
      <p>Evidence grades: Strong = large cohorts or consistent reviews · Moderate = reviews of small trials or one large trial · Weak = single small trials · Learns from you = research doesn't support a general rule, so your check-ins decide.</p>
      <p>{children ?? 'Femalogy gives general information, not medical advice. Phase dates are estimates and must not be used for contraception.'}</p>
    </footer>
  )
}
