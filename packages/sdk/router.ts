import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import type {
  GenerateTextRequest,
  GenerateTextResponse,
  RouterConfig,
} from "./types.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(__dirname, "../..");

export * from "./types.js";

export class Router {
  private config: RouterConfig;
  private pythonBin: string;

  private constructor(config: RouterConfig) {
    this.config = config;
    this.pythonBin = process.env.ADAPTIVE_ROUTER_PYTHON ?? "python3";
  }

  static init(config: RouterConfig = {}): Router {
    return new Router(config);
  }

  async generateText(
    request: GenerateTextRequest,
  ): Promise<GenerateTextResponse> {
    if (this.config.baseUrl) {
      const response = await fetch(`${this.config.baseUrl}/v1/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });
      if (!response.ok) {
        throw new Error(`Router HTTP error: ${response.status}`);
      }
      return (await response.json()) as GenerateTextResponse;
    }

    return this.generateTextViaPython(request);
  }

  private generateTextViaPython(
    request: GenerateTextRequest,
  ): Promise<GenerateTextResponse> {
    const payload = JSON.stringify({
      request,
      config: this.config,
    });

    return new Promise((resolvePromise, reject) => {
      const child = spawn(
        this.pythonBin,
        [resolve(PROJECT_ROOT, "scripts/ts_bridge.py")],
        {
          cwd: PROJECT_ROOT,
          stdio: ["pipe", "pipe", "pipe"],
        },
      );

      let stdout = "";
      let stderr = "";

      child.stdout.on("data", (chunk: Buffer) => {
        stdout += chunk.toString();
      });
      child.stderr.on("data", (chunk: Buffer) => {
        stderr += chunk.toString();
      });

      child.on("error", reject);
      child.on("close", (code) => {
        if (code !== 0) {
          reject(new Error(stderr || `Python bridge exited with code ${code}`));
          return;
        }
        try {
          resolvePromise(JSON.parse(stdout) as GenerateTextResponse);
        } catch (error) {
          reject(error);
        }
      });

      child.stdin.write(payload);
      child.stdin.end();
    });
  }
}
