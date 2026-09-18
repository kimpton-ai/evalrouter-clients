# Build and install the clients

Use a reviewed source commit or tag and record `git rev-parse HEAD` alongside
your build. An advancing branch name is not a reproducible version pin. A source
checkout needs no EvalRouter service credentials; build tools download their
dependencies from package registries.

## Python SDK and CLI

Python 3.12 and 3.13 are supported. At the repository root:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install ./packages/python
.venv/bin/python -c 'from kimpton_evalrouter import Client; print("SDK import succeeded")'
.venv/bin/evalrouter --help
```

This installs the SDK and CLI into the same environment. To use `evalrouter`
without the `.venv/bin/` prefix, activate that environment first. For a standalone
CLI installation, `uv tool install --python 3.12 ./packages/python` manages a
separate environment; `uv tool update-shell` can add its executable directory
to your shell path if needed.

To build only the Python archives with `uv`:

```sh
uv build ./packages/python --no-sources --out-dir dist
```

Install the wheel into your application environment:

```sh
python -m pip install /absolute/path/to/evalrouter-clients/dist/kimpton_evalrouter_sdk-0.1.0-py3-none-any.whl
```

## TypeScript client and complete artifact build

Use Node.js 22+ and npm, plus Python 3.12–3.13 and `uv` for the combined build:

```sh
python3.12 scripts/build.py
```

The helper installs the locked TypeScript compiler dependencies with `npm ci`,
compiles the client, and creates an npm archive containing the compiled client,
package metadata, README, and license. It also builds the Python wheel and
source archive. It never publishes to npm or PyPI.

The helper requires an empty `dist/` directory. Move a previous build somewhere
safe before rebuilding. Its `dist/manifest.json` records the file sizes and
SHA-256 hashes of all three generated archives. Preserve that manifest with
the source commit you built.

From your own Node.js project:

```sh
npm install /absolute/path/to/evalrouter-clients/dist/kimpton-ai-evalrouter-0.1.0.tgz
node --input-type=module -e 'import { Client } from "@kimpton-ai/evalrouter"; console.log(typeof Client)'
```

The client uses ESM. The import check performs no service request. Use the
[TypeScript examples](../packages/typescript/README.md) after configuring a
workspace API key. TypeScript source in this repository needs compilation;
install the built archive in consuming applications.

## Service access

Compilation, installation, and `--help` do not require an account. Actual API
requests require the account, workspace, permissions, and funding appropriate
to that operation. The repository does not contain credentials or grant
service access. Use the account's workspace key rather than deployment or
administrative credentials.
