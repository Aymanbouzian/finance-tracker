const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

const origin = 'https://pocketledger.example';
const assets = ['/offline/', '/static/pwa/icon-192.png'];
const source = readFileSync(path.join(__dirname, '../static/pwa/service-worker.js'), 'utf8')
  .replace('__PUBLIC_ASSETS__', JSON.stringify(assets))
  .replace('__OFFLINE_URL__', JSON.stringify('/offline/'))
  .replace('__CACHE_VERSION__', 'test');

function worker() {
  const listeners = {};
  const puts = [];
  const fetched = [];
  const stored = new Map([['/offline/', new Response('Offline public page')]]);
  class Request {
    constructor(input, options = {}) {
      Object.assign(this, {method: 'GET', mode: 'cors', credentials: 'same-origin'}, typeof input === 'object' ? input : {url: new URL(input, origin).href}, options);
    }
  }
  const cache = {
    match: async (key) => stored.get(typeof key === 'string' ? key : key.url),
    put: async (key, response) => { puts.push(key); stored.set(key, response); },
    addAll: async (requests) => { requests.forEach((request) => puts.push(request.url)); },
  };
  let offline = false;
  const context = {
    URL, Request, Response,
    self: {location: {origin}, addEventListener: (name, handler) => { listeners[name] = handler; }, skipWaiting: async () => {}, clients: {claim: async () => {}}},
    caches: {open: async () => cache, keys: async () => [], delete: async () => {}},
    fetch: async (request) => {
      fetched.push(request);
      if (offline) throw new Error('Network unavailable');
      return new Response('Private financial page');
    },
  };
  vm.runInNewContext(source, context);
  return {
    puts, fetched, cache,
    setOffline: () => { offline = true; },
    async dispatch(url, options = {}) {
      let result;
      listeners.fetch({request: new Request(url, options), respondWith: (promise) => { result = promise; }});
      return {intercepted: result !== undefined, response: result === undefined ? undefined : await result};
    },
    async install() {
      let result;
      listeners.install({waitUntil: (promise) => { result = promise; }});
      await result;
    },
  };
}

test('precache includes only explicitly public resources', async () => {
  const app = worker();
  await app.install();
  assert.deepEqual(app.puts, assets.map((url) => origin + url));
});

test('authenticated dashboard and logout navigations are network-only and never cached', async () => {
  const app = worker();
  for (const pathname of ['/', '/accounts/logout/', '/transactions/?q=private']) {
    const result = await app.dispatch(pathname, {mode: 'navigate'});
    assert.equal(await result.response.text(), 'Private financial page');
  }
  assert.equal(app.puts.length, 0);
  assert.ok(app.fetched.every((request) => request.cache === 'no-store'));
});

test('offline navigation returns public reconnect page without storing requested data', async () => {
  const app = worker();
  app.setOffline();
  const result = await app.dispatch('/transactions/', {mode: 'navigate'});
  assert.equal(await result.response.text(), 'Offline public page');
  assert.equal(app.puts.length, 0);
});

test('POST, APIs, unlisted static resources, and other origins bypass the worker', async () => {
  const app = worker();
  const cases = [
    ['/transactions/new/', {method: 'POST', mode: 'navigate'}],
    ['/assistant/ask/', {}],
    ['/static/private-upload.csv', {}],
    ['/static/pwa/icon-192.png?user=someone', {}],
    ['https://another.example/static/pwa/icon-192.png', {}],
  ];
  for (const [url, options] of cases) {
    assert.equal((await app.dispatch(url, options)).intercepted, false);
  }
  assert.equal(app.fetched.length, 0);
  assert.equal(app.puts.length, 0);
});

test('public asset request omits authentication and only caches its allowlisted URL', async () => {
  const app = worker();
  const result = await app.dispatch('/static/pwa/icon-192.png');
  assert.equal(result.intercepted, true);
  assert.deepEqual(app.puts, ['/static/pwa/icon-192.png']);
  assert.equal(app.fetched[0].credentials, 'omit');
});
