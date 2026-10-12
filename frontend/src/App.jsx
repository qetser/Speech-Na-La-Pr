import { useState } from 'react'
import Landing from './pages/Landing'
import Dashboard from './pages/Dashboard'
import './App.css'

function App() {
  const [view, setView] = useState('landing') // 'landing' | 'app'
  return view === 'landing'
    ? <Landing onStart={() => setView('app')} />
    : <Dashboard onHome={() => setView('landing')} />
}

export default App
