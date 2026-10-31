const STEP_LABELS = {
  home: '回到 Home 位',
  above_pick: '移动到抓取点上方',
  pick: '执行抓取',
  lift_from_pick: '抓取后抬升',
  above_place: '移动到放置点上方',
  place: '执行放置',
  retreat: '撤离放置区',
};

const ORDER_STATE_LABELS = {
  PENDING: '待执行',
  RUNNING: '执行中',
  DONE: '已完成',
  ERROR: '异常',
};

const STATUS_CODE_LABELS = {
  STARTED: '任务启动',
  STEP: '步骤推进',
  OK: '正常完成',
  ERROR: '执行异常',
};

function parseStepMessage(message = '') {
  const match = String(message).match(/^(\d+)\/(\d+)\s*->\s*([a-z_]+)$/i);
  if (!match) {
    return null;
  }
  return {
    current: match[1],
    total: match[2],
    action: match[3],
  };
}

export function formatOrderState(state = '') {
  return ORDER_STATE_LABELS[state] || state || '-';
}

export function formatStatusCode(code = '') {
  return STATUS_CODE_LABELS[code] || code || '-';
}

export function describeTaskStatus({ state = '', code = '', message = '' } = {}) {
  const step = parseStepMessage(message);
  if (step) {
    return `第 ${step.current} / ${step.total} 步：${STEP_LABELS[step.action] || step.action}`;
  }

  if (code === 'STARTED' && String(message).startsWith('template=')) {
    return `任务已启动，执行模板 ${String(message).slice('template='.length)}`;
  }

  if (code === 'OK') {
    return '任务完成，结果正常';
  }

  if (code === 'ERROR') {
    return message ? `任务异常：${message}` : '任务异常，请查看时间线';
  }

  const parts = [state, formatStatusCode(code), message].filter(Boolean);
  return parts.join(' / ') || '-';
}

export function summarizeOrderMessage(order = {}) {
  return describeTaskStatus({
    state: order.state,
    code: order.lastStatusCode,
    message: order.message,
  });
}
