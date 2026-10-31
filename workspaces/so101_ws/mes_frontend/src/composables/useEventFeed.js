import { ref } from 'vue';

export function useEventFeed() {
  const eventFeed = ref([]);
  const statusEvents = ref([]);
  const detections = ref([]);
  const visionTargets = ref([]);
  const leaderDebug = ref({
    leaderStatus: null,
    bridgeStatus: null,
    leaderJointState: null,
    gazeboJointState: null,
    followerStatus: null,
    updatedAt: null,
  });

  function pushEvent(type, title, detail) {
    eventFeed.value.unshift({
      id: `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
      type,
      title,
      detail,
      time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
    });
    eventFeed.value = eventFeed.value.slice(0, 18);
  }

  function rememberStatusEvent(payload) {
    if (payload?.heartbeat) {
      const existingIndex = statusEvents.value.findIndex((item) => {
        return item.requestId === payload.requestId && item.code === payload.code && item.message === payload.message;
      });
      if (existingIndex >= 0) {
        const next = [...statusEvents.value];
        next[existingIndex] = {
          ...next[existingIndex],
          ...payload,
          heartbeatCount: (next[existingIndex].heartbeatCount || 0) + 1,
        };
        statusEvents.value = next;
        return;
      }
    }

    statusEvents.value.unshift({
      id: `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
      heartbeatCount: payload?.heartbeat ? 1 : 0,
      ...payload,
    });
    statusEvents.value = statusEvents.value.slice(0, 12);
  }

  function rememberDetection(payload) {
    detections.value.unshift({
      id: `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
      payload,
      time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
    });
    detections.value = detections.value.slice(0, 10);
  }

  function rememberVisionTarget(payload) {
    visionTargets.value.unshift({
      id: `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
      payload,
      time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
    });
    visionTargets.value = visionTargets.value.slice(0, 10);
  }

  function rememberLeaderDebug(kind, payload) {
    const keyByKind = {
      leaderStatus: 'leaderStatus',
      bridgeStatus: 'bridgeStatus',
      leaderJointState: 'leaderJointState',
      gazeboJointState: 'gazeboJointState',
      followerStatus: 'followerStatus',
    };
    const key = keyByKind[kind];
    if (!key) {
      return;
    }
    leaderDebug.value = {
      ...leaderDebug.value,
      [key]: payload,
      updatedAt: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
    };
  }

  return {
    eventFeed,
    statusEvents,
    detections,
    visionTargets,
    leaderDebug,
    pushEvent,
    rememberStatusEvent,
    rememberDetection,
    rememberVisionTarget,
    rememberLeaderDebug,
  };
}
