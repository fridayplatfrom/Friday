/** Decode backend SSE incrementally, including split UTF-8 and SSE frames. */
export async function* readHarnessStream(response, signal) {
  if (!response.body) throw new Error('Tiny Expert OS returned no stream body');
  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8', { fatal: true });
  let pending = '';
  let finished = false;
  function parse(frame) {
    const data = frame.split('\n').filter(line => line.startsWith('data:'))
      .map(line => line.slice(5).replace(/^ /, '')).join('\n');
    if (!data) return null;
    const chunk = JSON.parse(data);
    if (chunk.type === 'error') throw new Error(chunk.message || 'Local expert request failed');
    if (typeof chunk.type !== 'string') throw new Error('Invalid Tiny Expert OS stream event');
    return chunk;
  }
  try {
    while (!finished) {
      signal?.throwIfAborted();
      const { value, done } = await reader.read();
      pending += done ? decoder.decode() : decoder.decode(value, { stream: true });
      pending = pending.replace(/\r\n/g, '\n');
      let end;
      while ((end = pending.indexOf('\n\n')) >= 0) {
        const frame = pending.slice(0, end);
        pending = pending.slice(end + 2);
        const chunk = parse(frame);
        if (!chunk) continue;
        signal?.throwIfAborted();
        if (chunk.type === 'finish') finished = true;
        yield chunk;
        if (finished) break;
      }
      if (pending.length > 1024 * 1024) throw new Error('Oversized Tiny Expert OS stream frame');
      if (done && !finished) throw new Error('Tiny Expert OS stream ended before finish');
    }
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
