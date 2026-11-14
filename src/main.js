import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './style.css';

import { karnatakaCrops } from './data/karnatakaCrops.js';
import { karnatakaMandis, commodityMarketPrices } from './data/marketData.js';
import { districtClimateBaselines, satellitePassesHistory, ndviTimeSeriesData } from './data/environmentalData.js';
import { storageService } from './services/storageService.js';
import { recommendationEngine } from './services/recommendationEngine.js';

/* ==========================================================================
   GLOBAL APPLICATION STATE
   ========================================================================== */
const state = {
  activeView: 'dashboard',
  plots: [],
  activePlotId: null,
  farmerProfile: null,
  plans: [],
  
  // Recommendation Engine controls
  recSeason: 'kharif',
  priceDeltaPct: 0,
  costDeltaPct: 0,
  
  // Market Intelligence filter
  selectedMandiId: 'all',

  // Map & Drawing state
  map: null,
  activeParcelLayer: null,
  pegMarkersGroup: null,
  drawingLineLayer: null,
  isDrawingMode: false,
  drawCoordinates: [], // array of [lng, lat]
  selectedSatellitePassId: 'pass-2026-11-12'
};

/* ==========================================================================
   INITIALIZATION
   ========================================================================== */
document.addEventListener('DOMContentLoaded', () => {
  initData();
  initNavigation();
  initMap();
  initEventListeners();
  renderAll();
});

function initData() {
  state.farmerProfile = storageService.getProfile();
  state.plots = storageService.getPlots();
  state.plans = storageService.getPlans();
  if (state.plots.length > 0) {
    state.activePlotId = state.plots[0].id;
  }
}

function getActivePlot() {
  return state.plots.find(p => p.id === state.activePlotId) || state.plots[0];
}

/* ==========================================================================
   PRIMARY NAVIGATION (7 SECTIONS)
   ========================================================================== */
function initNavigation() {
  const tabButtons = document.querySelectorAll('.nav-tab-btn');
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetView = btn.dataset.view;
      switchView(targetView);
    });
  });

  // Profile click from top avatar pill
  document.getElementById('header-farmer-pill')?.addEventListener('click', () => {
    switchView('profile');
  });
}

function switchView(viewName) {
  state.activeView = viewName;

  // Update tabs
  document.querySelectorAll('.nav-tab-btn').forEach(btn => {
    if (btn.dataset.view === viewName) btn.classList.add('active');
    else btn.classList.remove('active');
  });

  // Update view sections
  document.querySelectorAll('.view-section').forEach(sec => {
    if (sec.id === `view-${viewName}`) sec.classList.add('active');
    else sec.classList.remove('active');
  });

  // Invalidate map size when switching to My Land
  if (viewName === 'myland' && state.map) {
    setTimeout(() => {
      state.map.invalidateSize();
      centerMapOnActivePlot();
    }, 150);
  }

  // Refresh current view contents
  renderCurrentView();
}

/* ==========================================================================
   LEAFLET MAP & SATELLITE COCKPIT (MY LAND)
   ========================================================================== */
function initMap() {
  const mapElement = document.getElementById('map');
  if (!mapElement) return;

  state.map = L.map('map', {
    center: [13.2974, 77.1262],
    zoom: 16,
    minZoom: 4,
    maxZoom: 19,
    zoomControl: false
  });

  L.control.zoom({ position: 'topleft' }).addTo(state.map);

  // High-Resolution Esri World Imagery (Satellite)
  const esriSatellite = L.tileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    {
      maxZoom: 19,
      attribution: '&copy; Esri, Maxar, Earthstar Geographics'
    }
  );

  const esriReference = L.tileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
    { maxZoom: 19 }
  );

  esriSatellite.addTo(state.map);
  esriReference.addTo(state.map);

  state.activeParcelLayer = L.layerGroup().addTo(state.map);
  state.pegMarkersGroup = L.layerGroup().addTo(state.map);
  state.drawingLineLayer = L.polyline([], { color: '#ea580c', weight: 3, dashArray: '5, 8' }).addTo(state.map);

  // Map Click Listener for Plot Drawing
  state.map.on('click', (e) => {
    if (!state.isDrawingMode) return;
    handleMapClickForDrawing(e.latlng);
  });
}

function renderMapActiveParcel() {
  if (!state.map || !state.activeParcelLayer) return;
  state.activeParcelLayer.clearLayers();

  const plot = getActivePlot();
  if (!plot || !plot.boundary || !plot.boundary.coordinates) return;

  const overlayMode = document.getElementById('cockpit-overlay-mode')?.value || 'ndvi';

  // Determine parcel heatmap fill color matching reference image
  let fillColor = '#f97316'; // Vibrant orange default
  let fillOpacity = 0.55;
  let borderColor = '#ea580c';

  if (overlayMode === 'ndvi') {
    const ndvi = plot.satelliteSummary?.latestNdvi || 0.74;
    // Thermal heatmap scale (yellow to deep orange-red)
    if (ndvi >= 0.8) fillColor = '#dc2626'; // Peak canopy / deep red-orange
    else if (ndvi >= 0.7) fillColor = '#ea580c'; // High vigour
    else if (ndvi >= 0.55) fillColor = '#f59e0b'; // Moderate canopy yellow-amber
    else fillColor = '#eab308'; // Early/sparse canopy
    fillOpacity = 0.62;
    borderColor = '#ffffff';
  } else if (overlayMode === 'ndwi') {
    fillColor = '#0284c7'; // Canopy water blue
    fillOpacity = 0.5;
    borderColor = '#38bdf8';
  } else {
    // True Color: subtle border only
    fillOpacity = 0.15;
    borderColor = '#ffffff';
  }

  // Leaflet expects [lat, lng] array
  const latLngs = plot.boundary.coordinates[0].map(coord => [coord[1], coord[0]]);

  const polygon = L.polygon(latLngs, {
    color: borderColor,
    weight: 3.5,
    fillColor: fillColor,
    fillOpacity: fillOpacity,
    dashArray: overlayMode === 'truecolor' ? '4' : null
  });

  polygon.bindTooltip(`
    <div style="font-family: inherit; font-size: 12px; line-height: 1.4; color: #0f172a;">
      <strong style="color: #ea580c;">${plot.name}</strong><br/>
      <span>Area: <b>${plot.areaAcre} Acres</b> (${plot.areaGuntas} Guntas)</span><br/>
      <span>NDVI Mean: <b style="color: #ea580c;">${plot.satelliteSummary?.latestNdvi || 0.74}</b></span><br/>
      <span>Irrigation: <b>${plot.irrigationType.toUpperCase()}</b></span>
    </div>
  `, { sticky: true, opacity: 0.95 });

  polygon.addTo(state.activeParcelLayer);
}

function centerMapOnActivePlot() {
  const plot = getActivePlot();
  if (plot && plot.coordinates && state.map) {
    state.map.setView(plot.coordinates, 16);
  }
}

/* ==========================================================================
   INTERACTIVE PLOT BOUNDARY PEG DRAWING
   ========================================================================== */
function startDrawingMode() {
  state.isDrawingMode = true;
  state.drawCoordinates = [];
  state.pegMarkersGroup.clearLayers();
  state.drawingLineLayer.setLatLngs([]);

  const banner = document.getElementById('draw-helper-banner');
  const countSpan = document.getElementById('draw-points-count');
  if (banner) banner.classList.add('active');
  if (countSpan) countSpan.textContent = '(0 pegs)';

  showToast('Drawing mode active: Click satellite map to place plot boundary corner pegs.');
}

