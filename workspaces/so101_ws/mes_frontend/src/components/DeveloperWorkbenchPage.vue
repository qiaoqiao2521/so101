<script setup>
import { computed, ref, watch } from 'vue';
import {
  DEFAULT_TEMPLATE_NAME,
  JOINT_SPECS,
  buildMergePayload,
  buildPreviewPayload,
  buildWaypointValues,
  buildWorkbenchExport,
  createWorkbenchPose,
  degToRad,
  radToDeg,
} from '../lib/fixedActionWorkbench.js';
import { getDetectionSourceMeta } from '../lib/visionConsole.js';
import RuntimeTargetCard from './RuntimeTargetCard.vue';
import VisionEpisodeQualityPanel from './VisionEpisodeQualityPanel.vue';
import LightArmPreview from './LightArmPreview.vue';

const props = defineProps({
  systemBusy: { type: Object, required: true },
  systemStatus: { type: Object, required: true },
  runtimeTarget: { type: String, required: true },
  rosbridgeConnected: { type: Boolean, required: true },
  socketLabel: { type: String, required: true },
  detections: { type: Array, required: true },
  leaderDebug: { type: Object, default: () => ({}) },
  statusEvents: { type: Array, default: () => [] },
  visionEpisodeQuality: { type: Object, default: null },
});

const emit = defineEmits([
  'open-console',
  'connect-live',
  'refresh-system',
  'open-rviz',
  'stop-sim',
  'open-browser',
  'stop-browser',
  'set-runtime-target',
  'inject-status',
  'inject-red',
  'inject-blue',
  'preview-pose',
  'save-workbench',
  'merge-waypoints',
]);

const detectionPreview = computed(() => props.detections.slice(0, 4));
const leaderJointOrder = ['shoulder_pan', 'shoulder_lift', 'elbow_flex', 'wrist_flex', 'wrist_roll', 'gripper'];
const leaderPositionScales = [1, 1, 1, 1, -1, 1];
const leaderPositionOffsets = [0, 0, 0, 0, 0, 0];
const gazeboToPreviewScales = [1, 1, 1, 1, -1, 1];
const controlSide = ref('leader');
const hasSyncedFollowerPose = ref(false);
const currentPose = ref({
  ...createWorkbenchPose(1),
  name: 'debug_pose_1',
  joints: {
    shoulder_panDeg: 28,
    shoulder_liftDeg: -22,
    elbow_flexDeg: 58,
    wrist_flexDeg: -28,
    wrist_rollDeg: 36,
    gripper: 0.72,
  },
});
const templateName = ref(DEFAULT_TEMPLATE_NAME);
const currentWaypointValues = computed(() => buildWaypointValues(currentPose.value));
const rosPreviewEnabled = computed(() => props.rosbridgeConnected && props.systemStatus.simRunning);

function updateJoint(key, rawValue) {
  currentPose.value = {
    ...currentPose.value,
    joints: {
      ...currentPose.value.joints,
      [key]: Number(rawValue),
    },
  };
}

function resetCurrentPose() {
  currentPose.value = createWorkbenchPose(1);
}

function sendPreviewPose() {
  if (!rosPreviewEnabled.value) {
    return;
  }
  emit('preview-pose', buildPreviewPayload(currentPose.value));
}

function saveHeroWorkbench() {
  emit('save-workbench', {
    fileStem: templateName.value,
    content: buildWorkbenchExport(templateName.value, [currentPose.value]),
  });
}

function mergeHeroWaypoints() {
  emit('merge-waypoints', buildMergePayload(templateName.value, [currentPose.value]));
}

const poseEditorStats = computed(() => [
  {
    label: 'ROS 预览',
    value: rosPreviewEnabled.value ? '可发送' : '未就绪',
  },
  {
    label: '当前模板',
    value: templateName.value,
  },
  {
    label: '停留时长',
    value: `${currentPose.value.durationMs} ms`,
  },
]);

