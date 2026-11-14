import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './style.css';
import { agriZonesGeoJSON } from './data/agriZones.js';
import { sensorStations } from './data/sensorStations.js';
import { mandyaDistrictGeoJSON, mandyaTelemetryStations } from './data/mandyaData.js';

// Setup Map Center & Limits
const map = L.map('map', {
  center: [12.523, 76.898],
  zoom: 11,
  minZoom: 2,
  maxZoom: 18,
  worldCopyJump: true,
  zoomControl: true
});

map.zoomControl.setPosition('topleft');

/* ==========================================================================
   1. SKY-VIEW BASE LAYERS
   ========================================================================== */
const satelliteLayer = L.tileLayer(
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
  {
    maxZoom: 19,
    attribution: 'Sky-View: &copy; Esri, Maxar, Earthstar Geographics, USDA FSA, USGS, Aerogrid, IGN, IGP'
  }
);

const hybridReferenceLayer = L.tileLayer(
  'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
  {
    maxZoom: 19,
    attribution: 'Borders & Names: &copy; Esri'
  }
);

const topoLayer = L.tileLayer(
  'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
  {
    maxZoom: 17,
    attribution: 'Map data: &copy; OpenStreetMap contributors, SRTM | Map style: &copy; OpenTopoMap'
  }
);

// Add initial satellite layer
satelliteLayer.addTo(map);

/* ==========================================================================
   2. STATE MANAGEMENT
   ========================================================================== */
let currentScope = 'mandya'; // 'mandya' | 'global'
let activeCropFilter = 'all';
let isNdviMode = true;
let geojsonLayerGroup = L.layerGroup().addTo(map);
let sensorLayerGroup = L.layerGroup().addTo(map);

function getActiveDataset() {
  return currentScope === 'mandya' ? mandyaDistrictGeoJSON : agriZonesGeoJSON;
}

function getActiveSensors() {
  return currentScope === 'mandya' ? mandyaTelemetryStations : sensorStations;
}

/* ==========================================================================
   3. GEOMETRY STYLING & POLYGON LOGIC
   ========================================================================== */
function getPolygonStyle(feature) {
  const ndvi = feature.properties.ndviMean || 0.6;
  let fillColor = '#22c55e';

  if (isNdviMode) {
    if (feature.properties.category === 'reservoir') {
      fillColor = '#0284c7'; // Water blue
    } else if (ndvi >= 0.8) {
      fillColor = '#15803d'; // High biomass / dark green
    } else if (ndvi >= 0.7) {
      fillColor = '#22c55e'; // Dense green
    } else if (ndvi >= 0.6) {
      fillColor = '#84cc16'; // Moderate green/yellow
    } else if (ndvi >= 0.5) {
      fillColor = '#eab308'; // Semi-arid yellow
    } else {
      fillColor = '#d97706'; // Low canopy
    }
  } else {
    // Category colors
    const cat = feature.properties.category;
    if (cat === 'sugar_paddy' || cat === 'grains') fillColor = '#38bdf8';
    else if (cat === 'horticulture' || cat === 'specialty') fillColor = '#10b981';
    else if (cat === 'millets_dryland' || cat === 'oilseeds') fillColor = '#f59e0b';
    else if (cat === 'reservoir') fillColor = '#0284c7';
  }

  return {
    fillColor: fillColor,
    weight: 2,
    opacity: 0.9,
    color: '#ffffff',
    dashArray: '3',
    fillOpacity: 0.42
  };
}

