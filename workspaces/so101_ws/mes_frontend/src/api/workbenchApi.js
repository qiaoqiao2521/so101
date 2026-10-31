function createFetchJson(apiBase, fetchImpl) {
  return async function fetchJson(path, init = {}) {
    const response = await fetchImpl(`${apiBase.value}${path}`, init);
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }
    return response.json();
  };
}

export function createWorkbenchApi(apiBase, { fetchImpl = globalThis.fetch } = {}) {
  const fetchJson = createFetchJson(apiBase, fetchImpl);

  return {
    fetchLatestVisionQuality: () => fetchJson('/api/workbench/vision/latest-quality'),
    previewPose: (payload) =>
      fetchJson('/api/workbench/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }),
    saveExport: (payload) =>
      fetchJson('/api/workbench/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }),
    mergeWaypoints: (payload) =>
      fetchJson('/api/workbench/merge-waypoints', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }),
  };
}
