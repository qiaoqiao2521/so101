const SOCKET_CONNECTED_STATES = new Set(['connected']);
const SOCKET_LOADING_STATES = new Set(['connecting', 'handshake']);
const REAL_HARDWARE_TARGET = 'real_hardware';
const REAL_LEADER_TO_GAZEBO_TARGET = 'real_leader_to_gazebo';
const SIMULATION_TARGET = 'simulation';

function normalizeSystemStatus(systemStatus = {}) {
  const realHardware = systemStatus.realHardware || {};
  const rawRuntimeTarget = String(systemStatus.runtimeTarget || SIMULATION_TARGET).trim();
  const runtimeTarget =
    rawRuntimeTarget === REAL_HARDWARE_TARGET || rawRuntimeTarget === REAL_LEADER_TO_GAZEBO_TARGET
      ? rawRuntimeTarget
      : SIMULATION_TARGET;
  return {
    runtimeTarget,
    simRunning: Boolean(systemStatus.simRunning),
    gazeboRunning: Boolean(systemStatus.gazeboRunning),
    rvizRunning: Boolean(systemStatus.rvizRunning),
    rosbridgeConnected: Boolean(systemStatus.rosbridgeConnected),
    browserRunning: Boolean(systemStatus.browserRunning),
    realHardware: {
      online: Boolean(realHardware.online),
      allowExecute: Boolean(realHardware.allowExecute),
      safetyState: String(realHardware.safetyState || '').trim(),
    },
  };
}

export function buildDemoFlow({ systemStatus, rosbridgeConnected, socketState, selectedOrder }) {
  const normalized = normalizeSystemStatus(systemStatus);
  const targetIsHardware = normalized.runtimeTarget === REAL_HARDWARE_TARGET;
  const targetIsLeaderToGazebo = normalized.runtimeTarget === REAL_LEADER_TO_GAZEBO_TARGET;
  const simReady = normalized.simRunning && normalized.gazeboRunning;
  const hardwareReady =
    targetIsHardware &&
    (normalized.realHardware.allowExecute || normalized.realHardware.safetyState === 'READY');
  const runtimeReady = targetIsHardware ? hardwareReady : simReady;
  const runtimeSource = targetIsHardware
    ? hardwareReady
      ? 'hardware'
      : 'none'
    : simReady
      ? targetIsLeaderToGazebo
        ? 'leader_to_gazebo'
        : 'simulation'
      : 'none';
  const rosConnected = Boolean(rosbridgeConnected || normalized.rosbridgeConnected);
  const realtimeConnected = SOCKET_CONNECTED_STATES.has(socketState);
  const realtimeLoading = SOCKET_LOADING_STATES.has(socketState);
  const hasOrder = Boolean(selectedOrder);
  const orderRunning = hasOrder && selectedOrder.state === 'RUNNING';
  const orderDone = hasOrder && selectedOrder.state === 'DONE';
  const orderError = hasOrder && selectedOrder.state === 'ERROR';

  const steps = [
    {
      key: 'start-runtime',
      title: targetIsHardware ? '切到真机链路' : targetIsLeaderToGazebo ? '启动 leader -> Gazebo' : '启动 Gazebo 仿真',
      caption: targetIsHardware
        ? '当前首页主路径已锁定真机链路，不再允许用仿真 READY 顶替真机状态。'
        : targetIsLeaderToGazebo
          ? '当前目标是实物 leader 输入驱动 Gazebo simulated arm；没有 leader 输入时只能完成仿真侧准备。'
        : '加载 Gazebo 场景和基础服务，页面会自动轮询下一步。',
      hint: targetIsHardware
        ? hardwareReady
          ? '真机已满足执行门禁，可以继续连接 rosbridge。'
          : '请先让真机进入 READY / allowExecute，再继续实时链路连接。'
        : targetIsLeaderToGazebo
          ? simReady
            ? 'Gazebo 已就绪；下一步连接 rosbridge，并观察 /leader/gazebo_bridge/status。'
            : '先启动 Gazebo 主链；真实 leader 输入恢复后再跑 live smoke。'
        : simReady
          ? '仿真已就绪，可以继续连接 rosbridge。'
          : '启动后通常需要 3 到 8 秒。',
      actionLabel: targetIsHardware
        ? hardwareReady
          ? '真机已就绪'
          : '等待真机就绪'
        : targetIsLeaderToGazebo
          ? normalized.simRunning
            ? 'Gazebo 已启动'
            : '启动 leader -> Gazebo'
        : normalized.simRunning
          ? '仿真已启动'
          : '启动 Gazebo 仿真',
      status: runtimeReady ? 'completed' : 'active',
      enabled: targetIsHardware ? false : !runtimeReady,
    },
    {
      key: 'connect-rosbridge',
      title: '连接 rosbridge',
      caption: targetIsHardware
        ? '把 backend 接到真机链路里的 rosbridge 服务。'
        : targetIsLeaderToGazebo
          ? '把 backend 接到 leader -> Gazebo 链路里的 rosbridge 服务。'
          : '把 backend 接到仿真里已经启动的 rosbridge 服务。',
      hint: !runtimeReady
        ? targetIsHardware
          ? '请先让真机链路进入 READY，再连接 rosbridge。'
          : '请先启动仿真，再连接 rosbridge。'
        : rosConnected
          ? 'rosbridge 已连接。'
          : '点击后 backend 会尝试连接现有 rosbridge 服务。',
      actionLabel: rosConnected ? 'rosbridge 已连接' : '连接 rosbridge',
      status: !runtimeReady ? 'blocked' : rosConnected ? 'completed' : 'active',
      enabled: runtimeReady && !rosConnected,
    },
    {
      key: 'connect-realtime',
      title: '连接实时状态',
      caption: '让页面开始接收工单状态回传和检测流。',
      hint: !rosConnected
        ? '请先完成 rosbridge 连接。'
        : realtimeConnected
          ? '实时状态已连接。'
          : realtimeLoading
            ? '正在建立 WebSocket / STOMP 连接。'
            : '连接后页面会自动刷新工单与状态流。',
      actionLabel: realtimeConnected ? '实时状态已连接' : realtimeLoading ? '连接中...' : '连接实时状态',
      status: !rosConnected ? 'blocked' : realtimeConnected ? 'completed' : realtimeLoading ? 'loading' : 'active',
      enabled: rosConnected && !realtimeConnected && !realtimeLoading,
    },
    {
      key: 'dispatch-order',
      title: '创建并下发工单',
      caption: '选择动作模板，创建工单并直接交给任务执行器。',
      hint: !realtimeConnected
        ? '建议先连接实时状态，再下发工单。'
        : orderError
          ? '上一单异常，可重新创建或再次下发。'
          : orderDone
            ? '上一单已完成，可再次创建新工单。'
            : orderRunning
              ? '工单执行中，请观察时间线与状态回传。'
              : '推荐使用 pick_place_default 进行演示。',
      actionLabel: orderRunning ? '执行中' : '创建并下发工单',
      status: !realtimeConnected ? 'blocked' : orderRunning ? 'running' : orderDone ? 'completed' : orderError ? 'error' : 'active',
      enabled: realtimeConnected && !orderRunning,
    },
  ];

  const activeStep =
    steps.find((step) => step.status === 'active' || step.status === 'loading' || step.status === 'running') ||
    steps[steps.length - 1];

  return {
    simReady,
    hardwareReady,
    runtimeReady,
    runtimeSource,
    rosConnected,
    realtimeConnected,
    realtimeLoading,
    hasOrder,
    orderRunning,
    orderDone,
    orderError,
    activeStepKey: activeStep.key,
    steps,
  };
}

