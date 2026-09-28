import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

const startupSource = await readFile(new URL('../../../scripts/client-startup.js', import.meta.url), 'utf8');
const retryKey = 'histosphere:startup-reload-at';

function eventTarget() {
  const listeners = new Map();
  return {
    listeners,
    addEventListener(name, callback) {
      if (!listeners.has(name)) listeners.set(name, new Set());
      listeners.get(name).add(callback);
    },
    removeEventListener(name, callback) {
      listeners.get(name)?.delete(callback);
    },
    dispatchEvent(event) {
      for (const callback of [...(listeners.get(event.type) || [])]) callback(event);
    },
  };
}

function createPage({ storage = new Map(), storageFailure, now = 100000, bodyReady = true } = {}) {
  const elements = [];
  let focusedElement;
  function createElement(tagName) {
    const element = {
      ...eventTarget(),
      tagName: tagName.toUpperCase(),
      style: {},
      children: [],
      setAttribute(name, value) { this[name] = value; },
      append(...children) { this.children.push(...children); },
      remove() { this.removed = true; },
      focus() { focusedElement = this; },
    };
    elements.push(element);
    return element;
  }
  const body = createElement('body');
  const document = { ...eventTarget(), body: bodyReady ? body : null, createElement };
  const timers = new Map();
  let timerId = 0;
  let reloads = 0;
  const window = {
    ...eventTarget(),
    location: {
      href: 'http://127.0.0.1:3000/',
      origin: 'http://127.0.0.1:3000',
      reload() { reloads += 1; },
    },
    sessionStorage: {
      getItem(key) {
        if (storageFailure === 'read') throw new Error('Storage unavailable');
        return storage.get(key) ?? null;
      },
      setItem(key, value) {
        if (storageFailure === 'write') throw new Error('Storage unavailable');
        storage.set(key, value);
      },
      removeItem(key) {
        if (storageFailure) throw new Error('Storage unavailable');
        storage.delete(key);
      },
    },
    setTimeout(callback) { timers.set(++timerId, callback); return timerId; },
    clearTimeout(id) { timers.delete(id); },
  };
  vm.runInNewContext(startupSource, { window, document, URL, Date: { now: () => now } });
  return {
    window, document, body, storage, timers,
    get reloads() { return reloads; },
    get panel() { return elements.find((element) => element.id === 'histosphere-startup-error' && !element.removed); },
    get focusedElement() { return focusedElement; },
    failImport(url = '/_nuxt/node_modules/nuxt/dist/app/entry.js?v=old') {
      window.dispatchEvent({ type: 'unhandledrejection', reason: new Error(`Failed to fetch dynamically imported module: ${url}`) });
    },
    runTimers() {
      for (const [id, callback] of [...timers]) {
        timers.delete(id);
        callback();
      }
    },
    mount() { window.dispatchEvent({ type: 'histosphere:app-mounted' }); },
  };
}

test('startup import failure reloads once and deduplicates same-page failures', () => {
  const page = createPage();
  page.failImport();
  page.failImport();
  page.window.dispatchEvent({ type: 'error', target: { tagName: 'SCRIPT', src: '/_nuxt/entry.async.js' } });
  assert.equal(page.timers.size, 1);
  page.runTimers();
  assert.equal(page.reloads, 1);
  assert.equal(page.panel, undefined);
  assert.equal(page.storage.get(retryKey), '100000');
});

test('repeated startup failure after reload shows an accessible manual retry', () => {
  const storage = new Map();
  const firstPage = createPage({ storage });
  firstPage.failImport();
  firstPage.runTimers();
  const nextPage = createPage({ storage, now: 100500 });
  nextPage.failImport();
  nextPage.runTimers();
  assert.equal(nextPage.reloads, 0);
  assert.equal(nextPage.panel.role, 'alert');
  const button = nextPage.panel.children.at(-1);
  assert.equal(button.textContent, '重新載入');
  assert.equal(nextPage.focusedElement, button);
  button.dispatchEvent({ type: 'click' });
  assert.equal(nextPage.reloads, 1);
});

test('a slow repeated failure cannot restart an automatic reload loop', () => {
  const page = createPage({ storage: new Map([[retryKey, '100000']]), now: 160001 });
  page.failImport();
  page.runTimers();
  assert.equal(page.reloads, 0);
  assert.ok(page.panel);
});

test('unavailable browser storage shows manual retry without an automatic reload', () => {
  for (const storageFailure of ['read', 'write']) {
    const page = createPage({ storageFailure });
    page.failImport();
    page.runTimers();
    assert.equal(page.reloads, 0);
    assert.ok(page.panel);
    assert.doesNotThrow(() => page.mount());
  }
});

test('startup recovery ignores unrelated errors and external or lookalike module URLs', () => {
  const page = createPage();
  for (const url of ['https://example.com/_nuxt/entry.js', '/api/login', '/_nuxt-other/entry.js']) {
    page.failImport(url);
    page.window.dispatchEvent({ type: 'error', target: { tagName: 'SCRIPT', src: url } });
  }
  page.window.dispatchEvent({ type: 'error', target: { tagName: 'IMG', src: '/_nuxt/image.png' } });
  page.window.dispatchEvent({ type: 'unhandledrejection', reason: new Error('Failed to fetch') });
  page.window.dispatchEvent({ type: 'unhandledrejection', reason: null });
  assert.equal(page.timers.size, 0);
  assert.equal(page.panel, undefined);
  assert.equal(page.storage.size, 0);
});

test('same-origin script resource errors receive startup recovery', () => {
  const page = createPage();
  page.window.dispatchEvent({
    type: 'error',
    target: { tagName: 'SCRIPT', src: 'http://127.0.0.1:3000/_nuxt/entry.async.js' },
  });
  page.runTimers();
  assert.equal(page.reloads, 1);
});

test('successful mount cancels pending recovery, clears only its marker and removes listeners', () => {
  const storage = new Map([['existing-session', 'untouched']]);
  const page = createPage({ storage });
  page.failImport();
  page.mount();
  page.runTimers();
  page.failImport();
  assert.equal(page.reloads, 0);
  assert.equal(storage.has(retryKey), false);
  assert.equal(storage.get('existing-session'), 'untouched');
  for (const callbacks of page.window.listeners.values()) assert.equal(callbacks.size, 0);
});

test('successful mount removes the displayed recovery panel', () => {
  const page = createPage({ storage: new Map([[retryKey, '99999']]) });
  page.failImport();
  assert.ok(page.panel);
  page.mount();
  assert.equal(page.panel, undefined);
});

test('startup failure before body parsing waits for DOM and can be cancelled by mount', () => {
  const page = createPage({ storageFailure: 'read', bodyReady: false });
  page.failImport();
  assert.equal(page.panel, undefined);
  page.document.body = page.body;
  page.document.dispatchEvent({ type: 'DOMContentLoaded' });
  assert.ok(page.panel);

  const recoveredPage = createPage({ storageFailure: 'read', bodyReady: false });
  recoveredPage.failImport();
  recoveredPage.mount();
  recoveredPage.document.body = recoveredPage.body;
  recoveredPage.document.dispatchEvent({ type: 'DOMContentLoaded' });
  assert.equal(recoveredPage.panel, undefined);
});
