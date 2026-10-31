<script setup>
defineProps({
  drawerOpen: { type: Boolean, required: true },
  developerToolsEnabled: { type: Boolean, default: false },
  rosbridgeConnected: { type: Boolean, required: true },
  socketLabel: { type: String, required: true },
  systemToolMetrics: { type: Array, required: true },
  systemBusy: { type: Object, required: true },
});

const emit = defineEmits([
  'close',
  'open-rviz',
  'stop-sim',
  'refresh-system',
  'open-developer-page',
]);
</script>

<template>
  <transition name="drawer-fade">
    <aside v-if="drawerOpen" class="advanced-drawer">
      <div class="drawer-head">
        <div>
          <p class="eyebrow">System Tools</p>
          <h2>演示维护</h2>
          <p class="drawer-copy">这里只保留演示过程里的必要维护动作。开发联调、样本注入和姿态工作台已经拆成独立二级页。</p>
        </div>
        <button class="drawer-close" @click="emit('close')">关闭</button>
      </div>

      <section class="drawer-section">
        <div class="section-head compact">
          <p class="eyebrow dark-eyebrow">Maintenance Snapshot</p>
          <h3>当前维护状态</h3>
        </div>
        <div class="tool-summary-grid">
          <article v-for="item in systemToolMetrics" :key="item.label" class="tool-status-card" :class="item.tone">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </article>
        </div>
      </section>

      <section class="drawer-section">
        <div class="section-head compact">
          <p class="eyebrow dark-eyebrow">Maintenance Actions</p>
          <h3>演示维护</h3>
        </div>
        <div class="drawer-actions">
          <button class="subtle-action" @click="emit('refresh-system')">重新读取状态</button>
          <button class="subtle-action" :disabled="systemBusy.openRviz" @click="emit('open-rviz')">{{ systemBusy.openRviz ? '打开中...' : '打开 RViz 观察' }}</button>
          <button class="subtle-action danger-action" :disabled="systemBusy.stopSim" @click="emit('stop-sim')">{{ systemBusy.stopSim ? '结束中...' : '结束本轮演示' }}</button>
        </div>

        <div class="tool-note-panel">
          <article class="tool-note">
            <strong>普通使用</strong>
            <p>优先按首页三步流操作。这里仅用于恢复观察、确认状态和安全收尾。</p>
          </article>
          <article class="tool-note">
            <strong>rosbridge</strong>
            <p>{{ rosbridgeConnected ? 'backend 已连接 rosbridge。' : '当前未连接 rosbridge，请先回到主流程完成实时连接。' }}</p>
          </article>
          <article class="tool-note">
            <strong>实时状态</strong>
            <p>{{ socketLabel }}。若出现异常，先重新读取状态，再决定是否结束本轮演示。</p>
          </article>
        </div>
      </section>

      <section class="drawer-section">
        <div class="developer-gate">
          <div>
            <p class="eyebrow dark-eyebrow">Developer Workspace</p>
            <h3>开发能力已迁移</h3>
            <p class="empty-note">
              调试浏览器、样本注入、姿态工作台和原始检测流已经迁移到独立二级页。
              <template v-if="developerToolsEnabled">点击下方按钮进入开发工作台。</template>
            </p>
          </div>
          <span class="developer-tag">{{ developerToolsEnabled ? '二级页' : '隐藏中' }}</span>
        </div>

        <div v-if="developerToolsEnabled" class="drawer-actions">
          <button class="subtle-action" @click="emit('open-developer-page')">进入开发工作台</button>
        </div>
      </section>
    </aside>
  </transition>
</template>