const heroStats = computed(() => [
  {
    label: '实时链路',
    value: props.socketLabel,
    note: props.rosbridgeConnected ? 'backend 已连 rosbridge' : 'rosbridge 仍未连通',
  },
  {
    label: '姿态调试',
    value: props.systemStatus.simRunning ? '可联动 ROS' : '浏览器预览',
    note: props.systemStatus.simRunning ? '可把当前姿态推给预览链路' : '先回首页启动仿真，再启用 ROS 预览',
  },
  {
    label: '检测缓存',
    value: props.detections.length ? `${props.detections.length} 条` : '暂无消息',
    note: props.detections[0]?.time ? `最近消息 ${props.detections[0].time}` : '等待原始检测消息进入页面',
  },
  {
    label: '调试浏览器',
    value: props.systemStatus.browserRunning ? '在线' : '未启动',
    note: props.systemStatus.browserDebugUrl || '默认调试地址不可用',
  },
]);

const sideModeCopy = computed(() =>
  controlSide.value === 'leader'
    ? {
        title: '主臂同步调试',
        detail: '读取真实 leader 输入，只看 raw / mapped / Gazebo / delta，不发送控制指令。',
      }
    : {
        title: '从臂指令调试',
        detail: '浏览器姿态编辑会向当前执行体发送目标；单从臂模式下会走真实 follower adapter。',
      },
);

function normalizeJointState(msg) {
  if (!msg || typeof msg !== 'object') {
    return {};
  }
  const names = Array.isArray(msg.name) ? msg.name : [];
  const positions = Array.isArray(msg.position) ? msg.position : [];
  return names.reduce((acc, name, index) => {
    const value = Number(positions[index]);
    if (Number.isFinite(value)) {
      acc[name] = value;
    }
    return acc;
  }, {});
}

function formatRad(value) {
  return Number.isFinite(value) ? value.toFixed(4) : '-';
}

function jointStateToPoseJoints(msg) {
  const map = normalizeJointState(msg);
  const values = leaderJointOrder.map((name) => map[name]);
  if (!values.some((value) => Number.isFinite(value))) {
    return null;
  }
  return {
    ...currentPose.value.joints,
    shoulder_panDeg: Number.isFinite(values[0]) ? radToDeg(values[0]) : currentPose.value.joints.shoulder_panDeg,
    shoulder_liftDeg: Number.isFinite(values[1]) ? radToDeg(values[1]) : currentPose.value.joints.shoulder_liftDeg,
    elbow_flexDeg: Number.isFinite(values[2]) ? radToDeg(values[2]) : currentPose.value.joints.elbow_flexDeg,
    wrist_flexDeg: Number.isFinite(values[3]) ? radToDeg(values[3]) : currentPose.value.joints.wrist_flexDeg,
    wrist_rollDeg: Number.isFinite(values[4]) ? radToDeg(values[4]) : currentPose.value.joints.wrist_rollDeg,
    gripper: Number.isFinite(values[5]) ? values[5] : currentPose.value.joints.gripper,
  };
}

function syncCurrentPoseFromFollower() {
  const joints = jointStateToPoseJoints(props.leaderDebug?.gazeboJointState);
  if (!joints) {
    return false;
  }
  currentPose.value = {
    ...currentPose.value,
    name: currentPose.value.name || 'follower_live_pose',
    joints,
  };
  return true;
}

function formatStatusValue(value) {
  if (value === null || value === undefined || value === '') {
    return '-';
  }
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value.toFixed(value > 100 ? 0 : 2) : '-';
  }
  return String(value);
}

const leaderDebugRows = computed(() => {
  const leaderMap = normalizeJointState(props.leaderDebug?.leaderJointState);
  const gazeboMap = normalizeJointState(props.leaderDebug?.gazeboJointState);
  return leaderJointOrder.map((name, index) => {
    const leader = leaderMap[name];
    const mapped = Number.isFinite(leader)
      ? leader * leaderPositionScales[index] + leaderPositionOffsets[index]
      : Number.NaN;
    const gazebo = gazeboMap[name];
    const delta = Number.isFinite(mapped) && Number.isFinite(gazebo) ? mapped - gazebo : Number.NaN;
    return {
      name,
      axis: index + 1,
      scale: leaderPositionScales[index],
      leader,
      mapped,
      gazebo,
      delta,
    };
  });
});

function getMappedLeaderJoint(leaderMap, name, index) {
  const leader = leaderMap[name];
  return Number.isFinite(leader) ? leader * leaderPositionScales[index] + leaderPositionOffsets[index] : Number.NaN;
}

