import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

export function createFieldMap(container, tileStatus) {
  let map;
  let parcel;
  let geometry = null;
  let preview;
  let previewGeometry = null;
  let drawing = false;
  let vertices = [];
  let vertexLayer;
  let drawingLine;
  let changed;
  let basemap = 'satellite';
  let tileFailed = false;
  const layers = {};

  function renderPreview() {
    if (!map) return;
    preview?.remove();
    preview = previewGeometry ? L.geoJSON(previewGeometry, {
      style: { color: '#b96b16', weight: 3, dashArray: '6 4', fillOpacity: 0.2 },
    }).addTo(map) : null;
  }
  function redrawVertices() {
    vertexLayer.clearLayers();
    drawingLine?.remove();
    vertices.forEach((point, index) => {
      const icon = L.divIcon({ className: 'boundary-peg', html: `<span>${index + 1}</span>`,
        iconSize: [22, 22], iconAnchor: [11, 11] });
      const marker = L.marker([point[1], point[0]], { draggable: true, icon }).addTo(vertexLayer);
      marker.on('dragend', () => {
        const value = map.wrapLatLng(marker.getLatLng());
        vertices[index] = [value.lng, value.lat];
        redrawVertices();
      });
    });
    if (vertices.length > 1) drawingLine = L.polyline(vertices.map(([x, y]) => [y, x]),
      { color: '#b96b16', weight: 2, dashArray: '5 6', interactive: false }).addTo(map);
    previewGeometry = vertices.length >= 3
      ? { type: 'Polygon', coordinates: [[...vertices.map(point => [...point]), [...vertices[0]]]] } : null;
    renderPreview();
    changed?.(previewGeometry, vertices.length);
  }
  function render(fit = false) {
    if (!map) return;
    container.hidden = false;
    parcel?.remove();
    parcel = geometry ? L.geoJSON(geometry, {
      style: { color: '#216743', weight: 3, fillColor: '#216743', fillOpacity: 0.18 },
    }).addTo(map) : null;
    map.invalidateSize();
    if (fit && parcel && !drawing && !previewGeometry) map.fitBounds(parcel.getBounds(),
      { paddingTopLeft: [36, 70], paddingBottomRight: [36, 100], maxZoom: 18 });
    renderPreview();
  }
  function tileLayer(url, options, kind, primary = true) {
    const layer = L.tileLayer(url, options);
    layer.on('tileerror', () => {
      if (basemap === kind) {
        tileFailed = true;
        tileStatus.textContent = `${kind === 'satellite' ? 'Satellite' : 'Street'} basemap tiles unavailable. `
          + 'Try the other basemap. Stored boundaries and backend data are independent of imagery.';
      }
    });
    if (primary) layer.on('load', () => {
      if (basemap === kind && !tileFailed) tileStatus.textContent = '';
    });
    return layer;
  }
  const controls = {
    setGeometry(value) { geometry = value; render(true); },
    show() {
      const first = !map;
      if (first) {
        map = L.map(container, { zoomControl: true, minZoom: 2, maxZoom: 19 });
        map.setView([20, 0], 2);
        vertexLayer = L.layerGroup().addTo(map);
        map.on('click', event => {
          if (!drawing || vertices.length >= 9999) return;
          const point = map.wrapLatLng(event.latlng);
          vertices.push([point.lng, point.lat]);
          redrawVertices();
        });
        layers.satellite = L.layerGroup([
          tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            { maxZoom: 19, attribution: '&copy; Esri, Maxar, Earthstar Geographics' }, 'satellite'),
          tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
            { maxZoom: 19, attribution: '&copy; Esri' }, 'satellite', false),
        ]);
        layers.streets = tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
          { maxZoom: 19, attribution: '&copy; OpenStreetMap contributors' }, 'streets');
        tileStatus.textContent = 'Loading basemap imagery...';
        layers[basemap].addTo(map);
        new ResizeObserver(() => map.invalidateSize({ animate: false })).observe(container);
      }
      render(first);
    },
    setBasemap(value) {
      if (!['satellite', 'streets'].includes(value)) return;
      layers[basemap]?.remove();
      basemap = value;
      tileFailed = false;
      tileStatus.textContent = 'Loading basemap imagery...';
      controls.show();
      layers[basemap].addTo(map);
    },
    world() { controls.show(); map.setView([20, 0], 2); },
    fit() {
      controls.show();
      const target = preview ?? parcel;
      if (target) map.fitBounds(target.getBounds(),
        { paddingTopLeft: [36, 70], paddingBottomRight: [36, 100], maxZoom: 18 });
    },
    startDrawing(callback) {
      drawing = true;
      vertices = [];
      changed = callback;
      controls.show();
      map.doubleClickZoom.disable();
      redrawVertices();
    },
    undoDrawing() {
      if (!drawing) return;
      vertices.pop();
      redrawVertices();
    },
    finishDrawing() {
      if (vertices.length < 3) return false;
      drawing = false;
      map.doubleClickZoom.enable();
      vertexLayer.clearLayers();
      drawingLine?.remove();
      return true;
    },
    clearPreview() {
      drawing = false;
      changed = null;
      previewGeometry = null;
      vertices = [];
      vertexLayer?.clearLayers();
      drawingLine?.remove();
      map?.doubleClickZoom.enable();
      render();
    },
    previewGeometry(value) {
      previewGeometry = value;
      controls.show();
      controls.fit();
    },
    center(longitude, latitude) {
      controls.show();
      map.setView([latitude, longitude], 17);
    },
  };
  return controls;
}
