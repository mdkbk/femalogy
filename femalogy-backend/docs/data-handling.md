# How Femalogy handles data

For whoever runs Femalogy. The in-app version for users is `femalogy-web/src/pages/Privacy.tsx`, so keep the two in step.

## What is stored

| Data | Table | How it's stored |
|---|---|---|
| Email, display name | `users` | Plain text (needed to sign in and greet her) |
| Password | `users.password_hash` | Argon2id hash only. Nobody can read the password back. |
| Consent time | `users.consented_at` | When she agreed to health-data storage at sign-up (GDPR art. 9 explicit consent) |
| Onboarding answers | `users.avg_cycle_length`, `avg_period_length` | Plain numbers |
| Period dates | `periods` | Plain dates (the engine needs to compute with them) |
| Check-ins: mood, energy, sleep, symptoms | `checkins` | Plain values (the pattern engine needs them) |
| Check-in notes | `checkins.notes` | **Encrypted by the app** (Fernet, AES-128 + HMAC) with `FIELD_ENCRYPTION_KEY` before saving |
| Signed-in devices | `user_sessions` | SHA-256 of the session token only. The token itself is never stored. |
| Login attempts | `login_attempts` | Keyed hashes (HMAC with `SECRET_KEY`) of email and IP, pruned after 24 hours |

Nothing else is collected: no analytics, no ads, no third-party scripts or fonts, no AI services. All predictions and patterns are computed by our own code on our own server.

## Where it lives

- **App server:** Render, region Frankfurt (EU). Runs the code and keeps no data on disk.
- **Database:** Neon PostgreSQL, region Frankfurt (EU). Encrypted at rest by Neon, and connections require TLS (`sslmode=require`).
- **The user's browser:** only an httpOnly, Secure, SameSite=Lax session cookie. Page scripts can't read it, and no health data is kept in browser storage. API responses are sent with `Cache-Control: no-store`.

Render and Neon are processors acting on our behalf. Before real users, sign their Data Processing Agreements (both offer one).

## How access is protected

- **Sign-in:** Argon2id passwords. Common and very weak passwords are refused. Unknown emails and wrong passwords get the same message and take the same time, so attackers can't tell which emails have accounts.
- **Brute force:** after 10 wrong passwords for one email (or 30 from one network) within 15 minutes, sign-in pauses for 5 minutes, with a message saying how long to wait. A successful sign-in resets the count. Sign-ups are limited to 10 per network per hour. Per-email is the real protection, since IPs can be rotated.
- **Sessions:** random 256-bit tokens, 30 days. Signing out deletes the session on the server. "Sign out on all devices" deletes all of them.
- **Cross-site requests:** any request that changes data must come from Femalogy's own pages. The Origin header is checked, so other sites can't act with her cookie.
- **Headers:** a strict Content-Security-Policy (only our own scripts, styles and fonts), HSTS, no framing, nosniff, and a locked-down Permissions-Policy.
- **Startup checks:** the app refuses to start in production with a weak `SECRET_KEY`, a missing or invalid `FIELD_ENCRYPTION_KEY`, or SQLite.
- **Container:** runs as a non-root user. Secrets come only from environment variables and are never in the repo or the image.

## Her rights, built in

- **Access and portability:** Account menu → Download my data (`GET /api/me/export`, a JSON file with everything).
- **Erasure:** Account menu → Delete my account. It removes the user, periods, check-ins and sessions immediately. Neon's restore history keeps old data only until that window expires.
- **Withdraw consent:** deleting the account does this.

## Who can see what

- **She sees only her own data.** Every query is scoped to the signed-in user.
- **Whoever has the Neon credentials** (the operator) can technically read everything except notes. Keep those credentials to as few people as possible, turn on 2FA on Render, Neon and GitHub, and never paste them into chats or tickets.
- **`FIELD_ENCRYPTION_KEY`:** if it's lost, notes can't be decrypted. If it leaks, notes can be. Store it in a password manager, separately from the database credentials.

## Before launch (still open)

1. Put a contact email in `CONTACT_EMAIL` in `Privacy.tsx`. GDPR requires a way to reach the data controller.
2. Sign the Render and Neon DPAs.
3. Add password reset by email. This needs an email provider; until then, a forgotten password means a new account.
4. Turn on 2FA everywhere: GitHub, Render and Neon.
5. Medical content review: a gynecologist and nutritionist, plus sources for the red-flag texts.
6. Depending on where users are, check whether a full privacy policy and a lawyer's review are needed. This document is engineering notes, not legal advice.
