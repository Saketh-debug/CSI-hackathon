/**
 * App Shell — renders the full-page layout HTML.
 * MapLibre attaches to #map-container.
 * Search panel sits in #panel.
 */

export function createAppShell() {
  return `
    <!-- Top bar -->
    <header class="topbar">
      <div class="topbar-brand">
        <span class="topbar-icon">🏙️</span>
        <div>
          <span class="topbar-title">Hyderabad 3D</span>
          <span class="topbar-sub">HITEC City · Madhapur · Gachibowli</span>
        </div>
      </div>
      <div class="topbar-badges">
        <span class="badge badge-green">● Live OSM Data</span>
        <span class="badge badge-blue">MapLibre GL</span>
      </div>
    </header>

    <!-- Main layout -->
    <div class="layout">

      <!-- Left panel -->
      <aside class="panel" id="panel">

        <!-- Search section -->
        <div class="panel-section">
          <h2 class="panel-heading">🛵 Route Finder</h2>

          <div class="input-group">
            <label class="input-label">📍 Origin</label>
            <div class="input-row">
              <input
                id="input-origin"
                class="text-input"
                type="text"
                placeholder="e.g. Gachibowli, Hyderabad"
                value="Madhapur, Hyderabad"
              />
              <button class="icon-btn" id="btn-locate" title="Use my location">📡</button>
            </div>
          </div>

          <div class="input-group">
            <label class="input-label">🏁 Destination</label>
            <input
              id="input-dest"
              class="text-input"
              type="text"
              placeholder="e.g. Banjara Hills, Hyderabad"
              value="Banjara Hills, Hyderabad"
            />
          </div>

          <button class="btn-primary" id="btn-route">
            <span id="btn-route-text">Find Route</span>
            <span id="btn-route-spinner" class="spinner hidden"></span>
          </button>

          <!-- Route result card -->
          <div class="route-card hidden" id="route-card">
            <div class="route-stat">
              <span class="route-stat-val" id="stat-dist">—</span>
              <span class="route-stat-label">km</span>
            </div>
            <div class="route-divider"></div>
            <div class="route-stat">
              <span class="route-stat-val" id="stat-time">—</span>
              <span class="route-stat-label">min</span>
            </div>
            <div class="route-divider"></div>
            <div class="route-stat">
              <span class="route-stat-val" id="stat-nodes">—</span>
              <span class="route-stat-label">nodes</span>
            </div>
          </div>

          <div class="error-msg hidden" id="error-msg"></div>
        </div>

        <!-- Map controls -->
        <div class="panel-section">
          <h2 class="panel-heading">🎛️ Layers</h2>
          <div class="toggle-row">
            <span class="toggle-label">🏢 Buildings (3D)</span>
            <label class="toggle-switch">
              <input type="checkbox" id="toggle-buildings" checked />
              <span class="toggle-slider"></span>
            </label>
          </div>
          <div class="toggle-row">
            <span class="toggle-label">🛣️ Roads</span>
            <label class="toggle-switch">
              <input type="checkbox" id="toggle-roads" checked />
              <span class="toggle-slider"></span>
            </label>
          </div>
          <div class="toggle-row">
            <span class="toggle-label">🌑 3D Pitch</span>
            <label class="toggle-switch">
              <input type="checkbox" id="toggle-pitch" checked />
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>

        <!-- Legend -->
        <div class="panel-section panel-section--legend">
          <h2 class="panel-heading">🗺️ Road Types</h2>
          <div class="legend-item"><span class="legend-dot" style="background:#f97316"></span>Motorway / Trunk</div>
          <div class="legend-item"><span class="legend-dot" style="background:#eab308"></span>Primary</div>
          <div class="legend-item"><span class="legend-dot" style="background:#94a3b8"></span>Secondary</div>
          <div class="legend-item"><span class="legend-dot" style="background:#475569"></span>Residential</div>
          <div class="legend-item"><span class="legend-dot" style="background:#22d3ee"></span>Active Route</div>
        </div>

        <!-- Footer -->
        <div class="panel-footer">
          Data: OpenStreetMap · MapLibre GL · NetworkX<br/>
          CoolPath — Verdex Project
        </div>

      </aside>

      <!-- Map -->
      <main class="map-wrapper">
        <div id="map-container"></div>

        <!-- Overlay: loading state -->
        <div class="map-overlay" id="map-loading">
          <div class="loading-card">
            <div class="loading-spinner"></div>
            <p class="loading-text">Loading 3D city data…</p>
            <p class="loading-sub" id="loading-status">Connecting to backend</p>
          </div>
        </div>

        <!-- Compass / pitch indicator -->
        <div class="map-compass" id="compass-display">
          <span>↑ N</span>
        </div>
      </main>

    </div>
  `
}
