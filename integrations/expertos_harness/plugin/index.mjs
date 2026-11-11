/** Official DeepSeek Harness Cordis plugin entrypoint. */
import { defineTool } from '@deepseek-ai/dsh-tools';
import { ExpertBridgeClient } from './transport.mjs';
import { registerExpertTools } from './tools.mjs';

export const name = 'expertos-harness';
export const inject = ['tools'];

export function apply(ctx) {
  const token = process.env.EXPERTOS_BRIDGE_TOKEN;
  const client = new ExpertBridgeClient({ token, baseUrl: process.env.EXPERTOS_BRIDGE_URL || 'http://127.0.0.1:8765' });
  const allowHosts = (process.env.EXPERTOS_ALLOWED_HOSTS || '').split(',').map(s => s.trim().toLowerCase()).filter(Boolean);
  // Never enable test loopback in production plugin; tests inject it directly.
  registerExpertTools(ctx, defineTool, client, { allowHosts, allowTestLoopback: false });
}
