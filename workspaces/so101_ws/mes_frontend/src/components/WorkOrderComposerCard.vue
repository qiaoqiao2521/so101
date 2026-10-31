<script setup>
import { computed } from 'vue';
import { actionTemplateOptions } from '../lib/actionTemplates.js';
import { formatOrderState } from '../lib/demoNarration.js';

const props = defineProps({
  statusLabel: { type: String, required: true },
  caption: { type: String, required: true },
  detail: { type: String, required: true },
  buttonLabel: { type: String, required: true },
  busy: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  orderId: { type: String, required: true },
  actionTemplateId: { type: String, required: true },
  selectedOrder: { type: Object, default: null },
});

const emit = defineEmits(['update:orderId', 'update:actionTemplateId', 'submit']);

const currentOrderNote = computed(() => {
  if (!props.selectedOrder) {
    return '还没有聚焦工单。当前主链就绪后，这里会直接发起本轮演示工单。';
  }
  return `当前聚焦：${props.selectedOrder.orderId} · ${formatOrderState(props.selectedOrder.state)}`;
});
</script>

<template>
  <article class="action-card action-card-order">
    <div class="action-card-header">
      <div>
        <p class="eyebrow">Step 03</p>
        <h3>创建并下发工单</h3>
      </div>
      <span class="status-badge">{{ statusLabel }}</span>
    </div>

    <div class="action-card-copy">
      <p>{{ caption }}</p>
      <small>{{ detail }}</small>
    </div>

    <div class="order-fields">
      <label>
        <span>工单 ID</span>
        <input :value="orderId" @input="emit('update:orderId', $event.target.value)" />
      </label>
      <label>
        <span>动作模板</span>
        <select :value="actionTemplateId" @change="emit('update:actionTemplateId', $event.target.value)">
          <option v-for="option in actionTemplateOptions" :key="option.id" :value="option.id">
            {{ option.label }}
          </option>
        </select>
      </label>
    </div>

    <p class="order-note">{{ currentOrderNote }}</p>

    <div class="action-card-foot">
      <button class="primary-action" :disabled="disabled || busy" @click="emit('submit')">
        {{ buttonLabel }}
      </button>
    </div>
  </article>
</template>
