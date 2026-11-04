import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth'
import { Layout, Loading } from './components/ui'
import Checkin from './pages/Checkin'
import Guide from './pages/Guide'
import Plan from './pages/Plan'
import Today from './pages/Today'
import Welcome from './pages/Welcome'
import './styles.css'

function App() {
  const { user, ready } = useAuth()
  if (!ready) {
    return <main className="page"><Loading /></main>
  }
  if (!user) return <Welcome />
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Today />} />
        <Route path="plan" element={<Plan />} />
        <Route path="check-in" element={<Checkin />} />
        <Route path="guide" element={<Guide />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
