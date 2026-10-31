<script setup>
import { computed } from 'vue';
import {
  describeRealHardwareGate,
  describeRealHardwareRefresh,
  describeRealHardwareSummary,
  describeRealHardwareStage,
  describeRecentHardwareIssue,
  describeRecentHardwareIssueSummary,
} from '../lib/realHardwareStatus.js';

const props = defineProps({
  realHardware: { type: Object, required: true },
});

const calibrationLabelMap = {
  UNCALIBRATED: '未校准',
  INVALID: '校准无效',
  CALIBRATED_NOT_HOMED: '已校准待回中',
  READY: '已校准',
};

const safetyLabelMap = {
  LOCKED: '保护锁定',
  PROTECTIVE_STOP: '保护停机',
  READY: '已放行',
};

const stageLabel = computed(() => describeRealHardwareStage(props.realHardware));
const summaryLabel = computed(() => describeRealHardwareSummary(props.realHardware));
const calibrationLabel = computed(
  () => calibrationLabelMap[props.realHardware.calibrationState] || '待校准',
);
const safetyLabel = computed(
  () => safetyLabelMap[props.realHardware.safetyState] || '保护锁定',
);
const gateMessage = computed(() => describeRealHardwareGate(props.realHardware));
const refreshLabel = computed(() => describeRealHardwareRefresh(props.realHardware));
const recentIssueLabel = computed(() => describeRecentHardwareIssue(props.realHardware));
const recentIssueSummaryLabel = computed(() => describeRecentHardwareIssueSummary(props.realHardware));
const safetyChecks = computed(() =>
  Array.isArray(props.realHardware.safetyChecks) ? props.realHardware.safetyChecks : [],
);
const pendingSafetyChecks = computed(() => safetyChecks.value.filter((item) => !item.ok).slice(0, 4));

const overviewItems = computed(() => [
  {
    label: '当前阶段',
    value: stageLabel.value,
    tone: props.realHardware.allowExecute ? 'hardware-good' : 'hardware-warn',
  },
  {
    label: '最近刷新',
    value: refreshLabel.value,
    tone: props.realHardware.updatedAt
      ? 'hardware-info'
      : props.realHardware.online
        ? 'hardware-warn'
        : 'hardware-muted',
  },
  {
    label: '最近异常',
    value: recentIssueSummaryLabel.value,
    tone: props.realHardware.estopActive
      ? 'hardware-error'
      : recentIssueSummaryLabel.value === '无异常'
        ? 'hardware-good'
        : recentIssueSummaryLabel.value === '待确认'
          ? 'hardware-muted'
          : 'hardware-warn',
  },
]);

const statusItems = computed(() => [
  {
    label: '接入状态',
    value: props.realHardware.online ? '已接入' : '待接入',
    tone: props.realHardware.online ? 'hardware-info' : 'hardware-muted',
  },
  {
    label: '上电状态',
    value: props.realHardware.powerState || '未上电',
    tone: props.realHardware.powerState === '已上电' ? 'hardware-info' : 'hardware-muted',
  },
  {
    label: '校准状态',
    value: calibrationLabel.value,
    tone: props.realHardware.calibrationState === 'READY' ? 'hardware-good' : 'hardware-warn',
  },
  {
    label: '保护状态',
    value: safetyLabel.value,
    tone: props.realHardware.safetyState === 'READY' ? 'hardware-good' : 'hardware-warn',
  },
  {
    label: '放行状态',
    value: props.realHardware.allowExecute ? '可演示' : '未放行',
    tone: props.realHardware.allowExecute ? 'hardware-good' : 'hardware-warn',
  },
]);

const showAlert = computed(() => recentIssueLabel.value !== '无');
</script>

<template>
  <section class="hardware-panel">
    <div class="hardware-panel-head">
      <div>
        <p class="eyebrow">Stitch Safety Gate</p>
        <h2>真机状态</h2>
        <p class="section-copy">这张卡只回答三件事：真机是否接入、当前停在哪一步、为什么还不能直接演示动作。</p>
      </div>
      <span class="status-badge">{{ summaryLabel }}</span>
    </div>

    <div class="hardware-status-row">
      <article v-for="item in overviewItems" :key="item.label" class="hardware-status-chip" :class="item.tone">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </article>
    </div>

    <div class="hardware-status-row">
      <article v-for="item in statusItems" :key="item.label" class="hardware-status-chip" :class="item.tone">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </article>
    </div>

    <div class="hardware-footer">
      <p>{{ gateMessage }}</p>
      <small>演示链路：{{ realHardware.controlInterface || '待接入' }}</small>
    </div>

    <div v-if="pendingSafetyChecks.length" class="hardware-status-row">
      <article
        v-for="item in pendingSafetyChecks"
        :key="item.key"
        class="hardware-status-chip"
        :class="item.ok ? 'hardware-good' : 'hardware-muted'"
      >
        <span>{{ item.label }}</span>
        <strong>{{ item.ok ? '已满足' : '待确认' }}</strong>
      </article>
    </div>

    <p v-if="showAlert" class="hardware-alert">最近异常：{{ recentIssueLabel }}</p>
  </section>
</template>
