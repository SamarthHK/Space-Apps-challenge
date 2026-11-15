export const DEMO_PARCEL = {
  type: 'Polygon',
  coordinates: [[[76.8258, 12.5708], [76.8275, 12.5711], [76.8278, 12.5699],
    [76.8261, 12.5696], [76.8258, 12.5708]]],
};

export const DEMO_SEASONS = [
  {
    id: 'rice', number: '01', season: 'Kharif', months: 'JUL - DEC',
    name: 'Paddy', localName: 'Rice / Bhatta', family: 'Cereal',
    window: 'Nursery in June; transplant in July. Harvest November - December.',
    duration: 'About 120-135 days after transplanting', water: 'High water need',
    reason: 'Put the water-demanding crop in the monsoon window, not the dry summer.',
    note: 'Assumes a level, bunded field and dependable canal or supplemental irrigation. Rainfall alone is not a guarantee.',
    activeMonths: [0, 1, 2, 3, 4, 5],
  },
  {
    id: 'pulse', number: '02', season: 'Post-rice / early summer', months: 'FEB - APR',
    name: 'Green gram', localName: 'Moong / Hesaru', family: 'Legume',
    window: 'Sow in early February after draining the rice field. Harvest April.',
    duration: 'Short-duration crop, about 65-75 days', water: 'Light irrigation needed',
    reason: 'A short pulse fits after rice and avoids repeating a cereal crop.',
    note: 'Needs good drainage and irrigation at critical stages. Legume residues can support soil fertility; fertilizer savings are not guaranteed.',
    activeMonths: [7, 8, 9],
  },
  {
    id: 'rest', number: '03', season: 'Summer pause', months: 'MAY - JUN',
    name: 'Mulch & recharge', localName: 'Managed fallow', family: 'Soil care',
    window: 'Retain suitable residues in May; prepare bunds and the next rice nursery in June.',
    duration: 'No third cash crop assumed', water: 'Avoid extra summer irrigation',
    reason: 'Do not promise a third harvest when pre-monsoon water can be limited.',
    note: 'Manage weeds and residues; do not burn stubble. January is reserved for rice harvest delays, drainage and field preparation.',
    activeMonths: [10, 11],
  },
];

