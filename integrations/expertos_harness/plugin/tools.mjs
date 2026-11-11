import { runBrowserWorkflow } from './browser.mjs';

/** Harness tool declarations; depend only on public defineTool API. */
export function registerExpertTools(ctx, defineTool, client, options = {}) {
  const common = (name, description, parameters, path, body) => {
    ctx.tools.register(defineTool({
      name, description, parameters,
      output: { schema: { type: 'string' }, render: (_args, result) => [{ type: 'text', text: result }] },
      async execute(args, exec) {
        return JSON.stringify(await client.request(path, body(args), exec?.signal));
      },
    }));
  };
  common('expertos_experts', 'List available ExpertOS specialists and trained/untrained status.', {}, '/v1/experts', () => undefined);
  common('expertos_route', 'Select a bounded expert for a task. Abstains on unfamiliar requests.', {
    task: { type: 'string', required: true },
  }, '/v1/route', x => x);
  common('expertos_plan', 'Create a bounded website navigation, extraction, or fill-form plan. Does not execute.', {
    kind: { type: 'string', required: true }, url: { type: 'string', required: true },
  }, '/v1/plan', x => x);
  common('expertos_form_map', 'Match supplied keys to observed input controls; ambiguous controls abstain.', {
    controls_json: { type: 'string', required: true }, values_json: { type: 'string', required: true },
  }, '/v1/form/map', x => ({ controls: JSON.parse(x.controls_json), values: JSON.parse(x.values_json) }));
  common('expertos_form_verify', 'Compare expected vs actual form state; do not assume a click means success.', {
    expected_json: { type: 'string', required: true }, actual_json: { type: 'string', required: true },
  }, '/v1/form/verify', x => ({ expected: JSON.parse(x.expected_json), actual: JSON.parse(x.actual_json) }));
  common('expertos_propose_action', 'Ask an optional experimental neural model to propose a browser action; does not execute.', {
    task: { type: 'string', required: true }, context: { type: 'string', required: true },
  }, '/v1/action/propose', x => x);
  common('expertos_recover' , 'Suggest a bounded recovery action for a failed browser step.', {
    error_code: { type: 'string', required: true },
  }, '/v1/recover', x => x);
  common('expertos_read_source', 'Retrieve source passages by document ID; does not claim neural comprehension.', {
    document_id: { type: 'string', required: true }, question: { type: 'string', required: true },
  }, '/v1/source/read', x => x);
  ctx.tools.register(defineTool({
    name: 'expertos_browser_workflow',
    description: 'Run a safe, isolated browser extraction or form-fill workflow on an explicitly allowlisted site. Never submits forms, logs in, or approves payments. Requires ExpertOS bridge on loopback.',
    parameters: { url: { type: 'string', required: true },
      kind: { type: 'string', required: true, description: 'extract or fill_form' },
      values_json: { type: 'string', description: 'JSON object of exact non-sensitive field values; omit for extract' },
    },
    output: { schema: { type: 'string' }, render: (_a, x) => [{ type: 'text', text: x }] },
    async execute(args, exec) {
      const values = args.values_json ? JSON.parse(args.values_json) : {};
      const result = await runBrowserWorkflow({ url: args.url, kind: args.kind, values, client,
        allowHosts: options.allowHosts || [], allowTestLoopback: !!options.allowTestLoopback,
        signal: exec?.signal, playwrightLoader: options.playwrightLoader });
      return JSON.stringify(result);
    },
  }));
}
