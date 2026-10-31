const SOURCE_META = {
  real_yolo: {
    label: '真实 YOLO',
    shortLabel: '真实检测',
    isReal: true,
    toneClass: 'source-real',
    hint: '来自 YOLO 节点的实时检测结果。',
  },
  gazebo_color_detector: {
    label: 'Gazebo 仿真视觉',
    shortLabel: '仿真检测',
    isReal: false,
    toneClass: 'source-sim',
    hint: '来自 Gazebo RGB 相机和仿真颜色检测节点，可用于无真机阶段打通视觉全栈。',
  },
  demo_inject: {
    label: '演示注入',
    shortLabel: '演示消息',
    isReal: false,
    toneClass: 'source-demo',
    hint: '由前端主动写入检测流，仅用于联调和录屏。',
  },
  mock_yolo: {
    label: 'Mock 检测',
    shortLabel: 'Mock 流',
    isReal: false,
    toneClass: 'source-mock',
    hint: '来自 mock_yolo 节点，不代表真实相机推理。',
  },
  unknown: {
    label: '未知来源',
    shortLabel: '来源待确认',
    isReal: false,
    toneClass: 'source-unknown',
    hint: '当前消息缺少来源字段，前端无法确认是否来自真实 YOLO。',
  },
};

const CATEGORY_TEMPLATE_MAP = {
  red: 'pick_place_red',
  blue: 'pick_place_blue',
};

function roundNumber(value, digits = 1) {
  const factor = 10 ** digits;
  return Math.round(Number(value) * factor) / factor;
}

function toBoxArray(value) {
  if (!Array.isArray(value) || value.length !== 4) {
    return null;
  }
  const next = value.map((item) => Number(item));
  return next.every((item) => Number.isFinite(item)) ? next : null;
}

function normalizeDetectionItem(item = {}) {
  const xyxy = toBoxArray(item.bbox_xyxy);
  const xywh = toBoxArray(item.bbox_xywh);
  const legacyBox = toBoxArray(item.bbox);
  let center = null;
  let bboxLabel = '-';
  let bboxKind = '';

  if (xywh) {
    center = [roundNumber(xywh[0]), roundNumber(xywh[1])];
    bboxLabel = xywh.map((value) => roundNumber(value)).join(', ');
    bboxKind = 'xywh';
  } else if (xyxy) {
    center = [roundNumber((xyxy[0] + xyxy[2]) / 2), roundNumber((xyxy[1] + xyxy[3]) / 2)];
    bboxLabel = xyxy.map((value) => roundNumber(value)).join(', ');
    bboxKind = 'xyxy';
  } else if (legacyBox) {
    center = [roundNumber(legacyBox[0]), roundNumber(legacyBox[1])];
    bboxLabel = legacyBox.map((value) => roundNumber(value)).join(', ');
    bboxKind = 'xywh';
  }

  const category = String(item.category || '').trim().toLowerCase();
  const confidence = Number(item.confidence);

  return {
    category,
    confidence: Number.isFinite(confidence) ? confidence : 0,
    classId: item.class_id ?? null,
    bboxKind,
    bboxLabel,
    center,
    centerLabel: center ? `${center[0]}, ${center[1]}` : '-',
  };
}

export function resolveDetectionSource(payload = {}) {
  const source = String(payload?.source || '')
    .trim()
    .toLowerCase();

  if (SOURCE_META[source]) {
    return source;
  }
  if (payload?.frame_id && payload?.stamp && Array.isArray(payload?.detections)) {
    return 'real_yolo';
  }
  if (payload?.mock === true) {
    return 'mock_yolo';
  }
  return 'unknown';
}

export function getDetectionSourceMeta(payload = {}) {
  const key = resolveDetectionSource(payload);
  return {
    key,
    ...SOURCE_META[key],
  };
}

export function normalizeDetectionItems(payload = {}) {
  if (!payload || typeof payload !== 'object') {
    return [];
  }
  if (Array.isArray(payload.detections)) {
    return payload.detections.map((item) => normalizeDetectionItem(item)).filter((item) => item.category);
  }
  if (payload.category) {
    return [normalizeDetectionItem(payload)];
  }
  return [];
}

export function getLatestDetectionItem(payload = {}) {
  return normalizeDetectionItems(payload)[0] || null;
}

export function summarizeDetectionPayload(payload = {}) {
  const sourceMeta = getDetectionSourceMeta(payload);
  const items = normalizeDetectionItems(payload);
  const count = Number.isFinite(Number(payload?.count)) ? Number(payload.count) : items.length;
  const categories = items.map((item) => item.category).filter(Boolean).join(', ');
  const body = categories ? `${count} 个目标: ${categories}` : `${count} 个目标`;
  return `${sourceMeta.shortLabel} / ${body}`;
}

export function buildVisionTrace(payload = {}, selectedOrder = null) {
  const item = getLatestDetectionItem(payload);
  const recommendedTemplate = item ? CATEGORY_TEMPLATE_MAP[item.category] || '' : '';
  const currentTemplate = selectedOrder?.actionTemplateId || '';

  return {
    visual: item ? `${item.category} / ${(item.confidence * 100).toFixed(1)}%` : '暂无检测结果',
    visualNote: item && item.bboxKind ? `bbox_${item.bboxKind}: ${item.bboxLabel}` : '等待 /topic/detections 的下一条消息。',
    coordinate: item && item.center ? `像素中心 ${item.centerLabel}` : '未提供像素坐标',
    coordinateNote: '机器人坐标接口未接入，当前只能展示像素级结果。',
    command: currentTemplate || recommendedTemplate || '尚未绑定指令模板',
    commandNote: !item
      ? '先收到检测结果，再判断应该走哪条执行模板。'
      : currentTemplate
        ? recommendedTemplate && currentTemplate !== recommendedTemplate
          ? `当前工单为 ${currentTemplate}，但当前检测更像 ${recommendedTemplate}。`
          : `当前工单已绑定 ${currentTemplate}。`
        : recommendedTemplate
          ? `按当前类别，推荐模板为 ${recommendedTemplate}。`
          : '该类别尚未配置到执行模板的映射。',
  };
}
