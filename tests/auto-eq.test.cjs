// Run with: node --test tests/auto-eq.test.cjs
// Exercise the real single-file app with deterministic audio/recognition events.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(require('node:path').join(__dirname, '../index.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];

function app(settings = {}) {
  let time = 0;
  const elements = new Map();
  const ctx = new Proxy({
    measureText: text => ({ width: text.length * 45, actualBoundingBoxAscent: 72, actualBoundingBoxDescent: 22 }),
    createLinearGradient: () => ({ addColorStop() {} }),
    isPointInPath: () => true,
    getImageData: () => ({ data: new Uint8ClampedArray(1240 * 500 * 4) })
  }, { get: (o, k) => k in o ? o[k] : () => {} });
  function element() {
    return {
      dataset: {}, style: {}, lastElementChild: {}, listeners: {}, attributes: {},
      classList: { toggle() {} }, getContext: () => ctx,
      getBoundingClientRect: () => ({ width: 930, height: 300 }),
      setAttribute(k, v) { this.attributes[k] = v; },
      addEventListener(k, fn) { this.listeners[k] = fn; }, append() {}, focus() {}, select() {}
    };
  }
  const document = {
    getElementById(id) { if (!elements.has(id)) elements.set(id, element()); return elements.get(id); },
    createElement: element, addEventListener() {}
  };
  class Recognition { start() {} stop() {} }
  const sandbox = {
    document, performance: { now: () => time }, navigator: { userAgent: 'test' },
    localStorage: { getItem: () => JSON.stringify(settings), setItem() {} },
    matchMedia: () => ({ matches: false }), SpeechRecognition: Recognition,
    Path2D: class { constructor() { return new Proxy({}, { get: () => () => {} }); } },
    setTimeout: () => 1, clearTimeout() {}, requestAnimationFrame() {}, addEventListener() {}
  };
  sandbox.window = sandbox;
  const context = vm.createContext(sandbox);
  const exposure = `
    window.testApp = { A, EQ, S, sampleEq, updateEq, pushFrame, updateBaselines, onTranscript,
      startAudio, stopAudio, startListening, stopListening, startDemo, stopDemo, tickDemo, frame,
      buildRec, getRec: () => rec, setListening: v => { listening = v; },
      demoPhase: () => demo && demo.phase };
  `;
  vm.runInContext(script.replace(/\}\)\(\);\s*$/, exposure + '\n})();'), context);
  const api = sandbox.testApp;
  api.stopDemo();
  function live() {
    api.setListening(true); api.A.ok = true; api.A.noise = -50;
    api.A.ctx = { sampleRate: 48000 };
    api.A.analyser = { fftSize: 2048, disconnect() {} };
    api.A.fd = new Float32Array(1024).fill(-100);
    api.A.fd[5] = -30; api.A.fd[40] = -50;
  }
  function tick(ms, db = -31) {
    const end = time + ms;
    while (time < end) {
      time = Math.min(end, time + 50);
      api.sampleEq(time, db); api.pushFrame(time, db, 0.01);
      api.updateEq(time, 0.05); api.updateBaselines(time);
    }
  }
  return { api, sandbox, elements, live, tick, time: () => time, setTime: t => { time = t; } };
}

test('old saved settings gain Auto; scripted demo starts with EQ then captions', () => {
  const a = app({ range: 14, flow: 'single' });
  assert.equal(a.api.S.mode, 'auto');
  a.api.startDemo(); a.api.updateEq(0, 0.05);
  assert.equal(a.api.EQ.active, true);
  a.setTime(4600); a.api.tickDemo(4600); a.api.updateEq(4600, 0.05);
  assert.equal(a.api.demoPhase(), 'words'); assert.equal(a.api.EQ.active, false);
});

test('sound enters EQ; recognized speech preempts it; EQ returns after hold', () => {
  const a = app(); a.live(); a.tick(2400);
  assert.equal(a.api.EQ.active, false);
  a.tick(200); assert.equal(a.api.EQ.active, true);
  a.api.onTranscript('hello', 1);
  assert.equal(a.api.EQ.active, false);
  assert.equal(a.sandbox.__cs.state().words[0][0], 'hello');
  a.tick(2900); assert.equal(a.api.EQ.active, false);
  a.tick(200); assert.equal(a.api.EQ.active, true);
  a.api.onTranscript('hello can you hear me', 5);
  assert.equal(a.api.EQ.active, false);
  assert.equal(a.sandbox.__cs.state().words.map(w => w[0]).join(' '), 'can you hear me');
});

