<script setup>
import { computed, defineAsyncComponent, onBeforeUnmount, ref, watch } from 'vue';
import {
  DEFAULT_TEMPLATE_NAME,
  JOINT_SPECS,
  buildMergePayload,
  buildPreviewPayload,
  buildWaypointValues,
  buildWorkbenchExport,
  createRealtimePreviewScheduler,
  createWorkbenchPose,
  degToRad,
  formatActionTemplateSnippet,
  formatWaypointSnippet,
  normalizePose,
} from '../lib/fixedActionWorkbench.js';

const LightArmPreview = defineAsyncComponent(() => import('./LightArmPreview.vue'));

const props = defineProps({
  showHero: { type: Boolean, default: true },
  busyPreview: { type: Boolean, default: false },
  busySave: { type: Boolean, default: false },
  busyMerge: { type: Boolean, default: false },
  rosbridgeConnected: { type: Boolean, default: false },
  systemStatus: { type: Object, required: true },
});

const emit = defineEmits(['preview-pose', 'save-export', 'merge-waypoints']);

const currentPose = ref(createWorkbenchPose(1));
const templateName = ref(DEFAULT_TEMPLATE_NAME);
const capturedPoses = ref([]);
const selectedPoseIndex = ref(-1);
const exportMode = ref('all');
const realtimePreviewEnabled = ref(false);
const suppressRealtimePreview = ref(false);
const clipboardHint = ref('');
let clipboardTimer = null;

const previewScheduler = createRealtimePreviewScheduler((payload) => emit('preview-pose', payload), 180);

const exportPoses = computed(() => {
  if (exportMode.value === 'selected' && selectedPoseIndex.value >= 0) {
    return [capturedPoses.value[selectedPoseIndex.value]];
  }
  return capturedPoses.value.length ? capturedPoses.value : [currentPose.value];
});
const currentWaypointValues = computed(() => buildWaypointValues(currentPose.value));
const waypointSnippet = computed(() => formatWaypointSnippet(exportPoses.value));
const templateSnippet = computed(() => formatActionTemplateSnippet(templateName.value, exportPoses.value));
const combinedExport = computed(() => buildWorkbenchExport(templateName.value, exportPoses.value));
const rosPreviewEnabled = computed(() => props.rosbridgeConnected && props.systemStatus.simRunning);
const heroStats = computed(() => [
  {
    label: '浏览器校对',
    value: '实时可用',
    note: '不依赖 Gazebo，本地姿态始终可见',
  },
  {
    label: 'ROS 预览',
    value: rosPreviewEnabled.value ? '可发送' : '未就绪',
    note: rosPreviewEnabled.value ? '可把当前姿态推给预览链路' : '需要先在首页启动仿真并连上 rosbridge',
  },
  {
    label: '导出范围',
    value: exportMode.value === 'selected' ? '单步模板' : '完整序列',
    note: `${exportPoses.value.length} 个姿态会进入导出结果`,
  },
]);

function setClipboardHint(message) {
  clipboardHint.value = message;
  if (clipboardTimer) {
    window.clearTimeout(clipboardTimer);
  }
  clipboardTimer = window.setTimeout(() => {
    clipboardHint.value = '';
    clipboardTimer = null;
  }, 2200);
}

function resetCurrentPose() {
  const nextIndex = capturedPoses.value.length + 1;
  suppressRealtimePreview.value = true;
  currentPose.value = createWorkbenchPose(nextIndex);
  selectedPoseIndex.value = -1;
  queueMicrotask(() => {
    suppressRealtimePreview.value = false;
  });
}

function capturePose() {
  const normalized = normalizePose(currentPose.value);
  suppressRealtimePreview.value = true;
  capturedPoses.value = [...capturedPoses.value, normalized];
  selectedPoseIndex.value = capturedPoses.value.length - 1;
  currentPose.value = createWorkbenchPose(capturedPoses.value.length + 1);
  queueMicrotask(() => {
    suppressRealtimePreview.value = false;
  });
}

function loadPose(index) {
  const pose = capturedPoses.value[index];
  if (!pose) {
    return;
  }
  currentPose.value = normalizePose({
    ...pose,
    joints: { ...pose.joints },
  });
  selectedPoseIndex.value = index;
}

function overwriteSelectedPose() {
  if (selectedPoseIndex.value < 0) {
    return;
  }
  const next = [...capturedPoses.value];
  next[selectedPoseIndex.value] = normalizePose(currentPose.value);
  capturedPoses.value = next;
}

function removePose(index) {
  const next = [...capturedPoses.value];
  next.splice(index, 1);
  capturedPoses.value = next;
  if (selectedPoseIndex.value === index) {
    selectedPoseIndex.value = -1;
  } else if (selectedPoseIndex.value > index) {
    selectedPoseIndex.value -= 1;
  }
}

