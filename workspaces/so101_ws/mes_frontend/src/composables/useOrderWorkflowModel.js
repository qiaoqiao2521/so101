import { computed, ref } from 'vue';
import { defaultBusyState } from './useSystemRuntimeModel.js';

export function useOrderWorkflowModel({
  api,
  pushEvent,
  busy = ref(defaultBusyState()),
}) {
  const orderId = ref(`order-${Date.now()}`);
  const actionTemplateId = ref('pick_place_default');
  const orders = ref([]);
  const activeOrderId = ref('');

  const selectedOrder = computed(() => {
    if (!activeOrderId.value) {
      return orders.value[0] || null;
    }
    return orders.value.find((item) => item.orderId === activeOrderId.value) || null;
  });

  function markBusy(key, value) {
    busy.value = { ...busy.value, [key]: value };
  }

  async function refreshOrders() {
    try {
      const payload = await api.fetchOrders();
      orders.value = payload;
      if (payload.length === 0) {
        activeOrderId.value = '';
        return payload;
      }
      if (!activeOrderId.value || !payload.some((item) => item.orderId === activeOrderId.value)) {
        activeOrderId.value = payload[0].orderId;
      }
      return payload;
    } catch (error) {
      pushEvent('error', '工单刷新失败', String(error.message || error));
      return [];
    }
  }

  async function createOrder() {
    markBusy('createOrder', true);
    try {
      const created = await api.createOrder({
        orderId: orderId.value,
        actionTemplateId: actionTemplateId.value,
      });
      activeOrderId.value = created.orderId;
      pushEvent('info', '工单已创建', `${created.orderId} -> ${created.actionTemplateId}`);
      await refreshOrders();
      return created;
    } catch (error) {
      pushEvent('error', '创建工单失败', String(error.message || error));
      return null;
    } finally {
      markBusy('createOrder', false);
    }
  }

  async function dispatchOrder(targetOrderId = '') {
    const selected = targetOrderId || activeOrderId.value || orderId.value;
    if (!selected) {
      pushEvent('warn', '无法下发', '缺少工单 ID');
      return null;
    }

    markBusy('dispatchOrder', true);
    try {
      const payload = await api.dispatchOrder(selected, { priority: 1 });
      activeOrderId.value = selected;
      pushEvent('info', '工单已下发', `${selected} / ${payload.requestId}`);
      await refreshOrders();
      return payload;
    } catch (error) {
      pushEvent('error', '下发工单失败', String(error.message || error));
      return null;
    } finally {
      markBusy('dispatchOrder', false);
    }
  }

  async function createAndDispatchOrder() {
    const created = await createOrder();
    if (created) {
      await dispatchOrder(created.orderId);
    }
  }

  async function injectDemoStatus() {
    const requestId = selectedOrder.value?.lastRequestId || `demo-${Date.now()}`;
    try {
      await api.postStatus({
        requestId,
        state: '执行中',
        code: 'STEP',
        message: 'demo -> status timeline',
        ts: Date.now(),
      });
      pushEvent('info', '已发送调试状态', '状态时间线已收到一条调试消息。');
      await refreshOrders();
    } catch (error) {
      pushEvent('error', '发送调试状态失败', String(error.message || error));
    }
  }

  async function injectDemoDetection(category) {
    try {
      await api.postDetection({
        source: 'demo_inject',
        count: 1,
        detections: [
          {
            category,
            confidence: 0.95,
            bbox_xyxy: [120, 80, 220, 180],
            bbox_xywh: [170, 130, 100, 100],
          },
        ],
        ts: Date.now(),
      });
      pushEvent('info', '已写入演示注入', `${category} 目标已写入检测流，但这不是实时 YOLO 推理。`);
    } catch (error) {
      pushEvent('error', '写入演示注入失败', String(error.message || error));
    }
  }

  function formatStamp(value) {
    if (!value) {
      return '-';
    }
    return new Date(Number(value)).toLocaleString('zh-CN', { hour12: false });
  }

  async function previewWorkbenchPose(payload) {
    markBusy('previewPose', true);
    try {
      const result = await api.previewPose(payload);
      pushEvent('info', '已发送调试姿态', `${payload.name} / ${result.requestId}`);
      return result;
    } catch (error) {
      pushEvent('error', '调试姿态下发失败', String(error.message || error));
      return null;
    } finally {
      markBusy('previewPose', false);
    }
  }

  async function saveWorkbenchExport(payload) {
    markBusy('saveWorkbench', true);
    try {
      const result = await api.saveExport(payload);
      pushEvent('info', '调试片段已保存', result.path);
      return result;
    } catch (error) {
      pushEvent('error', '保存调试片段失败', String(error.message || error));
      return null;
    } finally {
      markBusy('saveWorkbench', false);
    }
  }

  async function mergeWorkbenchWaypoints(payload) {
    markBusy('mergeWaypoints', true);
    try {
      const result = await api.mergeWaypoints(payload);
      pushEvent('info', '已合并到 waypoints.yaml', `${result.templateName} / backup=${result.backupPath}`);
      return result;
    } catch (error) {
      pushEvent('error', '合并 waypoints.yaml 失败', String(error.message || error));
      return null;
    } finally {
      markBusy('mergeWaypoints', false);
    }
  }

  return {
    orderId,
    actionTemplateId,
    orders,
    activeOrderId,
    selectedOrder,
    refreshOrders,
    createOrder,
    dispatchOrder,
    createAndDispatchOrder,
    injectDemoStatus,
    injectDemoDetection,
    previewWorkbenchPose,
    saveWorkbenchExport,
    mergeWorkbenchWaypoints,
    formatStamp,
  };
}
