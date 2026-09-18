export class ClientError extends Error {
  idempotency_key?: string;
  constructor(
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = this.constructor.name;
  }
  toJSON() {
    return { code: this.code, message: this.message,
      ...(this.idempotency_key !== undefined ? { idempotency_key: this.idempotency_key } : {}) };
  }
}
export class APIError extends ClientError {
  constructor(
    public readonly status: number,
    code: string,
    public readonly requestId: string | null = null,
    message?: string,
    public readonly details: unknown = null,
  ) {
    super(code, message || `API request failed (HTTP ${status}, ${code}).`);
  }
  toJSON() {
    return {
      ...super.toJSON(),
      status: this.status,
      request_id: this.requestId,
      details: this.details,
    };
  }
}
export class RequestTimeout extends ClientError {
  constructor() {
    super(
      "request_timeout",
      "The request deadline expired; a submitted operation may have committed.",
    );
  }
}
export class WaitCancelled extends ClientError {
  constructor() {
    super(
      "wait_cancelled",
      "Local waiting was cancelled. The server evaluation was not cancelled.",
    );
  }
}
export type RequestOptions = { timeoutMs?: number; signal?: AbortSignal };
export type ClientOptions = {
  baseUrl?: string;
  apiKey?: string;
  workspaceId?: string;
  timeoutMs?: number;
  requestTimeoutMs?: number;
  maxRetries?: number;
  maxResponseBytes?: number;
  maxExportBytes?: number;
  allowHttp?: boolean;
  fetch?: typeof globalThis.fetch;
};
type Request = {
  body?: unknown;
  query?: object;
  retry: boolean;
  idempotency_key?: string;
  binary?: boolean;
  options?: RequestOptions;
};

export function positive(value: number, label: string): number {
  if (!Number.isFinite(value) || value <= 0 || value > 2_147_483_647)
    throw new ClientError(
      "invalid_configuration",
      `${label} must be a positive finite number no greater than 2147483647.`,
    );
  return value;
}
export function segment(value: string): string {
  if (
    typeof value !== "string" ||
    !/^[A-Za-z0-9_.:@+-]{1,200}$/.test(value) ||
    [".", ".."].includes(value)
  )
    throw new ClientError(
      "invalid_input",
      "Resource identifiers must be nonempty path-safe identifiers.",
    );
  return encodeURIComponent(value);
}
function normalizeBase(value: string, allowHttp: boolean): string {
  try {
    if (/[\u0000-\u0020\\]/.test(value)) throw new Error();
    const url = new URL(value);
    const local =
      url.hostname === "localhost" ||
      url.hostname === "[::1]" ||
      /^127\.\d+\.\d+\.\d+$/.test(url.hostname);
    if (
      url.username ||
      url.password ||
      url.search ||
      url.hash ||
      !["", "/v1"].includes(url.pathname.replace(/\/+$/, ""))
    )
      throw new Error();
    if (
      url.protocol !== "https:" &&
      !(url.protocol === "http:" && allowHttp && local)
    )
      throw new Error();
    return `${url.origin}/v1`;
  } catch {
    throw new ClientError(
      "invalid_configuration",
      "Set an HTTPS API origin or /v1 URL. Explicit HTTP is allowed only for loopback development.",
    );
  }
}
export function checkpoint(deadline: number, signal?: AbortSignal): number {
  if (signal?.aborted) throw new WaitCancelled();
  const remaining = deadline - performance.now();
  if (remaining <= 0) throw new RequestTimeout();
  return remaining;
}
export async function pause(
  delay: number,
  deadline: number,
  signal?: AbortSignal,
) {
  checkpoint(deadline, signal);
  const resumeAt = performance.now() + delay;
  // Timers can wake early. Recheck the monotonic clock so an early callback
  // cannot shorten Retry-After or turn a deadline-clipped wait into a retry.
  while (true) {
    const remaining = checkpoint(deadline, signal);
    const waiting = resumeAt - performance.now();
    if (waiting <= 0) return;
    await new Promise<void>((resolve, reject) => {
      const cleanup = () => {
        clearTimeout(timer);
        signal?.removeEventListener("abort", abort);
      };
      const abort = () => {
        cleanup();
        reject(new WaitCancelled());
      };
      const timer = setTimeout(
        () => {
          cleanup();
          resolve();
        },
        Math.ceil(Math.min(waiting, remaining)),
      );
      signal?.addEventListener("abort", abort, { once: true });
      if (signal?.aborted) abort();
    });
  }
}
function retryDelay(attempt: number, header: string | null): number {
  let delay = Math.min(5000, 250 * 2 ** attempt) + Math.random() * 250;
  if (header && header.length < 100) {
    const numeric = Number(header);
    const suggested = Number.isFinite(numeric)
      ? numeric * 1000
      : Date.parse(header) - Date.now();
    if (Number.isFinite(suggested)) delay = Math.max(delay, suggested);
  }
  return delay;
}
function secretValues(body: unknown): string[] {
  if (!body || typeof body !== "object") return [];
  return Object.entries(body).flatMap(([key, value]) => [
    ...(/key|secret|token|password/i.test(key) &&
    typeof value === "string" &&
    value
      ? [value]
      : []),
    ...secretValues(value),
  ]);
}
function safeErrorValue(value: unknown, secrets: string[], depth = 0): unknown {
  if (depth > 4) return "[truncated]";
  if (typeof value === "string") {
    let text = value;
    for (const secret of secrets) text = text.replaceAll(secret, "[redacted]");
    return text.replace(/[\u0000-\u001f\u007f-\u009f]/g, " ").slice(0, 2000);
  }
  if (Array.isArray(value))
    return value
      .slice(0, 100)
      .map((item) => safeErrorValue(item, secrets, depth + 1));
  if (value && typeof value === "object")
    return Object.fromEntries(
      Object.entries(value)
        .slice(0, 100)
        .map(([key, item]) => [
          (safeErrorValue(key, secrets) as string).slice(0, 100),
          /key|secret|token|password|authorization|cookie/i.test(key)
            ? "[redacted]"
            : safeErrorValue(item, secrets, depth + 1),
        ]),
    );
  return value === null ||
    typeof value === "number" ||
    typeof value === "boolean"
    ? value
    : null;
}
async function readBody(
  response: Response,
  maximum: number,
  deadline: number,
  signal?: AbortSignal,
): Promise<Uint8Array> {
  const reader = response.body?.getReader();
  if (!reader) return new Uint8Array();
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      checkpoint(deadline, signal);
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > maximum)
        throw new ClientError(
          "response_too_large",
          "API response exceeds the configured size limit.",
        );
      chunks.push(value);
    }
    checkpoint(deadline, signal);
    return Buffer.concat(chunks);
  } finally {
    await reader.cancel().catch(() => undefined);
    reader.releaseLock();
  }
}

