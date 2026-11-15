import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

export function createFieldMap(container, tileStatus) {
  let map;
  let parcel;
  let geometry = null;
  function render() {
    if (!map) return;
    if (parcel) map.removeLayer(parcel);
    parcel = null;
    if (!geometry) {
      container.hidden = true;
      return;
    }
    container.hidden = false;
    map.invalidateSize();
    parcel = L.geoJSON(geometry, { style: { color: '#216743', fillOpacity: 0.15 } }).addTo(map);
    map.fitBounds(parcel.getBounds(), { padding: [24, 24] });
  }
  return {
    setGeometry(value) { geometry = value; render(); },
    show() {
      if (!map) {
        map = L.map(container, { zoomControl: true });
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
  };
}
