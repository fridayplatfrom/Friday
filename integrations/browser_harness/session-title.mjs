// Harness names sessions concurrently with the agent turn. Metadata must never
// occupy the interactive website conversation or change its connection status.
export function localSessionTitle(options) {
  const messages = options.messages || [];
  if (!messages.some(message => message.source?.kind === 'dsh-session-title-llm')) return null;
  const request = messages.find(message => message.source?.kind === 'dsh-session-title-llm');
  const text = (request.content || []).filter(block => block.type === 'text').map(block => block.text).join('\n');
  let humanText = '';
  try {
    const array = JSON.parse(text.slice(text.indexOf('[')));
    humanText = array.find(message => typeof message.text === 'string' && message.text.trim())?.text || '';
  } catch { /* Malformed metadata falls back locally; never send it to the website. */ }
  const clean = humanText.normalize('NFC').replace(/[\p{Cc}\p{Cf}]/gu, ' ').replace(/[`#*_<>\[\]{}]/g, '').replace(/\s+/g, ' ').trim();
  return Array.from(clean.split(' ').slice(0, 5).join(' ') || 'New conversation').slice(0, 72).join('');
}
