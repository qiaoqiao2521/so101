import { ref } from 'vue';
import { createOrdersApi } from '../api/ordersApi.js';
import { createRosApi } from '../api/rosApi.js';
import { createSystemApi } from '../api/systemApi.js';
import { createWorkbenchApi } from '../api/workbenchApi.js';
import { defaultBusyState, useSystemRuntimeModel } from './useSystemRuntimeModel.js';
import { useOrderWorkflowModel } from './useOrderWorkflowModel.js';

export function useMesBackend(apiBase, { pushEvent, fetchImpl = globalThis.fetch }) {
  const systemBusy = ref(defaultBusyState());
  const systemApi = createSystemApi(apiBase, { fetchImpl });
  const ordersApi = createOrdersApi(apiBase, { fetchImpl });
  const rosApi = createRosApi(apiBase, { fetchImpl });
  const workbenchApi = createWorkbenchApi(apiBase, { fetchImpl });

  const orderWorkflow = useOrderWorkflowModel({
    api: {
      ...ordersApi,
      ...rosApi,
      ...workbenchApi,
    },
    pushEvent,
    busy: systemBusy,
  });

  const systemRuntime = useSystemRuntimeModel({
    api: {
      ...systemApi,
      fetchRosbridgeHealth: rosApi.fetchHealth,
      connectRosbridge: rosApi.connectRosbridge,
    },
    pushEvent,
    busy: systemBusy,
    afterSystemAction: orderWorkflow.refreshOrders,
  });

  return {
    ...orderWorkflow,
    rosbridgeConnected: systemRuntime.rosbridgeConnected,
    systemStatus: systemRuntime.systemStatus,
    systemBusy,
    refreshOrders: orderWorkflow.refreshOrders,
    refreshRosbridgeHealth: systemRuntime.refreshRosbridgeHealth,
    refreshSystemStatus: systemRuntime.refreshSystemStatus,
    startSimulation: systemRuntime.startSimulation,
    openRviz: systemRuntime.openRviz,
    stopSimulation: systemRuntime.stopSimulation,
    openBrowser: systemRuntime.openBrowser,
    stopBrowser: systemRuntime.stopBrowser,
    setRuntimeTarget: systemRuntime.setRuntimeTarget,
    connectRosbridge: systemRuntime.connectRosbridge,
    fetchLatestVisionQuality: workbenchApi.fetchLatestVisionQuality,
  };
}
