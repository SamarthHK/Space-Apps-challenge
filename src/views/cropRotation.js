import { createFieldMap } from '../map/fieldMap.js';
import { DEMO_PARCEL, DEMO_SEASONS, summarizeDemoGeometry, buildDemoExplanation } from '../data/rotationDemo.js';

const months = ['Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
const illustrations = {
  rice: '<path d="M56 96Q64 60 60 24M60 52Q40 52 34 31M61 65Q83 61 88 39M59 79Q37 78 30 58"/><path d="M58 31l-9-9m12 18l11-12m-27 17l-9-3m43 12l9-2m-46 18l-10-2"/><path d="M49 103h28"/>',
  pulse: '<path d="M34 88Q46 40 90 30Q91 75 54 94Q36 105 34 88Z"/><path d="M41 88Q60 60 82 40"/><circle cx="53" cy="79" r="6"/><circle cx="65" cy="63" r="6"/><circle cx="77" cy="47" r="6"/>',
  rest: '<path d="M22 89h84M28 103h72M43 76Q62 61 80 76M62 69V48M61 57Q42 55 42 39Q61 37 62 54M64 50Q82 50 84 32Q65 30 64 50"/><path d="M30 26v10m-5-5h10M96 62v10m-5-5h10"/>',
};
const illustration = id => `<svg viewBox="0 0 128 128" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${illustrations[id]}</svg>`;

export function createCropRotation(container) {
  container.innerHTML = `
    <header class="rotation-heading">
      <div><p class="rotation-eyebrow">BHUMI / CROP INTELLIGENCE</p>
        <h1>A better season starts here.</h1>
        <p>One plot. A thoughtful rotation. A whole year in view.</p></div>
      <span class="rotation-demo-badge"><span></span> INTERACTIVE DEMO</span>
    </header>
    <div class="rotation-disclosure"><strong>A preview, not a prediction.</strong>
      Real polygon input, fixed example crops, simulated scan and AI explanation. No live agronomic analysis or backend required.</div>
    <div id="rotation-selection">
      <section class="rotation-selector">
        <div class="rotation-selection-copy">
          <p class="rotation-eyebrow">01 / START WITH YOUR LAND</p>
          <h2>Draw a boundary.<br>See the possibilities.</h2>
          <p>Mark a plot on the map, use your selected field, or load our example parcel near Mandya.</p>
          <div class="rotation-actions">
            <button type="button" class="btn-primary" id="rotation-draw">Draw a plot</button>
            <button type="button" class="btn-secondary" id="rotation-sample">Use example parcel</button>
            <button type="button" class="btn-secondary" id="rotation-use-field" disabled>Use selected field boundary</button>
          </div>
          <button type="button" class="btn-primary" id="rotation-finish" hidden>Finish boundary</button>
          <p id="rotation-selection-status" role="status">No boundary selected. The example is a fictional parcel, not a saved field.</p>
          <div class="rotation-input-summary" id="rotation-input-summary" hidden></div>
        </div>
        <div class="rotation-map-shell">
          <div class="rotation-map-caption"><span class="rotation-live-dot"></span> PLOT SELECTOR <span>Boundary input</span></div>
          <div id="rotation-map" aria-label="Crop rotation polygon selection map"></div>
          <p class="rotation-map-hint">Pan or zoom to your plot. While drawing, click to add corners; drag handles to adjust.</p>
        </div>
      </section>
      <p class="rotation-tile-status" id="rotation-tile-status" role="status"></p>
      <section class="rotation-scenario">
        <div><p class="rotation-eyebrow">THE DEMO SCENARIO</p><h3>Mandya's irrigated lowlands</h3>
          <p>Applied to every polygon, regardless of location. Not inferred from the map.</p></div>
        <div class="rotation-assumption"><span>SOIL / ASSUMED</span><strong>Clay loam</strong></div>
        <div class="rotation-assumption"><span>WATER / ASSUMED</span><strong>Reliable irrigation</strong></div>
        <button type="button" class="btn-primary" id="rotation-scan" disabled>Generate demo rotation <span aria-hidden="true">&rarr;</span></button>
      </section>
      <section class="rotation-scan-panel" id="rotation-scan-panel" hidden aria-labelledby="rotation-scan-title">
        <div><span class="rotation-scan-symbol" aria-hidden="true">+</span><div>
          <p class="rotation-eyebrow">SIMULATED SCAN</p><h3 id="rotation-scan-title">Reading your selected boundary</h3></div></div>
        <progress id="rotation-progress" max="4" value="0" aria-label="Demo scan progress"></progress>
        <p id="rotation-scan-status" role="status">Only the polygon is real input. All regional conditions are preset.</p>
      </section>
    </div>
    <div id="rotation-report" hidden>
      <section class="rotation-report-hero">
        <div><p class="rotation-eyebrow">YOUR ILLUSTRATIVE ROTATION / JULY TO JUNE</p>
          <h2>Grow with the monsoon.<br>Give the soil a change.</h2>
          <p>Paddy, then a short pulse, then room to recharge.<br>A water-aware example for irrigated Mandya.</p>
          <div class="rotation-hero-tags"><span>2 crop families</span><span>1 summer pause</span><span>Fixed demo scenario</span></div>
        </div>
        <div class="rotation-plot-stamp"><span>SELECTED BOUNDARY</span><strong id="rotation-report-area"></strong>
          <p id="rotation-report-location"></p><small>Approximate map area, not surveyed</small>
          <button type="button" id="rotation-edit">Change plot &rarr;</button></div>
      </section>
      <div class="rotation-section-title"><div><p class="rotation-eyebrow">02 / YOUR YEAR, AT A GLANCE</p>
        <h2>The right crop. The right window.</h2></div><span>Illustrative windows, not a dated forecast</span></div>
      <section class="rotation-calendar" aria-labelledby="rotation-calendar-title">
        <h3 id="rotation-calendar-title" class="rotation-sr-only">July to June crop calendar</h3>
        <div class="rotation-calendar-inner">
          <div class="rotation-calendar-row rotation-calendar-months"><span>GROWING WINDOW</span>${months.map(month => `<span>${month}</span>`).join('')}</div>
          ${DEMO_SEASONS.map(crop => `<div class="rotation-calendar-row"><strong>${crop.name}</strong>${months.map((month, index) =>
    `<span class="${crop.activeMonths.includes(index) ? `rotation-calendar-cell ${crop.id}` : ''}" aria-label="${month}: ${crop.activeMonths.includes(index) ? crop.name : 'not scheduled'}">${crop.activeMonths.includes(index) ? '<span aria-hidden="true"></span>' : ''}</span>`).join('')}</div>`).join('')}
        </div>
        <p>January: drainage, harvest-delay buffer and land preparation. June: next rice nursery preparation overlaps the summer pause.</p>
      </section>
      <section class="rotation-crop-grid" aria-label="Season by season crop plan">
        ${DEMO_SEASONS.map(crop => `<article class="rotation-crop-card ${crop.id}">
          <div class="rotation-crop-top"><span>${crop.number} / ${crop.season}</span><strong>${crop.months}</strong></div>
          <div class="rotation-crop-name"><div><span>${crop.family}</span><h3>${crop.name}</h3><p>${crop.localName}</p></div>${illustration(crop.id)}</div>
          <p class="rotation-crop-reason">${crop.reason}</p>
          <dl><dt>WHEN</dt><dd>${crop.window}</dd><dt>DURATION</dt><dd>${crop.duration}</dd><dt>WATER</dt><dd>${crop.water}</dd></dl>
          <p class="rotation-crop-note">${crop.note}</p>
        </article>`).join('')}
      </section>
      <section class="rotation-explanation" aria-labelledby="rotation-explanation-title">
        <header><div class="rotation-ai-mark" aria-hidden="true">B</div><div>
          <p class="rotation-eyebrow">BHUMI FIELD NOTES</p><h2 id="rotation-explanation-title">Why this rotation?</h2></div>
          <span id="rotation-stream-state">Scripted explanation</span></header>
        <p class="rotation-explanation-label">Simulated AI response / preset reasoning, not a live LLM</p>
        <div id="rotation-explanation-text" aria-busy="false"></div>
        <footer><span id="rotation-explanation-status" role="status"></span>
          <button type="button" class="btn-secondary" id="rotation-reveal">Show full explanation</button></footer>
      </section>
      <section class="rotation-reality-check"><h3>Before this becomes a real planting plan</h3>
        <p>Check soil tests, water availability, drainage, variety duration and local sowing windows with KVK Mandya.
        No yields, prices, confidence scores or soil measurements have been invented. This page is not saved as a backend planting plan.</p>
        <details><summary>Agronomy references & demo assumptions</summary>
          <p>The cereal-to-pulse sequence is illustrative. Southern Indian early-summer green gram calendars support the short pulse window;
          they do not establish suitability for a particular Mandya plot. Crop timing must be checked locally.</p>
          <a href="https://agritech.tnau.ac.in/agriculture/pulses_greengram.html" target="_blank" rel="noopener noreferrer">TNAU: green gram seasons, duration and cultivation</a>
          <a href="https://www.organicmandya.com/farming/tools/karnataka-crop-calendar/" target="_blank" rel="noopener noreferrer">Organic Mandya: indicative Karnataka crop calendar</a>
          <p>Assumed, not measured: irrigated lowland, clay-loam soil, adequate drainage after rice and supplemental water for pulses.
          No variety, fertilizer dose or pesticide prescription is generated.</p>
        </details>
      </section>
    </div>`;

  const get = id => container.querySelector(`#${id}`);
  const map = createFieldMap(get('rotation-map'), get('rotation-tile-status'));
  let geometry = null;
  let summary = null;
  let source = '';
  let storedField = null;
  let drawing = false;
  let scanning = false;
  let scanTimer;
  let streamTimer;
  let paragraphs = [];
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const setStatus = text => { get('rotation-selection-status').textContent = text; };

  function show() {
    map.center(76.8268, 12.5704);
    if (geometry) map.previewGeometry(geometry);
  }
  function resetResults() {
    clearTimeout(scanTimer);
    clearInterval(streamTimer);
    scanning = false;
    get('rotation-report').hidden = true;
    get('rotation-scan-panel').hidden = true;
    get('rotation-selection').hidden = false;
  }
  function setBoundary(value, label) {
    resetResults();
    map.clearPreview();
    geometry = null;
    summary = null;
    drawing = false;
    get('rotation-finish').hidden = true;
    get('rotation-input-summary').hidden = true;
    get('rotation-scan').disabled = true;
    try {
      summary = summarizeDemoGeometry(value);
      geometry = structuredClone(value);
      source = label;
      map.previewGeometry(geometry);
      get('rotation-input-summary').textContent =
        `${summary.areaHa.toFixed(2)} ha approx. / ${summary.vertices} boundary points / ${source}`;
      get('rotation-input-summary').hidden = false;
      get('rotation-scan').disabled = false;
      setStatus('Boundary ready. The crop sequence uses the fixed Mandya scenario below.');
    } catch (error) {
      setStatus(error.message);
    }
  }
  function fullExplanation() {
    clearInterval(streamTimer);
    get('rotation-explanation-text').replaceChildren(...paragraphs.map(text => {
      const paragraph = document.createElement('p');
      paragraph.textContent = text;
      return paragraph;
    }));
    get('rotation-explanation-text').setAttribute('aria-busy', 'false');
    get('rotation-stream-state').textContent = 'Explanation complete';
    get('rotation-explanation-status').textContent = 'Scripted demo complete. No live model was called.';
    get('rotation-reveal').hidden = true;
  }
  function streamExplanation() {
    clearInterval(streamTimer);
    paragraphs = buildDemoExplanation(summary);
    get('rotation-explanation-text').replaceChildren();
    get('rotation-explanation-text').setAttribute('aria-busy', 'true');
    get('rotation-stream-state').textContent = 'Writing demo explanation...';
    get('rotation-explanation-status').textContent = 'Streaming preset reasoning, not model output.';
    get('rotation-reveal').hidden = false;
    if (reducedMotion) { fullExplanation(); return; }
    let paragraphIndex = 0;
    let wordIndex = 0;
    let paragraph;
    streamTimer = setInterval(() => {
      if (!wordIndex) {
        paragraph = document.createElement('p');
        get('rotation-explanation-text').append(paragraph);
      }
      const words = paragraphs[paragraphIndex].split(' ');
      wordIndex = Math.min(wordIndex + 5, words.length);
      paragraph.textContent = words.slice(0, wordIndex).join(' ');
      if (wordIndex === words.length) {
        paragraphIndex++;
        wordIndex = 0;
        if (paragraphIndex === paragraphs.length) fullExplanation();
      }
    }, 40);
  }
  function renderReport() {
    scanning = false;
    get('rotation-selection').hidden = true;
    get('rotation-report').hidden = false;
    get('rotation-report-area').textContent = `${summary.areaHa.toFixed(2)} ha`;
    get('rotation-report-location').textContent = `${source} / ${summary.vertices} points`;
    streamExplanation();
    get('rotation-report').scrollIntoView({ block: 'start' });
    get('rotation-edit').focus({ preventScroll: true });
  }

  get('rotation-sample').addEventListener('click', () => setBoundary(DEMO_PARCEL, 'Example parcel'));
  get('rotation-use-field').addEventListener('click', () => {
    if (storedField?.geometry) setBoundary(storedField.geometry, storedField.name || 'Selected field');
  });
  get('rotation-draw').addEventListener('click', () => {
    resetResults();
    const previousGeometry = geometry;
    geometry = null;
    summary = null;
    get('rotation-input-summary').hidden = true;
    get('rotation-scan').disabled = true;
    get('rotation-finish').hidden = false;
    drawing = true;
    map.clearPreview();
    if (previousGeometry) map.previewGeometry(previousGeometry);
    map.startDrawing(value => {
      geometry = value;
      setStatus(value ? 'Outline ready. Adjust the handles or finish the boundary.' : 'Click at least three corners on the map.');
    });
    get('rotation-map').scrollIntoView({ block: 'center' });
  });
  get('rotation-finish').addEventListener('click', () => {
    if (!drawing || !map.finishDrawing()) { setStatus('Add at least three corners before finishing.'); return; }
    setBoundary(geometry, 'Your drawn plot');
  });
  get('rotation-scan').addEventListener('click', () => {
    if (!summary || drawing || scanning) return;
    scanning = true;
    get('rotation-scan').disabled = true;
    get('rotation-scan-panel').hidden = false;
    get('rotation-progress').value = 0;
    const steps = [
      ['Reading your selected boundary', `${summary.vertices} points / approximately ${summary.areaHa.toFixed(2)} hectares. No remote sensing request.`],
      ['Loading the Mandya example', 'Using assumed clay-loam soil and reliable irrigation. Not measured conditions.'],
      ['Arranging seasonal crop windows', 'Preset sequence: monsoon paddy, early-summer green gram, summer pause.'],
      ['Preparing your demo field notes', 'Scripted explanation ready. No live AI model or crop service called.'],
    ];
    let step = 0;
    const advance = () => {
      if (step === steps.length) { renderReport(); return; }
      get('rotation-scan-title').textContent = steps[step][0];
      get('rotation-scan-status').textContent = steps[step][1];
      get('rotation-progress').value = ++step;
      scanTimer = setTimeout(advance, reducedMotion ? 100 : 600);
    };
    advance();
  });
  get('rotation-edit').addEventListener('click', () => {
    resetResults();
    get('rotation-scan').disabled = !summary;
    show();
    get('rotation-draw').focus();
    get('rotation-selection').scrollIntoView({ block: 'start' });
  });
  get('rotation-reveal').addEventListener('click', fullExplanation);
  window.addEventListener('pagehide', () => {
    clearTimeout(scanTimer);
    clearInterval(streamTimer);
  });
  return {
    show,
    setField(field) {
      storedField = field;
      get('rotation-use-field').disabled = !field?.geometry;
    },
  };
}
