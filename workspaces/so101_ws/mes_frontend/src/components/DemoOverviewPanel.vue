<script setup>
defineProps({
  primaryPrompt: { type: String, required: true },
  primaryPromptDetail: { type: String, required: true },
  overallStateTone: { type: String, required: true },
  overviewMetrics: { type: Array, required: true },
});
</script>

<template>
  <section class="overview-panel">
    <div class="prompt-banner" :class="overallStateTone">
      <span class="prompt-label">下一步操作提示</span>
      <strong>{{ primaryPrompt }}</strong>
      <p class="prompt-detail">{{ primaryPromptDetail }}</p>
    </div>

    <div class="overview-grid">
      <article v-for="item in overviewMetrics" :key="item.label" class="overview-card" :class="item.tone">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </article>
    </div>
  </section>
</template>