function generateTemplateFromSelected() {
  const pose = capturedPoses.value[selectedPoseIndex.value];
  if (!pose) {
    return;
  }
  templateName.value = `${pose.name}_template`;
  exportMode.value = 'selected';
}

function useAllCapturedPoses() {
  exportMode.value = 'all';
}

function sendPreviewPose() {
  if (!rosPreviewEnabled.value) {
    return;
  }
  emit('preview-pose', buildPreviewPayload(currentPose.value));
}

function saveExport() {
  emit('save-export', {
    fileStem: templateName.value,
    content: combinedExport.value,
  });
}

function mergeIntoWaypoints() {
  emit('merge-waypoints', buildMergePayload(templateName.value, exportPoses.value));
}

function updateJoint(key, rawValue) {
  currentPose.value = {
    ...currentPose.value,
    joints: {
      ...currentPose.value.joints,
      [key]: Number(rawValue),
    },
  };
}

async function copyExport() {
  try {
    await navigator.clipboard.writeText(combinedExport.value);
    setClipboardHint('YAML 已复制');
  } catch {
    setClipboardHint('复制失败，请手动复制下方文本');
  }
}

function downloadExport() {
  const blob = new Blob([combinedExport.value], { type: 'text/yaml;charset=utf-8' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  link.href = url;
  link.download = `${templateName.value || DEFAULT_TEMPLATE_NAME}.yaml`;
  link.click();
  URL.revokeObjectURL(url);
}

watch(
  () => props.rosbridgeConnected,
  (connected) => {
    if (!connected) {
      realtimePreviewEnabled.value = false;
      previewScheduler.cancel();
    }
  },
);

watch(
  () => realtimePreviewEnabled.value,
  (enabled) => {
    if (!enabled) {
      previewScheduler.cancel();
    }
  },
);

watch(
  () => [currentPose.value.durationMs, ...buildWaypointValues(currentPose.value)],
  () => {
    if (!realtimePreviewEnabled.value || suppressRealtimePreview.value || !rosPreviewEnabled.value) {
      previewScheduler.cancel();
      return;
    }
    previewScheduler.schedule(buildPreviewPayload(currentPose.value));
  },
);

onBeforeUnmount(() => {
  previewScheduler.cancel();
  if (clipboardTimer) {
    window.clearTimeout(clipboardTimer);
  }
});
</script>

<template>
  <section class="pose-workbench-page workspace-view">
    <header v-if="props.showHero" class="pose-workbench-hero">
      <div class="pose-workbench-copy">
        <p class="eyebrow dark-eyebrow">Stitch / Pose Workbench</p>
        <h2>六轴姿态工作台</h2>
        <p class="subhead-dark">
          这个页面只负责六轴姿态校对、片段导出和回灌入口。浏览器里的轻量模型优先服务“姿态是否合理”的快速判断，不承担 Gazebo 的仿真职责。
        </p>
      </div>
      <div class="pose-workbench-stats">
        <article v-for="item in heroStats" :key="item.label" class="pose-workbench-stat">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <small>{{ item.note }}</small>
        </article>
      </div>
    </header>

    <div class="pose-workbench-layout">
      <section class="pose-panel pose-editor-panel">
        <div class="section-head compact-head">
          <p class="eyebrow dark-eyebrow">Pose Editor</p>
          <h3>六轴姿态编辑</h3>
        </div>
        <p class="empty-note">当前姿态在这里编辑，右侧模型会实时变化。只有在仿真和 rosbridge 就绪后，才需要把当前姿态发送到 ROS 预览链路。</p>

        <label class="field-stack">
          <span>姿态名称</span>
          <input v-model="currentPose.name" class="debug-input" />
        </label>

        <label class="field-stack">
          <span>停留时长 (ms)</span>
          <input v-model.number="currentPose.durationMs" class="debug-input" type="number" min="100" max="10000" step="50" />
        </label>

        <label class="toggle-row">
          <input v-model="realtimePreviewEnabled" :disabled="!rosPreviewEnabled" type="checkbox" />
          <span>拖动时同步发送到 ROS 预览</span>
        </label>

        <div class="drawer-actions compact-actions">
          <button class="subtle-action" @click="resetCurrentPose">恢复 Home</button>
          <button class="subtle-action" @click="capturePose">采集当前姿态</button>
          <button class="subtle-action" :disabled="selectedPoseIndex < 0" @click="overwriteSelectedPose">覆盖选中姿态</button>
          <button class="subtle-action" :disabled="props.busyPreview || !rosPreviewEnabled" @click="sendPreviewPose">
            {{ props.busyPreview ? '发送中...' : '发送当前姿态到 ROS' }}
          </button>
        </div>

        <div v-for="(spec, index) in JOINT_SPECS" :key="spec.key" class="joint-card">
          <div class="joint-row">
            <strong>{{ index + 1 }}. {{ spec.label }}</strong>
            <span v-if="spec.kind === 'angle'">{{ currentPose.joints[spec.key].toFixed(2) }}° / {{ degToRad(currentPose.joints[spec.key]).toFixed(4) }} rad</span>
            <span v-else>{{ currentPose.joints[spec.key].toFixed(2) }}</span>
          </div>
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
            class="debug-input"
            type="number"
            :min="spec.min"
            :max="spec.max"
            :step="spec.step"
            @input="updateJoint(spec.key, $event.target.value)"
          />
        </div>

        <div class="preview-card">
          <p class="eyebrow dark-eyebrow">当前 waypoint</p>
          <code>{{ currentWaypointValues.join(', ') }}</code>
        </div>
      </section>

      <section class="pose-panel pose-preview-panel">
        <div class="section-head compact-head">
          <p class="eyebrow dark-eyebrow">Light Preview</p>
          <h3>轻量 3D 姿态预览</h3>
        </div>
        <p class="empty-note">深色机械臂是当前姿态，灰色是 Home 参考。这个视图只做姿态校对，不做碰撞、动力学和场景仿真。</p>
        <LightArmPreview :pose="currentPose" />
      </section>

      <section class="pose-panel pose-sequence-panel">
        <div class="section-head compact-head">
          <p class="eyebrow dark-eyebrow">Export & Merge</p>
          <h3>序列、保存、导出、回灌</h3>
        </div>
        <p class="empty-note">保存是写入工作区生成目录，导出是浏览器复制或下载，回灌是把模板直接合并进 `waypoints.yaml`。</p>

        <div class="sequence-head">
          <strong>已采集姿态</strong>
          <span>{{ capturedPoses.length }} 个</span>
        </div>

        <div class="pose-list">
          <article
            v-for="(pose, index) in capturedPoses"
            :key="pose.id"
            class="pose-card"
            :class="{ 'pose-card-selected': selectedPoseIndex === index }"
          >
            <header>
              <strong>{{ index + 1 }}. {{ pose.name }}</strong>
              <span>{{ pose.durationMs }} ms</span>
            </header>
            <p>{{ buildWaypointValues(pose).join(', ') }}</p>
            <div class="drawer-actions compact-actions">
              <button class="subtle-action" @click="loadPose(index)">载入</button>
              <button class="subtle-action danger-action" @click="removePose(index)">删除</button>
            </div>
          </article>
          <p v-if="capturedPoses.length === 0" class="empty-note">还没有采集姿态。先调当前关节，再点“采集当前姿态”。</p>
        </div>

        <label class="field-stack">
          <span>模板名称</span>
          <input v-model="templateName" class="debug-input" />
        </label>

        <div class="drawer-actions compact-actions">
          <button class="subtle-action" :disabled="selectedPoseIndex < 0" @click="generateTemplateFromSelected">选中姿态做单步模板</button>
          <button class="subtle-action" @click="useAllCapturedPoses">使用全部姿态导出</button>
        </div>

        <div class="drawer-actions compact-actions">
          <button class="subtle-action" :disabled="props.busySave" @click="saveExport">{{ props.busySave ? '保存中...' : '保存到工作区' }}</button>
          <button class="subtle-action" @click="copyExport">复制 YAML</button>
          <button class="subtle-action" @click="downloadExport">下载 YAML</button>
          <button class="subtle-action" :disabled="props.busyMerge" @click="mergeIntoWaypoints">{{ props.busyMerge ? '回灌中...' : '回灌到 waypoints.yaml' }}</button>
        </div>
        <p class="empty-note">
          当前导出范围：{{ exportMode === 'selected' ? '选中姿态单步模板' : '全部已采集姿态' }}
          <span v-if="clipboardHint"> · {{ clipboardHint }}</span>
        </p>

        <label class="field-stack">
          <span>waypoints.yaml 片段</span>
          <textarea class="debug-textarea" :value="waypointSnippet" readonly />
        </label>
        <label class="field-stack">
          <span>action_templates 片段</span>
          <textarea class="debug-textarea" :value="templateSnippet" readonly />
        </label>
        <label class="field-stack">
          <span>完整可导出片段</span>
          <textarea class="debug-textarea large-textarea" :value="combinedExport" readonly />
        </label>
      </section>
    </div>
  </section>
</template>
