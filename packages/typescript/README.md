# EvalRouter TypeScript client

Client for trusted Node.js 22+ applications, using ESM, distributed under the
proprietary [Kimpton EvalRouter SDK License](LICENSE). Build the archive using
the repository's [source build instructions](../../docs/BUILDING.md), then install
it with `npm install /absolute/path/to/kimpton-ai-evalrouter-0.1.0.tgz`.
Discover evaluations and models,
submit bounded evaluation runs, inspect results, and export reports.

Use API keys only in a trusted server process, never a browser bundle. Set
`EVALROUTER_BASE_URL`, `EVALROUTER_API_KEY` and `EVALROUTER_WORKSPACE_ID` after
creating and funding an account in the web application. The public API origin is
`https://api.evalrouter.ai`. Package download does not grant service access.
While website access is restricted, obtain an invitation from your EvalRouter
operator before setting up the account and workspace key.

```typescript
import { Client } from "@kimpton-ai/evalrouter";

const client = new Client();
const available = await client.evals.list();
// Select an admitted exact reference and compatible model from discovery.
const run = await client.run({
  model: "YOUR_MANAGED_MODEL",
  eval: "YOUR_EXACT_EVAL_REFERENCE",
  budgetUsd: "1.00",
  idempotencyKey: "my-durable-evaluation-request",
});
const result = await client.runs.results(run.id);
await client.runs.exportToFile(run.id, "result.json", { format: "json" });
```

A budget is a spending cap, not a price guarantee or assurance that an eval fits.
Managed model routes and checked `connection:<id>` endpoints retain their distinct
billing bases. Alternatively use `quotes.create`, review the quote, then
`runs.create(body, durableIdempotencyKey)`. Retry the same authorized request with
the same idempotency key. Local timeouts do not establish that a submitted run
failed to commit.

The supported resources are `catalog`, `evals`, `connections`, `quotes`,
`evaluations` and `runs`. `catalog.evals` and `catalog.eval` are discovery aliases.
The package includes named request/response types, `Client` (`EvalRouter` alias),
`APIError`, `ClientError`, `RequestTimeout`, `WaitCancelled`, and typed
request/wait options. `runs.wait` supports local abort/deadlines; `runs.cancel`
explicitly cancels server work. `runs.exportToFile` handles versioned JSON/CSV/HTML
exports and refuses overwrites by default. Workspace and API configuration can
also be passed in `ClientOptions`.

The HTTP service enforces account access and workspace permissions. Configure
the client with an existing workspace API key.
