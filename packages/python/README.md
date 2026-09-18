# EvalRouter Python SDK and CLI

Python SDK and CLI for Python 3.12–3.13, distributed under the proprietary
[Kimpton EvalRouter SDK License](LICENSE). Discover evaluations and models,
submit bounded evaluation runs, inspect results, and export reports.

From this repository's root, install with
`python -m pip install ./packages/python` using Python 3.12 or 3.13. The same
installation supplies `kimpton_evalrouter` and the `evalrouter` console command.
See [source build instructions](../../docs/BUILDING.md) for isolated CLI and wheel
installation. A registry release is not required for this source installation.

Set `EVALROUTER_BASE_URL` to the configured API origin, `EVALROUTER_API_KEY` to a
workspace API key, and `EVALROUTER_WORKSPACE_ID` to its workspace. The public API
origin is `https://api.evalrouter.ai`. Package download does not grant service
access. While website access is restricted, obtain an invitation from your
EvalRouter operator, then create and fund the account in the web application.
Never paste credentials into command arguments, source files, logs, or browser
code. HTTPS is required outside explicit loopback development (`--allow-http`).

```python
from kimpton_evalrouter import Client

with Client() as client:
    available = client.evals.list()
    # Choose an admitted exact eval reference and compatible model from discovery.
    run = client.run(
        model="YOUR_MANAGED_MODEL",
        eval="YOUR_EXACT_EVAL_REFERENCE",
        budget_usd="1.00",
        idempotency_key="my-durable-evaluation-request",
    )
    result = client.runs.results(run["id"])
    client.runs.export_to_file(run["id"], "result.json", params={"format": "json"})
```

The budget is a cap, not a price guarantee or promise that a particular evaluation
fits. Check catalog availability and coverage. Managed routes and checked
`connection:<id>` endpoints have distinct billing bases. A quote does not execute
work. Reuse an idempotency key for retries of the same authorized submission.

For explicit quote review, create a documented `NewQuote` JSON object in
`quote.json`, then use the returned quote ID:

```sh
evalrouter catalog --json
evalrouter catalog --models --json
evalrouter quote --config quote.json --json
evalrouter run --quote YOUR_QUOTE_ID --idempotency-key my-durable-request --wait --json
evalrouter results YOUR_RUN_ID --json
evalrouter export YOUR_RUN_ID --format json --output result.json
```

The supported CLI commands are `catalog`, `quote`, `run`, `status`, `wait`,
`cancel`, `results`, `export`, and `connections list/create/check/update/disable`.
Run a command with `--help` for flags. Connection credentials are read through
`--key-env`, never a credential argument. JSON input can use `--config -` for
stdin. `--json` prints one result on stdout; progress is on stderr. Exit status
0 means success, 1 an API/transport or failed-run error, 2 invalid input or a
rejected request, and 4 a partial/cancelled waited run. Interrupting a local wait
does not cancel server work. Use `cancel` explicitly.

The Python API exposes `Client` (`EvalRouter` alias), `catalog`, `evals`,
`connections`, `quotes`, `evaluations`, `runs`, their request/response types, and
bounded wait/export helpers. `catalog.evals`/`catalog.eval` retain the discovery
aliases. Errors are `ClientError`, `APIError`, `RequestTimeout` and `WaitCancelled`.
Use `RequestOptions` for request deadlines and local cancellation. JSON/CSV/HTML
exports require an explicit destination and refuse overwrite unless requested.
Account setup and key creation are separate web steps; the CLI uses an existing
workspace API key.
