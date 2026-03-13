import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/global.css'

// Leaflet CSS — required or maps render as a grey box
import 'leaflet/dist/leaflet.css'
// Fix Leaflet marker icon path broken by Vite/webpack bundling
import L from 'leaflet'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

