<script setup>
import { formatOrderState, formatStatusCode } from '../lib/demoNarration.js';

defineProps({
  statusEvents: { type: Array, required: true },
});
</script>

<template>
  <section class="status-panel compact-panel">
    <div class="section-head compact">
      <p class="eyebrow">状态回传</p>
      <h2>状态时间线</h2>
    </div>
    <div class="status-list">
      <article v-for="item in statusEvents" :key="item.id" class="status-item">
        <header>
          <strong>{{ formatOrderState(item.state) }} / {{ formatStatusCode(item.code) }}</strong>
          <span>{{ item.time }}</span>
        </header>
        <p>{{ item.summary || item.message }}</p>
        <small>请求 ID：{{ item.requestId }}</small>
      </article>
      <p v-if="statusEvents.length === 0" class="empty-note">尚未收到结构化状态流。</p>
    </div>
  </section>
</template>
