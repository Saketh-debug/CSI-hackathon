/**
 * App Configuration
 * =================
 * Single place to change backend URL, map defaults, styling constants.
 */

// Backend API base URL — change to deployed URL when hosting
export const BACKEND_URL = 'http://localhost:8000'

// Map defaults
export const MAP_CENTER  = [78.3762, 17.4474]   // [lon, lat] — Madhapur
export const MAP_ZOOM    = 15
export const MAP_PITCH   = 50
export const MAP_BEARING = -15

// Road colours by type (also used in legend)
export const ROAD_COLORS = {
  motorway:        '#f97316',
  motorway_link:   '#f97316',
  trunk:           '#fb923c',
  trunk_link:      '#fb923c',
  primary:         '#eab308',
  primary_link:    '#eab308',
  secondary:       '#94a3b8',
  secondary_link:  '#94a3b8',
  tertiary:        '#64748b',
  tertiary_link:   '#64748b',
  residential:     '#475569',
  default:         '#334155',
}

// Building rendering
export const BUILDING_COLOR       = '#1e3a5f'
export const BUILDING_BASE_HEIGHT = 0