function handleMapClickForDrawing(latlng) {
  // Store as [lng, lat] for GeoJSON standard
  state.drawCoordinates.push([latlng.lng, latlng.lat]);

  // Place custom orange peg marker
  const pegIcon = L.divIcon({
    className: 'custom-peg-marker',
    html: `<div style="width:12px; height:12px; background:#ea580c; border:2px solid #ffffff; border-radius:50%; box-shadow:0 0 4px rgba(0,0,0,0.4);"></div>`,
    iconSize: [12, 12],
    iconAnchor: [6, 6]
  });

  const marker = L.marker([latlng.lat, latlng.lng], { icon: pegIcon }).addTo(state.pegMarkersGroup);

  // Update line connecting pegs
  const linePoints = state.drawCoordinates.map(c => [c[1], c[0]]);
  state.drawingLineLayer.setLatLngs(linePoints);

  const countSpan = document.getElementById('draw-points-count');
  if (countSpan) countSpan.textContent = `(${state.drawCoordinates.length} pegs placed)`;
}

function finishDrawing() {
  if (state.drawCoordinates.length < 3) {
    alert('Please place at least 3 corner pegs to form a closed agricultural plot boundary.');
    return;
  }

  // Close the polygon ring
  const closedCoords = [...state.drawCoordinates, state.drawCoordinates[0]];
  const calculatedAcres = calculatePolygonAreaAcres(closedCoords);
  const calculatedGuntas = Math.round(calculatedAcres * 40);
  const calculatedHectares = (calculatedAcres * 0.404686).toFixed(2);

  // Pre-fill Add Plot modal
  document.getElementById('new-plot-acres').value = calculatedAcres.toFixed(2);
  document.getElementById('new-plot-name').value = `New Drawn Plot (${calculatedAcres.toFixed(2)} ac)`;

  // Save temporary geometry on modal
  window._temporaryDrawnBoundary = {
    type: "Polygon",
    coordinates: [closedCoords]
  };

  cancelDrawing();
  openModal('modal-add-plot');
  showToast(`Boundary calculated: ${calculatedAcres.toFixed(2)} Acres (${calculatedGuntas} Guntas).`);
}

function cancelDrawing() {
  state.isDrawingMode = false;
  state.drawCoordinates = [];
  state.pegMarkersGroup.clearLayers();
  state.drawingLineLayer.setLatLngs([]);

  const banner = document.getElementById('draw-helper-banner');
  if (banner) banner.classList.remove('active');
}

/**
 * Fast spherical planar projection polygon area calculation (Cartesian Shoelace)
 */
function calculatePolygonAreaAcres(coords) {
  if (coords.length < 3) return 0;
  const lat0 = coords[0][1] * Math.PI / 180;
  const mPerDegLat = 111132;
  const mPerDegLng = 111320 * Math.cos(lat0);
  let areaSqM = 0;
  for (let i = 0; i < coords.length; i++) {
    const j = (i + 1) % coords.length;
    const x1 = coords[i][0] * mPerDegLng;
    const y1 = coords[i][1] * mPerDegLat;
    const x2 = coords[j][0] * mPerDegLng;
    const y2 = coords[j][1] * mPerDegLat;
    areaSqM += (x1 * y2) - (x2 * y1);
  }
  areaSqM = Math.abs(areaSqM) / 2;
  return areaSqM / 4046.8564224;
}

/* ==========================================================================
   RENDER METHODS FOR ALL 7 VIEWS
   ========================================================================== */
function renderAll() {
  renderHeaderControls();
  renderCurrentView();
}

function renderHeaderControls() {
  // Global Plot Selector in Header
  const plotSelect = document.getElementById('global-plot-select');
  if (plotSelect) {
    plotSelect.innerHTML = state.plots.map(p => `
      <option value="${p.id}" ${p.id === state.activePlotId ? 'selected' : ''}>
        ${p.name} (${p.areaAcre} ac)
      </option>
    `).join('');
  }

  // Farmer Name
  const farmerNameSpan = document.getElementById('header-farmer-name');
  if (farmerNameSpan && state.farmerProfile) {
    farmerNameSpan.textContent = state.farmerProfile.name.split(' ')[0] + ' G.';
  }
}

function renderCurrentView() {
  switch (state.activeView) {
    case 'dashboard':
      renderDashboard();
      break;
    case 'myland':
      renderMyLand();
      break;
    case 'landanalysis':
      renderLandAnalysis();
      break;
    case 'recommendations':
      renderCropRecommendations();
      break;
    case 'market':
      renderMarketIntelligence();
      break;
    case 'plans':
      renderPlantingPlans();
      break;
    case 'profile':
      renderProfile();
      break;
  }
}

/* --------------------------------------------------------------------------
   VIEW 1: DASHBOARD RENDERING
   -------------------------------------------------------------------------- */
function renderDashboard() {
  const activePlot = getActivePlot();
  const totalArea = state.plots.reduce((sum, p) => sum + p.areaAcre, 0);
  const totalGuntas = Math.round(totalArea * 40);

  // Update Metrics
  document.getElementById('dash-metric-plots').textContent = state.plots.length;
  document.getElementById('dash-metric-area').textContent = `${totalArea.toFixed(2)} ac`;

  const verifiedCount = state.plots.filter(p => p.soilRecord?.hasSoilTest).length;
  document.getElementById('dash-metric-soil-status').textContent = `${verifiedCount}/${state.plots.length} Verified`;

  // Evaluate recommendations for active plot
  const evalResult = recommendationEngine.evaluatePlot(activePlot, 'kharif');
  document.getElementById('dash-metric-suitable-crops').textContent = `${evalResult.suitableCount} Crops`;

  const topCrop = evalResult.recommendations[0];
  if (topCrop) {
    document.getElementById('dash-metric-top-return').textContent = `₹${topCrop.financials.expected.netReturnPerAcre.toLocaleString()}`;
  }

  // Alert Banner for missing soil test
  const alertBanner = document.getElementById('dash-alert-banner');
  const alertTitle = document.getElementById('dash-alert-title');
  const alertDesc = document.getElementById('dash-alert-desc');

  const unverifiedPlot = state.plots.find(p => !p.soilRecord?.hasSoilTest);
  if (unverifiedPlot) {
    alertBanner.style.display = 'flex';
    alertTitle.textContent = `Soil-Test Lab Record Missing for ${unverifiedPlot.name}`;
    alertDesc.textContent = `Using regional baseline for ${unverifiedPlot.district}. Enter laboratory Soil Health Card parameters for 100% accurate fertilizer & net return calibration.`;
  } else {
    alertBanner.style.display = 'none';
  }

  // Top Crops Preview List
  const listContainer = document.getElementById('dash-crop-list');
  const subtitle = document.getElementById('dash-rec-subtitle');
  if (subtitle) {
    subtitle.textContent = `For ${activePlot.name} (${activePlot.areaAcre} Acres) • Kharif Season`;
  }

  if (listContainer) {
    listContainer.innerHTML = evalResult.recommendations.slice(0, 4).map((rec, idx) => `
      <div class="crop-preview-item">
        <div class="crop-item-left">
          <div class="crop-rank-badge">${idx + 1}</div>
          <div>
            <div class="crop-name-strong">${rec.crop.name} <span class="crop-kannada-name">(${rec.crop.kannadaName})</span></div>
            <div style="font-size:0.75rem; color:var(--text-subtle);">
              Duration: ${rec.crop.cropDurationDays} days &bull; Water: ${rec.crop.waterRequirements.totalMm} mm &bull; Yield: ${rec.financials.expected.yieldPerAcre} qtl/ac
            </div>
          </div>
        </div>
        <div>
          <div class="crop-return-val">+₹${rec.financials.expected.netReturnPerAcre.toLocaleString()}</div>
          <div class="crop-return-lbl">Expected Net / Acre</div>
        </div>
      </div>
    `).join('');
  }

  // Active Plans Preview List
  const plansContainer = document.getElementById('dash-plans-list');
  if (plansContainer) {
    if (state.plans.length === 0) {
      plansContainer.innerHTML = `<div style="font-size:0.8rem; color:var(--text-subtle); padding:0.5rem 0;">No active planting plans saved yet.</div>`;
    } else {
      plansContainer.innerHTML = state.plans.slice(0, 3).map(plan => `
        <div class="crop-preview-item" style="padding:0.65rem 0.85rem;">
          <div>
            <div style="font-size:0.85rem; font-weight:700; color:var(--text-main);">${plan.cropName}</div>
            <div style="font-size:0.72rem; color:var(--text-subtle);">${plan.plotName} &bull; ${plan.cultivatedAcre} ac</div>
          </div>
          <div style="text-align:right;">
            <div style="font-size:0.9rem; font-weight:800; color:var(--status-green);">+₹${plan.expectedNetReturn.toLocaleString()}</div>
            <div style="font-size:0.68rem; color:var(--text-subtle);">Net Return</div>
          </div>
        </div>
      `).join('');
    }
  }
}

