<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue';
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

const props = defineProps({
  busyPreview: { type: Boolean, default: false },
  busySave: { type: Boolean, default: false },
  busyMerge: { type: Boolean, default: false },
});

const emit = defineEmits(['preview-pose', 'save-export', 'merge-waypoints']);

const currentPose = ref(createWorkbenchPose(1));
const templateName = ref(DEFAULT_TEMPLATE_NAME);
const capturedPoses = ref([]);
const selectedPoseIndex = ref(-1);
const exportMode = ref('all');
const realtimePreviewEnabled = ref(false);
const suppressRealtimePreview = ref(false);
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

watch(
  () => realtimePreviewEnabled.value,
  (enabled) => {
    if (!enabled) {
      previewScheduler.cancel();
    }
  },
);

watch(
  () => [
    currentPose.value.durationMs,
    ...buildWaypointValues(currentPose.value),
  ],
  () => {
    if (!realtimePreviewEnabled.value || suppressRealtimePreview.value) {
      previewScheduler.cancel();
      return;
    }
    previewScheduler.schedule(buildPreviewPayload(currentPose.value));
  },
);

onBeforeUnmount(() => {
  previewScheduler.cancel();
});
</script>

<template>
  <section class="drawer-section workbench-section">
    <div class="workbench-head">
      <div>
        <h3>固定动作调试器</h3>
        <p class="empty-note">参考旧 Electron 工具重做。这里直接输出 SO101 可落地的 waypoint / template 片段。</p>
      </div>
      <div class="drawer-actions compact-actions">
        <button class="subtle-action" @click="resetCurrentPose">恢复 Home</button>
        <button class="subtle-action" @click="capturePose">采集当前姿态</button>
        <button class="subtle-action" :disabled="selectedPoseIndex < 0" @click="overwriteSelectedPose">覆盖选中姿态</button>
        <button class="subtle-action" :disabled="props.busyPreview" @click="sendPreviewPose">{{ props.busyPreview ? '发送中...' : '发送当前姿态到仿真' }}</button>
      </div>
    </div>

    <div class="workbench-grid">
      <div class="workbench-editor">
        <label class="field-stack">
          <span>姿态名称</span>
          <input v-model="currentPose.name" class="debug-input" />
        </label>
        <label class="field-stack">
          <span>停留时长 (ms)</span>
          <input v-model.number="currentPose.durationMs" class="debug-input" type="number" min="100" max="10000" step="50" />
        </label>
        <label class="toggle-row">
          <input v-model="realtimePreviewEnabled" type="checkbox" />
          <span>拖动滑块时实时预览到 Gazebo</span>
        </label>

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
          <p class="eyebrow dark-eyebrow">当前 waypoint 预览</p>
          <code>{{ currentWaypointValues.join(', ') }}</code>
        </div>
      </div>

      <div class="workbench-sequence">
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
          <button class="subtle-action" :disabled="selectedPoseIndex < 0" @click="generateTemplateFromSelected">从选中姿态生成单步模板</button>
          <button class="subtle-action" @click="useAllCapturedPoses">使用全部姿态导出</button>
          <button class="subtle-action" :disabled="props.busySave" @click="saveExport">{{ props.busySave ? '保存中...' : '保存到工作区文件' }}</button>
          <button class="subtle-action" :disabled="props.busyMerge" @click="mergeIntoWaypoints">{{ props.busyMerge ? '合并中...' : '一键合并到 waypoints.yaml' }}</button>
        </div>
        <p class="empty-note">当前导出范围：{{ exportMode === 'selected' ? '选中姿态单步模板' : '全部已采集姿态' }}</p>

        <label class="field-stack">
          <span>waypoints.yaml 片段</span>
          <textarea class="debug-textarea" :value="waypointSnippet" readonly />
        </label>
        <label class="field-stack">
          <span>action_templates 片段</span>
          <textarea class="debug-textarea" :value="templateSnippet" readonly />
        </label>
        <label class="field-stack">
          <span>完整可复制片段</span>
          <textarea class="debug-textarea large-textarea" :value="combinedExport" readonly />
        </label>
      </div>
    </div>
  </section>
</template>
