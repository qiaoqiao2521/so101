import { ref } from 'vue';
import { defaultRealHardwareStatus } from '../lib/realHardwareStatus.js';

export function defaultSystemStatus() {
  return {
    runtimeTarget: 'simulation',
    simRunning: false,
    gazeboRunning: false,
    rvizRunning: false,
    rosbridgeConnected: false,
    browserRunning: false,
    simPid: null,
    rvizPid: null,
    browserPid: null,
    simLog: '',
    rvizLog: '',
    browserLog: '',
    browserDebugUrl: 'http://127.0.0.1:9223',
    realHardware: defaultRealHardwareStatus(),
  };
}

export function defaultBusyState() {
  return {
    startSim: false,
    openRviz: false,
    stopSim: false,
    openBrowser: false,
    stopBrowser: false,
    setRuntimeTarget: false,
    connectRosbridge: false,
    createOrder: false,
    dispatchOrder: false,
    previewPose: false,
    saveWorkbench: false,
    mergeWaypoints: false,
  };
}

function summarizeSystemStatus(status = {}) {
  const parts = [];
  if (status.simRunning && status.gazeboRunning) {
    parts.push('Gazebo 仿真已就绪');
  } else if (status.simRunning) {
    parts.push('仿真进程已启动');
  }
  if (status.rvizRunning) {
    parts.push('RViz 已打开');
  }
  if (status.rosbridgeConnected) {
    parts.push('rosbridge 已连接');
  }
  if (status.browserRunning) {
    parts.push('调试浏览器在线');
  }
  if (status.runtimeTarget === 'real_hardware') {
    parts.push('当前显式目标: 真机链路');
  } else if (status.runtimeTarget === 'real_leader_to_gazebo') {
    parts.push('当前显式目标: leader -> Gazebo');
  } else {
    parts.push('当前显式目标: 仿真链路');
  }
  return parts.join(' / ') || '状态已更新';
}

export function useSystemRuntimeModel({
  api,
  pushEvent,
  busy = ref(defaultBusyState()),
  afterSystemAction = async () => {},
}) {
  const systemStatus = ref(defaultSystemStatus());
  const rosbridgeConnected = ref(false);

  function markBusy(key, value) {
    busy.value = { ...busy.value, [key]: value };
  }

  function syncSystemStatus(payload = {}) {
    const nextStatus = {
      ...defaultSystemStatus(),
      ...payload,
      realHardware: {
        ...defaultRealHardwareStatus(),
        ...(payload.realHardware || {}),
      },
    };
    rosbridgeConnected.value = Boolean(nextStatus.rosbridgeConnected);
    systemStatus.value = nextStatus;
  }

  async function refreshSystemStatus() {
    try {
      const payload = await api.fetchSystemStatus();
      syncSystemStatus(payload);
      return payload;
    } catch (error) {
      pushEvent('warn', '系统状态读取失败', String(error.message || error));
      return null;
    }
  }

  async function refreshRosbridgeHealth() {
    try {
      const payload = await api.fetchRosbridgeHealth();
      rosbridgeConnected.value = Boolean(payload.connected);
      systemStatus.value = {
        ...systemStatus.value,
        rosbridgeConnected: Boolean(payload.connected),
      };
      return payload;
    } catch {
      rosbridgeConnected.value = false;
      systemStatus.value = {
        ...systemStatus.value,
        rosbridgeConnected: false,
      };
      return null;
    }
  }

  async function runSystemAction(actionKey, action, successTitle) {
    markBusy(actionKey, true);
    try {
      const payload = await action();
      const nextStatus = payload.status || null;
      if (nextStatus) {
        syncSystemStatus(nextStatus);
      }
      pushEvent('info', successTitle, summarizeSystemStatus(payload.status || payload));
      await afterSystemAction();
      await refreshRosbridgeHealth();
      if (!nextStatus) {
        await refreshSystemStatus();
      }
      return payload;
    } catch (error) {
      pushEvent('error', `${successTitle}失败`, String(error.message || error));
      return null;
    } finally {
      markBusy(actionKey, false);
    }
  }

  function startSimulation() {
    return runSystemAction('startSim', () => api.startSimulation(), '仿真启动请求已发送');
  }

  function openRviz() {
    return runSystemAction('openRviz', () => api.openRviz(), 'RViz 打开请求已发送');
  }

  function stopSimulation() {
    return runSystemAction('stopSim', () => api.stopSimulation(), '仿真停止请求已发送');
  }

  function openBrowser() {
    return runSystemAction('openBrowser', () => api.openBrowser(), '调试浏览器启动请求已发送');
  }

  function stopBrowser() {
    return runSystemAction('stopBrowser', () => api.stopBrowser(), '调试浏览器停止请求已发送');
  }

  function setRuntimeTarget(runtimeTarget) {
    const targetLabel =
      runtimeTarget === 'real_hardware'
        ? '已切到真机链路目标'
        : runtimeTarget === 'real_leader_to_gazebo'
          ? '已切到 leader -> Gazebo 目标'
          : '已切到仿真链路目标';
    return runSystemAction(
      'setRuntimeTarget',
      () => api.setRuntimeTarget(runtimeTarget),
      targetLabel,
    );
  }

  async function connectRosbridge() {
    markBusy('connectRosbridge', true);
    try {
      const payload = await api.connectRosbridge();
      pushEvent(
        'info',
        'rosbridge 连接请求已发送',
        payload.ok ? 'backend 已连上 rosbridge。' : '已发送连接请求，正在等待状态刷新。',
      );
      await refreshRosbridgeHealth();
      await refreshSystemStatus();
      return payload;
    } catch (error) {
      pushEvent('error', '连接 rosbridge 失败', String(error.message || error));
      return null;
    } finally {
      markBusy('connectRosbridge', false);
    }
  }

  return {
    busy,
    rosbridgeConnected,
    systemStatus,
    refreshSystemStatus,
    refreshRosbridgeHealth,
    startSimulation,
    openRviz,
    stopSimulation,
    openBrowser,
    stopBrowser,
    setRuntimeTarget,
    connectRosbridge,
  };
}