// Render Crop Zones & Belts
function renderAgriZones() {
  geojsonLayerGroup.clearLayers();

  const dataset = getActiveDataset();
  const filteredFeatures = dataset.features.filter(f => {
    if (activeCropFilter === 'all') return true;
    return f.properties.category === activeCropFilter;
  });

  const geoLayer = L.geoJSON(
    { type: 'FeatureCollection', features: filteredFeatures },
    {
      style: getPolygonStyle,
      onEachFeature: (feature, layer) => {
        const props = feature.properties;
        layer.bindTooltip(`
          <div style="font-family: inherit; font-size: 12px; line-height: 1.4;">
            <strong style="color: #38bdf8;">${props.name}</strong><br/>
            <span>NDVI: <b style="color: ${props.ndviColor};">${props.ndviMean}</b> &bull; ${props.cropTypeSummary || props.category}</span>
          </div>
        `, { sticky: true, opacity: 0.95 });

        layer.on('mouseover', function (e) {
          const l = e.target;
          l.setStyle({
            weight: 3.5,
            color: '#38bdf8',
            dashArray: '',
            fillOpacity: 0.6
          });
          if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
            l.bringToFront();
          }
        });

        layer.on('mouseout', function (e) {
          geoLayer.resetStyle(e.target);
        });

        layer.on('click', function (e) {
          openZoneInspector(props);
          if (props.flyTo) {
            map.flyTo([props.flyTo.lat, props.flyTo.lng], props.flyTo.zoom, { duration: 1.5 });
          } else {
            map.fitBounds(e.target.getBounds(), { padding: [50, 50], maxZoom: 12 });
          }
        });
      }
    }
  );

  geoLayer.addTo(geojsonLayerGroup);
}

/* ==========================================================================
   4. IN-FIELD TELEMETRY SENSORS
   ========================================================================== */
function renderSensorStations() {
  sensorLayerGroup.clearLayers();
  const sensors = getActiveSensors();

  sensors.forEach(sensor => {
    const statusClass = sensor.status;

    const customIcon = L.divIcon({
      className: 'custom-sensor-icon',
      html: `
        <div class="iot-sensor-beacon ${statusClass}">
          <div class="iot-beacon-ring"></div>
          <div class="iot-beacon-dot"></div>
        </div>
      `,
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    });

    const marker = L.marker([sensor.lat, sensor.lng], { icon: customIcon });

    marker.bindTooltip(`
      <div style="font-family: inherit; font-size: 12px; line-height: 1.4;">
        <strong style="color: #4ade80;">Telemetry Node: ${sensor.id}</strong><br/>
        <span>${sensor.name}</span><br/>
        <span>Moisture: <b>${sensor.soilMoisturePct}%</b> | Temp: <b>${sensor.canopyTempC}°C</b></span>
      </div>
    `, { sticky: true, opacity: 0.95 });

    marker.on('click', () => {
      openSensorInspector(sensor);
      map.flyTo([sensor.lat, sensor.lng], 13, { duration: 1.4 });
    });

    marker.addTo(sensorLayerGroup);
  });
}

/* ==========================================================================
   5. INSPECTOR HUD DRAWER LOGIC
   ========================================================================== */
const inspectorEl = document.getElementById('hud-inspector');
const inspectTag = document.getElementById('inspect-tag');
const inspectTitle = document.getElementById('inspect-title');
const inspectSubtitle = document.getElementById('inspect-subtitle');
const inspectNdvi = document.getElementById('inspect-ndvi');
const inspectMoisture = document.getElementById('inspect-moisture');
const inspectTemp = document.getElementById('inspect-temp');
const inspectRisk = document.getElementById('inspect-risk');
const inspectCrops = document.getElementById('inspect-crops');
const inspectArea = document.getElementById('inspect-area');
const inspectSoil = document.getElementById('inspect-soil');
const inspectWater = document.getElementById('inspect-water');
const inspectCycle = document.getElementById('inspect-cycle');
const inspectYield = document.getElementById('inspect-yield');
const inspectSatellite = document.getElementById('inspect-satellite');
const btnPing = document.getElementById('btn-ping-telemetry');
const btnExport = document.getElementById('btn-export-geojson');