export class Transport {
  readonly timeoutMs: number;
  readonly requestTimeoutMs: number;
  readonly maxRetries: number;
  readonly maxResponseBytes: number;
  readonly maxExportBytes: number;
  #base: string;
  #key: string | undefined;
  #workspace: string | undefined;
  #fetch: typeof globalThis.fetch;
  constructor(options: ClientOptions = {}) {
    if (typeof window !== "undefined")
      throw new ClientError(
        "invalid_configuration",
        "Use workspace API keys only in trusted server applications.",
      );
    this.#base = normalizeBase(
      options.baseUrl ?? process.env.EVALROUTER_BASE_URL ?? "",
      options.allowHttp === true,
    );
    this.#key = options.apiKey ?? process.env.EVALROUTER_API_KEY;
    this.#workspace =
      options.workspaceId ?? process.env.EVALROUTER_WORKSPACE_ID;
    for (const [label, value] of [
      ["API key", this.#key],
      ["Workspace ID", this.#workspace],
    ]) {
      if (
        value !== undefined &&
        (typeof value !== "string" || !/^[\x21-\x7e]{1,4096}$/.test(value))
      )
        throw new ClientError(
          "invalid_configuration",
          `${label} must be printable non-space ASCII.`,
        );
    }
    this.timeoutMs = positive(options.timeoutMs ?? 120_000, "Timeout");
    this.requestTimeoutMs = positive(
      options.requestTimeoutMs ?? 30_000,
      "Request timeout",
    );
    this.maxRetries = options.maxRetries ?? 2;
    if (
      !Number.isInteger(this.maxRetries) ||
      this.maxRetries < 0 ||
      this.maxRetries > 5
    )
      throw new ClientError(
        "invalid_configuration",
        "maxRetries must be between 0 and 5.",
      );
    this.maxResponseBytes = options.maxResponseBytes ?? 64 * 1024 * 1024;
    this.maxExportBytes = options.maxExportBytes ?? 256 * 1024 * 1024;
    for (const value of [this.maxResponseBytes, this.maxExportBytes]) {
      if (!Number.isSafeInteger(value) || value < 1)
        throw new ClientError(
          "invalid_configuration",
          "Response size limits must be positive safe integers.",
        );
    }
    this.#fetch = options.fetch ?? globalThis.fetch;
  }
  async request<T>(method: string, path: string, request: Request): Promise<T> {
    const options = request.options ?? {};
    const deadline =
      performance.now() +
      positive(options.timeoutMs ?? this.timeoutMs, "Timeout");
    if (!path.startsWith("/") || path.startsWith("//"))
      throw new ClientError("invalid_input", "Invalid API resource path.");
    const url = new URL(this.#base + path);
    const headers: Record<string, string> = {
      Accept: request.binary ? "*/*" : "application/json",
      "User-Agent": "kimpton-evalrouter-typescript/0.1.0",
    };
    if (this.#key) headers.Authorization = `Bearer ${this.#key}`;
    if (this.#workspace) headers["X-Workspace-Id"] = this.#workspace;
    if (request.idempotency_key !== undefined) {
      if (
        typeof request.idempotency_key !== "string" ||
        !/^[\x20-\x7e]{1,128}$/.test(request.idempotency_key)
      )
        throw new ClientError(
          "invalid_input",
          "Idempotency keys must contain 1–128 printable ASCII characters.",
        );
      headers["Idempotency-Key"] = request.idempotency_key;
    }
    let body: string | undefined;
    try {
      body =
        request.body === undefined
          ? undefined
          : JSON.stringify(request.body, (_key, value: unknown) => {
              if (typeof value === "number" && !Number.isFinite(value))
                throw new Error();
              return value;
            });
      for (const [key, value] of Object.entries(request.query ?? {})) {
        if (value !== undefined && value !== null)
          url.searchParams.set(key, String(value));
      }
    } catch {
      throw new ClientError(
        "invalid_input",
        "Request data must be JSON-serializable.",
      );
    }
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const secrets = [this.#key, ...secretValues(request.body)].filter(
      (v): v is string => !!v,
    );
    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      const remaining = checkpoint(deadline, options.signal);
      const controller = new AbortController();
      const abort = () => controller.abort();
      options.signal?.addEventListener("abort", abort, { once: true });
      const timer = setTimeout(
        abort,
        Math.ceil(Math.min(remaining, this.requestTimeoutMs)),
      );
      let error: ClientError;
      let delay = retryDelay(attempt, null);
      try {
        checkpoint(deadline, options.signal);
        const response = await this.#fetch(url, {
          method,
          headers,
          body,
          signal: controller.signal,
          redirect: "manual",
          credentials: "omit",
        });
        if (response.status >= 300 && response.status < 400) {
          await response.body?.cancel().catch(() => undefined);
          throw new APIError(response.status, "redirect_rejected");
        }
        const raw = await readBody(
          response,
          response.ok
            ? request.binary
              ? this.maxExportBytes
              : this.maxResponseBytes
            : 65536,
          deadline,
          options.signal,
        );
        if (response.ok) {
          if (request.binary) return raw as T;
          try {
            const value: unknown = JSON.parse(
              new TextDecoder("utf-8", { fatal: true }).decode(raw),
            );
            if (!value || typeof value !== "object" || Array.isArray(value))
              throw new Error();
            checkpoint(deadline, options.signal);
            return value as T;
          } catch (e) {
            if (e instanceof ClientError) throw e;
            throw new ClientError(
              "invalid_response",
              "API returned an invalid JSON object.",
            );
          }
        }
        let code = "http_error",
          requestId = response.headers.get("X-Request-Id");
        let message: string | undefined,
          details: unknown = null;
        try {
          const serverError = JSON.parse(new TextDecoder().decode(raw))?.error;
          const candidate: unknown = serverError?.code;
          if (
            typeof candidate === "string" &&
            /^[a-z][a-z0-9_]{0,99}$/.test(candidate)
          )
            code = candidate;
          if (typeof serverError?.message === "string")
            message = safeErrorValue(serverError.message, secrets) as string;
          details = safeErrorValue(serverError?.details, secrets);
        } catch {
          /* Untrusted response text does not enter exceptions. */
        }
        if (secrets.some((secret) => code.includes(secret)))
          code = "http_error";
        if (
          !requestId ||
          !/^[A-Za-z0-9_-]{1,100}$/.test(requestId) ||
          secrets.some((secret) => requestId!.includes(secret))
        )
          requestId = null;
        error = new APIError(
          response.status,
          code,
          requestId,
          message,
          details,
        );
        if (![429, 502, 503, 504].includes(response.status)) throw error;
        delay = retryDelay(attempt, response.headers.get("Retry-After"));
      } catch (e) {
        checkpoint(deadline, options.signal);
        if (e instanceof ClientError) throw e;
        error = new ClientError(
          "network_error",
          "The API request failed; a submitted operation may have committed.",
        );
      } finally {
        clearTimeout(timer);
        options.signal?.removeEventListener("abort", abort);
      }
      if (!request.retry || attempt === this.maxRetries) throw error;
      await pause(delay, deadline, options.signal);
    }
    throw new Error("Unreachable retry state");
  }
}

export class Resource {
  constructor(protected readonly client: Transport) {}
}