function firstFinite(...values) {
  return values.find((value) => Number.isFinite(value));
}

const livePreviewPose = computed(() => {
  if (controlSide.value !== 'leader') {
    return currentPose.value;
  }

  const leaderMap = normalizeJointState(props.leaderDebug?.leaderJointState);
  const gazeboMap = normalizeJointState(props.leaderDebug?.gazeboJointState);
  const jointRad = leaderJointOrder.map((name, index) =>
    firstFinite(gazeboMap[name], getMappedLeaderJoint(leaderMap, name, index)),
  );

  if (!jointRad.some((value) => Number.isFinite(value))) {
    return currentPose.value;
  }

  return {
    ...currentPose.value,
    name: 'leader_live_preview',
    joints: {
      ...currentPose.value.joints,
      shoulder_panDeg: Number.isFinite(jointRad[0]) ? radToDeg(jointRad[0] * gazeboToPreviewScales[0]) : currentPose.value.joints.shoulder_panDeg,
      shoulder_liftDeg: Number.isFinite(jointRad[1]) ? radToDeg(jointRad[1] * gazeboToPreviewScales[1]) : currentPose.value.joints.shoulder_liftDeg,
      elbow_flexDeg: Number.isFinite(jointRad[2]) ? radToDeg(jointRad[2] * gazeboToPreviewScales[2]) : currentPose.value.joints.elbow_flexDeg,
      wrist_flexDeg: Number.isFinite(jointRad[3]) ? radToDeg(jointRad[3] * gazeboToPreviewScales[3]) : currentPose.value.joints.wrist_flexDeg,
      wrist_rollDeg: Number.isFinite(jointRad[4]) ? radToDeg(jointRad[4] * gazeboToPreviewScales[4]) : currentPose.value.joints.wrist_rollDeg,
      gripper: Number.isFinite(jointRad[5]) ? jointRad[5] : currentPose.value.joints.gripper,
    },
  };
});

const leaderDebugStatus = computed(() => {
  const leaderStatus = props.leaderDebug?.leaderStatus || {};
  const bridgeStatus = props.leaderDebug?.bridgeStatus || {};
  const followerStatus = props.leaderDebug?.followerStatus || {};
  return [
    { label: 'leader state', value: leaderStatus.state },
    { label: 'connected', value: leaderStatus.connected },
    { label: 'calibrated', value: leaderStatus.calibrated },
    { label: 'leader hz', value: leaderStatus.hz },
    { label: 'age ms', value: leaderStatus.age_ms ?? leaderStatus.ageMs },
    { label: 'bridge state', value: bridgeStatus.state },
    { label: 'bridge reasons', value: Array.isArray(bridgeStatus.last_reasons) ? bridgeStatus.last_reasons.join(', ') || '-' : bridgeStatus.last_reasons },
    { label: 'follower software', value: followerStatus.software_ready },
    { label: 'follower hardware', value: followerStatus.hardware_bus_ready },
    { label: 'follower dry-run', value: followerStatus.dry_run },
    { label: 'follower cmds', value: followerStatus.sent_command_count },
    { label: 'updated', value: props.leaderDebug?.updatedAt },
  ];
});

const followerActionPreview = computed(() => {
  const action = props.leaderDebug?.followerStatus?.last_sent_action || {};
  return Object.entries(action)
    .map(([key, value]) => `${key}=${formatStatusValue(value)}`)
    .join(' / ') || '-';
});

const followerLastError = computed(() => props.leaderDebug?.followerStatus?.last_error || '-');

const followerPoseSyncReady = computed(() => Boolean(jointStateToPoseJoints(props.leaderDebug?.gazeboJointState)));

watch(
  () => controlSide.value,
  (side) => {
    if (side === 'follower' && !hasSyncedFollowerPose.value && syncCurrentPoseFromFollower()) {
      hasSyncedFollowerPose.value = true;
    }
  },
);
</script>

