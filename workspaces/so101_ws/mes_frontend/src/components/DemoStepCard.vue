<script setup>
defineProps({
  step: { type: Object, required: true },
  eyebrow: { type: String, required: true },
  toneClass: { type: String, required: true },
  buttonClass: { type: String, required: true },
  busy: { type: Boolean, default: false },
  buttonLabel: { type: String, required: true },
});

const emit = defineEmits(['action']);
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
    <div class="step-action-row">
      <button class="step-action" :class="buttonClass" :disabled="!step.enabled || busy" @click="emit('action')">
        {{ buttonLabel }}
      </button>
      <span v-if="!step.enabled" class="step-reason">前置步骤未完成</span>
    </div>
  </article>
</template>
