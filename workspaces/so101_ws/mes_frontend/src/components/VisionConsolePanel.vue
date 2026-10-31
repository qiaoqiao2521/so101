<script setup>
import { computed } from 'vue';
import { buildVisionTrace, getDetectionSourceMeta, getLatestDetectionItem } from '../lib/visionConsole.js';

const props = defineProps({
  detectionEntry: { type: Object, default: null },
  visionTargetEntry: { type: Object, default: null },
  selectedOrder: { type: Object, default: null },
  formatStamp: { type: Function, required: true },
});

const payload = computed(() => props.detectionEntry?.payload || null);
const sourceMeta = computed(() => getDetectionSourceMeta(payload.value || {}));
const latestItem = computed(() => getLatestDetectionItem(payload.value || {}));
const latestTarget = computed(() => {
  const targets = props.visionTargetEntry?.payload?.targets || [];
  if (!latestItem.value) {
    return targets[0] || null;
  }
  return targets.find((target) => target.category === latestItem.value.category) || targets[0] || null;
});
const trace = computed(() => buildVisionTrace(payload.value || {}, props.selectedOrder));

const detectionTime = computed(() => {
  if (payload.value?.ts) {
    return props.formatStamp(payload.value.ts);
  }
  return props.detectionEntry?.time || '-';
});

const detectionRows = computed(() => [
  {
    label: '当前来源',
    value: sourceMeta.value.label,
    note: sourceMeta.value.hint,
  },
  {
    label: '目标类别',
    value: latestItem.value?.category || '-',
    note: latestItem.value ? `置信度 ${(latestItem.value.confidence * 100).toFixed(1)}%` : '尚未收到目标类别。',
  },
  {
    label: '框坐标',
    value: latestItem.value?.bboxLabel || '-',
    note: latestItem.value?.bboxKind ? `使用 bbox_${latestItem.value.bboxKind}` : '暂无 bbox 数据。',
  },
  {
    label: '消息时间',
    value: detectionTime.value,
    note: payload.value?.frame_id ? `frame_id: ${payload.value.frame_id}` : '当前消息未附带 frame_id。',
  },
]);

const worldCoordinate = computed(() => {
  const world = latestTarget.value?.world_xyz;
  if (!Array.isArray(world) || world.length < 3) {
    return '-';
  }
  return world.map((value) => Number(value).toFixed(3)).join(', ');
});

const targetNote = computed(() => {
  if (!latestTarget.value) {
    return '等待 /topic/vision-targets 的桌面坐标候选。';
  }
  const pixel = latestTarget.value.pixel_center;
  const pixelLabel = Array.isArray(pixel) ? `像素中心 ${pixel.join(', ')}` : '像素中心未提供';
  return `${pixelLabel} -> world/table 坐标。`;
});

const sourceStatement = computed(() => {
  if (!payload.value) {
    return '当前还没有检测消息。';
  }
  if (sourceMeta.value.isReal) {
    return '当前检测来自真实 YOLO。';
  }
  if (sourceMeta.value.key === 'unknown') {
    return '当前无法确认是否来自真实 YOLO。';
  }
  return `当前检测不是来自真实 YOLO，而是${sourceMeta.value.label}。`;
});

const cameraCopy = computed(() => {
  if (!payload.value) {
    return '等待检测流接入。这里会展示最新视觉来源、目标摘要和坐标信息。';
  }
  if (sourceMeta.value.key === 'real_yolo') {
    return 'YOLO 节点在线后，这里展示的结果可被视为真实检测链路的最新一帧摘要。';
  }
  if (sourceMeta.value.key === 'gazebo_color_detector') {
    return '当前展示的是 Gazebo RGB 相机生成的仿真视觉结果，用于无真机阶段验证前端、后端和检测触发链。';
  }
  if (sourceMeta.value.key === 'demo_inject') {
    return '当前展示的是写入检测流的演示消息，只用于联调和讲解，不代表真实相机推理。';
  }
  if (sourceMeta.value.key === 'mock_yolo') {
    return '当前展示的是 mock_yolo 节点发布的测试消息，用于模拟联调，不代表真实 YOLO。';
  }
  return '消息已到达页面，但来源字段缺失，暂时无法确认它是否来自真实 YOLO。';
});

</script>

<template>
  <section class="vision-panel">
    <div class="section-head compact">
      <p class="eyebrow">Latest Return</p>
      <h2>最新回传</h2>
      <p class="vision-intro">首页只保留最新一条检测回传的来源、摘要和可解释状态，不再把视觉说明做成首屏主角。</p>
    </div>

    <div class="vision-summary-grid">
      <article class="vision-summary-card">
        <div class="vision-summary-head">
          <div>
            <span class="card-label">Source</span>
            <strong>{{ sourceMeta.label }}</strong>
          </div>
          <span class="source-pill" :class="sourceMeta.toneClass">{{ detectionTime }}</span>
        </div>
        <p>{{ sourceStatement }}</p>
      </article>

      <article class="vision-summary-card">
        <div class="vision-summary-head">
          <div>
            <span class="card-label">Detection</span>
            <strong>{{ detectionRows[1].value }}</strong>
          </div>
        </div>
        <p>{{ detectionRows[1].note }}</p>
        <div class="vision-summary-meta">
          <span>坐标</span>
          <strong>{{ detectionRows[2].value }}</strong>
        </div>
      </article>

      <article class="vision-summary-card">
        <div class="vision-summary-head">
          <div>
            <span class="card-label">Target</span>
            <strong>{{ worldCoordinate }}</strong>
          </div>
        </div>
        <p>{{ targetNote }}</p>
        <div class="vision-summary-meta">
          <span>坐标系</span>
          <strong>{{ visionTargetEntry?.payload?.target_frame || 'world' }}</strong>
        </div>
      </article>

      <article class="vision-summary-card">
        <div class="vision-summary-head">
          <div>
            <span class="card-label">Trace</span>
            <strong>{{ trace.command }}</strong>
          </div>
        </div>
        <p>{{ trace.commandNote }}</p>
        <div class="vision-summary-meta">
          <span>视觉结果</span>
          <strong>{{ trace.visual }}</strong>
        </div>
      </article>
    </div>

    <p class="vision-inline-note">{{ cameraCopy }}</p>
  </section>
</template>
