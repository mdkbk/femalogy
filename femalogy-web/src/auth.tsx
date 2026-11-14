import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, setUnauthorizedHandler, type Profile } from './api'

interface AuthState {
  user: Profile | null
  ready: boolean
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string, name: string | undefined, consent: boolean) => Promise<void>
  signOut: () => Promise<void>
  /** Forget the user locally when the server says the session is gone. */
  clear: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Profile | null>(null)
  const [ready, setReady] = useState(false)

  const clear = useCallback(() => setUser(null), [])

  const signOut = useCallback(async () => {
    try {
      await api.logout() // ends the session on the server, not just in this tab
    } finally {
      setUser(null)
    }
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(clear)
    // the session cookie is httpOnly, so ask the server whether she's signed in
    api
      .me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setReady(true))
  }, [clear])

  const value = useMemo<AuthState>(
    () => ({
      user,
      ready,
      signOut,
      clear,
      signIn: async (email, password) => {
        await api.login(email, password)
        setUser(await api.me())
      },
      signUp: async (email, password, name, consent) => {
        await api.register(email, password, name, consent)
        setUser(await api.me())
      },
    }),
    [user, ready, signOut, clear],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
