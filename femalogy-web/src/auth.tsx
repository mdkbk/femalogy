import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, getToken, setToken, setUnauthorizedHandler, type Profile } from './api'

interface AuthState {
  user: Profile | null
  ready: boolean
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string, name?: string) => Promise<void>
  signOut: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Profile | null>(null)
  const [ready, setReady] = useState(false)

  const signOut = useCallback(() => {
    setToken(null)
    setUser(null)
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(signOut)
    if (!getToken()) {
      setReady(true)
      return
    }
    api
      .me()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setReady(true))
  }, [signOut])

  const value = useMemo<AuthState>(
    () => ({
      user,
      ready,
      signOut,
      signIn: async (email, password) => {
        const { access_token } = await api.login(email, password)
        setToken(access_token)
        setUser(await api.me())
      },
      signUp: async (email, password, name) => {
        const { access_token } = await api.register(email, password, name)
        setToken(access_token)
        setUser(await api.me())
      },
    }),
    [user, ready, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
