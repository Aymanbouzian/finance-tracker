const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

const source = readFileSync(path.join(__dirname, '../web/app-worker.js'), 'utf8');
const ORIGIN = 'https://ledger.example';
const CACHE = 'pocketledger-flutter-public-v1';
const OFFLINE = `${ORIGIN}/app/offline.html`;

test('Flutter starts without a second worker replacing the offline worker', () => {
  const bootstrap = readFileSync(path.join(__dirname, '../web/flutter_bootstrap.js'), 'utf8')
    .replace('{{flutter_js}}', '').replace('{{flutter_build_config}}', '');
  const calls = [];
  vm.runInNewContext(bootstrap, {_flutter: {loader: {load: options => calls.push(options)}}});
  assert.equal(calls.length, 1);
  assert.equal(calls[0]?.serviceWorkerSettings, undefined);
});

function worker({fetchResult, offlineResult, cacheFailure = false, keys = []} = {}) {
  const listeners = {};
  const calls = {open: [], add: [], match: [], put: [], deleted: [], fetched: [], claim: 0, skipWaiting: 0};
  const cache = {
    add: async (url) => calls.add.push(url),
    put: async (...args) => calls.put.push(args),
  };
  const self = {
    registration: {scope: `${ORIGIN}/app/`},
    location: {origin: ORIGIN},
    clients: {claim: async () => { calls.claim += 1; }},
    skipWaiting: async () => { calls.skipWaiting += 1; },
    addEventListener: (type, handler) => { listeners[type] = handler; },
  };
  const caches = {
    open: async (name) => { calls.open.push(name); return cache; },
    keys: async () => keys,
    delete: async (name) => { calls.deleted.push(name); return true; },
    match: async (url, options) => {
      calls.match.push({url, cacheName: options?.cacheName});
      if (cacheFailure) throw new Error('Storage unavailable');
      return offlineResult;
    },
  };
  const fetch = async (request) => {
    calls.fetched.push(request);
    if (fetchResult instanceof Error) throw fetchResult;
    return fetchResult ?? new Response('online application');
  };
  vm.runInNewContext(source, {self, caches, fetch, URL, Response});
  function dispatch(type, request) {
    let completion;
    let response;
    listeners[type]({
      request,
      waitUntil: (promise) => { completion = promise; },
      respondWith: (promise) => { response = promise; },
    });
    return {completion, response};
  }
  return {calls, dispatch};
}

const request = (url = `${ORIGIN}/app/`, mode = 'navigate', method = 'GET') => ({url, mode, method});

test('installation caches only the generic offline notice and activates promptly', async () => {
  const {calls, dispatch} = worker();
  await dispatch('install').completion;
  assert.deepEqual(calls.open, [CACHE]);
  assert.deepEqual(calls.add, [OFFLINE]);
  assert.equal(calls.skipWaiting, 1);
  assert.equal(calls.put.length, 0);
  assert.equal(calls.fetched.length, 0);
});

test('activation cleans only older caches belonging to this Flutter worker', async () => {
  const old = 'pocketledger-flutter-public-v0';
  const {calls, dispatch} = worker({keys: [CACHE, old, 'other-app-cache', 'pocketledger-static-v1']});
  await dispatch('activate').completion;
  assert.deepEqual(calls.deleted, [old]);
  assert.equal(calls.claim, 1);
});

test('online navigation is network first and does not cache the response', async () => {
  const online = new Response('private authenticated content');
  const {calls, dispatch} = worker({fetchResult: online});
  const navigation = request(`${ORIGIN}/app/planning`);
  assert.equal(await dispatch('fetch', navigation).response, online);
  assert.deepEqual(calls.fetched, [navigation]);
  assert.equal(calls.match.length, 0);
  assert.equal(calls.put.length, 0);
  assert.equal(calls.add.length, 0);
});

test('HTTP errors are returned as received without replacing them with offline content', async () => {
  const unavailable = new Response('server unavailable', {status: 503});
  const {calls, dispatch} = worker({fetchResult: unavailable});
  assert.equal(await dispatch('fetch', request()).response, unavailable);
  assert.equal(calls.match.length, 0);
});

test('network failure serves only the notice from the current public cache', async () => {
  const offline = new Response('A moment to reconnect.');
  const {calls, dispatch} = worker({fetchResult: new Error('offline'), offlineResult: offline});
  assert.equal(await dispatch('fetch', request()).response, offline);
  assert.deepEqual(calls.match, [{url: OFFLINE, cacheName: CACHE}]);
  assert.equal(calls.put.length, 0);
});

for (const cacheFailure of [false, true]) {
  test(`offline navigation has a useful non-cacheable 503 when cache is ${cacheFailure ? 'unavailable' : 'empty'}`, async () => {
    const {dispatch} = worker({fetchResult: new Error('offline'), cacheFailure});
    const result = await dispatch('fetch', request()).response;
    assert.equal(result.status, 503);
    assert.equal(result.headers.get('Cache-Control'), 'no-store');
    assert.match(await result.text(), /Changes are not queued offline/);
  });
}

test('API and private routes bypass the worker, including explicit navigations', () => {
  const {calls, dispatch} = worker();
  for (const route of ['/api/session/', '/api/overview/', '/api/export/', '/accounts/login/', '/classic/', '/application/']) {
    for (const mode of ['cors', 'navigate']) {
      assert.equal(dispatch('fetch', request(ORIGIN + route, mode)).response, undefined, `${route} ${mode}`);
    }
  }
  assert.equal(calls.fetched.length, 0);
  assert.equal(calls.match.length, 0);
  assert.equal(calls.put.length, 0);
});

test('mutations, cross-origin requests, and ordinary assets are untouched', () => {
  const {calls, dispatch} = worker();
  for (const entry of [
    request(`${ORIGIN}/app/`, 'navigate', 'POST'),
    request(`${ORIGIN}/app/`, 'navigate', 'DELETE'),
    request(`${ORIGIN}/app/`, 'navigate', 'HEAD'),
    request('https://external.example/app/'),
    request(`${ORIGIN}/app/main.dart.js`, 'no-cors'),
    request(`${ORIGIN}/app/canvaskit/canvaskit.wasm`, 'cors'),
  ]) assert.equal(dispatch('fetch', entry).response, undefined);
  assert.equal(calls.fetched.length, 0);
  assert.equal(calls.match.length, 0);
  assert.equal(calls.put.length, 0);
});
