<script setup>
defineProps({
  statusLabel: { type: String, required: true },
  caption: { type: String, required: true },
  detail: { type: String, required: true },
  buttonLabel: { type: String, required: true },
  busy: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  socketLabel: { type: String, required: true },
  rosbridgeConnected: { type: Boolean, required: true },
});

const emit = defineEmits(['action']);
</script>

<template>
  <article class="action-card action-card-live">
    <div class="action-card-header">
      <div>
        <p class="eyebrow">Step 02</p>
        <h3>连接实时状态</h3>
      </div>
      <span class="status-badge">{{ statusLabel }}</span>
    </div>

    <div class="action-card-copy">
      <p>{{ caption }}</p>
      <small>{{ detail }}</small>
    </div>

    <div class="signal-row">
      <span class="signal-chip">{{ rosbridgeConnected ? 'rosbridge connected' : 'rosbridge offline' }}</span>
      <span class="signal-chip">{{ socketLabel }}</span>
    </div>

    <div class="action-card-foot">
      <button class="secondary-action" :disabled="disabled || busy" @click="emit('action')">
        {{ buttonLabel }}
      </button>
    </div>
  </article>
</template>
