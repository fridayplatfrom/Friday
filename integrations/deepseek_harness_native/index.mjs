/**
 * Native DeepSeek Harness LLM Replacement Plugin (`tiny-experts-native-llm`).
 *
 * Replaces DeepSeek's cloud LLM providers (`deepseek-official`, `deepseek-account`)
 * and registers `tiny-experts` so that 100% of user prompts inside DeepSeek Harness
 * (Desktop App, Web UI, and Headless CLI) are answered and live-streamed by the
 * local Tiny Expert OS (54-Book Physics & 7-Core Neural-Symbolic Engine).
 */
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { setTimeout as delay } from "node:timers/promises";
import { readHarnessStream } from "./stream.mjs";

export const name = "tiny-experts-native-llm";
export const inject = ["llm"];

const DEFAULT_PYTHON_API_URL = "http://127.0.0.1:8000";
const DEFAULT_PYTHON_EXE = "C:/Users/ankus/.gemini/antigravity/scratch/tiny_expert_system/.venv/Scripts/python.exe";
const DEFAULT_WEB_APP_SCRIPT = "C:/Users/ankus/.gemini/antigravity/scratch/tiny_expert_system/web_app.py";
const DEFAULT_PROJECT_ROOT = "C:/Users/ankus/.gemini/antigravity/scratch/tiny_expert_system";

const OWNED_PROVIDERS = [
  "tiny-experts",
  "deepseek-account",
  "deepseek-official",
];

const PROVIDER_DISPLAY_NAMES = {
  "tiny-experts": "Tiny Expert OS (54-Book Physics & 7-Core)",
  "deepseek-account": "Tiny Expert OS (54-Book Physics & 7-Core)",
  "deepseek-official": "Tiny Expert OS (54-Book Physics & 7-Core)",
};

const MODEL_DEFINITIONS = [
  {
    id: "tiny-expert-physics-v1",
    name: "Tiny Expert OS — Physics Retrieval & Calculators",
    description:
      "Local rules, optional neural classifiers, source retrieval and bounded symbolic calculations",
    inputModalities: ["text", "image"],
  },
  {
    id: "deepseek-flash",
    name: "Tiny Expert OS — Physics Retrieval & Calculators",
    description:
      "Local Tiny Expert OS replacing DeepSeek-Flash with 54-Book Physics & 7-Core Neural-Symbolic Engine",
    inputModalities: ["text", "image"],
  },
  {
    id: "deepseek-v4-pro",
    name: "Tiny Expert OS — Symbolic and Formula Tools",
    description:
      "Bounded formula calculations and predefined symbolic derivations; no independent correctness guarantee",
    inputModalities: ["text", "image"],
  },
];

const REASONING_EFFORTS = [
  {
    id: "low",
    name: "Fast",
    description: "Fast 2-Stage Neural Routing + Direct Formula Evaluation",
  },
  {
    id: "medium",
    name: "Standard",
    description: "Specialist Concept Classification + Multi-Book Citations",
  },
  {
    id: "high",
    name: "Detailed Execution Report",
    description:
      "Full 10-Pillar Symbolic CAS, First-Principles Euler-Lagrange Derivation, 4-Part Mathematical Proof & 54-Book SHA-256 Verification",
  },
];

let serverBootPromise = null;

async function isPythonBackendAlive(apiUrl) {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 1500);
    try {
      const res = await fetch(`${apiUrl}/api/status`, {
        method: "GET",
        headers: { Host: new URL(apiUrl).host },
        signal: controller.signal,
      });
      return res.ok;
    } finally {
      clearTimeout(timer);
    }
  } catch {
    return false;
  }
}

async function ensurePythonBackend(config = {}) {
  const apiUrl = config.pythonApiUrl || DEFAULT_PYTHON_API_URL;
  if (await isPythonBackendAlive(apiUrl)) {
    return apiUrl;
  }
  if (serverBootPromise) {
    await serverBootPromise;
    return apiUrl;
  }
  serverBootPromise = (async () => {
    const pythonExe = config.pythonExe || DEFAULT_PYTHON_EXE;
    const webAppScript = config.webAppScript || DEFAULT_WEB_APP_SCRIPT;
    const projectRoot = config.projectRoot || DEFAULT_PROJECT_ROOT;
    const port = new URL(apiUrl).port || "8000";

    if (existsSync(pythonExe) && existsSync(webAppScript)) {
      const child = spawn(pythonExe, [webAppScript, "--port", String(port), "--no-browser"], {
        cwd: projectRoot,
        detached: true,
        stdio: "ignore",
        windowsHide: true,
      });
      child.unref();
    }

    for (let attempt = 0; attempt < 120; attempt += 1) {
      if (await isPythonBackendAlive(apiUrl)) {
        return apiUrl;
      }
      await delay(400);
    }
    return apiUrl;
  })();

  try {
    await serverBootPromise;
  } finally {
    serverBootPromise = null;
  }
  return apiUrl;
}