/* --------------------------------------------------------------------------
   VIEW 2: MY LAND RENDERING (PRECISION SATELLITE COCKPIT)
   -------------------------------------------------------------------------- */
function renderMyLand() {
  renderMapActiveParcel();
  centerMapOnActivePlot();

  const plot = getActivePlot();

  // Update Right Sidebar: Satellite Pass List (matches reference GUI)
  const passContainer = document.getElementById('cockpit-pass-list');
  if (passContainer) {
    passContainer.innerHTML = satellitePassesHistory.map(pass => `
      <div class="pass-row-item ${pass.id === state.selectedSatellitePassId ? 'active' : ''}" data-pass-id="${pass.id}">
        <div class="pass-left">
          <div class="pass-thumb-icon">🛰️</div>
          <div class="pass-meta">
            <span class="pass-date">${pass.dateFormatted}</span>
            <span class="pass-mission">${pass.satellite} &bull; ${pass.resolution}</span>
          </div>
        </div>
        <div class="pass-cloud-badge ${pass.cloudCoverPct > 30 ? 'high-cloud' : ''}">
          ☁️ ${pass.cloudCoverPct}%
        </div>
      </div>
    `).join('');

    // Attach click listeners to passes
    passContainer.querySelectorAll('.pass-row-item').forEach(el => {
      el.addEventListener('click', () => {
        state.selectedSatellitePassId = el.dataset.passId;
        renderMyLand();
        const selected = satellitePassesHistory.find(p => p.id === state.selectedSatellitePassId);
        if (selected) {
          showToast(`Pass selected: ${selected.dateFormatted} (${selected.canopyStatus})`);
        }
      });
    });
  }

  // Update Parcel Details in sidebar
  const infoEl = document.getElementById('cockpit-plot-info-text');
  if (infoEl) {
    infoEl.innerHTML = `
      <div><b>Plot:</b> ${plot.name}</div>
      <div><b>Taluk / Village:</b> ${plot.taluk}, ${plot.village}</div>
      <div><b>Survey No:</b> ${plot.surveyNumber || 'N/A'}</div>
      <div><b>Area:</b> ${plot.areaAcre} ac (${plot.areaGuntas} guntas / ${plot.areaHectares} ha)</div>
      <div><b>Irrigation:</b> ${plot.irrigationType.toUpperCase()} (${plot.waterAvailability})</div>
      <div><b>Soil:</b> ${plot.soilRecord?.textureDisplay || 'Red sandy loam'}</div>
      <div style="margin-top:0.4rem; padding-top:0.4rem; border-top:1px dashed var(--border-medium); color:var(--orange-700);">
        <b>Canopy Status:</b> ${plot.satelliteSummary?.canopyCondition || 'Active'}
      </div>
    `;
  }

  // Render SVG Bottom Drawer Time-Series Graph (matches reference GUI)
  renderTimeSeriesSvg();
}

function renderTimeSeriesSvg() {
  const svg = document.getElementById('timeseries-chart-svg');
  if (!svg) return;

  const data = ndviTimeSeriesData;
  const width = 900;
  const height = 130;
  const paddingLeft = 45;
  const paddingRight = 20;
  const paddingTop = 15;
  const paddingBottom = 25;

  const chartWidth = width - paddingLeft - paddingRight;
  const chartHeight = height - paddingTop - paddingBottom;

  const stepX = chartWidth / (data.length - 1);

  // Helper coordinate mapper for NDVI (0 to 1)
  const getY = (val) => paddingTop + chartHeight * (1 - Math.max(0, Math.min(1, val)));

  // Generate path data for Mean NDVI (Orange curve)
  let meanPath = `M ${paddingLeft} ${getY(data[0].mean)}`;
  for (let i = 1; i < data.length; i++) {
    meanPath += ` L ${paddingLeft + i * stepX} ${getY(data[i].mean)}`;
  }

  // Generate path data for Max NDVI (Green curve)
  let maxPath = `M ${paddingLeft} ${getY(data[0].max)}`;
  for (let i = 1; i < data.length; i++) {
    maxPath += ` L ${paddingLeft + i * stepX} ${getY(data[i].max)}`;
  }

  // Generate Grid lines & Dates
  let gridSvg = '';
  [0.2, 0.4, 0.6, 0.8, 1.0].forEach(level => {
    const y = getY(level);
    gridSvg += `
      <line x1="${paddingLeft}" y1="${y}" x2="${width - paddingRight}" y2="${y}" stroke="#e2e8f0" stroke-width="1" />
      <text x="${paddingLeft - 8}" y="${y + 4}" font-size="10" fill="#94a3b8" text-anchor="end">${level.toFixed(1)}</text>
    `;
  });

  let xLabels = '';
  let rainfallBars = '';
  data.forEach((d, idx) => {
    const x = paddingLeft + idx * stepX;
    xLabels += `<text x="${x}" y="${height - 5}" font-size="10" fill="#64748b" text-anchor="middle">${d.date}</text>`;
    
    // Rainfall bar at bottom
    const barHeight = (d.rainfallMm / 100) * 40;
    rainfallBars += `<rect x="${x - 5}" y="${height - paddingBottom - barHeight}" width="10" height="${barHeight}" fill="rgba(2, 132, 199, 0.35)" rx="2"/>`;
  });

  svg.innerHTML = `
    ${gridSvg}
    ${rainfallBars}
    <path d="${maxPath}" fill="none" stroke="#16a34a" stroke-width="2" stroke-dasharray="3, 3" />
    <path d="${meanPath}" fill="none" stroke="#ea580c" stroke-width="2.8" />
    ${data.map((d, i) => `
      <circle cx="${paddingLeft + i * stepX}" cy="${getY(d.mean)}" r="4" fill="#ea580c" stroke="#ffffff" stroke-width="1.5"/>
    `).join('')}
    ${xLabels}
  `;
}

/* --------------------------------------------------------------------------
   VIEW 3: LAND ANALYSIS RENDERING
   -------------------------------------------------------------------------- */