function openZoneInspector(props) {
  inspectTag.textContent = currentScope === 'mandya' ? 'MANDYA TALUK AGRO-ZONE' : 'CROPLAND BIOME';
  inspectTag.style.color = '#4ade80';
  inspectTag.style.borderColor = 'rgba(74, 222, 128, 0.4)';

  inspectTitle.textContent = props.name;
  inspectSubtitle.textContent = props.taluk 
    ? `${props.taluk} Taluk &bull; Mandya District, Karnataka`
    : `${props.region} &bull; ${props.country}`;

  inspectNdvi.textContent = props.ndviMean.toFixed(2);
  inspectMoisture.textContent = props.moistureStatus ? props.moistureStatus.split(' ')[0] : (props.groundwaterDepthMeters || '32%');
  inspectTemp.textContent = props.temperatureCanopy || '26.5°C';
  inspectRisk.textContent = props.riskAlert ? props.riskAlert.split(' - ')[0] : 'Normal';

  inspectCrops.textContent = props.primaryCrops.join(', ');
  inspectArea.textContent = props.areaHectares 
    ? `${(props.areaHectares).toLocaleString()} Hectares`
    : 'Monitored Basin';

  inspectSoil.textContent = `${props.soilType} (pH ${props.soilPh})`;
  inspectWater.textContent = props.irrigationSource || props.irrigationType;
  inspectCycle.textContent = props.croppingSeasons || props.growingSeason;
  inspectYield.textContent = props.projectedYield;
  inspectSatellite.textContent = props.remoteSensingSource || props.satelliteMission;

  inspectorEl.classList.add('open');
}

function openSensorInspector(sensor) {
  inspectTag.textContent = `IOT FIELD NODE &bull; ${sensor.id}`;
  inspectTag.style.color = '#38bdf8';
  inspectTag.style.borderColor = 'rgba(56, 189, 248, 0.4)';

  inspectTitle.textContent = sensor.name;
  inspectSubtitle.textContent = `${sensor.region} (Lat: ${sensor.lat.toFixed(4)}, Lng: ${sensor.lng.toFixed(4)})`;
  inspectNdvi.textContent = (sensor.ndreIndex * 1.8).toFixed(2);
  inspectMoisture.textContent = `${sensor.soilMoisturePct}%`;
  inspectTemp.textContent = `${sensor.canopyTempC}°C`;
  inspectRisk.textContent = sensor.status.toUpperCase();

  inspectCrops.textContent = sensor.crop;
  inspectArea.textContent = `Organization: ${sensor.sourceOrg || 'Regional Agro-Met Network'}`;
  inspectSoil.textContent = `Root-zone Moisture: ${sensor.soilMoisturePct}% (0-30cm sensor probe)`;
  inspectWater.textContent = `Rainfall (24h): ${sensor.rainfall24hMm} mm &bull; Solar: ${sensor.solarIrradianceWm2} W/m²`;
  inspectCycle.textContent = `Air Humidity: ${sensor.humidityPct}% &bull; Battery: ${sensor.batteryPct}%`;
  inspectYield.textContent = `NDRE Chlorophyll Index: ${sensor.ndreIndex}`;
  inspectSatellite.textContent = 'Ground-Truth Calibration Node';

  inspectorEl.classList.add('open');
}

document.getElementById('inspect-close').addEventListener('click', () => {
  inspectorEl.classList.remove('open');
});

/* ==========================================================================
   6. SCOPE SWITCHER (MANDYA VS GLOBAL)
   ========================================================================== */
const btnScopeMandya = document.getElementById('btn-scope-mandya');
const btnScopeGlobal = document.getElementById('btn-scope-global');
const hudSubtitle = document.getElementById('hud-subtitle');
const statCropland = document.getElementById('stat-cropland');
const statNdvi = document.getElementById('stat-ndvi');
const statNodes = document.getElementById('stat-nodes');
const statOrbit = document.getElementById('stat-orbit');
const regionSelect = document.getElementById('region-jump');
const filterChipsContainer = document.querySelector('.filter-chips');

