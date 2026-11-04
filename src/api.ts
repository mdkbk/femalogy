// Typed client for the Femalogy API. Shapes mirror app/schemas.py in the backend.

const BASE = import.meta.env.VITE_API_URL ?? '/api'
const TOKEN_KEY = 'femalogy.token'

export type Phase = 'menstrual' | 'follicular' | 'ovulation' | 'luteal'

export interface Source {
  id: string
  authors: string
  year: number
  title: string
  journal: string
  doi: string
  url: string
}
export interface Tip {
  id: string
  category: string
  text: string
  grade: 'strong' | 'moderate' | 'weak' | 'personal'
  sources: Source[]
}
export interface PhaseGuide {
  phase: Phase
  title: string
  summary: string
  tips: Tip[]
}
export interface RedFlag {
  id: string
  text: string
}
export interface Today {
  date: string
  cycle_day: number
  phase: Phase
  phase_title: string
  is_estimate: boolean
  cycle_length_estimate: number
  period_length_estimate: number
  ovulation_day_estimate: number
  ovulation_date_estimate: string
  next_period_estimate: string
  days_until_next_period: number
  confidence: 'low' | 'medium' | 'high'
  complete_cycles_logged: number
  flags: string[]
  red_flags: RedFlag[]
  guide: PhaseGuide
  disclaimer: string
}
export interface Insight {
  id: string
  kind: 'metric' | 'symptom'
  key: string
  phase: Phase
  direction: 'lower' | 'higher' | 'often'
  area: string
  text: string
  suggestion: string
  cycles: number
  checkins: number
}
export interface Myth {
  id: string
  claim: string
  verdict: 'not_supported' | 'partly_true' | 'false'
  verdict_label: string
  text: string
  area: string
  phases: Phase[]
  sources: Source[]
}
export interface SyncArea {
  id: string
  title: string
  personal: Insight[]
  tips: Tip[]
  myths: Myth[]
}
export interface Sync {
  date: string
  phase: Phase
  phase_title: string
  phase_summary: string
  cycle_day: number
  personal_status: 'learning' | 'ready'
  cycles_with_checkins: number
  cycles_needed: number
  areas: SyncArea[]
  disclaimer: string
}
export interface PlanBlock {
  phase: Phase
  title: string
  start: string
  end: string
  days: number
  is_prediction: boolean
  personal: Insight[]
}
export interface Plan {
  start: string
  blocks: PlanBlock[]
  personal_status: 'learning' | 'ready'
  disclaimer: string
}
export interface Period {
  id: string
  start_date: string
  end_date: string | null
}
export interface CalendarDay {
  date: string
  phase: Phase
}
export interface CheckIn {
  id: string
  day: string
  mood: number | null
  energy: number | null
  sleep_quality: number | null
  symptoms: string[]
  notes: string | null
  phase_at_checkin: Phase | null
  red_flags: RedFlag[]
}
export type CheckInInput = Omit<CheckIn, 'id' | 'phase_at_checkin' | 'red_flags'>
export interface Profile {
  id: string
  email: string
  display_name: string | null
  avg_cycle_length: number | null
  avg_period_length: number | null
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}
export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* storage blocked: the session just won't survive a reload */
  }
}

let onUnauthorized: () => void = () => {}
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn
}

function messageFrom(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const d = (body as { detail: unknown }).detail
    if (typeof d === 'string') return d
    if (Array.isArray(d) && d.length) {
      const first = d[0] as { msg?: string }
      return (first.msg ?? fallback).replace(/^Value error, /, '')
    }
  }
  return fallback
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body && typeof init.body === 'string') headers.set('Content-Type', 'application/json')
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, { ...init, headers })
  } catch {
    throw new ApiError(0, "Can't reach the Femalogy server. Is the backend running?")
  }
  if (res.status === 204) return undefined as T
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    if (res.status === 401 && token) onUnauthorized()
    throw new ApiError(res.status, messageFrom(body, `Something went wrong (${res.status})`))
  }
  return body as T
}

/** The user's local date as YYYY-MM-DD. Always sent so phases match her day, not the server's. */
export function localToday(): string {
  const d = new Date()
  return toISO(d)
}
export function toISO(d: Date): string {
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

const q = (params: Record<string, string | number | undefined>) => {
  const s = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined) s.set(k, String(v))
  return `?${s}`
}

export const api = {
  register: (email: string, password: string, display_name?: string) =>
    request<{ access_token: string }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, display_name: display_name || null }),
    }),
  login: (email: string, password: string) =>
    request<{ access_token: string }>('/auth/login', {
      method: 'POST',
      body: new URLSearchParams({ username: email, password }),
    }),
  me: () => request<Profile>('/me'),
  deleteMe: () => request<void>('/me', { method: 'DELETE' }),

  today: (on = localToday()) => request<Today>(`/today${q({ on })}`),
  sync: (on = localToday()) => request<Sync>(`/sync${q({ on })}`),
  plan: (on = localToday(), days = 56) => request<Plan>(`/plan${q({ on, days })}`),
  calendar: (on: string, days: number) => request<CalendarDay[]>(`/calendar${q({ on, days })}`),

  periods: () => request<Period[]>('/periods'),
  addPeriod: (start_date: string, end_date: string | null) =>
    request<Period>('/periods', { method: 'POST', body: JSON.stringify({ start_date, end_date }) }),
  updatePeriod: (id: string, start_date: string, end_date: string | null) =>
    request<Period>(`/periods/${id}`, { method: 'PATCH', body: JSON.stringify({ start_date, end_date }) }),
  deletePeriod: (id: string) => request<void>(`/periods/${id}`, { method: 'DELETE' }),

  checkins: () => request<CheckIn[]>('/checkins'),
  saveCheckin: (c: CheckInInput) => request<CheckIn>('/checkins', { method: 'PUT', body: JSON.stringify(c) }),

  guide: (phase: Phase) => request<PhaseGuide>(`/guide/${phase}`),
  myths: () => request<Myth[]>('/myths'),
}
