import { useState } from 'react'
import { useAuth } from '../auth'
import { LockIcon, Logo } from '../components/ui'

export default function Welcome() {
  const { signIn, signUp } = useAuth()
  const [mode, setMode] = useState<'signin' | 'signup'>('signin')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const up = mode === 'signup'

  return (
    <div className="welcome">
      <header style={{ maxWidth: 1120, width: '100%', margin: '0 auto', padding: '18px 24px' }}>
        <div className="brand"><Logo /><span>femalogy</span></div>
      </header>
      <main>
        <section className="fx-up" style={{ flex: '999 1 420px', display: 'flex', flexDirection: 'column', gap: 24 }}>
          <h1>Cycle syncing, <span style={{ color: 'var(--accent)', fontStyle: 'italic' }}>backed by research.</span></h1>
          <p style={{ fontSize: 19, color: 'var(--ink-2)', maxWidth: 520 }}>
            Femalogy shows which phase you're in, what research really says about it, and over time, how each phase actually feels for you.
          </p>
          <ul className="points">
            <li>
              <span className="ic" style={{ background: '#F7DDE3' }} aria-hidden="true">
                <svg width="20" height="20" viewBox="0 0 24 24"><path d="M5 4.5h11a3 3 0 0 1 3 3V20H8a3 3 0 0 1-3-3z M5 17a3 3 0 0 1 3-3h11" fill="none" stroke="#A93F57" strokeWidth="1.8" strokeLinejoin="round" /></svg>
              </span>
              <div><strong style={{ display: 'block' }}>Every tip has a source</strong><span className="muted">With an evidence grade, so you know how sure the research is.</span></div>
            </li>
            <li>
              <span className="ic" style={{ background: '#EFE5F2' }} aria-hidden="true">
                <svg width="20" height="20" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8" fill="none" stroke="#7A5A8A" strokeWidth="1.8" /><path d="M12 7.5V12l3 2" fill="none" stroke="#7A5A8A" strokeWidth="1.8" strokeLinecap="round" /></svg>
              </span>
              <div><strong style={{ display: 'block' }}>Synced to you, not to a template</strong><span className="muted">After two cycles of check-ins, your plan uses your own patterns.</span></div>
            </li>
            <li>
              <span className="ic" style={{ background: '#FBEED6' }} aria-hidden="true"><LockIcon color="#8A5A14" /></span>
              <div><strong style={{ display: 'block' }}>Private by design</strong><span className="muted">Your notes are encrypted, and you can delete everything at any time.</span></div>
            </li>
          </ul>
        </section>

        <section className="auth-card fx-up fx-d1" aria-label="Account">
          <div role="tablist" aria-label="Sign in or create account" className="seg">
            <button type="button" role="tab" aria-selected={!up} onClick={() => { setMode('signin'); setErr('') }}>Sign in</button>
            <button type="button" role="tab" aria-selected={up} onClick={() => { setMode('signup'); setErr('') }}>Create account</button>
          </div>
          <form style={{ display: 'flex', flexDirection: 'column', gap: 16 }} onSubmit={async (e) => {
            e.preventDefault()
            setBusy(true)
            setErr('')
            try {
              if (up) await signUp(email, password, name.trim() || undefined)
              else await signIn(email, password)
            } catch (x) {
              setErr((x as Error).message)
            } finally {
              setBusy(false)
            }
          }}>
            {up && (
              <label className="field">What should we call you?
                <input type="text" autoComplete="nickname" maxLength={100} value={name} onChange={(e) => setName(e.target.value)} />
              </label>
            )}
            <label className="field">Email
              <input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </label>
            <label className="field">Password
              <input type="password" required minLength={up ? 8 : undefined} autoComplete={up ? 'new-password' : 'current-password'}
                value={password} onChange={(e) => setPassword(e.target.value)} />
            </label>
            {up && <p className="small muted" style={{ marginTop: -8 }}>At least 8 characters.</p>}
            {err && <p className="error small" role="alert">{err}</p>}
            <button className="btn" disabled={busy} style={{ minHeight: 52, fontSize: 17 }}>
              {busy ? 'One moment…' : up ? 'Create my account' : 'Sign in'}
            </button>
          </form>
          <p className="small muted" style={{ textAlign: 'center' }}>General information, not medical advice. Dates are estimates and not for contraception.</p>
        </section>
      </main>
    </div>
  )
}
