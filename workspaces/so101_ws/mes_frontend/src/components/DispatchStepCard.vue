<script setup>
import { actionTemplateOptions } from '../lib/actionTemplates.js';

defineProps({
  step: { type: Object, required: true },
  eyebrow: { type: String, required: true },
  toneClass: { type: String, required: true },
  actionTemplateId: { type: String, required: true },
  orderId: { type: String, required: true },
  busyCreate: { type: Boolean, default: false },
  busyDispatch: { type: Boolean, default: false },
  busyDance: { type: Boolean, default: false },
  primaryLabel: { type: String, required: true },
});

const emit = defineEmits(['update:actionTemplateId', 'update:orderId', 'create', 'create-and-dispatch', 'dance-demo']);
</script>

<template>
  <article class="step-card" :class="toneClass" :data-step-key="step.key">
    <div class="step-index">{{ eyebrow }}</div>
    <div class="step-body">
      <div class="step-copy">
        <h3>{{ step.title }}</h3>
        <p>{{ step.caption }}</p>
      </div>
      <span class="step-status">{{ step.status }}</span>
    </div>
    <p class="step-hint">{{ step.hint }}</p>

    <div class="dispatch-box">
      <div class="dispatch-fields">
        <label>
          <span>动作模板</span>
          <select :value="actionTemplateId" @change="emit('update:actionTemplateId', $event.target.value)">
            <option v-for="option in actionTemplateOptions" :key="option.id" :value="option.id">
              {{ option.label }}
            </option>
          </select>
        </label>
        <label>
          <span>工单 ID</span>
          <input :value="orderId" type="text" @input="emit('update:orderId', $event.target.value)" />
        </label>
      </div>
      <div class="dispatch-actions">
        <button class="step-action primary-action" :disabled="!step.enabled || busyCreate || busyDispatch" @click="emit('create-and-dispatch')">
          {{ primaryLabel }}
        </button>
        <button class="step-action subtle-action" :disabled="!step.enabled || busyCreate" @click="emit('create')">
          {{ busyCreate ? '创建中...' : '仅创建工单' }}
        </button>
        <button class="step-action accent-action" :disabled="!step.enabled || busyCreate || busyDispatch || busyDance" @click="emit('dance-demo')">
          {{ busyDance ? '起舞中...' : '播放音乐并起舞' }}
        </button>
      </div>
      <span v-if="!step.enabled" class="step-reason">建议先完成实时状态连接</span>
    </div>
  </article>
</template>