class TinyExpertLlmAdapter {
  constructor(ctx, config = {}) {
    this.ctx = ctx;
    this.config = config;
  }

  providerInfo(provider) {
    return {
      id: provider,
      name: PROVIDER_DISPLAY_NAMES[provider] || "Tiny Expert OS (54-Book Physics & 7-Core)",
    };
  }

  providerRetryPolicy(_provider) {
    return undefined;
  }

  imageRequestPricing(_provider, _model) {
    return undefined;
  }

  imageRequestTarget(_provider, _model, image) {
    return {
      width: image.width,
      height: image.height,
      maxBytes: image.bytes,
    };
  }

  async listModels(provider) {
    return MODEL_DEFINITIONS.map((m) => ({
      provider,
      id: m.id,
      name: m.name,
      description: m.description,
      inputModalities: [...m.inputModalities],
    }));
  }

  async resolveModel(provider, model, _signal) {
    const matched = MODEL_DEFINITIONS.find((m) => m.id === model);
    return {
      provider,
      id: model,
      name: matched
        ? matched.name
        : "Tiny Expert OS — Physics Retrieval & Calculators",
      description: matched
        ? matched.description
        : "100% Local 54-Book Physics & 7-Core Neural-Symbolic Engine",
      inputModalities: ["text", "image"],
      context: { contextWindow: 128000 },
      defaultMaxTokens: 8192,
      systemPromptUpdate: "in-history",
      toolUpdate: "addition-only",
      reasoning: {
        efforts: REASONING_EFFORTS.map((e) => ({ ...e })),
        defaultEffort: "high",
      },
    };
  }

  async prepareCall(provider, model, signal) {
    return {
      model: await this.resolveModel(provider, model, signal),
      stream: (options) => this.stream(options),
    };
  }

  _enrichMessagesWithHostImagePaths(messages) {
    const attachments = this.ctx.get?.("attachments");
    if (!attachments || typeof attachments.imageHostPath !== "function") {
      return messages;
    }
    return (messages || []).map((msg) => {
      if (!msg || !Array.isArray(msg.content)) return msg;
      const nextContent = msg.content.map((block) => {
        if (block && block.type === "image" && block.attachment) {
          try {
            const hostPath = attachments.imageHostPath(block.attachment);
            if (hostPath) {
              return { ...block, hostPath };
            }
          } catch {
            // Ignore attachment lookup errors
          }
        }
        return block;
      });
      return { ...msg, content: nextContent };
    });
  }

  async *stream(options) {
    const signal = options?.signal;
    signal?.throwIfAborted?.();

    const apiUrl = await ensurePythonBackend(this.config);
    signal?.throwIfAborted?.();

    const enrichedMessages = this._enrichMessagesWithHostImagePaths(options?.messages || []);
    const payload = {
      provider: options?.provider || "tiny-experts",
      model: options?.model || "tiny-expert-physics-v1",
      reasoningEffort: options?.reasoningEffort || "high",
      purpose: options?.purpose,
      messages: enrichedMessages,
    };

    const res = await fetch(`${apiUrl}/api/harness/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Host: new URL(apiUrl).host,
      },
      body: JSON.stringify(payload),
      signal,
    });

    if (!res.ok) {
      const errText = await res.text().catch(() => `HTTP ${res.status}`);
      throw new Error(`Tiny Expert OS backend error (${res.status}): ${errText}`);
    }

    // Forward backend events as they arrive; never replay buffered JSON with
    // artificial token delays. Fetch and the reader share the abort signal.
    yield* readHarnessStream(res, signal);
  }
}

export function apply(ctx, config = {}) {
  const adapter = new TinyExpertLlmAdapter(ctx, config);

  // Pre-warm the local Python TinyExpertOrchestrator backend in the background
  ensurePythonBackend(config).catch(() => {});

  // Register configurable providers for the Settings -> Models UI
  try {
    ctx.llm.registerConfigurableProviders(
      OWNED_PROVIDERS.map((provider) => ({
        provider,
        displayName: PROVIDER_DISPLAY_NAMES[provider],
        settingsNs: `tiny-experts-${provider}`,
        settingsPath: [],
      }))
    );
  } catch {
    // If any configurable provider entry already exists, ignore directory duplicate
  }

  // Register our TinyExpertLlmAdapter across all three routes:
  // "tiny-experts", "deepseek-account", and "deepseek-official"
  ctx.llm.registerAdapter(OWNED_PROVIDERS, adapter);
}

export default {
  name,
  inject,
  apply,
};
