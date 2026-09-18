import { Catalog, Evals, Evaluations, Connections, Quotes, Runs } from "./resources.js";
import { randomUUID } from "node:crypto";
import type { RunRecord } from "./types.js";
import { Transport } from "./transport.js";

export {
  APIError,
  ClientError,
  RequestTimeout,
  WaitCancelled,
} from "./transport.js";
export type { ClientOptions, RequestOptions } from "./transport.js";
export type { WaitOptions } from "./helpers.js";
export type * from "./types.js";

export class Client extends Transport {
  readonly catalog = new Catalog(this);
  readonly connections = new Connections(this);
  readonly quotes = new Quotes(this);
  readonly runs = new Runs(this);
  readonly evals = new Evals(this);
  readonly evaluations = new Evaluations(this);

  /**
   * The canonical call: route `eval` to whichever provider owns it and run it.
   * `model` is a managed route id or `connection:<uuid>`;
   * `eval` is `eval://provider/name/version` or `name@version`.
   */
  async run(input: {
    model: string;
    eval: string;
    budgetUsd?: number | string;
    maxChargeMicrousd?: string;
    provider?: string;
    coverage?: Record<string, unknown>;
    name?: string;
    metadata?: Record<string, string>;
    idempotencyKey?: string;
    wait?: boolean;
    timeoutMs?: number;
    pollIntervalMs?: number;
  }): Promise<RunRecord> {
    const body: Record<string, unknown> = {
      model: input.model,
      eval: input.eval,
      name: input.name ?? "Evaluation",
      metadata: input.metadata ?? {},
    };
    if (input.provider) body.provider = input.provider;
    if (input.coverage) body.coverage = input.coverage;
    if (input.maxChargeMicrousd !== undefined) body.max_charge_microusd = input.maxChargeMicrousd;
    else body.budget_usd = String(input.budgetUsd);
    const run = await this.evaluations.create(
      body as never,
      input.idempotencyKey ?? `run-${randomUUID()}`,
    );
    if (input.wait === false) return run;
    return this.runs.wait(String(run.id), {
      timeoutMs: input.timeoutMs,
      pollIntervalMs: input.pollIntervalMs,
    });
  }
}

export { Client as EvalRouter };