function applyScope(scope) {
  currentScope = scope;
  activeCropFilter = 'all';

  if (scope === 'mandya') {
    btnScopeMandya.classList.add('active');
    btnScopeGlobal.classList.remove('active');
    hudSubtitle.innerHTML = 'MANDYA SATELLITE GEOMAP &bull; KAVERI AGRO-BASIN';

    statCropland.textContent = '268.0k ha';
    statNdvi.innerHTML = '0.81 <small class="text-sub">Peak Cane</small>';
    statNodes.textContent = '8 Active (KSNDMC)';
    statOrbit.textContent = 'KRS Dam 124.8 ft FSL';

    // Update Region Dropdown
    regionSelect.innerHTML = `
      <option value="" disabled selected>Fly to Mandya taluk or canal...</option>
      <option value="mandya-central">🌾 Mandya Central & VC Canal Command</option>
      <option value="pandavapura-sugar">🍬 Pandavapura Sugar Agro-Zone</option>
      <option value="srirangapatna-delta">🌴 Srirangapatna Kaveri Island</option>
      <option value="maddur-coconut-sericulture">🥥 Maddur Coconut & Sericulture</option>
      <option value="malavalli-ragi">🌾 Malavalli Ragi & Agro-Silvo</option>
      <option value="nagamangala-plateau">🌾 Nagamangala Millet Plateau</option>
      <option value="kr-pet-hemavati">🌿 K.R. Pet & Hemavati Belt</option>
      <option value="krs-reservoir-lifeline">🌊 Krishna Raja Sagara (KRS) Dam</option>
    `;

    // Update Filter Chips
    filterChipsContainer.innerHTML = `
      <button class="chip active" data-crop="all">All</button>
      <button class="chip" data-crop="sugar_paddy">Sugarcane & Paddy</button>
      <button class="chip" data-crop="horticulture">Coconut & Horticulture</button>
      <button class="chip" data-crop="millets_dryland">Millets & Ragi</button>
      <button class="chip" data-crop="reservoir">KRS Reservoir</button>
    `;

    // Fly to Mandya
    map.flyTo([12.523, 76.898], 11, { duration: 1.8 });
    showToast('Switched focus to Mandya District, Karnataka (Kaveri Basin)');
  } else {
    btnScopeGlobal.classList.add('active');
    btnScopeMandya.classList.remove('active');
    hudSubtitle.innerHTML = 'GLOBAL SATELLITE GEOMAP &bull; AGRICULTURAL INTELLIGENCE';

    statCropland.textContent = '247.9M ha';
    statNdvi.innerHTML = '0.71 <small class="text-sub">Healthy</small>';
    statNodes.textContent = '10 Active';
    statOrbit.textContent = 'Sentinel-2A / 10m MSI';

    // Restore Global Dropdown
    regionSelect.innerHTML = `
      <option value="" disabled selected>Select a global breadbasket...</option>
      <option value="us-corn-belt">🌽 US Corn & Soybean Belt</option>
      <option value="california-central-valley">🍇 California Central Valley</option>
      <option value="mato-grosso-cerrado">🌱 Brazil Mato Grosso (Cerrado)</option>
      <option value="argentine-pampas">🌾 Argentine Humid Pampas</option>
      <option value="ukrainian-chernozem">🌻 Ukrainian Chernozem Plain</option>
      <option value="indo-gangetic-plain">🍚 Indo-Gangetic Alluvial Basin</option>
      <option value="sanjiang-plain">🌾 Northeast China Plain</option>
      <option value="po-river-valley">🌿 Italian Po River Valley</option>
      <option value="nile-river-delta">🌿 Nile Delta & Valley Oasis</option>
      <option value="murray-darling-basin">🌾 Australian Murray-Darling</option>
    `;

    // Restore Global Chips
    filterChipsContainer.innerHTML = `
      <button class="chip active" data-crop="all">All</button>
      <button class="chip" data-crop="grains">Grains & Cereals</button>
      <button class="chip" data-crop="oilseeds">Oilseeds & Soy</button>
      <button class="chip" data-crop="specialty">Orchards & Specialty</button>
    `;

    // Fly to Global
    map.flyTo([25.0, 10.0], 3, { duration: 2.0 });
    showToast('Switched to Global Breadbaskets Sky-View');
  }

  // Re-bind chip listeners
  attachChipListeners();
  renderAgriZones();
  renderSensorStations();
  openZoneInspector(getActiveDataset().features[0].properties);
}

btnScopeMandya.addEventListener('click', () => applyScope('mandya'));
btnScopeGlobal.addEventListener('click', () => applyScope('global'));