function renderLandAnalysis() {
  const plot = getActivePlot();
  const soil = plot.soilRecord || {};
  const water = plot.waterRecord || {};
  const climate = districtClimateBaselines[plot.district] || districtClimateBaselines["Tumakuru"];

  // Soil Health Card Data
  const badge = document.getElementById('shc-badge-status');
  if (badge) {
    badge.textContent = soil.hasSoilTest ? 'Verified Lab Record' : 'Estimated Regional Baseline';
    badge.style.background = soil.hasSoilTest ? 'var(--orange-100)' : '#fef2f2';
    badge.style.color = soil.hasSoilTest ? 'var(--orange-700)' : 'var(--status-red)';
  }

  document.getElementById('shc-card-meta').textContent = `${soil.labName || 'Regional Reference Center'} • ${soil.cardNo || 'Unregistered'}`;
  document.getElementById('soil-texture-display').textContent = soil.textureDisplay || 'Red Sandy Loam';
  document.getElementById('soil-depth-display').textContent = `${soil.soilDepth || 'Medium'} root zone depth`;
  document.getElementById('soil-drainage-display').textContent = soil.drainage || 'Well-drained';

  document.getElementById('soil-ph-val').textContent = soil.ph || '6.6';
  document.getElementById('soil-ec-val').textContent = soil.electricalConductivity || '0.32';
  document.getElementById('soil-oc-val').textContent = `${soil.organicCarbonPct || 0.52}%`;
  document.getElementById('soil-n-val').textContent = `${soil.nitrogenKgHa || 215} kg/ha`;
  document.getElementById('soil-p-val').textContent = `${soil.phosphorusKgHa || 22.4} kg/ha`;
  document.getElementById('soil-k-val').textContent = `${soil.potassiumKgHa || 275} kg/ha`;

  // Water Audit Data
  document.getElementById('water-method').textContent = `${plot.irrigationType.toUpperCase()} (${plot.waterAvailability})`;
  document.getElementById('water-depth').textContent = `${water.borewellDepthFt || 0} feet`;
  document.getElementById('water-yield').textContent = `${water.groundwaterYieldInches || 0} inches (${water.borewellReliability || 'Seasonal'})`;
  document.getElementById('water-cost').textContent = `₹${water.irrigationCostPerHour || 0} / hour`;
  document.getElementById('water-quality').textContent = water.waterQuality || 'Normal agricultural suitability';

  // Climate Audit Data
  document.getElementById('climate-region-name').textContent = `${climate.district} District Baseline • ${climate.agroZone}`;
  document.getElementById('clim-rainfall').textContent = `${climate.annualRainfallMm} mm (Kharif: ${climate.kharifRainfallMm} mm, Rabi: ${climate.rabiRainfallMm} mm)`;
  document.getElementById('clim-dryspells').textContent = climate.avgDrySpellsKharif;
  document.getElementById('clim-drought').textContent = climate.droughtVulnerability;
}

/* --------------------------------------------------------------------------
   VIEW 4: CROP RECOMMENDATIONS RENDERING (PROFIT ENGINE)
   -------------------------------------------------------------------------- */
