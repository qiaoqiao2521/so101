function createFetchJson(apiBase, fetchImpl) {
  return async function fetchJson(path, init = {}) {
    const response = await fetchImpl(`${apiBase.value}${path}`, init);
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }
    return response.json();
  };
}

export function createSystemApi(apiBase, { fetchImpl = globalThis.fetch } = {}) {
  const fetchJson = createFetchJson(apiBase, fetchImpl);

  return {
    fetchSystemStatus: () => fetchJson('/api/system/status'),
    startSimulation: () => fetchJson('/api/system/start-sim', { method: 'POST' }),
    setRuntimeTarget: (runtimeTarget) =>
      fetchJson('/api/system/runtime-target', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ runtimeTarget }),
      }),
    openRviz: () => fetchJson('/api/system/open-rviz', { method: 'POST' }),
    stopSimulation: () => fetchJson('/api/system/stop-sim', { method: 'POST' }),
    openBrowser: () => fetchJson('/api/system/open-browser', { method: 'POST' }),
    stopBrowser: () => fetchJson('/api/system/stop-browser', { method: 'POST' }),
  };
}
