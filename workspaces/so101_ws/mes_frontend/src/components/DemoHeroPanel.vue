<script setup>
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref } from 'vue';

const LightArmPreview = defineAsyncComponent(() => import('./LightArmPreview.vue'));

defineProps({
  overallStateLabel: { type: String, required: true },
  overallStateTone: { type: String, required: true },
  primaryPrompt: { type: String, required: true },
  primaryPromptDetail: { type: String, required: true },
  heroMetrics: { type: Array, required: true },
  drawerOpen: { type: Boolean, required: true },
});

const emit = defineEmits(['toggle-drawer', 'start-runtime', 'enter-workspace']);

const currentTime = ref(new Date());
let timerId = null;

const heroPreviewPose = computed(() => {
  const seconds = currentTime.value.getSeconds() + currentTime.value.getMilliseconds() / 1000;
  return {
    id: 'hero-live-preview',
    name: 'live_command_pose',
    durationMs: 1200,
    joints: {
      shoulder_panDeg: Math.sin(seconds * 0.42) * 32,
      shoulder_liftDeg: -18 + Math.sin(seconds * 0.32) * 16,
      elbow_flexDeg: 34 + Math.cos(seconds * 0.38) * 22,
      wrist_flexDeg: -16 + Math.sin(seconds * 0.52) * 26,
      wrist_rollDeg: Math.cos(seconds * 0.48) * 42,
      gripper: 0.48 + (Math.sin(seconds * 0.72) + 1) * 0.22,
    },
  };
});

onMounted(() => {
  timerId = window.setInterval(() => {
    currentTime.value = new Date();
  }, 1000);
});

onBeforeUnmount(() => {
  if (timerId) {
    window.clearInterval(timerId);
    timerId = null;
  }
});
</script>

<template>
  <section class="figmake-hero-stack fade-up fade-up-1">
    <div class="panel figmake-hero-panel">
      <span class="corner-mark tl" />
      <span class="corner-mark tr" />
      <span class="corner-mark bl" />
      <span class="corner-mark br" />

      <div class="figmake-hero-copy">
        <div class="figmake-mission-line">
          <span />
          <strong>// MISSION 0426 / NEXT ACTION</strong>
        </div>
        <h2>
          {{ primaryPrompt }}<br />
          <span>►</span> SO-ARM101 实时链路
        </h2>
        <p>{{ primaryPromptDetail }}</p>

        <div class="figmake-hero-mini-metrics">
          <article v-for="item in heroMetrics.slice(0, 3)" :key="item.label" class="panel-flat">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <small>● {{ item.meta }}</small>
          </article>
        </div>

        <div class="figmake-hero-actions">
          <button class="btn-primary" :disabled="overallStateTone === 'tone-ready'" @click="emit('start-runtime')">START SIMULATION</button>
          <button class="btn-secondary" @click="emit('enter-workspace')">ENTER WORKSPACE</button>
          <span>↳ {{ overallStateLabel }}</span>
        </div>
      </div>

      <div class="figmake-hero-arm">
        <div class="figmake-ring-wrap" aria-hidden="true">
          <svg class="ring-rot" width="320" height="320" viewBox="0 0 320 320">
            <circle cx="160" cy="160" r="150" fill="none" stroke="var(--cyan)" stroke-opacity="0.2" stroke-width="0.6" stroke-dasharray="3 6" />
            <circle cx="310" cy="160" r="2" fill="var(--cyan)" />
            <circle cx="235" cy="290" r="2" fill="var(--cyan)" />
            <circle cx="85" cy="290" r="2" fill="var(--cyan)" />
            <circle cx="10" cy="160" r="2" fill="var(--cyan)" />
            <circle cx="85" cy="30" r="2" fill="var(--cyan)" />
            <circle cx="235" cy="30" r="2" fill="var(--cyan)" />
          </svg>
          <svg class="ring-rot-rev" width="260" height="260" viewBox="0 0 260 260">
            <circle cx="130" cy="130" r="120" fill="none" stroke="var(--amber)" stroke-opacity="0.25" stroke-width="0.6" stroke-dasharray="1 8" />
          </svg>
        </div>
        <div class="hero-arm-stage arm-float" aria-label="SO101 virtual arm preview">
          <div class="hero-arm-head">
            <span>THREE.JS LIVE ARM</span>
            <strong>SO-ARM101 / R2.6</strong>
          </div>
          <LightArmPreview :pose="heroPreviewPose" />
        </div>
        <div class="chip chip-cyan figmake-live-chip"><span class="glow-dot" /> LIVE TELEMETRY</div>
        <div class="chip chip-mute figmake-model-chip">MODEL: SO-ARM101 / R2.6</div>
      </div>
    </div>

    <div class="figmake-metrics-row">
      <article v-for="(item, index) in heroMetrics" :key="item.label" class="panel figmake-metric-card fade-up" :class="`fade-up-${(index % 6) + 1}`">
        <span class="corner-mark tr" />
        <header>
          <div>
            <i class="pulse-dot" />
            <span>{{ item.label }}</span>
          </div>
          <small>#{{ String(index + 1).padStart(2, '0') }}</small>
        </header>
        <strong>{{ item.value }}</strong>
        <div class="figmake-progress">
          <div class="prog-bar" :style="{ width: `${item.progress ?? 0}%`, '--c1': 'var(--primary)', '--c2': 'var(--cyan)', '--glow': 'rgba(123,108,201,0.42)' }" />
        </div>
        <footer>
          <span>▲ LIVE</span>
          <span>{{ item.progress ?? 0 }}%</span>
        </footer>
      </article>
    </div>
  </section>
</template>
