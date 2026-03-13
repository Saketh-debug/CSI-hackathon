import { useState, useEffect, useCallback } from 'react'
import client from './client'

// ─────────────────────────────────────────────────────────
// Generic fetch hook
// ─────────────────────────────────────────────────────────
function useFetch(url) {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  const refetch = useCallback(() => {
    setLoading(true)
    setError(null)
    client.get(url)
      .then(r => setData(r.data))
      .catch(e => setError(e.response?.data?.detail || e.message))
      .finally(() => setLoading(false))
  }, [url])

  useEffect(() => { refetch() }, [refetch])

  return { data, loading, error, refetch }
}

// ─────────────────────────────────────────────────────────
// Temperature (LST) data — used by Heatmap + Dashboard
// ─────────────────────────────────────────────────────────
export function useTemperatureData() {
  return useFetch('/api/temperature')
}

// ─────────────────────────────────────────────────────────
// Tree Canopy (NDVI) data — used by TreeCanopy + Dashboard
// ─────────────────────────────────────────────────────────
export function useCanopyData() {
  return useFetch('/api/canopy')
}

// ─────────────────────────────────────────────────────────
// 24-hour Forecast — used by Heatmap
// ─────────────────────────────────────────────────────────
export function useForecastData() {
  return useFetch('/api/forecast')
}

// ─────────────────────────────────────────────────────────
// Aggregated Dashboard summary
// ─────────────────────────────────────────────────────────
export function useSummaryData() {
  return useFetch('/api/summary')
}

// ─────────────────────────────────────────────────────────
// Route computation — triggered imperatively on button click
// ─────────────────────────────────────────────────────────
export function useRoute() {
  const [result, setResult]   = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)

  const compute = useCallback(async (origin, destination, weights = {}) => {
    if (!origin?.trim() || !destination?.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const r = await client.post('/api/route', {
        origin,
        destination,
        shade_weight:  weights.shade   ?? 0.5,
        temp_weight:   weights.temp    ?? 0.3,
        max_deviation: weights.maxDev  ?? 1.3,
      })
      setResult(r.data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Routing failed')
    } finally {
      setLoading(false)
    }
  }, [])

  return { result, loading, error, compute }
}
