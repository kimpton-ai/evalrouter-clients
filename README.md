# EvalRouter clients

Python SDK, Python CLI, and TypeScript client for the EvalRouter API. Discover
available evaluations and models, submit a run with a spending cap, inspect its
results, and export a report.

This repository contains the client source and build tools. It uses the
proprietary [Kimpton EvalRouter SDK License](LICENSE), which permits building
the unmodified source for your own authorized use of EvalRouter. It is not an
open-source license.

## Install from source

Use Python 3.12 or 3.13. From a checkout of this repository:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install ./packages/python
.venv/bin/evalrouter --help
```

The installation provides both `kimpton_evalrouter` and the `evalrouter` command.
It does not require a PyPI release. For an isolated CLI installation with `uv`:

```sh
uv tool install --python 3.12 ./packages/python
evalrouter --help
```

To build the Python wheel, source archive, and TypeScript npm archive, install
Python 3.12–3.13, `uv`, Node.js 22+, and npm, then run:

```sh
python3.12 scripts/build.py
```

The three archives and their SHA-256 manifest appear in `dist/`. Install the
TypeScript archive in your own Node.js project:

```sh
npm install /absolute/path/to/evalrouter-clients/dist/kimpton-ai-evalrouter-0.1.0.tgz
```

See [building and installing](docs/BUILDING.md) for separate package builds,
version pinning, and verification. These source instructions do not depend on
either package being published to a registry.

## Connect to EvalRouter

An authorized account, workspace, and workspace API key are required to use the
service. Obtain an invitation if account access is restricted, then complete
account setup and funding in the web application. Installing a client does not
grant account access or credits.

Set `EVALROUTER_BASE_URL` to `https://api.evalrouter.ai`, and supply
`EVALROUTER_API_KEY` and `EVALROUTER_WORKSPACE_ID` through your process environment
or secret manager. Keep keys in trusted server or terminal processes.

- [Python SDK and CLI usage](packages/python/README.md)
- [TypeScript usage](packages/typescript/README.md)

The CLI prints results to stdout when requested. SDK methods return objects to
your code; they do not create a terminal session or print results automatically.
