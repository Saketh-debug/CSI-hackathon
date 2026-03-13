import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import Dashboard from './pages/Dashboard'
import Heatmap from './pages/Heatmap'
import TreeCanopy from './pages/TreeCanopy'
import CoolPathRouter from './pages/CoolPathRouter'
import Messaging from './pages/Messaging'
import MobileCoolPathRouter from './pages/MobileCoolPathRouter'
import ChatBot from './components/ChatBot'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/heatmap" element={<Heatmap />} />
        <Route path="/canopy" element={<TreeCanopy />} />
        <Route path="/router" element={<CoolPathRouter />} />
        <Route path="/messaging" element={<Messaging />} />
        <Route path="/mobile-router" element={<MobileCoolPathRouter />} />
      </Routes>
      {/* EcoAssist AI chat bot — floats on every page */}
      <ChatBot />
    </BrowserRouter>
  )
}
