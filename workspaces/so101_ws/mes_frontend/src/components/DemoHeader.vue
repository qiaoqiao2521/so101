<script setup>
defineProps({
  overallStateLabel: { type: String, required: true },
  overallStateTone: { type: String, required: true },
  drawerOpen: { type: Boolean, required: true },
});

const emit = defineEmits(['toggle-drawer']);
</script>

<template>
  <header class="topbar">
    <div class="brand-block">
      <p class="eyebrow">SO-101 MES DEMO CONSOLE</p>
      <h1>演示控制台</h1>
      <p class="subhead">默认页面只服务演示路径。系统维护和开发调试已经从主流程里拆开。</p>
    </div>
    <div class="header-actions">
      <div class="state-chip" :class="overallStateTone">
        <span class="chip-label">当前状态</span>
        <strong>{{ overallStateLabel }}</strong>
      </div>
      <button class="drawer-toggle" @click="emit('toggle-drawer')">
        {{ drawerOpen ? '收起系统工具' : '系统工具' }}
      </button>
    </div>
  </header>
</template>