export function getPrimaryPrompt(flow) {
  switch (flow.activeStepKey) {
    case 'start-runtime':
      return flow.runtimeSource === 'hardware' || flow.hardwareReady
        ? '真机链路已就绪，可以继续连接 rosbridge。'
        : flow.steps[0]?.title === '切到真机链路'
          ? '当前显式目标是真机链路，请先把真机放到 READY。'
          : '先启动 Gazebo 仿真。';
    case 'connect-rosbridge':
      return '第二步已解锁，点连接 rosbridge。';
    case 'connect-realtime':
      return '第三步已解锁，点连接实时状态。';
    case 'dispatch-order':
      if (flow.orderRunning) {
        return '工单正在执行，请观察状态流与时间线。';
      }
      if (flow.orderDone) {
        return '本轮演示已完成。';
      }
      if (flow.orderError) {
        return '上一单异常，请重新创建并下发工单。';
      }
      return '系统已就绪，点创建并下发工单。';
    default:
      return '请按照步骤引导完成演示环境初始化。';
  }
}

export function getPrimaryPromptDetail(flow) {
  switch (flow.activeStepKey) {
    case 'start-runtime':
      return flow.steps[0]?.title === '切到真机链路'
        ? '这里不会再被仿真状态自动接管。只有真机门禁 READY，首页主链才会继续。'
        : '仿真路径通常需要等待 3 到 8 秒；当前显式目标锁定为仿真链。';
    case 'connect-rosbridge':
      return '这一步点一次即可。连接成功后，第三步会自动解锁。';
    case 'connect-realtime':
      return '连接成功后，页面会自动订阅状态流和检测流，并刷新工单信息。';
    case 'dispatch-order':
      if (flow.orderRunning) {
        return '等待右侧工单状态变成 DONE / OK，即可说明整条演示链跑通。';
      }
      if (flow.orderDone) {
        return '当前工单已经到达 DONE / OK。需要复演时，直接创建一张新工单即可。';
      }
      if (flow.orderError) {
        return '建议先查看右侧时间线，再重新创建新工单复演。';
      }
      return '默认模板 pick_place_default 适合演示，保持默认即可直接下发。';
    default:
      return '按照当前高亮步骤继续，无需切到高级模式。';
  }
}

export function getOverallStateLabel(flow) {
  if (!flow.runtimeReady) {
    return '未就绪';
  }
  if (!flow.rosConnected || !flow.realtimeConnected) {
    return '启动中';
  }
  if (flow.orderRunning) {
    return '执行中';
  }
  if (flow.orderError) {
    return '异常';
  }
  if (flow.orderDone) {
    return '已完成';
  }
  return '可演示';
}

export function getOverallStateTone(flow) {
  switch (getOverallStateLabel(flow)) {
    case '可演示':
      return 'tone-ready';
    case '执行中':
      return 'tone-running';
    case '已完成':
      return 'tone-done';
    case '异常':
      return 'tone-error';
    case '启动中':
      return 'tone-booting';
    default:
      return 'tone-offline';
  }
}
