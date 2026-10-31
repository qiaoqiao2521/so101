const DEFAULT_SAFETY_CHECKS = [
  { key: 'driver_online', label: '驱动在线', ok: false, detail: '等待真机状态源接入' },
  { key: 'status_fresh', label: '状态新鲜', ok: false, detail: '等待状态刷新' },
  { key: 'power_on', label: '已上电', ok: false, detail: '当前未上电' },
  { key: 'estop_clear', label: '急停正常', ok: true, detail: '当前未检测到急停' },
  { key: 'calibrated', label: '已完成校准', ok: false, detail: '尚未加载校准配置' },
  { key: 'homed', label: '已安全回中', ok: false, detail: '尚未完成安全回中' },
  { key: 'gate_enabled', label: '系统已放行', ok: false, detail: '默认保护态，需人工确认后放行' },
];

const QUIET_ERROR_MESSAGES = new Set(['', '无', '待接入真机状态源']);

export function defaultRealHardwareStatus() {
  return {
    online: false,
    controlInterface: '待接入',
    powerState: '未上电',
    estopActive: false,
    mode: '安全待机',
    lastError: '待接入真机状态源',
    allowExecute: false,
    updatedAt: '',
    safetyState: 'LOCKED',
    gateReasonCode: 'WAITING_FOR_HARDWARE',
    gateReasonLabel: '待接入真机',
    calibrationState: 'UNCALIBRATED',
    homed: false,
    safetyChecks: DEFAULT_SAFETY_CHECKS,
  };
}

function cloneDefaultSafetyChecks() {
  return DEFAULT_SAFETY_CHECKS.map((item) => ({ ...item }));
}

function normalizeSafetyChecks(items) {
  if (!Array.isArray(items) || items.length === 0) {
    return cloneDefaultSafetyChecks();
  }
  return items.map((item) => ({
    key: item?.key || '',
    label: item?.label || '未命名检查项',
    ok: Boolean(item?.ok),
    detail: item?.detail || '',
  }));
}

function normalizeRealHardwareStatus(status = {}) {
  return {
    ...defaultRealHardwareStatus(),
    ...status,
    online: Boolean(status.online),
    estopActive: Boolean(status.estopActive),
    allowExecute: Boolean(status.allowExecute),
    homed: Boolean(status.homed),
    safetyChecks: normalizeSafetyChecks(status.safetyChecks),
  };
}

function findSafetyCheck(status, key) {
  return status.safetyChecks.find((item) => item.key === key);
}

export function resolveRealHardwareStatus(systemStatus = {}) {
  const payload = systemStatus.realHardware || {};
  return normalizeRealHardwareStatus(payload);
}

export function describeRealHardwareStage(status = {}) {
  const resolved = normalizeRealHardwareStatus(status);

  if (!resolved.online) {
    return '未接入';
  }
  if (resolved.powerState !== '已上电') {
    return '已接入但未上电';
  }
  if (resolved.calibrationState !== 'READY') {
    return '已上电但未校准';
  }
  if (!resolved.allowExecute) {
    return '已校准但未放行';
  }
  return '允许最小动作验证';
}

export function isRealHardwareStatusUnclear(status = {}) {
  const resolved = normalizeRealHardwareStatus(status);
  if (!resolved.online) {
    return false;
  }
  const freshCheck = findSafetyCheck(resolved, 'status_fresh');
  if (freshCheck) {
    return !freshCheck.ok;
  }
  return !resolved.updatedAt;
}

export function describeRealHardwareSummary(status = {}) {
  const resolved = normalizeRealHardwareStatus(status);

  if (resolved.estopActive || resolved.safetyState === 'PROTECTIVE_STOP') {
    return '真机保护中';
  }
  if (isRealHardwareStatusUnclear(resolved)) {
    return '状态待确认，先不演示';
  }
  if (resolved.allowExecute) {
    return '可安排空载演示';
  }

  switch (describeRealHardwareStage(resolved)) {
    case '未接入':
      return '等待接入真机';
    case '已接入但未上电':
      return '等待设备上电';
    case '已上电但未校准':
      return '先完成校准';
    case '已校准但未放行':
      return '已完成准备，待人工放行';
    default:
      return '可安排空载演示';
  }
}

export function describeRealHardwareGate(status = {}) {
  const resolved = normalizeRealHardwareStatus(status);

  if (resolved.estopActive) {
    return '已触发急停，需人工复位后再继续演示。';
  }
  if (resolved.safetyState === 'PROTECTIVE_STOP') {
    return '系统处于保护停机，确认风险解除后再继续演示。';
  }
  if (isRealHardwareStatusUnclear(resolved)) {
    return '最近状态还未确认，系统继续保持保护，暂不进入动作演示。';
  }

  switch (describeRealHardwareStage(resolved)) {
    case '未接入':
      return '演示仍停留在接机准备阶段，接入真机状态后再进入下一步。';
    case '已接入但未上电':
      return '真机已接入，下一步先确认设备上电。';
    case '已上电但未校准':
      return '真机已上电，下一步先完成校准与安全回中。';
    case '已校准但未放行':
      return '当前只展示准备就绪状态，仍需人工确认后再进入动作演示。';
    default:
      return '已满足最小动作演示前置条件，建议先做空载确认。';
  }
}

export function describeRealHardwareRefresh(status = {}) {
  const resolved = normalizeRealHardwareStatus(status);
  if (resolved.updatedAt) {
    return resolved.updatedAt;
  }
  if (resolved.online) {
    return '暂未收到最新时间戳';
  }
  return '待接入后自动刷新';
}

export function describeRecentHardwareIssue(status = {}) {
  const resolved = normalizeRealHardwareStatus(status);
  const lastError = String(resolved.lastError || '').trim();

  if (resolved.estopActive) {
    return '急停已触发';
  }
  if (resolved.safetyState === 'PROTECTIVE_STOP' && QUIET_ERROR_MESSAGES.has(lastError)) {
    return '系统处于保护停机';
  }
  if (QUIET_ERROR_MESSAGES.has(lastError)) {
    return '无';
  }
  return lastError;
}

export function describeRecentHardwareIssueSummary(status = {}) {
  const resolved = normalizeRealHardwareStatus(status);
  const recentIssue = describeRecentHardwareIssue(resolved);

  if (recentIssue === '无') {
    return isRealHardwareStatusUnclear(resolved) ? '待确认' : '无异常';
  }
  if (resolved.estopActive) {
    return '急停触发';
  }
  if (resolved.safetyState === 'PROTECTIVE_STOP') {
    return '保护停机';
  }
  return '需查看';
}