function attachChipListeners() {
  const chips = document.querySelectorAll('.chip');
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      chips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      activeCropFilter = chip.dataset.crop;
      renderAgriZones();
      showToast(`Filter: ${chip.textContent.trim()}`);
    });
  });
}

/* ==========================================================================
   7. BASE LAYER & CONTROLS
   ========================================================================== */
const layerButtons = document.querySelectorAll('.layer-btn');
layerButtons.forEach(btn => {
  btn.addEventListener('click', () => {
    layerButtons.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const layerType = btn.dataset.baselayer;
    map.removeLayer(satelliteLayer);
    map.removeLayer(hybridReferenceLayer);
    map.removeLayer(topoLayer);

    if (layerType === 'satellite') {
      satelliteLayer.addTo(map);
    } else if (layerType === 'hybrid') {
      satelliteLayer.addTo(map);
      hybridReferenceLayer.addTo(map);
    } else if (layerType === 'topo') {
      topoLayer.addTo(map);
    }
    showToast(`Base Layer: ${btn.textContent.trim()}`);
  });
});

document.getElementById('toggle-zones').addEventListener('change', (e) => {
  if (e.target.checked) geojsonLayerGroup.addTo(map);
  else map.removeLayer(geojsonLayerGroup);
});

document.getElementById('toggle-sensors').addEventListener('change', (e) => {
  if (e.target.checked) sensorLayerGroup.addTo(map);
  else map.removeLayer(sensorLayerGroup);
});

document.getElementById('toggle-ndvi').addEventListener('change', (e) => {
  isNdviMode = e.target.checked;
  renderAgriZones();
  showToast(isNdviMode ? 'NDVI Vegetation Health Mode Active' : 'Crop Category Color Mode Active');
});

regionSelect.addEventListener('change', (e) => {
  const zoneId = e.target.value;
  const dataset = getActiveDataset();
  const targetFeature = dataset.features.find(f => f.id === zoneId);
  if (targetFeature && targetFeature.properties.flyTo) {
    const { lat, lng, zoom } = targetFeature.properties.flyTo;
    map.flyTo([lat, lng], zoom, { duration: 1.8 });
    openZoneInspector(targetFeature.properties);
    showToast(`Navigated to: ${targetFeature.properties.name}`);
  }
});

btnPing.addEventListener('click', () => {
  btnPing.disabled = true;
  btnPing.innerHTML = 'Connecting to Local Telemetry...';

  setTimeout(() => {
    const deltaMoisture = (Math.random() * 1.4 - 0.7).toFixed(1);
    const deltaTemp = (Math.random() * 0.8 - 0.4).toFixed(1);

    const currentMoisture = parseFloat(inspectMoisture.textContent) || 35.0;
    const currentTemp = parseFloat(inspectTemp.textContent) || 26.0;

    inspectMoisture.textContent = `${(currentMoisture + parseFloat(deltaMoisture)).toFixed(1)}%`;
    inspectTemp.textContent = `${(currentTemp + parseFloat(deltaTemp)).toFixed(1)}°C`;

    btnPing.disabled = false;
    btnPing.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
      Simulate Satellite Pass & Telemetry Ping
    `;
    showToast(currentScope === 'mandya' ? 'Downlink refreshed from KSNDMC / VC Farm probe.' : 'Telemetry refreshed from orbital downlink.');
  }, 600);
});

btnExport.addEventListener('click', () => {
  const dataset = getActiveDataset();
  const filename = currentScope === 'mandya' ? 'mandya_kaveri_agricultural_zones.geojson' : 'global_agricultural_zones.geojson';
  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(dataset, null, 2));
  const downloadAnchor = document.createElement('a');
  downloadAnchor.setAttribute("href", dataStr);
  downloadAnchor.setAttribute("download", filename);
  document.body.appendChild(downloadAnchor);
  downloadAnchor.click();
  downloadAnchor.remove();
  showToast(`Exported ${filename}`);
});

function showToast(message) {
  const toast = document.getElementById('hud-toast');
  toast.textContent = message;
  toast.classList.add('visible');
  setTimeout(() => {
    toast.classList.remove('visible');
  }, 3000);
}

// Initialize Mandya as default
applyScope('mandya');
