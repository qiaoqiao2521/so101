<script setup>
import { computed } from 'vue';

const props = defineProps({
  detections: { type: Array, required: true },
});

const latestEntry = computed(() => props.detections[0] || null);
const latestCount = computed(() => {
  const payload = latestEntry.value?.payload;
  return payload?.count ?? payload?.detections?.length ?? 0;
});
const latestCategories = computed(() => {
  const labels = (latestEntry.value?.payload?.detections || [])
    .map((item) => item.category)
    .filter(Boolean);
  return labels.length ? labels : [];
});

function summarizeEntry(entry) {
  const detections = entry.payload?.detections || [];
  if (detections.length === 0) {
    return '收到检测消息，但当前 payload 未携带目标明细。';
  }

  return detections
    .map((item) => {
      const confidence = typeof item.confidence === 'number' ? `${Math.round(item.confidence * 100)}%` : '-';
      return `${item.category || 'unknown'} · ${confidence}`;
    })
    .join(' / ');
}
</script>

<template>
  <section class="vision-panel">
    <div class="section-head compact">
      <p class="eyebrow">Vision Results</p>
      <h2>检测结果</h2>
    </div>

    <div v-if="latestEntry" class="vision-hero">
      <div>
        <span class="vision-label">最新回传</span>
        <strong>{{ latestCount }} 个目标</strong>
        <p>{{ latestCategories.length ? latestCategories.join(' · ') : '当前消息未携带类别标签' }}</p>
      </div>
      <span class="vision-time">{{ latestEntry.time }}</span>
    </div>

    <div v-else class="empty-card">
      <strong>视觉结果待接入</strong>
      <p>完成实时状态连接后，最新检测回传会直接出现在这里。</p>
    </div>

    <div class="vision-stream">
      <article v-for="entry in detections.slice(0, 4)" :key="entry.id" class="vision-item">
        <header>
          <strong>{{ entry.payload.count ?? entry.payload.detections?.length ?? 0 }} detections</strong>
          <span>{{ entry.time }}</span>
        </header>
        <p>{{ summarizeEntry(entry) }}</p>
      </article>
    </div>
  </section>
</template>