<template>
  <section class="developer-workbench-page workspace-view">
    <div class="side-mode-switch" :class="`side-mode-${controlSide}`">
      <div>
        <p class="eyebrow dark-eyebrow">Control Side</p>
        <h3>{{ sideModeCopy.title }}</h3>
        <span>{{ sideModeCopy.detail }}</span>
      </div>
      <div class="side-mode-actions" role="group" aria-label="选择调试侧">
        <button class="side-mode-button leader-side" :class="{ active: controlSide === 'leader' }" @click="controlSide = 'leader'">主 · Leader 输入</button>
        <button class="side-mode-button follower-side" :class="{ active: controlSide === 'follower' }" @click="controlSide = 'follower'">从 · 执行体指令</button>
      </div>
    </div>

    <header class="developer-workbench-hero">
      <div class="developer-pose-editor" :class="{ 'side-muted': controlSide !== 'follower', 'follower-side-active': controlSide === 'follower' }">
        <div class="developer-pose-head">
          <div>
            <p class="eyebrow dark-eyebrow">Follower Command</p>
            <h2>从臂 / 执行体指令编辑</h2>
            <small class="side-role-note">这里是前端给当前执行体发目标；单从臂模式下会发送到真实 follower adapter。</small>
          </div>
          <div class="developer-head-actions">
            <button class="subtle-action" @click="emit('connect-live')">{{ socketLabel === '已连接' ? '实时链路已连接' : '连接实时链路' }}</button>
            <button class="subtle-action developer-back-action" @click="emit('open-console')">返回演示控制台</button>
          </div>
        </div>

        <div class="developer-pose-stats">
          <article v-for="item in poseEditorStats" :key="item.label" class="panel-flat">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </article>
        </div>

        <div class="developer-pose-form">
          <label class="field-stack">
            <span>姿态名称</span>
            <input v-model="currentPose.name" class="debug-input" />
          </label>

          <label class="field-stack">
            <span>模板名称</span>
            <input v-model="templateName" class="debug-input" />
          </label>

          <label class="field-stack">
            <span>停留时长 (ms)</span>
            <input v-model.number="currentPose.durationMs" class="debug-input" type="number" min="100" max="10000" step="50" />
          </label>
        </div>

        <div class="developer-pose-actions">
          <button class="subtle-action" @click="resetCurrentPose">恢复 Home</button>
          <button class="subtle-action" :disabled="!followerPoseSyncReady" @click="syncCurrentPoseFromFollower">吸附当前从臂</button>
          <button class="subtle-action" :disabled="systemBusy.previewPose || !rosPreviewEnabled" @click="sendPreviewPose">
            {{ systemBusy.previewPose ? '发送中...' : '发送到 ROS' }}
          </button>
          <button class="subtle-action" :disabled="systemBusy.saveWorkbench" @click="saveHeroWorkbench">
            {{ systemBusy.saveWorkbench ? '保存中...' : '保存模板' }}
          </button>
          <button class="subtle-action" :disabled="systemBusy.mergeWaypoints" @click="mergeHeroWaypoints">
            {{ systemBusy.mergeWaypoints ? '回灌中...' : '回灌 waypoints' }}
          </button>
        </div>

        <div class="developer-joint-stack">
          <article v-for="(spec, index) in JOINT_SPECS" :key="spec.key" class="developer-joint-card">
            <header>
              <strong>{{ index + 1 }}. {{ spec.label }}</strong>
              <span v-if="spec.kind === 'angle'">{{ currentPose.joints[spec.key].toFixed(1) }}° / {{ degToRad(currentPose.joints[spec.key]).toFixed(4) }} rad</span>
              <span v-else>{{ currentPose.joints[spec.key].toFixed(2) }}</span>
            </header>
            <div class="developer-joint-controls">
              <input
                :value="currentPose.joints[spec.key]"
                class="debug-slider"
                type="range"
                :min="spec.min"
                :max="spec.max"
                :step="spec.step"
                @input="updateJoint(spec.key, $event.target.value)"
              />
              <input
                :value="currentPose.joints[spec.key]"
                class="debug-input developer-joint-number"
                type="number"
                :min="spec.min"
                :max="spec.max"
                :step="spec.step"
                @input="updateJoint(spec.key, $event.target.value)"
              />
            </div>
          </article>
        </div>

        <div class="developer-waypoint-line panel-flat">
          <span>当前 waypoint</span>
          <code>{{ currentWaypointValues.join(', ') }}</code>
        </div>
      </div>

      <div class="developer-workbench-showcase" :class="{ 'side-muted': controlSide !== 'follower', 'follower-side-active': controlSide === 'follower' }" aria-label="SO101 large three.js preview">
        <div class="developer-showcase-head">
          <span>THREE.JS MODEL VIEW</span>
          <strong>{{ controlSide === 'leader' ? 'SO-ARM101 / EXECUTOR LIVE PREVIEW' : 'SO-ARM101 / COMMAND PREVIEW' }}</strong>
        </div>
        <LightArmPreview :pose="livePreviewPose" />
        <div class="developer-workbench-stats">
          <article v-for="item in heroStats" :key="item.label" class="developer-workbench-stat">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <small>{{ item.note }}</small>
          </article>
        </div>
      </div>
    </header>

    <div class="developer-workbench-layout">
      <section class="developer-panel">
        <div class="section-head compact-head">
          <p class="eyebrow dark-eyebrow">System Debug</p>
          <h3>系统调试与浏览器控制</h3>
        </div>
        <p class="empty-note">这些动作属于开发联调路径，不再出现在首页或系统工具抽屉里。</p>

        <RuntimeTargetCard
          :runtime-target="runtimeTarget"
          :busy="systemBusy.setRuntimeTarget"
          :sim-running="systemStatus.simRunning"
          :real-hardware="systemStatus.realHardware"
          @set-target="emit('set-runtime-target', $event)"
        />

        <div class="drawer-actions">
          <button class="subtle-action" @click="emit('refresh-system')">重新读取状态</button>
          <button class="subtle-action" :disabled="systemBusy.openRviz" @click="emit('open-rviz')">{{ systemBusy.openRviz ? '打开中...' : '打开 RViz 观察' }}</button>
          <button class="subtle-action danger-action" :disabled="systemBusy.stopSim" @click="emit('stop-sim')">{{ systemBusy.stopSim ? '结束中...' : '结束本轮演示' }}</button>
          <button class="subtle-action" :disabled="systemBusy.openBrowser" @click="emit('open-browser')">{{ systemBusy.openBrowser ? '拉起中...' : '拉起调试浏览器' }}</button>
          <button class="subtle-action" :disabled="systemBusy.stopBrowser" @click="emit('stop-browser')">{{ systemBusy.stopBrowser ? '关闭中...' : '关闭调试浏览器' }}</button>
        </div>

        <dl class="runtime-grid developer-runtime-grid">
          <div>
            <dt>simPid</dt>
            <dd>{{ systemStatus.simPid || '-' }}</dd>
          </div>
          <div>
            <dt>rvizPid</dt>
            <dd>{{ systemStatus.rvizPid || '-' }}</dd>
          </div>
          <div>
            <dt>browserPid</dt>
            <dd>{{ systemStatus.browserPid || '-' }}</dd>
          </div>
          <div>
            <dt>rosbridge</dt>
            <dd>{{ rosbridgeConnected ? 'connected' : 'disconnected' }}</dd>
          </div>
          <div>
            <dt>simLog</dt>
            <dd>{{ systemStatus.simLog || '-' }}</dd>
          </div>
          <div>
            <dt>rvizLog</dt>
            <dd>{{ systemStatus.rvizLog || '-' }}</dd>
          </div>
          <div>
            <dt>browserLog</dt>
            <dd>{{ systemStatus.browserLog || '-' }}</dd>
          </div>
          <div>
            <dt>browserDebugUrl</dt>
            <dd>{{ systemStatus.browserDebugUrl || '-' }}</dd>
          </div>
        </dl>
      </section>

      <section class="developer-panel leader-debug-panel" :class="{ 'leader-side-active': controlSide === 'leader' }">
        <div class="section-head compact-head">
          <p class="eyebrow dark-eyebrow">Leader Signal Debug</p>
          <h3>主臂输入与执行体映射</h3>
        </div>
        <p class="empty-note">只读调试：显示 `/leader/joint_states`、映射后目标、执行体 `/joint_states` 与差值。单从臂模式下这里的执行体观测来自 follower adapter。</p>

        <div class="drawer-actions">
          <button class="subtle-action" @click="emit('connect-live')">{{ socketLabel === '已连接' ? '实时链路已连接' : '连接实时链路' }}</button>
          <span class="signal-chip">{{ rosbridgeConnected ? 'rosbridge connected' : 'rosbridge offline' }}</span>
          <span class="signal-chip">{{ socketLabel }}</span>
        </div>

        <dl class="runtime-grid leader-debug-status-grid">
          <div v-for="item in leaderDebugStatus" :key="item.label">
            <dt>{{ item.label }}</dt>
            <dd>{{ formatStatusValue(item.value) }}</dd>
          </div>
        </dl>

        <div class="developer-note-grid">
          <article class="developer-note-card">
            <span>Follower software link</span>
            <p>{{ props.leaderDebug?.followerStatus?.software_ready ? '软件链路已能接收并转换轨迹。' : '等待 follower adapter 状态。' }}</p>
          </article>
          <article class="developer-note-card">
            <span>Follower hardware bus</span>
            <p>{{ props.leaderDebug?.followerStatus?.hardware_bus_ready ? '硬件总线已连接。' : '硬件总线未确认，不声明真实 follower 闭环。' }}</p>
          </article>
          <article class="developer-note-card">
            <span>Last follower action</span>
            <p>{{ followerActionPreview }}</p>
          </article>
          <article class="developer-note-card">
            <span>Follower error</span>
            <p>{{ followerLastError }}</p>
          </article>
        </div>

        <div class="leader-debug-table-wrap">
          <table class="leader-debug-table">
            <thead>
              <tr>
                <th>axis</th>
                <th>joint</th>
                <th>scale</th>
                <th>leader</th>
                <th>mapped</th>
                <th>gazebo</th>
                <th>delta</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in leaderDebugRows" :key="row.name">
                <td>{{ row.axis }}</td>
                <td>{{ row.name }}</td>
                <td>{{ row.scale }}</td>
                <td>{{ formatRad(row.leader) }}</td>
                <td>{{ formatRad(row.mapped) }}</td>
                <td>{{ formatRad(row.gazebo) }}</td>
                <td :class="{ 'leader-debug-warn': Math.abs(row.delta) > 0.15 }">{{ formatRad(row.delta) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="developer-panel">
        <div class="section-head compact-head">
          <p class="eyebrow dark-eyebrow">Demo Inject / Debug Trigger</p>
          <h3>演示注入、调试触发与原始消息</h3>
        </div>
        <p class="empty-note">这里的消息只用于联调、录屏和链路排障。演示注入不等于真实 YOLO，调试触发也不应被描述成视觉结果。</p>

        <div class="drawer-actions">
          <button class="subtle-action" @click="emit('inject-status')">发送调试状态</button>
          <button class="subtle-action" @click="emit('inject-red')">注入红色目标（演示）</button>
          <button class="subtle-action" @click="emit('inject-blue')">注入蓝色目标（演示）</button>
        </div>

        <div class="developer-note-grid">
          <article class="developer-note-card">
            <span>真实检测</span>
            <p>来自 YOLO 节点的消息，才可用于说明视觉链路真实在线。</p>
          </article>
          <article class="developer-note-card">
            <span>样本注入</span>
            <p>手动写入检测流或状态流，仅用于联调和讲解，不代表真实推理。</p>
          </article>
          <article class="developer-note-card">
            <span>调试触发</span>
            <p>姿态预览和浏览器控制只验证执行链路，不应混用成视觉结果。</p>
          </article>
        </div>

        <div class="detection-list developer-detection-list">
          <article v-for="entry in detectionPreview" :key="entry.id" class="detection-card">
            <header>
              <strong>{{ getDetectionSourceMeta(entry.payload).label }} · {{ entry.payload.count ?? entry.payload.detections?.length ?? 0 }} detections</strong>
              <span>{{ entry.time }}</span>
            </header>
            <p>{{ JSON.stringify(entry.payload) }}</p>
          </article>
          <p v-if="detectionPreview.length === 0" class="empty-note">尚未收到检测流原始消息。</p>
        </div>
      </section>
    </div>

    <VisionEpisodeQualityPanel
      :quality="visionEpisodeQuality"
      :status-events="statusEvents"
    />
  </section>
</template>
