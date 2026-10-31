import { computed, ref } from 'vue';
import { describeTaskStatus } from '../lib/demoNarration.js';
import { summarizeDetectionPayload } from '../lib/visionConsole.js';

function summarizeVisionTargetPayload(payload = {}) {
  const count = Number.isFinite(Number(payload?.count)) ? Number(payload.count) : payload?.targets?.length || 0;
  const categories = (payload?.targets || []).map((item) => item.category).filter(Boolean).join(', ');
  return categories ? `${count} 个桌面候选: ${categories}` : `${count} 个桌面候选`;
}

export function useRealtimeFeed({
  wsBase,
  rosbridgeConnected,
  connectRosbridge,
  refreshOrders,
  pushEvent,
  rememberStatusEvent,
  rememberDetection,
  rememberVisionTarget,
  rememberLeaderDebug,
  formatStamp,
}) {
  const socketState = ref('idle');
  const connectBusy = ref(false);
  let stompSocket = null;

  const socketLabel = computed(() => {
    return {
      idle: '未连接',
      connecting: '连接中',
      handshake: '握手中',
      connected: '已连接',
      error: '错误',
      closed: '已断开',
    }[socketState.value];
  });

  function sendFrame(command, headers = {}, body = '') {
    if (!stompSocket || stompSocket.readyState !== WebSocket.OPEN) {
      return;
    }
    const lines = [command];
    Object.entries(headers).forEach(([key, value]) => lines.push(`${key}:${value}`));
    lines.push('');
    lines.push(body);
    stompSocket.send(`${lines.join('\n')}\0`);
  }

  function parseFrames(raw) {
    return raw
      .split('\0')
      .map((frame) => frame.trim())
      .filter(Boolean)
      .map((frame) => {
        const [headerBlock, ...bodyParts] = frame.split('\n\n');
        const headerLines = headerBlock.split('\n');
        const command = headerLines[0];
        const headers = {};
        for (const line of headerLines.slice(1)) {
          const index = line.indexOf(':');
          if (index > 0) {
            headers[line.slice(0, index)] = line.slice(index + 1);
          }
        }
        return { command, headers, body: bodyParts.join('\n\n') };
      });
  }

  async function connectWs() {
    if (stompSocket && [WebSocket.OPEN, WebSocket.CONNECTING].includes(stompSocket.readyState)) {
      pushEvent('warn', '实时状态已连接', '无需重复连接');
      return;
    }

    connectBusy.value = true;
    try {
      if (!rosbridgeConnected.value) {
        await connectRosbridge();
      }

      socketState.value = 'connecting';
      stompSocket = new WebSocket(`${wsBase.value}/ws`);

      stompSocket.onopen = () => {
        socketState.value = 'handshake';
        sendFrame('CONNECT', {
          'accept-version': '1.2',
          'heart-beat': '0,0',
          host: '127.0.0.1',
        });
      };

      stompSocket.onmessage = async (event) => {
        for (const frame of parseFrames(event.data)) {
          if (frame.command === 'CONNECTED') {
            socketState.value = 'connected';
            pushEvent('success', '实时状态已连接', '/topic/task-status、/topic/detections、/topic/vision-targets 与 follower debug 已订阅');
            sendFrame('SUBSCRIBE', {
              id: 'task-status-sub',
              destination: '/topic/task-status',
            });
            sendFrame('SUBSCRIBE', {
              id: 'detections-sub',
              destination: '/topic/detections',
            });
            sendFrame('SUBSCRIBE', {
              id: 'vision-targets-sub',
              destination: '/topic/vision-targets',
            });
            sendFrame('SUBSCRIBE', {
              id: 'leader-status-sub',
              destination: '/topic/leader-status',
            });
            sendFrame('SUBSCRIBE', {
              id: 'leader-gazebo-status-sub',
              destination: '/topic/leader-gazebo-status',
            });
            sendFrame('SUBSCRIBE', {
              id: 'leader-joint-states-sub',
              destination: '/topic/leader-joint-states',
            });
            sendFrame('SUBSCRIBE', {
              id: 'gazebo-joint-states-sub',
              destination: '/topic/gazebo-joint-states',
            });
            sendFrame('SUBSCRIBE', {
              id: 'real-follower-status-sub',
              destination: '/topic/real-follower-status',
            });
            continue;
          }
          if (frame.command === 'MESSAGE') {
            const destination = frame.headers.destination || '';
            if (destination === '/topic/task-status') {
              try {
                const payload = JSON.parse(frame.body);
                const isHeartbeat = payload.heartbeat === true;
                rememberStatusEvent({
                  requestId: payload.requestId || '-',
                  state: payload.state || '-',
                  code: payload.code || '-',
                  message: payload.message || '',
                  summary: describeTaskStatus(payload),
                  time: formatStamp(payload.ts),
                  heartbeat: isHeartbeat,
                });
                if (!isHeartbeat) {
                  pushEvent('live', '状态回传', describeTaskStatus(payload));
                  await refreshOrders();
                }
              } catch {
                pushEvent('live', '状态回传', frame.body);
              }
              continue;
            }
            if (destination === '/topic/detections') {
              try {
                const payload = JSON.parse(frame.body);
                rememberDetection(payload);
                pushEvent('live', '检测回传', summarizeDetectionPayload(payload));
              } catch {
                pushEvent('warn', '检测消息解析失败', frame.body);
              }
              continue;
            }
            if (destination === '/topic/vision-targets') {
              try {
                const payload = JSON.parse(frame.body);
                rememberVisionTarget(payload);
                pushEvent('live', '目标坐标', summarizeVisionTargetPayload(payload));
              } catch {
                pushEvent('warn', '目标坐标解析失败', frame.body);
              }
              continue;
            }
            if (destination === '/topic/leader-status') {
              try {
                rememberLeaderDebug?.('leaderStatus', JSON.parse(frame.body));
              } catch {
                rememberLeaderDebug?.('leaderStatus', frame.body);
              }
              continue;
            }
            if (destination === '/topic/leader-gazebo-status') {
              try {
                rememberLeaderDebug?.('bridgeStatus', JSON.parse(frame.body));
              } catch {
                rememberLeaderDebug?.('bridgeStatus', frame.body);
              }
              continue;
            }
            if (destination === '/topic/leader-joint-states') {
              try {
                rememberLeaderDebug?.('leaderJointState', JSON.parse(frame.body));
              } catch {
                rememberLeaderDebug?.('leaderJointState', frame.body);
              }
              continue;
            }
            if (destination === '/topic/gazebo-joint-states') {
              try {
                rememberLeaderDebug?.('gazeboJointState', JSON.parse(frame.body));
              } catch {
                rememberLeaderDebug?.('gazeboJointState', frame.body);
              }
              continue;
            }
            if (destination === '/topic/real-follower-status') {
              try {
                rememberLeaderDebug?.('followerStatus', JSON.parse(frame.body));
              } catch {
                rememberLeaderDebug?.('followerStatus', frame.body);
              }
            }
            continue;
          }
          if (frame.command === 'ERROR') {
            socketState.value = 'error';
            pushEvent('error', 'STOMP 错误', frame.body || JSON.stringify(frame.headers));
          }
        }
      };

      stompSocket.onerror = () => {
        socketState.value = 'error';
        pushEvent('error', '实时状态连接失败', '请检查 backend /ws 与浏览器控制台');
      };

      stompSocket.onclose = () => {
        socketState.value = socketState.value === 'error' ? 'error' : 'closed';
        pushEvent('warn', '实时状态已断开', '如需继续联调请重新连接');
      };
    } finally {
      connectBusy.value = false;
    }
  }

  function closeWs() {
    if (stompSocket && [WebSocket.OPEN, WebSocket.CONNECTING].includes(stompSocket.readyState)) {
      stompSocket.close();
    }
    stompSocket = null;
  }

  return {
    socketState,
    socketLabel,
    connectBusy,
    connectWs,
    closeWs,
  };
}
