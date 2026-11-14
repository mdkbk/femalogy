import { Link } from 'react-router-dom'
import { useAuth } from '../auth'
import { Logo } from '../components/ui'

// Set this before launch: the address people write to about their data (required by GDPR).
const CONTACT_EMAIL = ''

export default function Privacy() {
  const { user } = useAuth()
  return (
    <>
      {!user && (
        <header style={{ maxWidth: 1120, width: '100%', margin: '0 auto', padding: '18px 24px' }}>
          <Link to="/" className="brand"><Logo /><span>femalogy</span></Link>
        </header>
      )}
      <main className="page narrow">
        <div className="page-head">
          <h1>How we handle your data</h1>
          <p className="muted">In plain words: what Femalogy stores, where, how it's protected, and what you can do about it.</p>
        </div>

        <article className="card prose">
          <h2>What we store</h2>
          <ul>
            <li><strong>Your account:</strong> email, the name you chose, and your password as a one-way hash (we can't read it).</li>
            <li><strong>Your cycle:</strong> the period dates you log, and any average cycle length you tell us.</li>
            <li><strong>Your check-ins:</strong> mood, energy, sleep, symptoms and notes.</li>
            <li><strong>When you agreed</strong> to us storing this, and the devices you're signed in on.</li>
          </ul>

          <h2>What we don't do</h2>
          <ul>
            <li>No ads, no selling or sharing your data, no tracking or analytics tools.</li>
            <li>No third-party scripts or fonts: the app loads everything from our own server.</li>
            <li>Your estimates are worked out by our own code. Your data isn't sent to any AI service.</li>
          </ul>

          <h2>Where it's stored</h2>
          <ul>
            <li>In the European Union (Frankfurt, Germany): the app runs on Render and the database on Neon (PostgreSQL).</li>
            <li>Both providers only store and run things for us. They don't use your data for anything else.</li>
          </ul>

          <h2>How it's protected</h2>
          <ul>
            <li>Everything travels encrypted (HTTPS), and the database is encrypted on disk.</li>
            <li>Your check-in notes get an extra layer: they're encrypted with our own key before being saved, so they stay unreadable even inside the database.</li>
            <li>Passwords are hashed with Argon2id. Sign-in is protected against password guessing.</li>
            <li>You stay signed in with a secure cookie that page scripts can't read. Signing out ends the session on our server.</li>
          </ul>

          <h2>Your choices</h2>
          <ul>
            <li><strong>Download</strong> everything we store about you, any time (account menu → Download my data).</li>
            <li><strong>Delete</strong> your account and all your data, any time (account menu → Delete my account). It's removed straight away. Database backups are kept for a short period by our provider and then disappear too.</li>
            <li><strong>Sign out on all devices</strong> if you lose a phone.</li>
          </ul>

          <h2>Good to know</h2>
          <ul>
            <li>Femalogy gives general information, not medical advice. Dates are estimates and must not be used for contraception.</li>
            {CONTACT_EMAIL && <li>Questions or requests about your data: <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a></li>}
          </ul>
        </article>
        {!user && <Link to="/" className="link-strong">Back to sign in</Link>}
      </main>
    </>
  )
}
