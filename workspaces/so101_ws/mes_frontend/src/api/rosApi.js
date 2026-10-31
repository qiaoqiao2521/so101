function createFetchJson(apiBase, fetchImpl) {
  return async function fetchJson(path, init = {}) {
    const response = await fetchImpl(`${apiBase.value}${path}`, init);
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }
    return response.json();
  };
}

export function createRosApi(apiBase, { fetchImpl = globalThis.fetch } = {}) {
  const fetchJson = createFetchJson(apiBase, fetchImpl);

  return {
    fetchHealth: () => fetchJson('/api/ros/health'),
    connectRosbridge: () => fetchJson('/api/ros/connect', { method: 'POST' }),
    postStatus: (payload) =>
      fetchJson('/api/ros/status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }),
    postDetection: (payload) =>
      fetchJson('/api/ros/detections', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }),
  };
}
