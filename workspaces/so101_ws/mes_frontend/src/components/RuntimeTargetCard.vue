<script setup>
const props = defineProps({
  runtimeTarget: { type: String, required: true },
  busy: { type: Boolean, default: false },
  simRunning: { type: Boolean, default: false },
  realHardware: { type: Object, default: () => ({}) },
});

const emit = defineEmits(['set-target']);

function runtimeTargetLabel(runtimeTarget) {
  if (runtimeTarget === 'real_hardware') {
    return '真机目标';
  }
  if (runtimeTarget === 'real_leader_to_gazebo') {
    return 'leader -> Gazebo';
  }
  return '仿真目标';
}
</script>

<template>
  <article class="action-card runtime-target-card">
    <div class="action-card-header">
      <div>
        <p class="eyebrow">Step 01</p>
        <h3>选择运行目标</h3>
      </div>
      <span class="status-badge">{{ runtimeTargetLabel(runtimeTarget) }}</span>
    </div>

    <div class="action-card-copy runtime-target-copy">
      <p>
        {{ runtimeTarget === 'real_hardware'
          ? '首页主链现在只认真机 READY / allowExecute，不再被仿真状态自动接管。'
          : runtimeTarget === 'real_leader_to_gazebo'
            ? '首页主链现在以 Gazebo 为执行体、实物 leader 为输入源；无 leader 输入时只做仿真侧准备。'
            : '首页主链现在只认 Gazebo 仿真状态，不再被真机 READY 状态抢占。' }}
      </p>
      <small>
        仿真运行: {{ simRunning ? '已启动' : '未启动' }} · 真机门禁:
        {{ realHardware.allowExecute || realHardware.safetyState === 'READY' ? 'READY' : (realHardware.safetyState || '未就绪') }}
      </small>
    </div>

    <div class="runtime-target-actions">
      <button
        class="secondary-action runtime-target-button"
        :class="{ 'runtime-target-button-active': runtimeTarget === 'simulation' }"
        :disabled="busy"
        @click="emit('set-target', 'simulation')"
      >
        使用仿真链
      </button>
      <button
        class="secondary-action runtime-target-button"
        :class="{ 'runtime-target-button-active': runtimeTarget === 'real_hardware' }"
        :disabled="busy"
        @click="emit('set-target', 'real_hardware')"
      >
        使用真机链
      </button>
      <button
        class="secondary-action runtime-target-button"
        :class="{ 'runtime-target-button-active': runtimeTarget === 'real_leader_to_gazebo' }"
        :disabled="busy"
        @click="emit('set-target', 'real_leader_to_gazebo')"
      >
        leader -> Gazebo
      </button>
    </div>
  </article>
</template>
