import { ref } from 'vue';

const DEFAULT_POLL_INTERVAL_MS = 3000;

const DEFAULT_WORKSPACE_TABS = [
  {
    key: 'console',
    label: '演示控制台',
    eyebrow: 'Primary Flow',
    summary: '保留工单演示主路径',
  },
  {
    key: 'developer',
    label: '开发工作台',
    eyebrow: 'Developer Workspace',
    summary: '承接调试浏览器、注入与姿态调试',
  },
];

function getInitialWorkspaceTab(timerApi) {
  const location = timerApi?.location;
  const search = location?.search || '';
  const hash = String(location?.hash || '').replace(/^#/, '');
  const queryTab = new URLSearchParams(search).get('tab');
  const requestedTab = queryTab || hash;
  return DEFAULT_WORKSPACE_TABS.some((tab) => tab.key === requestedTab) ? requestedTab : 'console';
}

export function useConsoleWorkspace({
  systemRuntime,
  orderWorkflow,
  realtimeFeed,
  pushEvent,
  timerApi = globalThis.window,
  pollIntervalMs = DEFAULT_POLL_INTERVAL_MS,
}) {
  const activeTab = ref(getInitialWorkspaceTab(timerApi));
  const drawerOpen = ref(false);
  const workspaceTabs = DEFAULT_WORKSPACE_TABS;
  let pollTimer = null;

  async function refreshWorkspace() {
    if (typeof document !== 'undefined' && document.hidden) {
      return;
    }

    if (activeTab.value !== 'console') {
      return;
    }

    await orderWorkflow.refreshOrders();
    await systemRuntime.refreshSystemStatus();
    await systemRuntime.refreshRosbridgeHealth();
  }

  async function onMountedInit() {
    await refreshWorkspace();
    pushEvent('info', '演示舱已就绪', '首页现已收束为演示主路径，开发动作已收口到二级入口。');
    pollTimer = timerApi?.setInterval?.(() => refreshWorkspace(), pollIntervalMs) ?? null;
  }

  function onUnmountedCleanup() {
    if (pollTimer !== null) {
      timerApi?.clearInterval?.(pollTimer);
      pollTimer = null;
    }
    realtimeFeed.closeWs();
  }

  function selectWorkspaceTab(tabKey) {
    activeTab.value = tabKey;
    if (tabKey !== 'console') {
      drawerOpen.value = false;
      return;
    }
    refreshWorkspace();
  }

  function toggleDrawer() {
    drawerOpen.value = !drawerOpen.value;
  }

  function openDeveloperWorkspace() {
    selectWorkspaceTab('developer');
  }

  function openConsoleWorkspace() {
    selectWorkspaceTab('console');
  }

  function connectLiveRuntime() {
    return realtimeFeed.connectWs();
  }

  return {
    activeTab,
    drawerOpen,
    workspaceTabs,
    connectLiveRuntime,
    onMountedInit,
    onUnmountedCleanup,
    openConsoleWorkspace,
    openDeveloperWorkspace,
    selectWorkspaceTab,
    toggleDrawer,
  };
}
