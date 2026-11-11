/** Restore a known conversation through Harness's Session domain; never submit work. */
export function sessionRecovery(bridge, controller) {
  const pending = new Map();
  return (sessionId) => {
    if (typeof sessionId !== 'string' || !bridge.sessions.get(sessionId)) return Promise.reject(new Error('Unknown saved Friday conversation.'));
    if (pending.has(sessionId)) return pending.get(sessionId);
    const operation = (async () => {
      const inspection = await controller.inspect(sessionId);
      if (inspection.meta?.origin === 'subagent') throw new Error('Subagent conversations use native subagent recovery.');
      let selection;
      for (const event of inspection.events || []) {
        if (event.type === 'request/header') selection = event.data?.header?.config;
        if (event.type === 'model/selection') selection = event.data;
      }
      if (selection?.provider !== 'browser-web') throw new Error('This conversation is not using a Friday browser model.');
      const result = await controller.resolveAgent(sessionId);
      if (result.error) throw result.error;
      if (!result.agent || result.agent.id !== sessionId) throw new Error('Native conversation restoration did not return the saved identity.');
      return {ok:true, sessionId, loaded:true, status:result.agent.status, provider:selection.provider, model:selection.model, replayed:false};
    })().finally(() => { if (pending.get(sessionId) === operation) pending.delete(sessionId); });
    pending.set(sessionId, operation);
    return operation;
  };
}