function renderCropRecommendations() {
  const plot = getActivePlot();
  const season = state.recSeason;
  const adjustments = {
    priceDeltaPct: state.priceDeltaPct,
    costDeltaPct: state.costDeltaPct
  };

  const evalResult = recommendationEngine.evaluatePlot(plot, season, adjustments);

  // Update Summary Header
  document.getElementById('rec-count-suitable').textContent = `${evalResult.suitableCount} Suitable Crops`;
  document.getElementById('rec-plot-name-display').textContent = `${plot.name} (${plot.areaAcre} Acres)`;

  // Slider display labels
  const priceLabel = document.getElementById('label-price-adjust');
  const costLabel = document.getElementById('label-cost-adjust');
  if (priceLabel) priceLabel.textContent = `${state.priceDeltaPct > 0 ? '+' : ''}${state.priceDeltaPct}%`;
  if (costLabel) costLabel.textContent = `${state.costDeltaPct > 0 ? '+' : ''}${state.costDeltaPct}%`;

  // Render Ranked Cards
  const container = document.getElementById('rec-cards-container');
  if (container) {
    if (evalResult.recommendations.length === 0) {
      container.innerHTML = `
        <div class="card" style="text-align:center; padding:2rem;">
          <h3 style="color:var(--status-red); margin-bottom:0.5rem;">No Crops Passed All Agronomic Filters for this Season</h3>
          <p style="font-size:0.85rem; color:var(--text-subtle);">
            Try selecting 'All Seasons' or inspect the disqualified criteria below.
          </p>
        </div>
      `;
    } else {
      container.innerHTML = evalResult.recommendations.map((item, idx) => {
        const c = item.crop;
        const f = item.financials;
        const exp = f.expected;
        const pess = f.pessimistic;
        const opt = f.optimistic;

        return `
          <div class="rec-card-full">
            <!-- HEADER -->
            <div class="rec-card-header">
              <div class="rec-title-block">
                <div class="rec-rank-num">#${idx + 1}</div>
                <div>
                  <div class="rec-crop-name">
                    ${c.name} <span class="crop-kannada-name" style="font-size:1rem;">(${c.kannadaName})</span>
                  </div>
                  <div class="rec-crop-sci">
                    ${c.scientificName} &bull; Duration: ${c.cropDurationDays} days &bull; Season: ${c.season.toUpperCase()}
                  </div>
                </div>
              </div>

              <!-- TOTAL PLOT NET RETURN PROMINENT DISPLAY -->
              <div style="text-align:right;">
                <div class="net-return-label">Total Plot Expected Net Return</div>
                <div class="rec-financial-summary">
                  <span class="net-return-huge">+₹${exp.totalPlotNetReturn.toLocaleString()}</span>
                  <span style="font-size:0.85rem; color:var(--text-muted); font-weight:600;">(₹${exp.netReturnPerAcre.toLocaleString()}/ac)</span>
                </div>
              </div>
            </div>

            <!-- KEY AGRONOMIC MATCHES & GUIDANCE -->
            <div style="font-size:0.8rem; margin-bottom:0.85rem; display:flex; gap:0.5rem; flex-wrap:wrap;">
              <span class="brand-badge" style="background:#f0fdf4; color:#15803d; border:1px solid #bbf7d0;">
                BCR Ratio: ${exp.bcr}x
              </span>
              <span class="brand-badge" style="background:#f0f9ff; color:#0369a1; border:1px solid #bae6fd;">
                Water: ${c.waterRequirements.totalMm} mm
              </span>
              <span class="brand-badge" style="background:#fff7ed; color:#c2410c; border:1px solid #fed7aa;">
                Sowing: ${c.sowingWindow}
              </span>
              <span class="brand-badge" style="background:#faf5ff; color:#7e22ce; border:1px solid #e9d5ff;">
                Expected Yield: ${exp.yieldPerAcre} qtl/ac
              </span>
            </div>

            <!-- STAGE C: 3-SCENARIO FINANCIAL MATRIX -->
            <div class="scenarios-grid">
              <!-- PESSIMISTIC -->
              <div class="scenario-box">
                <div class="scenario-header pessimistic">
                  <span>📉 Pessimistic Scenario</span>
                  <span style="font-size:0.68rem; font-weight:600;">(-20% Yield / Glut)</span>
                </div>
                <div class="scenario-stat-row">
                  <span>Yield / Acre:</span>
                  <span class="scenario-stat-val">${pess.yieldPerAcre} qtl</span>
                </div>
                <div class="scenario-stat-row">
                  <span>Farm-Gate Price:</span>
                  <span class="scenario-stat-val">₹${pess.pricePerQuintal}/qtl</span>
                </div>
                <div class="scenario-stat-row" style="border-top:1px dashed var(--border-medium); padding-top:0.25rem; margin-top:0.25rem;">
                  <span style="font-weight:700;">Plot Net Return:</span>
                  <span class="scenario-stat-val" style="color:${pess.totalPlotNetReturn > 0 ? 'var(--status-green)' : 'var(--status-red)'};">
                    +₹${pess.totalPlotNetReturn.toLocaleString()}
                  </span>
                </div>
              </div>

              <!-- EXPECTED -->
              <div class="scenario-box expected">
                <div class="scenario-header expected">
                  <span>⭐ Expected Scenario</span>
                  <span style="font-size:0.68rem; font-weight:700;">(Modal APMC Baseline)</span>
                </div>
                <div class="scenario-stat-row">
                  <span>Yield / Acre:</span>
                  <span class="scenario-stat-val">${exp.yieldPerAcre} qtl</span>
                </div>
                <div class="scenario-stat-row">
                  <span>Farm-Gate Price:</span>
                  <span class="scenario-stat-val">₹${exp.pricePerQuintal}/qtl</span>
                </div>
                <div class="scenario-stat-row" style="border-top:1px dashed var(--orange-300); padding-top:0.25rem; margin-top:0.25rem;">
                  <span style="font-weight:700; color:var(--orange-700);">Plot Net Return:</span>
                  <span class="scenario-stat-val" style="color:var(--status-green); font-size:0.92rem;">
                    +₹${exp.totalPlotNetReturn.toLocaleString()}
                  </span>
                </div>
              </div>

              <!-- OPTIMISTIC -->
              <div class="scenario-box">
                <div class="scenario-header optimistic">
                  <span>🚀 Optimistic Scenario</span>
                  <span style="font-size:0.68rem; font-weight:600;">(+15% Yield / Peak)</span>
                </div>
                <div class="scenario-stat-row">
                  <span>Yield / Acre:</span>
                  <span class="scenario-stat-val">${opt.yieldPerAcre} qtl</span>
                </div>
                <div class="scenario-stat-row">
                  <span>Farm-Gate Price:</span>
                  <span class="scenario-stat-val">₹${opt.pricePerQuintal}/qtl</span>
                </div>
                <div class="scenario-stat-row" style="border-top:1px dashed var(--border-medium); padding-top:0.25rem; margin-top:0.25rem;">
                  <span style="font-weight:700;">Plot Net Return:</span>
                  <span class="scenario-stat-val" style="color:var(--status-green);">
                    +₹${opt.totalPlotNetReturn.toLocaleString()}
                  </span>
                </div>
              </div>
            </div>

            <!-- ITEMIZED CULTIVATION BUDGET (Stage B Details) -->
            <div class="cost-breakdown-details">
              <div style="font-weight:700; color:var(--text-main); margin-bottom:0.2rem;">
                Cultivation Cost Breakdown: ₹${f.cultivationCostPerAcre.toLocaleString()} / Acre (Total Budget for Plot: ₹${f.totalPlotCost.toLocaleString()})
              </div>
              <div class="cost-chips-grid">
                <div class="cost-chip"><span>Land Prep:</span> <b>₹${c.cultivationCostPerAcre.landPreparation}</b></div>
                <div class="cost-chip"><span>Seeds:</span> <b>₹${c.cultivationCostPerAcre.seeds}</b></div>
                <div class="cost-chip"><span>FYM / Manure:</span> <b>₹${c.cultivationCostPerAcre.farmyardManure}</b></div>
                <div class="cost-chip"><span>Fertilizers:</span> <b>₹${c.cultivationCostPerAcre.fertilizers}</b></div>
                <div class="cost-chip"><span>Sowing Labour:</span> <b>₹${c.cultivationCostPerAcre.sowingAndTransplanting}</b></div>
                <div class="cost-chip"><span>Weeding:</span> <b>₹${c.cultivationCostPerAcre.weedingAndIntercultivation}</b></div>
                <div class="cost-chip"><span>Plant Protection:</span> <b>₹${c.cultivationCostPerAcre.plantProtection}</b></div>
                <div class="cost-chip"><span>Harvesting:</span> <b>₹${c.cultivationCostPerAcre.harvestingAndThreshing}</b></div>
                <div class="cost-chip"><span>APMC Transport:</span> <b>₹${c.cultivationCostPerAcre.postHarvestTransport}</b></div>
              </div>
            </div>

            <!-- RISKS & ACTION BUTTON -->
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:1rem; padding-top:0.75rem; border-top:1px solid var(--border-subtle); flex-wrap:wrap; gap:0.5rem;">
              <div style="font-size:0.78rem; color:var(--text-subtle);">
                🛡️ <b>Key Risk:</b> ${c.pestsAndDiseases[0]?.name || 'Moisture deficit'} &bull; ${c.localGuidance.keyAdvantage}
              </div>
              <button class="btn-primary btn-sm btn-plan-crop" data-crop-id="${c.id}" data-crop-name="${c.name} (${c.kannadaName})" data-net="${exp.totalPlotNetReturn}" data-budget="${f.totalPlotCost}">
                Commit to Planting Plan &rarr;
              </button>
            </div>
          </div>
        `;
      }).join('');

      // Attach planting plan commit buttons
      container.querySelectorAll('.btn-plan-crop').forEach(btn => {
        btn.addEventListener('click', () => {
          const cropId = btn.dataset.cropId;
          openPlanModalWithCrop(cropId);
        });
      });
    }
  }

  // Render Disqualified Crops Accordion
  const disqContainer = document.getElementById('disqualified-crops-container');
  if (disqContainer) {
    if (evalResult.disqualified.length === 0) {
      disqContainer.innerHTML = `<div style="font-size:0.8rem; color:var(--text-subtle); padding:0.5rem 0;">No crops disqualified in this season filter.</div>`;
    } else {
      disqContainer.innerHTML = evalResult.disqualified.map(item => `
        <div class="disqualified-item">
          <div class="disqualified-title">
            ❌ ${item.crop.name} (${item.crop.kannadaName}) — Disqualified
          </div>
          <div class="disqualified-reason">
            ${item.agronomicDisqualifiers.map(d => `• ${d}`).join('<br/>')}
          </div>
        </div>
      `).join('');
    }
  }
}

/* --------------------------------------------------------------------------
   VIEW 5: MARKET INTELLIGENCE RENDERING
   -------------------------------------------------------------------------- */
