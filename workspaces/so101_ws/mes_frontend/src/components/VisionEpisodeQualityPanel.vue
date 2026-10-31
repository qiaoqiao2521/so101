<script setup>
import { computed } from 'vue';
import {
  buildVisionEpisodeQualityCards,
  normalizeVisionEpisodeQuality,
} from '../lib/visionEpisodeQuality.js';

const props = defineProps({
  quality: { type: Object, default: null },
  statusEvents: { type: Array, default: () => [] },
});

const model = computed(() => normalizeVisionEpisodeQuality(props.quality, { statusEvents: props.statusEvents }));
const cards = computed(() => buildVisionEpisodeQualityCards(model.value));
const candidatePath = computed(() => model.value.candidateManifestPath || '等待 candidate manifest 注入');
const nativeBlockedReason = computed(() => {
  if (model.value.nativeLeRobotAvailable) {
    return model.value.nativeLeRobotPath || 'native LeRobot dataset ready';
  }
  return model.value.nativeLeRobotBlockedReason || '等待 native LeRobot probe 结果注入';
});
const yoloSmokeSummary = computed(() => {
  if (model.value.yoloSmokeStatus === 'passed') {
    return model.value.yoloSmokePath || model.value.yoloBestWeightPath || 'YOLO train/predict smoke done';
  }
  return '等待 YOLO smoke report 注入';
});
</script>

<template>
  <section class="developer-panel vision-quality-panel">
    <div class="section-head compact-head">
      <p class="eyebrow dark-eyebrow">Vision Episode Quality</p>
      <h3>采集质量面板</h3>
    </div>
    <p class="empty-note">
      展示最近一次采集的校验、数据集转换与时间同步结果；没有报告的项目保持待检查。
    </p>

    <div class="vision-quality-head">
      <div>
        <span>最近 episode</span>
        <strong>{{ model.episodeId || '等待注入' }}</strong>
      </div>
      <span class="quality-pill" :class="`quality-${model.datasetValidationStatus}`">
        {{ model.datasetValidationLabel }}
      </span>
    </div>

    <div class="vision-quality-grid">
      <article v-for="card in cards" :key="card.label" class="vision-quality-card" :class="card.tone">
        <span>{{ card.label }}</span>
        <strong>{{ card.value }}</strong>
        <small>{{ card.note }}</small>
      </article>
    </div>

    <dl class="runtime-grid vision-quality-paths">
      <div>
        <dt>candidate manifest</dt>
        <dd>{{ candidatePath }}</dd>
      </div>
      <div>
        <dt>native LeRobot</dt>
        <dd>{{ nativeBlockedReason }}</dd>
      </div>
      <div>
        <dt>YOLO smoke</dt>
        <dd>{{ yoloSmokeSummary }}</dd>
      </div>
    </dl>

    <p v-if="!model.hasData" class="empty-note">
      暂未取得完整采集报告。请先完成一次采集并生成质量报告，再刷新查看；当前连接状态不代表数据已经通过校验。
    </p>
  </section>
</template>
