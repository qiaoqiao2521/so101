<script setup>
import { formatOrderState, formatStatusCode, summarizeOrderMessage } from '../lib/demoNarration.js';

defineProps({
  selectedOrder: { type: Object, default: null },
  formatStamp: { type: Function, required: true },
  statusTone: { type: Function, required: true },
});
</script>

<template>
  <section class="focus-panel">
    <div class="section-head compact">
      <p class="eyebrow">工单追踪</p>
      <h2>当前工单</h2>
    </div>
    <div v-if="selectedOrder" class="focused-card" :class="statusTone(selectedOrder.state)">
      <div class="focused-head">
        <strong>{{ selectedOrder.orderId }}</strong>
        <span class="state-pill" :class="statusTone(selectedOrder.state)">{{ formatOrderState(selectedOrder.state) }}</span>
      </div>
      <p class="order-summary">{{ summarizeOrderMessage(selectedOrder) }}</p>
      <dl>
        <div>
          <dt>动作模板</dt>
          <dd>{{ selectedOrder.actionTemplateId }}</dd>
        </div>
        <div>
          <dt>请求 ID</dt>
          <dd>{{ selectedOrder.lastRequestId || '-' }}</dd>
        </div>
        <div>
          <dt>结果代码</dt>
          <dd>{{ formatStatusCode(selectedOrder.lastStatusCode) }}</dd>
        </div>
        <div>
          <dt>最近更新时间</dt>
          <dd>{{ formatStamp(selectedOrder.updatedAt) }}</dd>
        </div>
      </dl>
    </div>
    <div v-else class="empty-card">
      <strong>暂无工单</strong>
      <p>接通当前主链后，就可以直接创建并下发工单。</p>
    </div>
  </section>
</template>