function renderMarketIntelligence() {
  const mandiFilter = state.selectedMandiId;
  const container = document.getElementById('market-commodity-grid');
  if (!container) return;

  const entries = Object.entries(commodityMarketPrices);

  container.innerHTML = entries.map(([cropKey, data]) => {
    // Filter mandi reports
    let reports = data.mandiReports;
    if (mandiFilter !== 'all') {
      reports = reports.filter(r => r.mandiId === mandiFilter);
    }

    if (reports.length === 0) return '';

    const primaryReport = reports[0];
    const trendIcon = primaryReport.trend === 'up' ? '↗️ Upward' : (primaryReport.trend === 'down' ? '↘️ Downward' : '➡️ Stable');

    return `
      <div class="commodity-card">
        <div class="commodity-header">
          <div>
            <div class="commodity-name">${data.cropName} <span style="color:var(--orange-600); font-size:0.9rem;">(${data.kannadaName})</span></div>
            <div style="font-size:0.75rem; color:var(--text-subtle);">Mandi: <b>${primaryReport.mandiName}</b> &bull; ${primaryReport.dataSource}</div>
          </div>
          <span class="brand-badge" style="background:#f0fdf4; color:#15803d;">MSP: ₹${data.mspSupportPrice}</span>
        </div>

        <div class="commodity-prices-row">
          <div>
            <div style="font-size:0.68rem; color:var(--text-subtle);">MODAL PRICE</div>
            <div class="modal-price-highlight">₹${primaryReport.modalPrice.toLocaleString()}</div>
            <div style="font-size:0.68rem; color:var(--text-muted);">${data.unit}</div>
          </div>
          <div style="text-align:right;">
            <div style="font-size:0.72rem; color:var(--text-subtle);">Min: <b>₹${primaryReport.minPrice}</b> | Max: <b>₹${primaryReport.maxPrice}</b></div>
            <div style="font-size:0.72rem; color:var(--text-subtle); margin-top:0.2rem;">Daily Arrivals: <b>${primaryReport.dailyArrivalsQuintals} Quintals</b></div>
            <div style="font-size:0.72rem; font-weight:700; color:var(--orange-700); margin-top:0.2rem;">Trend: ${trendIcon}</div>
          </div>
        </div>

        <!-- FARM-GATE CASH REALIZATION -->
        <div style="font-size:0.78rem; background:var(--bg-orange-soft); padding:0.65rem 0.85rem; border-radius:var(--radius-sm); border:1px solid var(--orange-200);">
          <div style="display:flex; justify-content:space-between; font-weight:700; color:var(--orange-700); margin-bottom:0.25rem;">
            <span>Estimated Farm-Gate Realization:</span>
            <span>₹${data.farmGatePriceDeductions.estFarmGatePrice.toLocaleString()} / qtl</span>
          </div>
          <div style="font-size:0.7rem; color:var(--text-muted);">
            Deductions: APMC Cess (1.5%), Bagging (₹${data.farmGatePriceDeductions.baggingPerQuintal}), Weighing (₹${data.farmGatePriceDeductions.weighingLaborPerQuintal}), Transport (~${data.farmGatePriceDeductions.avgTransportDistanceKm} km).
          </div>
        </div>
      </div>
    `;
  }).join('');
}

/* --------------------------------------------------------------------------
   VIEW 6: PLANTING PLANS RENDERING
   -------------------------------------------------------------------------- */
function renderPlantingPlans() {
  const plans = state.plans;

  const totalAcreage = plans.reduce((sum, p) => sum + p.cultivatedAcre, 0);
  const totalBudget = plans.reduce((sum, p) => sum + p.budgetCostTotal, 0);
  const totalProfit = plans.reduce((sum, p) => sum + p.expectedNetReturn, 0);
  const totalBuffer = plans.reduce((sum, p) => sum + p.pessimisticNetReturn, 0);

  document.getElementById('plans-metric-acreage').textContent = `${totalAcreage.toFixed(2)} ac`;
  document.getElementById('plans-metric-budget').textContent = `₹${totalBudget.toLocaleString()}`;
  document.getElementById('plans-metric-profit').textContent = `₹${totalProfit.toLocaleString()}`;
  document.getElementById('plans-metric-buffer').textContent = `₹${totalBuffer.toLocaleString()}`;

  const container = document.getElementById('plans-cards-grid');
  if (!container) return;

  if (plans.length === 0) {
    container.innerHTML = `
      <div class="card" style="grid-column: 1 / -1; text-align:center; padding:2.5rem;">
        <h3 style="color:var(--text-muted); margin-bottom:0.5rem;">No Planting Plans Created Yet</h3>
        <p style="font-size:0.85rem; color:var(--text-subtle); margin-bottom:1rem;">
          Go to Crop Recommendations to evaluate suitable crops and commit decisions into planting plans.
        </p>
        <button class="btn-primary" onclick="window.switchViewGlobal('recommendations')">
          Explore Crop Recommendations &rarr;
        </button>
      </div>
    `;
  } else {
    container.innerHTML = plans.map(p => `
      <div class="plan-card">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.5rem;">
          <div>
            <div style="font-size:1.1rem; font-weight:800; color:var(--text-main);">${p.cropName}</div>
            <div style="font-size:0.78rem; color:var(--text-subtle);">${p.plotName} &bull; <b>${p.cultivatedAcre} Acres</b></div>
          </div>
          <span class="brand-badge" style="background:#f0fdf4; color:#15803d;">${p.status || 'Active Plan'}</span>
        </div>

        <div style="font-size:0.78rem; line-height:1.7; margin:0.75rem 0; color:var(--text-muted);">
          <div>📅 <b>Sowing Window:</b> ${p.sowingWindow}</div>
          <div>🌾 <b>Expected Harvest:</b> ${p.harvestWindow}</div>
          <div>💧 <b>Water Strategy:</b> ${p.irrigationStrategy || 'Rainfed'}</div>
        </div>

        <div style="background:var(--bg-surface-soft); border-radius:var(--radius-sm); padding:0.75rem; margin-bottom:0.85rem;">
          <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:0.25rem;">
            <span>Required Budget:</span> <b>₹${p.budgetCostTotal.toLocaleString()}</b>
          </div>
          <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:0.25rem;">
            <span>Expected Revenue:</span> <b>₹${p.expectedGrossRevenue.toLocaleString()}</b>
          </div>
          <div style="display:flex; justify-content:space-between; font-size:0.95rem; font-weight:800; color:var(--status-green); border-top:1px dashed var(--border-medium); padding-top:0.35rem; margin-top:0.35rem;">
            <span>Net Return:</span> <span>+₹${p.expectedNetReturn.toLocaleString()}</span>
          </div>
        </div>

        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size:0.7rem; color:var(--text-subtle);">Worst Case: ₹${p.pessimisticNetReturn.toLocaleString()}</span>
          <button class="btn-secondary btn-sm btn-delete-plan" data-plan-id="${p.id}" style="color:var(--status-red); border-color:#fca5a5;">
            Delete Plan
          </button>
        </div>
      </div>
    `).join('');

    // Attach delete listeners
    container.querySelectorAll('.btn-delete-plan').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.planId;
        if (confirm('Are you sure you want to remove this planting plan?')) {
          storageService.deletePlan(id);
          state.plans = storageService.getPlans();
          renderPlantingPlans();
          showToast('Planting plan deleted.');
        }
      });
    });
  }
}

/* --------------------------------------------------------------------------
   VIEW 7: MY PROFILE RENDERING
   -------------------------------------------------------------------------- */
function renderProfile() {
  const p = state.farmerProfile;
  if (!p) return;

  document.getElementById('prof-name').value = p.name || '';
  document.getElementById('prof-kannada-name').value = p.kannadaName || '';
  document.getElementById('prof-phone').value = p.phone || '';
  document.getElementById('prof-shc').value = p.soilHealthCardNo || '';
  document.getElementById('prof-district').value = p.district || 'Tumakuru';
  document.getElementById('prof-taluk').value = p.taluk || 'Tumakuru';
  document.getElementById('prof-village').value = p.village || '';
  document.getElementById('prof-risk').value = p.riskTolerance || 'balanced';
  document.getElementById('prof-objective').value = p.primaryObjective || 'profit_maximization';
}

/* ==========================================================================
   EVENT LISTENERS & MODAL MANAGEMENT
   ========================================================================== */
