function createFetchJson(apiBase, fetchImpl) {
  return async function fetchJson(path, init = {}) {
    const response = await fetchImpl(`${apiBase.value}${path}`, init);
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }
    return response.json();
  };
}

export function createOrdersApi(apiBase, { fetchImpl = globalThis.fetch } = {}) {
  const fetchJson = createFetchJson(apiBase, fetchImpl);

  return {
    fetchOrders: () => fetchJson('/api/orders'),
    createOrder: ({ orderId, actionTemplateId }) =>
      fetchJson('/api/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ orderId, actionTemplateId }),
      }),
    dispatchOrder: (orderId, { priority = 1 } = {}) =>
      fetchJson(`/api/orders/${orderId}/dispatch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ priority }),
      }),
  };
}
