<script setup>
defineProps({
  eyebrow: { type: String, default: 'Step 02' },
  title: { type: String, default: '启动仿真' },
  statusLabel: { type: String, required: true },
  caption: { type: String, required: true },
  detail: { type: String, required: true },
  buttonLabel: { type: String, required: true },
  busy: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
});

const emit = defineEmits(['action']);
</script>

<template>
  <article class="action-card action-card-runtime">
    <div class="action-card-header">
      <div>
        <p class="eyebrow">{{ eyebrow }}</p>
        <h3>{{ title }}</h3>
      </div>
      <span class="status-badge">{{ statusLabel }}</span>
    </div>

    <div class="action-card-copy">
      <p>{{ caption }}</p>
      <small>{{ detail }}</small>
    </div>

    <div class="action-card-foot">
      <button class="primary-action" :disabled="disabled || busy" @click="emit('action')">
        {{ buttonLabel }}
      </button>
    </div>
  </article>
</template>
