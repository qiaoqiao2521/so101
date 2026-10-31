export const DEFAULT_TEMPLATE_NAME = 'debug_sequence';

const HOME_POSE_RAD = [0.0, -0.2, 0.4, -0.2, 0.0, 0.2];

export const JOINT_SPECS = [
  {
    key: 'shoulder_panDeg',
    label: '肩偏航',
    yamlKey: 'shoulder_pan',
    kind: 'angle',
    min: -180,
    max: 180,
    step: 1,
  },
  {
    key: 'shoulder_liftDeg',
    label: '肩抬升',
    yamlKey: 'shoulder_lift',
    kind: 'angle',
    min: -120,
    max: 120,
    step: 1,
  },
  {
    key: 'elbow_flexDeg',
    label: '肘弯曲',
    yamlKey: 'elbow_flex',
    kind: 'angle',
    min: -120,
    max: 120,
    step: 1,
  },
  {
    key: 'wrist_flexDeg',
    label: '腕俯仰',
    yamlKey: 'wrist_flex',
    kind: 'angle',
    min: -180,
    max: 180,
    step: 1,
  },
  {
    key: 'wrist_rollDeg',
    label: '腕旋转',
    yamlKey: 'wrist_roll',
    kind: 'angle',
    min: -180,
    max: 180,
    step: 1,
  },
  {
    key: 'gripper',
    label: '夹爪',
    yamlKey: 'gripper',
    kind: 'gripper',
    min: 0,
    max: 1.2,
    step: 0.01,
  },
];

function round(value, decimals = 2) {
  const scale = 10 ** decimals;
  return Math.round(value * scale) / scale;
}

export function degToRad(value) {
  return round((value * Math.PI) / 180, 4);
}

export function radToDeg(value) {
  return round((value * 180) / Math.PI, 2);
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function formatYamlScalar(value) {
  if (Number.isInteger(value)) {
    return `${value}.0`;
  }
  return value.toFixed(4).replace(/0+$/, '').replace(/\.$/, '.0');
}

export function createWorkbenchPose(index = 1) {
  return {
    id: `pose-${index}-${Date.now()}`,
    name: `debug_pose_${index}`,
    durationMs: 1200,
    joints: {
      shoulder_panDeg: radToDeg(HOME_POSE_RAD[0]),
      shoulder_liftDeg: radToDeg(HOME_POSE_RAD[1]),
      elbow_flexDeg: radToDeg(HOME_POSE_RAD[2]),
      wrist_flexDeg: radToDeg(HOME_POSE_RAD[3]),
      wrist_rollDeg: radToDeg(HOME_POSE_RAD[4]),
      gripper: HOME_POSE_RAD[5],
    },
  };
}

export function normalizePose(pose) {
  return {
    ...pose,
    name: String(pose.name || '').trim(),
    durationMs: clamp(Number(pose.durationMs) || 1200, 100, 10000),
    joints: JOINT_SPECS.reduce((acc, spec) => {
      const raw = Number(pose.joints?.[spec.key]);
      acc[spec.key] = round(clamp(Number.isFinite(raw) ? raw : spec.min, spec.min, spec.max), spec.kind === 'angle' ? 2 : 4);
      return acc;
    }, {}),
  };
}

export function buildWaypointValues(pose) {
  const normalized = normalizePose(pose);
  return JOINT_SPECS.map((spec) => {
    const value = normalized.joints[spec.key];
    if (spec.kind === 'angle') {
      return degToRad(value);
    }
    return round(value, 4);
  });
}

export function formatWaypointSnippet(poses) {
  const rows = ['waypoints:'];
  poses.forEach((pose) => {
    const normalized = normalizePose(pose);
    rows.push(`  ${normalized.name}:`);
    buildWaypointValues(normalized).forEach((value) => {
      rows.push(`  - ${formatYamlScalar(value)}`);
    });
  });
  return rows.join('\n');
}

export function formatActionTemplateSnippet(templateName, poses) {
  const safeName = String(templateName || DEFAULT_TEMPLATE_NAME).trim() || DEFAULT_TEMPLATE_NAME;
  const rows = [
    'action_templates:',
    `  ${safeName}:`,
    '    detection_required: false',
    '    sequence:',
  ];
  poses.forEach((pose) => {
    rows.push(`    - ${normalizePose(pose).name}`);
  });
  return rows.join('\n');
}

export function buildWorkbenchExport(templateName, poses) {
  return [formatWaypointSnippet(poses), '', formatActionTemplateSnippet(templateName, poses)].join('\n');
}

export function buildPreviewPayload(pose) {
  const normalized = normalizePose(pose);
  return {
    name: normalized.name,
    durationSec: round(normalized.durationMs / 1000, 2),
    positions: buildWaypointValues(normalized),
  };
}

export function buildMergePayload(templateName, poses) {
  const safeName = String(templateName || DEFAULT_TEMPLATE_NAME).trim() || DEFAULT_TEMPLATE_NAME;
  return {
    templateName: safeName,
    poses: poses.map((pose) => {
      const normalized = normalizePose(pose);
      return {
        name: normalized.name,
        durationMs: normalized.durationMs,
        positions: buildWaypointValues(normalized),
      };
    }),
  };
}

export function createRealtimePreviewScheduler(sendFn, delayMs = 180) {
  let timer = null;
  return {
    schedule(payload) {
      if (timer) {
        globalThis.clearTimeout(timer);
      }
      timer = globalThis.setTimeout(() => {
        timer = null;
        sendFn(payload);
      }, delayMs);
    },
    cancel() {
      if (timer) {
        globalThis.clearTimeout(timer);
        timer = null;
      }
    },
  };
}