test('silence and short noises do not enter EQ; quiet fades and exits', () => {
  const a = app(); a.live(); a.tick(10000, -85);
  assert.equal(a.api.EQ.active, false);
  a.tick(500); a.tick(2000, -85);
  assert.equal(a.api.EQ.active, false);
  a.tick(3000); assert.equal(a.api.EQ.active, true);
  a.tick(1500, -85); assert.equal(a.api.EQ.active, false);
  assert.ok(a.api.EQ.levels.every(x => x < 0.01));
});

test('sustained music-only audio does not recalibrate normal voice', () => {
  const a = app(); a.live(); const base = a.api.A.base;
  a.tick(30000);
  assert.equal(a.api.EQ.active, true);
  assert.equal(a.api.A.voicedDb.length, 0);
  assert.equal(a.api.A.base, base);
  a.tick(1000, -18); // speech louder than the steady background
  a.api.onTranscript('hello', 1);
  assert.ok(a.api.A.voicedDb.length > 0);
});

test('spectrum responds to frequency content and silence has finite zero targets', () => {
  const a = app(); a.live(); a.api.A.fd.fill(-100); a.api.A.fd[5] = -20; a.tick(3000);
  const low = Array.from(a.api.EQ.targets);
  assert.ok(Math.max(...low.slice(0, 5)) > Math.max(...low.slice(10)));
  a.api.A.fd.fill(-Infinity); a.tick(1500, -100);
  assert.ok(a.api.EQ.targets.every(x => Number.isFinite(x) && x === 0));
});

test('manual Captions / EQ modes override Auto and analysis-off exits EQ', () => {
  const a = app(); a.live(); a.api.S.mode = 'captions'; a.tick(4000);
  assert.equal(a.api.EQ.active, false);
  a.api.S.mode = 'eq'; a.tick(100); assert.equal(a.api.EQ.active, true);
  a.api.onTranscript('hello', 1); assert.equal(a.api.EQ.active, true);
  a.api.S.analysis = false; a.api.updateEq(a.time(), 0.05);
  assert.equal(a.api.EQ.active, false);
});

test('hidden interim results still interrupt EQ before final text arrives', () => {
  const a = app({ interim: false }); a.live(); a.tick(3000);
  a.api.buildRec();
  const result = [{ transcript: 'hello' }]; result.isFinal = false;
  a.api.getRec().onresult({ resultIndex: 0, results: [result] });
  assert.equal(a.api.EQ.active, false);
  assert.equal(a.sandbox.__cs.state().words.length, 0);
});

test('recognition no-speech/restarts leave EQ active; missing audio clears it', () => {
  const a = app(); a.live(); a.tick(3000); a.api.buildRec();
  a.api.getRec().onerror({ error: 'no-speech' }); a.api.getRec().onend();
  assert.equal(a.api.EQ.active, true);
  a.api.A.ok = false; a.api.updateEq(a.time(), 0.05);
  assert.equal(a.api.EQ.active, false);
});

test('stopping clears EQ; a new session must accumulate sound again', () => {
  const a = app(); a.live(); a.tick(3000); a.api.stopListening();
  assert.equal(a.api.EQ.active, false); assert.equal(a.api.EQ.soundMs, 0);
  a.live(); a.tick(1000); assert.equal(a.api.EQ.active, false);
});

test('late microphone permission after Stop releases the stream', async () => {
  const a = app(); a.api.setListening(true);
  let grant, stopped = false;
  a.sandbox.AudioContext = class { async resume() {} };
  a.sandbox.navigator.mediaDevices = { getUserMedia: () => new Promise(resolve => { grant = resolve; }) };
  const pending = a.api.startAudio(); await new Promise(resolve => setImmediate(resolve));
  a.api.stopAudio(); a.api.setListening(false);
  grant({ getTracks: () => [{ stop() { stopped = true; } }] });
  await pending;
  assert.equal(stopped, true); assert.equal(a.api.A.ok, false);
});

test('log identifies Auto EQ version and includes setting and mode changes', () => {
  const a = app(); a.live(); a.tick(3000);
  a.elements.get('inRange').value = 8;
  a.elements.get('inRange').listeners.input(); a.elements.get('inRange').listeners.change();
  a.elements.get('btnLog').listeners.click();
  assert.match(a.elements.get('logBox').value, /Caption Shades log v3/);
  assert.match(a.elements.get('logBox').value, /mode\s+eq/);
  assert.match(a.elements.get('logBox').value, /range=8/);
});