function initEventListeners() {
  // Global Plot Selector
  document.getElementById('global-plot-select')?.addEventListener('change', (e) => {
    state.activePlotId = e.target.value;
    renderAll();
    centerMapOnActivePlot();
    showToast(`Switched active plot: ${getActivePlot().name}`);
  });

  // Cockpit map overlay mode selector
  document.getElementById('cockpit-overlay-mode')?.addEventListener('change', () => {
    renderMapActiveParcel();
  });

  // Center on parcel button
  document.getElementById('btn-fit-parcel')?.addEventListener('click', centerMapOnActivePlot);

  // Drawing Peg Mode buttons
  document.getElementById('btn-start-drawing')?.addEventListener('click', startDrawingMode);
  document.getElementById('btn-finish-drawing')?.addEventListener('click', finishDrawing);
  document.getElementById('btn-cancel-drawing')?.addEventListener('click', cancelDrawing);

  // Bottom drawer collapse toggle (matches reference GUI toggle arrow)
  const drawerToggleBar = document.getElementById('drawer-toggle-bar');
  const btnToggleDrawer = document.getElementById('btn-toggle-drawer');
  const drawer = document.getElementById('cockpit-bottom-drawer');

  const toggleDrawer = () => {
    if (drawer) {
      drawer.classList.toggle('collapsed');
      if (btnToggleDrawer) {
        btnToggleDrawer.innerHTML = drawer.classList.contains('collapsed')
          ? `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="18 15 12 9 6 15"/></svg>`
          : `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>`;
      }
    }
  };

  drawerToggleBar?.addEventListener('click', toggleDrawer);
  btnToggleDrawer?.addEventListener('click', (e) => {
    e.stopPropagation();
    toggleDrawer();
  });

  // Quick Action buttons on dashboard
  document.getElementById('btn-dash-run-rec')?.addEventListener('click', () => switchView('recommendations'));
  document.getElementById('btn-dash-add-plot')?.addEventListener('click', () => openModal('modal-add-plot'));
  document.getElementById('btn-dash-view-all-recs')?.addEventListener('click', () => switchView('recommendations'));
  document.getElementById('btn-dash-resolve-alert')?.addEventListener('click', () => openModal('modal-soil-data'));
  document.getElementById('act-draw-plot')?.addEventListener('click', () => {
    switchView('myland');
    setTimeout(startDrawingMode, 300);
  });
  document.getElementById('act-compare-mandi')?.addEventListener('click', () => switchView('market'));
  document.getElementById('act-run-scenarios')?.addEventListener('click', () => switchView('recommendations'));

  // Season Buttons in Crop Recommendations
  document.querySelectorAll('#rec-season-tabs .season-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#rec-season-tabs .season-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.recSeason = btn.dataset.season;
      renderCropRecommendations();
    });
  });

  // Price & Cost Sensitivity Sliders
  const priceSlider = document.getElementById('slider-price-adjust');
  const costSlider = document.getElementById('slider-cost-adjust');

  priceSlider?.addEventListener('input', (e) => {
    state.priceDeltaPct = parseInt(e.target.value, 10);
    renderCropRecommendations();
  });

  costSlider?.addEventListener('input', (e) => {
    state.costDeltaPct = parseInt(e.target.value, 10);
    renderCropRecommendations();
  });

  document.getElementById('btn-reset-sensitivity')?.addEventListener('click', () => {
    if (priceSlider) priceSlider.value = 0;
    if (costSlider) costSlider.value = 0;
    state.priceDeltaPct = 0;
    state.costDeltaPct = 0;
    renderCropRecommendations();
    showToast('Sensitivity sliders reset.');
  });

  // Mandi Filter Pills
  document.querySelectorAll('#market-mandi-bar .mandi-pill-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#market-mandi-bar .mandi-pill-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.selectedMandiId = btn.dataset.mandi;
      renderMarketIntelligence();
    });
  });

  // Plan creation button
  document.getElementById('btn-create-new-plan')?.addEventListener('click', () => {
    openPlanModalWithCrop();
  });

  document.getElementById('btn-save-top-plan')?.addEventListener('click', () => {
    const activePlot = getActivePlot();
    const evalResult = recommendationEngine.evaluatePlot(activePlot, state.recSeason);
    if (evalResult.recommendations.length > 0) {
      openPlanModalWithCrop(evalResult.recommendations[0].crop.id);
    }
  });

  // Open Soil Modal button
  document.getElementById('btn-open-soil-modal')?.addEventListener('click', () => {
    const plot = getActivePlot();
    const soil = plot.soilRecord || {};
    document.getElementById('modal-soil-cardno').value = soil.cardNo || `SHC-KA-${plot.district.slice(0,3).toUpperCase()}-2026-${Math.floor(Math.random()*90000+10000)}`;
    document.getElementById('modal-soil-lab').value = soil.labName || 'ICAR-KVK Soil Health Center';
    document.getElementById('modal-soil-ph').value = soil.ph || 6.6;
    document.getElementById('modal-soil-ec').value = soil.electricalConductivity || 0.35;
    document.getElementById('modal-soil-oc').value = soil.organicCarbonPct || 0.55;
    document.getElementById('modal-soil-n').value = soil.nitrogenKgHa || 220;
    document.getElementById('modal-soil-p').value = soil.phosphorusKgHa || 22.0;
    document.getElementById('modal-soil-k').value = soil.potassiumKgHa || 270;
    document.getElementById('modal-soil-depth').value = soil.soilDepth || 'medium';
    document.getElementById('modal-soil-drainage').value = soil.drainage || 'well_drained';
    openModal('modal-soil-data');
  });

  // Export GeoJSON
  document.getElementById('btn-export-current-geojson')?.addEventListener('click', () => {
    const plot = getActivePlot();
    const geojson = {
      type: "Feature",
      properties: {
        id: plot.id,
        name: plot.name,
        district: plot.district,
        taluk: plot.taluk,
        areaAcre: plot.areaAcre,
        irrigation: plot.irrigationType
      },
      geometry: plot.boundary
    };
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(geojson, null, 2));
    const dl = document.createElement('a');
    dl.setAttribute("href", dataStr);
    dl.setAttribute("download", `${plot.id}_parcel.geojson`);
    document.body.appendChild(dl);
    dl.click();
    dl.remove();
    showToast(`Exported ${plot.name} GeoJSON`);
  });

  // Form Submissions
  setupForms();

  // Modal Close buttons
  document.querySelectorAll('[data-close]').forEach(btn => {
    btn.addEventListener('click', () => {
      const modalId = btn.dataset.close;
      closeModal(modalId);
    });
  });

  // Close modals on overlay backdrop click
  document.querySelectorAll('.modal-overlay').forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal(modal.id);
    });
  });

  // Save Profile buttons
  const saveProfileHandler = () => {
    state.farmerProfile.name = document.getElementById('prof-name').value;
    state.farmerProfile.kannadaName = document.getElementById('prof-kannada-name').value;
    state.farmerProfile.phone = document.getElementById('prof-phone').value;
    state.farmerProfile.soilHealthCardNo = document.getElementById('prof-shc').value;
    state.farmerProfile.district = document.getElementById('prof-district').value;
    state.farmerProfile.taluk = document.getElementById('prof-taluk').value;
    state.farmerProfile.village = document.getElementById('prof-village').value;
    state.farmerProfile.riskTolerance = document.getElementById('prof-risk').value;
    state.farmerProfile.primaryObjective = document.getElementById('prof-objective').value;

    storageService.saveProfile(state.farmerProfile);
    renderHeaderControls();
    showToast('Farmer profile saved successfully.');
  };

  document.getElementById('btn-save-profile')?.addEventListener('click', saveProfileHandler);
  document.getElementById('btn-save-profile-bottom')?.addEventListener('click', saveProfileHandler);

  // Reset Demo Data
  document.getElementById('btn-reset-demo-data')?.addEventListener('click', () => {
    if (confirm('Reset all plots, soil records, and planting plans to factory sample state?')) {
      storageService.resetToDefaults();
      initData();
      renderAll();
      showToast('Reset to Karnataka pilot defaults.');
    }
  });
}

