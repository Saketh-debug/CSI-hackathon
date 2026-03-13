import { useEffect } from 'react'
import { useMap } from 'react-leaflet'

export default function MapResizer() {
  const map = useMap()
  
  useEffect(() => {
    // Let the browser finish painting the container size
    // before asking Leaflet to re-measure itself and request tiles.
    const id = setTimeout(() => {
      map.invalidateSize()
    }, 100)
    
    return () => clearTimeout(id)
  }, [map])
  
  return null
}
