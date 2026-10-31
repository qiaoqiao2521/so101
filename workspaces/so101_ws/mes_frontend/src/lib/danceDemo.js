export const DANCE_TEMPLATE_ID = 'dance_demo';

export function buildDanceOrderId(now = () => Date.now()) {
  return `dance-${now()}`;
}

export function createDanceDemoRunner({
  now = () => Date.now(),
  setActionTemplateId,
  setOrderId,
  playAudio,
  createAndDispatchOrder,
  pushEvent,
}) {
  return async function runDanceDemo() {
    const orderId = buildDanceOrderId(now);
    setActionTemplateId(DANCE_TEMPLATE_ID);
    setOrderId(orderId);

    try {
      await playAudio();
    } catch (error) {
      pushEvent?.('warn', '音乐播放失败', String(error?.message || error));
    }

    await createAndDispatchOrder();
    pushEvent?.('info', '音乐舞蹈演示已启动', `${orderId} -> ${DANCE_TEMPLATE_ID}`);
    return orderId;
  };
}