const radius = 6371008.8;
const radians = degrees => degrees * Math.PI / 180;
const cross = (a, b, c) => (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
const onSegment = (a, b, p) => Math.abs(cross(a, b, p)) < 1e-14 &&
  p[0] >= Math.min(a[0], b[0]) && p[0] <= Math.max(a[0], b[0]) &&
  p[1] >= Math.min(a[1], b[1]) && p[1] <= Math.max(a[1], b[1]);
function intersects(a, b, c, d) {
  return (cross(a, b, c) * cross(a, b, d) < 0 && cross(c, d, a) * cross(c, d, b) < 0) ||
    onSegment(a, b, c) || onSegment(a, b, d) || onSegment(c, d, a) || onSegment(c, d, b);
}

export function summarizeDemoGeometry(geometry) {
  if (!geometry || !['Polygon', 'MultiPolygon'].includes(geometry.type)) {
    throw new Error('Draw a polygon or choose a field with a recorded polygon boundary.');
  }
  const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
  if (!Array.isArray(polygons) || !polygons.length) throw new Error('The boundary is empty.');
  let area = 0;
  let vertices = 0;
  const points = [];
  for (const polygon of polygons) {
    if (!Array.isArray(polygon) || !polygon.length) throw new Error('The boundary is empty.');
    let polygonArea = 0;
    for (const [ringIndex, ring] of polygon.entries()) {
      if (!Array.isArray(ring) || ring.length < 4 || ring.length > 501) {
        throw new Error('Use a closed boundary with 3-500 points per ring for this demo.');
      }
      if (ring.some(point => !Array.isArray(point) || point.length < 2 ||
        !Number.isFinite(point[0]) || !Number.isFinite(point[1]) ||
        Math.abs(point[0]) > 180 || Math.abs(point[1]) > 85)) {
        throw new Error('The boundary contains invalid map coordinates.');
      }
      if (ring[0][0] !== ring.at(-1)[0] || ring[0][1] !== ring.at(-1)[1]) {
        throw new Error('Close the polygon before scanning.');
      }
      let ringArea = 0;
      let planarArea = 0;
      for (let i = 0; i < ring.length - 1; i++) {
        const a = ring[i], b = ring[i + 1];
        planarArea += cross(ring[0], a, b);
        if (a[0] === b[0] && a[1] === b[1]) throw new Error('Remove duplicate adjacent points and draw again.');
        for (let j = i + 2; j < ring.length - 1; j++) {
          if (i === 0 && j === ring.length - 2) continue;
          if (intersects(a, b, ring[j], ring[j + 1])) {
            throw new Error('The polygon crosses itself. Draw a simple outline and try again.');
          }
        }
        ringArea += radians(b[0] - a[0]) * (2 + Math.sin(radians(a[1])) + Math.sin(radians(b[1])));
      }
      const squareMeters = Math.abs(ringArea * radius * radius / 2);
      if (Math.abs(planarArea) < 1e-14 || squareMeters < 1) {
        throw new Error('Select a plot larger than one square metre.');
      }
      polygonArea += ringIndex === 0 ? squareMeters : -squareMeters;
      vertices += ring.length - 1;
      if (ringIndex === 0) points.push(...ring.slice(0, -1));
    }
    if (polygonArea < 1) throw new Error('The boundary has no usable area.');
    area += polygonArea;
  }
  const longitudes = points.map(point => point[0]);
  const latitudes = points.map(point => point[1]);
  return {
    areaHa: area / 10000, vertices,
    longitude: (Math.min(...longitudes) + Math.max(...longitudes)) / 2,
    latitude: (Math.min(...latitudes) + Math.max(...latitudes)) / 2,
  };
}

export function buildDemoExplanation(summary) {
  return [
    `Your selected boundary covers approximately ${summary.areaHa.toFixed(2)} hectares, centred at ${Math.abs(summary.latitude).toFixed(4)} ${summary.latitude < 0 ? 'S' : 'N'}, ${Math.abs(summary.longitude).toFixed(4)} ${summary.longitude < 0 ? 'W' : 'E'}. The rotation below follows a full July-to-June growing cycle, balancing the main monsoon crop with a short pulse and a summer recovery window.`,
    'The planning profile assumes a level, bunded clay-loam field in irrigated Mandya, Karnataka, with reliable monsoon-season irrigation and enough supplemental water for a short pulse. Soil type, drainage and water supply are planning assumptions to confirm on the ground.',
    'First, paddy in Kharif. A June nursery and July transplanting align the main growing period with the southwest monsoon. Harvest is planned for November-December, depending on variety and planting date. Rice needs substantial water, so this choice only makes sense if the assumed canal or irrigation supply is actually available.',
    'Next, green gram in early February, harvested around April. January leaves a buffer for a delayed rice harvest, drainage and land preparation. A roughly 65-75 day pulse fits the warmer window and changes crop family after a cereal. It must not sit in waterlogged soil; supplemental irrigation and a locally suitable variety are essential. Nitrogen fixation can help the system when nodulation and residue management are good, but it does not mean free fertilizer for the next crop.',
    'Finally, a managed May-June break rather than a thirsty third cash crop. Retain suitable residues, control weeds and prepare bunds and the next nursery. This avoids assuming unlimited summer water. If irrigation fails, do not follow the rice sequence: ask the local KVK about a rainfed alternative such as finger millet and a suitable pulse.',
    'Before planting, confirm soil test results, drainage, canal-release dates, variety duration and local sowing advice with KVK Mandya. Adjust the calendar to the actual monsoon onset and irrigation schedule rather than treating the month labels as fixed sowing dates.',
  ];
}