function setupForms() {
  // Add Plot Form
  document.getElementById('form-add-plot')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const acres = parseFloat(document.getElementById('new-plot-acres').value) || 2.0;
    const guntas = Math.round(acres * 40);
    const district = document.getElementById('new-plot-district').value;
    const taluk = document.getElementById('new-plot-taluk').value;
    const name = document.getElementById('new-plot-name').value;

    // Use drawn geometry or create a default parcel box around district
    const defaultCoords = district === 'Mandya' ? [12.525, 76.895] : [13.340, 77.100];
    const boundary = window._temporaryDrawnBoundary || {
      type: "Polygon",
      coordinates: [
        [
          [defaultCoords[1] - 0.002, defaultCoords[0] + 0.002],
          [defaultCoords[1] + 0.002, defaultCoords[0] + 0.002],
          [defaultCoords[1] + 0.002, defaultCoords[0] - 0.002],
          [defaultCoords[1] - 0.002, defaultCoords[0] - 0.002],
          [defaultCoords[1] - 0.002, defaultCoords[0] + 0.002]
        ]
      ]
    };
    window._temporaryDrawnBoundary = null;

    const newPlot = {
      id: `plot-${Date.now()}`,
      name,
      district,
      taluk,
      village: document.getElementById('new-plot-village').value,
      surveyNumber: document.getElementById('new-plot-survey').value,
      areaAcre: acres,
      areaGuntas: guntas,
      areaHectares: (acres * 0.404686).toFixed(2),
      coordinates: defaultCoords,
      boundary,
      irrigationType: document.getElementById('new-plot-irrigation').value,
      waterAvailability: document.getElementById('new-plot-water-avail').value,
      previousCrops: [document.getElementById('new-plot-prev-crops').value || "Ragi / Groundnut"],
      soilRecord: {
        hasSoilTest: false,
        cardNo: "",
        testDate: "",
        labName: "",
        texture: document.getElementById('new-plot-soil-texture').value,
        textureDisplay: document.getElementById('new-plot-soil-texture').selectedOptions[0].text,
        ph: 6.5,
        electricalConductivity: 0.35,
        organicCarbonPct: 0.52,
        nitrogenKgHa: 220,
        phosphorusKgHa: 22.0,
        potassiumKgHa: 260,
        soilDepth: "medium",
        drainage: "well_drained"
      },
      waterRecord: {
        borewellDepthFt: 400,
        groundwaterYieldInches: 1.5,
        irrigationCostPerHour: 80
      },
      satelliteSummary: {
        latestNdvi: 0.72,
        canopyCondition: "Active Canopy",
        vegetationAnomaly: "+5% vs baseline",
        cloudCoverLatest: 2
      }
    };

    storageService.addPlot(newPlot);
    state.plots = storageService.getPlots();
    state.activePlotId = newPlot.id;

    closeModal('modal-add-plot');
    renderAll();
    centerMapOnActivePlot();
    showToast(`Registered plot: ${newPlot.name}`);
  });

  // Soil Form
  document.getElementById('form-soil-data')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const plot = getActivePlot();
    plot.soilRecord = {
      hasSoilTest: true,
      cardNo: document.getElementById('modal-soil-cardno').value,
      testDate: new Date().toISOString().split('T')[0],
      labName: document.getElementById('modal-soil-lab').value,
      texture: plot.soilRecord?.texture || "red_sandy_loam",
      textureDisplay: plot.soilRecord?.textureDisplay || "Red Sandy Loam",
      ph: parseFloat(document.getElementById('modal-soil-ph').value),
      electricalConductivity: parseFloat(document.getElementById('modal-soil-ec').value),
      organicCarbonPct: parseFloat(document.getElementById('modal-soil-oc').value),
      nitrogenKgHa: parseInt(document.getElementById('modal-soil-n').value, 10),
      phosphorusKgHa: parseFloat(document.getElementById('modal-soil-p').value),
      potassiumKgHa: parseInt(document.getElementById('modal-soil-k').value, 10),
      soilDepth: document.getElementById('modal-soil-depth').value,
      drainage: document.getElementById('modal-soil-drainage').value
    };

    storageService.updatePlot(plot);
    state.plots = storageService.getPlots();
    closeModal('modal-soil-data');
    renderAll();
    showToast('Updated Soil Health Card records.');
  });

  // Create Planting Plan Form
  document.getElementById('form-create-plan')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const plotId = document.getElementById('plan-input-plot').value;
    const cropId = document.getElementById('plan-input-crop').value;
    const acres = parseFloat(document.getElementById('plan-input-acre').value) || 1.0;
    const sowing = document.getElementById('plan-input-sow').value;

    const plot = state.plots.find(p => p.id === plotId) || getActivePlot();
    const crop = karnatakaCrops.find(c => c.id === cropId) || karnatakaCrops[0];

    const financials = recommendationEngine.calculateCropFinancials(crop, acres, {
      priceDeltaPct: state.priceDeltaPct,
      costDeltaPct: state.costDeltaPct
    });

    const newPlan = {
      id: `plan-${Date.now()}`,
      plotId: plot.id,
      plotName: plot.name,
      cropId: crop.id,
      cropName: `${crop.name} (${crop.popularVarieties[0]})`,
      kannadaName: crop.kannadaName,
      cultivatedAcre: acres,
      sowingWindow: sowing,
      harvestWindow: crop.harvestWindow,
      budgetCostTotal: financials.totalPlotCost,
      expectedGrossRevenue: financials.expected.totalPlotGrossRevenue,
      expectedNetReturn: financials.expected.totalPlotNetReturn,
      pessimisticNetReturn: financials.pessimistic.totalPlotNetReturn,
      optimisticNetReturn: financials.optimistic.totalPlotNetReturn,
      waterRequirementMm: crop.waterRequirements.totalMm,
      irrigationStrategy: crop.waterRequirements.irrigationNeeds,
      status: "Active Planned",
      createdAt: new Date().toISOString().split('T')[0]
    };

    storageService.addPlan(newPlan);
    state.plans = storageService.getPlans();
    closeModal('modal-create-plan');
    switchView('plans');
    showToast(`Saved planting plan for ${crop.name}!`);
  });
}

function openPlanModalWithCrop(cropId = null) {
  const plotSelect = document.getElementById('plan-input-plot');
  const cropSelect = document.getElementById('plan-input-crop');
  const acreInput = document.getElementById('plan-input-acre');

  if (plotSelect) {
    plotSelect.innerHTML = state.plots.map(p => `
      <option value="${p.id}" ${p.id === state.activePlotId ? 'selected' : ''}>
        ${p.name} (${p.areaAcre} Acres)
      </option>
    `).join('');
  }

  if (cropSelect) {
    cropSelect.innerHTML = karnatakaCrops.map(c => `
      <option value="${c.id}" ${c.id === cropId ? 'selected' : ''}>
        ${c.name} (${c.kannadaName}) &bull; ${c.season.toUpperCase()}
      </option>
    `).join('');
  }

  if (acreInput) {
    acreInput.value = getActivePlot().areaAcre;
  }

  openModal('modal-create-plan');
}

/* ==========================================================================
   HELPERS & MODALS
   ========================================================================== */
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add('active');
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('active');
}

function showToast(message) {
  const toast = document.getElementById('hud-toast');
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add('visible');
  setTimeout(() => {
    toast.classList.remove('visible');
  }, 3200);
}

// Global hook for in-page navigation links
window.switchViewGlobal = switchView;
