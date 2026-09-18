// Generated resource methods. Edit OpenAPI and client-operations.json.
import type * as types from "./types.js";
import { Resource, segment, type RequestOptions } from "./transport.js";
import { RunHelpers } from "./helpers.js";
import { validateSubmission } from "./boundary.js";

export class Catalog extends Resource {
  async evals(params: types.CatalogEvalsParams = {}, options?: RequestOptions): Promise<types.Page_EvalRecord_> {
    return this.client.request<types.Page_EvalRecord_>("GET", `/evals`, { retry: true, options, query: params });
  }
  async eval(ref: string, options?: RequestOptions): Promise<types.EvalRecord> {
    return this.client.request<types.EvalRecord>("GET", `/evals/${segment(ref)}`, { retry: true, options });
  }
  async benchmarks(params: types.CatalogBenchmarksParams = {}, options?: RequestOptions): Promise<types.Page_BenchmarkRecord_> {
    return this.client.request<types.Page_BenchmarkRecord_>("GET", `/catalog/benchmarks`, { retry: true, options, query: params });
  }
  async benchmark(slug: string, options?: RequestOptions): Promise<types.BenchmarkDetail> {
    return this.client.request<types.BenchmarkDetail>("GET", `/catalog/benchmarks/${segment(slug)}`, { retry: true, options });
  }
  async models(params: types.CatalogModelsParams = {}, options?: RequestOptions): Promise<types.Page_ManagedRoute_> {
    return this.client.request<types.Page_ManagedRoute_>("GET", `/catalog/models`, { retry: true, options, query: params });
  }
  async execution_options(options?: RequestOptions): Promise<types.ExecutionOptions> {
    return this.client.request<types.ExecutionOptions>("GET", `/catalog/execution-options`, { retry: true, options });
  }
  async environments(params: types.CatalogEnvironmentsParams = {}, options?: RequestOptions): Promise<types.Page_EnvironmentRecord_> {
    return this.client.request<types.Page_EnvironmentRecord_>("GET", `/catalog/environments`, { retry: true, options, query: params });
  }
  async environment(family: string, options?: RequestOptions): Promise<types.EnvironmentFamily> {
    return this.client.request<types.EnvironmentFamily>("GET", `/catalog/environments/${segment(family)}`, { retry: true, options });
  }
}

export class Connections extends Resource {
  async list(params: types.ConnectionsListParams = {}, options?: RequestOptions): Promise<types.Page_ConnectionRecord_> {
    return this.client.request<types.Page_ConnectionRecord_>("GET", `/connections`, { retry: true, options, query: params });
  }
  async create(body: types.NewConnection, options?: RequestOptions): Promise<types.ConnectionRecord> {
    return this.client.request<types.ConnectionRecord>("POST", `/connections`, { retry: false, options, body: body });
  }
  async check(connection_id: string, options?: RequestOptions): Promise<types.ConnectionRecord> {
    return this.client.request<types.ConnectionRecord>("POST", `/connections/${segment(connection_id)}/check`, { retry: false, options });
  }
  async update(connection_id: string, body: types.UpdateConnection, options?: RequestOptions): Promise<types.ConnectionRecord> {
    return this.client.request<types.ConnectionRecord>("PATCH", `/connections/${segment(connection_id)}`, { retry: false, options, body: body });
  }
  async disable(connection_id: string, options?: RequestOptions): Promise<types.OKResponse> {
    return this.client.request<types.OKResponse>("DELETE", `/connections/${segment(connection_id)}`, { retry: false, options });
  }
}

export class Quotes extends Resource {
  async create(body: types.NewQuote, options?: RequestOptions): Promise<types.QuoteRecord> {
    validateSubmission("quotes", body);
    return this.client.request<types.QuoteRecord>("POST", `/quotes`, { retry: false, options, body: body });
  }
  async get(quote_id: string, options?: RequestOptions): Promise<types.QuoteRecord> {
    return this.client.request<types.QuoteRecord>("GET", `/quotes/${segment(quote_id)}`, { retry: true, options });
  }
}

export class Runs extends RunHelpers {
  async create(body: types.NewRun, idempotency_key: string, options?: RequestOptions): Promise<types.RunRecord> {
    return this.client.request<types.RunRecord>("POST", `/runs`, { retry: true, options, body: body, idempotency_key: idempotency_key });
  }
  async list(params: types.RunsListParams = {}, options?: RequestOptions): Promise<types.Page_RunRecord_> {
    return this.client.request<types.Page_RunRecord_>("GET", `/runs`, { retry: true, options, query: params });
  }
  async get(run_id: string, options?: RequestOptions): Promise<types.RunRecord> {
    return this.client.request<types.RunRecord>("GET", `/runs/${segment(run_id)}`, { retry: true, options });
  }
  async receipt(run_id: string, options?: RequestOptions): Promise<types.RunReceipt> {
    return this.client.request<types.RunReceipt>("GET", `/runs/${segment(run_id)}/receipt`, { retry: true, options });
  }
  async executions(run_id: string, params: types.RunsExecutionsParams = {}, options?: RequestOptions): Promise<types.SandboxExecutionPage> {
    return this.client.request<types.SandboxExecutionPage>("GET", `/runs/${segment(run_id)}/executions`, { retry: true, options, query: params });
  }
  async events(run_id: string, params: types.RunsEventsParams = {}, options?: RequestOptions): Promise<types.EventPage> {
    return this.client.request<types.EventPage>("GET", `/runs/${segment(run_id)}/events`, { retry: true, options, query: params });
  }
  async cancel(run_id: string, options?: RequestOptions): Promise<types.RunRecord> {
    return this.client.request<types.RunRecord>("POST", `/runs/${segment(run_id)}/cancel`, { retry: true, options });
  }
  async results(run_id: string, params: types.RunsResultsParams = {}, options?: RequestOptions): Promise<types.ResultRecord> {
    return this.client.request<types.ResultRecord>("GET", `/runs/${segment(run_id)}/results`, { retry: true, options, query: params });
  }
  async export(run_id: string, params: types.RunsExportParams = {}, options?: RequestOptions): Promise<Uint8Array> {
    return this.client.request<Uint8Array>("GET", `/runs/${segment(run_id)}/export`, { retry: true, options, query: params, binary: true });
  }
}

export class Evals extends Resource {
  async list(params: types.EvalsListParams = {}, options?: RequestOptions): Promise<types.Page_EvalRecord_> {
    return this.client.request<types.Page_EvalRecord_>("GET", `/evals`, { retry: true, options, query: params });
  }
  async get(ref: string, options?: RequestOptions): Promise<types.EvalRecord> {
    return this.client.request<types.EvalRecord>("GET", `/evals/${segment(ref)}`, { retry: true, options });
  }
}

export class Evaluations extends Resource {
  async create(body: types.NewEvaluation, idempotency_key: string, options?: RequestOptions): Promise<types.RunRecord> {
    validateSubmission("evaluations", body);
    return this.client.request<types.RunRecord>("POST", `/evaluations`, { retry: true, options, body: body, idempotency_key: idempotency_key });
  }
  async get(evaluation_id: string, options?: RequestOptions): Promise<types.RunRecord> {
    return this.client.request<types.RunRecord>("GET", `/evaluations/${segment(evaluation_id)}`, { retry: true, options });
  }
}
