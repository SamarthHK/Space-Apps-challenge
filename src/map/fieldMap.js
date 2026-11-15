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
  let changed;
  const vertexIcon = L.divIcon({ className: 'leaflet-div-icon', iconSize: [10, 10] });

  function renderPreview() {
    if (!map) return;
    if (preview) map.removeLayer(preview);
    preview = previewGeometry ? L.geoJSON(previewGeometry, {
      style: { color: '#b96b16', dashArray: '6 4', fillOpacity: 0.2 },
    }).addTo(map) : null;
  }
  function redrawVertices() {
    vertexLayer.clearLayers();
    vertices.forEach((point, index) => {
      const marker = L.marker([point[1], point[0]], { draggable: true, icon: vertexIcon }).addTo(vertexLayer);
      marker.on('dragend', () => {
        const value = marker.getLatLng();
        vertices[index] = [value.lng, value.lat];
        redrawVertices();
      });
    });
    previewGeometry = vertices.length >= 3
      ? { type: 'Polygon', coordinates: [[...vertices.map(point => [...point]), [...vertices[0]]]] } : null;
    renderPreview();
    changed?.(previewGeometry);
  }
  function addVertex(event) {
    if (!drawing || vertices.length >= 9999) return;
    vertices.push([event.latlng.lng, event.latlng.lat]);
    redrawVertices();
  }
  function render() {
    if (!map) return;
    if (parcel) map.removeLayer(parcel);
    parcel = null;
    if (!geometry) {
      container.hidden = !drawing && !previewGeometry;
      if (!container.hidden) { map.invalidateSize(); renderPreview(); }
      return;
    }
    container.hidden = false;
    map.invalidateSize();
    parcel = L.geoJSON(geometry, { style: { color: '#216743', fillOpacity: 0.15 } }).addTo(map);
    map.fitBounds(parcel.getBounds(), { padding: [24, 24] });
    renderPreview();
  }
  const controls = {
    setGeometry(value) { geometry = value; render(); },
    show() {
      if (!map) {
        map = L.map(container, { zoomControl: true });
        map.setView([0, 0], 2);
        vertexLayer = L.layerGroup().addTo(map);
        map.on('click', addVertex);
        const tiles = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '&copy; OpenStreetMap contributors', maxZoom: 19,
        });
        tiles.on('tileerror', () => {
          tileStatus.textContent = 'Base-map tiles unavailable. Stored field geometry is independent of the tile service.';
        });
        tiles.addTo(map);
      }
      render();
    },
    startDrawing(callback) {
      drawing = true;
      vertices = [];
      changed = callback;
      controls.show();
      map.doubleClickZoom.disable();
      redrawVertices();
    },
    finishDrawing() {
      if (vertices.length < 3) return false;
      drawing = false;
      map.doubleClickZoom.enable();
      vertexLayer.clearLayers();
      return true;
    },
    clearPreview() {
      drawing = false;
      changed = null;
      previewGeometry = null;
      vertices = [];
      vertexLayer?.clearLayers();
      map?.doubleClickZoom.enable();
      renderPreview();
      render();
    },
    previewGeometry(value) {
      previewGeometry = value;
      controls.show();
      container.hidden = false;
      map.invalidateSize();
      renderPreview();
      if (preview) map.fitBounds(preview.getBounds(), { padding: [24, 24] });
    },
    center(longitude, latitude) {
      controls.show();
      container.hidden = false;
      map.invalidateSize();
      map.setView([latitude, longitude], 17);
    },
  };
  return controls;
}
