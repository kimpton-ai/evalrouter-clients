"""One explicit quote, one idempotent run; machine output never mixes progress."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import APIError, Client, ClientError


class Parser(argparse.ArgumentParser):
    def error(self, message):
        # Parser messages can echo arbitrary arguments. Never echo a mistyped
        # credential, including one supplied through an unsupported option.
        self.print_usage(sys.stderr)
        self.exit(2, "Invalid command arguments. Use --help for accepted options.\n")


def parser():
    common = Parser(add_help=False)
    common.add_argument(
        "--json",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Write one JSON result to stdout; progress goes to stderr",
    )
    common.add_argument(
        "--base-url", default=argparse.SUPPRESS, help="API origin; otherwise EVALROUTER_BASE_URL"
    )
    common.add_argument(
        "--workspace-id",
        default=argparse.SUPPRESS,
        help="Workspace; otherwise EVALROUTER_WORKSPACE_ID",
    )
    common.add_argument(
        "--allow-http",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Allow loopback HTTP for local development",
    )
    common.add_argument(
        "--timeout",
        type=float,
        default=argparse.SUPPRESS,
        help="Request deadline in seconds (default 120)",
    )
    root = Parser(
        prog="evalrouter",
        parents=[common],
        description="Choose a benchmark, review a quote, run and export. Credentials come from EVALROUTER_API_KEY.",
    )
    commands = root.add_subparsers(dest="command", required=True, parser_class=Parser)

    def command(name, help_text):
        return commands.add_parser(name, help=help_text, parents=[common])

    def pagination(p):
        p.add_argument("--cursor")
        p.add_argument("--limit", type=int, default=50)

    catalog = command("catalog", "List maintained benchmark versions or models")
    catalog.add_argument("--models", action="store_true")
    catalog.add_argument("--slug")
    catalog.add_argument("--query", default="")
    catalog.add_argument("--status", choices=["candidate", "active", "quarantined", "retired"])
    catalog.add_argument("--runner", choices=["inspect", "lm-eval"])
    catalog.add_argument("--capability")
    pagination(catalog)
    connections = command(
        "connections", "List, create, check, update or disable endpoint connections"
    )
    sub = connections.add_subparsers(dest="action", required=True, parser_class=Parser)
    listing = sub.add_parser("list", parents=[common])
    pagination(listing)
    create = sub.add_parser("create", parents=[common])
    for option in ("name", "endpoint", "model"):
        create.add_argument(f"--{option}", required=True)
    create.add_argument(
        "--protocol", choices=["openai_chat", "openai_completions"], default="openai_chat"
    )
    create.add_argument(
        "--key-env",
        default="PROVIDER_API_KEY",
        help="Environment variable containing the provider credential",
    )
    create.add_argument("--max-output-tokens", type=int, default=4096)
    create.add_argument("--context-window", type=int, default=32768)
    for action in ("check", "disable", "update"):
        item = sub.add_parser(action, parents=[common])
        item.add_argument("connection_id")
        if action == "update":
            item.add_argument("--config", required=True, help="JSON request file, or - for stdin")
    quote = command("quote", "Create a quote without starting an evaluation, or retrieve one")
    choice = quote.add_mutually_exclusive_group(required=True)
    choice.add_argument("--config", help="NewQuote JSON file, or - for stdin")
    choice.add_argument("--id", help="Retrieve an existing quote")
    run = command("run", "Start exactly the reviewed quote; retry with the same key")
    run.add_argument("--quote", required=True)
    run.add_argument("--idempotency-key", required=True)
    run.add_argument("--name", default="Evaluation")
    run.add_argument("--wait", action="store_true")
    status = command("status", "Inspect an evaluation or list recent evaluations")
    status.add_argument("run_id", nargs="?")
    pagination(status)
    wait = command("wait", "Wait locally without cancelling server work on interruption")
    wait.add_argument("run_id")
    for item in (wait, run):
        item.add_argument("--wait-timeout", type=float, default=3600)
        item.add_argument("--poll-interval", type=float, default=2)
    cancel = command("cancel", "Request cancellation of one evaluation")
    cancel.add_argument("run_id")
    results = command("results", "Retrieve native scores, coverage and uncertainty")
    results.add_argument("run_id")
    results.add_argument("--version", type=int)
    export = command("export", "Save a complete versioned export to an explicit file")
    export.add_argument("run_id")
    export.add_argument("--version", type=int)
    export.add_argument("--format", choices=["json", "csv", "html"], default="json")
    export.add_argument("--output", required=True)
    export.add_argument("--overwrite", action="store_true")
    return root


def read_object(name):
    try:
        if name == "-":
            raw = sys.stdin.buffer.read(256 * 1024 + 1)
        else:
            with Path(name).open("rb") as stream:
                raw = stream.read(256 * 1024 + 1)
        if len(raw) > 256 * 1024:
            raise ValueError()
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (OSError, ValueError, UnicodeError):
        raise ClientError(
            "invalid_input", "Provide a valid JSON object no larger than 256 KiB."
        ) from None


def terminal_exit(run):
    return 0 if run["status"] == "completed" else 1 if run["status"] == "failed" else 4


def progress():
    previous = None

    def changed(run):
        nonlocal previous
        state = (run.get("status"), run.get("completed_count"), run.get("error_count"))
        if state != previous:
            print(
                json.dumps(
                    {
                        "run_id": run["id"],
                        "status": state[0],
                        "completed": state[1],
                        "errors": state[2],
                    }
                ),
                file=sys.stderr,
                flush=True,
            )
            previous = state

    return changed


def execute(client, args):
    command = args.command
    if command == "catalog":
        if args.models and args.slug:
            raise ClientError("invalid_input", "Choose either models or a benchmark slug.")
        value = (
            client.catalog.models()
            if args.models
            else client.catalog.benchmark(args.slug)
            if args.slug
            else client.catalog.benchmarks(
                params={
                    "q": args.query,
                    "status": args.status,
                    "runner": args.runner,
                    "capability": args.capability,
                    "cursor": args.cursor,
                    "limit": args.limit,
                }
            )
        )
    elif command == "connections":
        if args.action == "list":
            value = client.connections.list(params={"cursor": args.cursor, "limit": args.limit})
        elif args.action == "create":
            credential = os.environ.get(args.key_env)
            if not credential:
                raise ClientError(
                    "invalid_configuration",
                    "The selected provider credential environment variable is empty.",
                )
            value = client.connections.create(
                {
                    "name": args.name,
                    "base_url": args.endpoint,
                    "model_id": args.model,
                    "api_key": credential,
                    "protocol": args.protocol,
                    "max_output_tokens": args.max_output_tokens,
                    "context_window": args.context_window,
                }
            )
        elif args.action == "update":
            value = client.connections.update(args.connection_id, read_object(args.config))
        else:
            value = getattr(client.connections, args.action)(args.connection_id)
    elif command == "quote":
        value = (
            client.quotes.get(args.id)
            if args.id
            else client.quotes.create(read_object(args.config))
        )
    elif command == "run":
        value = client.runs.create(
            {"quote_id": args.quote, "name": args.name}, idempotency_key=args.idempotency_key
        )
        if args.wait:
            value = client.runs.wait(
                value["id"],
                timeout=args.wait_timeout,
                poll_interval=args.poll_interval,
                on_progress=progress(),
            )
            return value, terminal_exit(value)
    elif command == "status":
        value = (
            client.runs.get(args.run_id)
            if args.run_id
            else client.runs.list(params={"cursor": args.cursor, "limit": args.limit})
        )
    elif command == "wait":
        value = client.runs.wait(
            args.run_id,
            timeout=args.wait_timeout,
            poll_interval=args.poll_interval,
            on_progress=progress(),
        )
        return value, terminal_exit(value)
    elif command == "cancel":
        value = client.runs.cancel(args.run_id)
    elif command == "results":
        value = client.runs.results(args.run_id, params={"version": args.version})
    else:
        path = client.runs.export_to_file(
            args.run_id,
            args.output,
            params={"format": args.format, "version": args.version},
            overwrite=args.overwrite,
        )
        value = {
            "run_id": args.run_id,
            "path": str(path),
            "format": args.format,
            "version": args.version,
        }
    return value, 0


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        with Client(
            base_url=getattr(args, "base_url", None),
            workspace_id=getattr(args, "workspace_id", None),
            allow_http=getattr(args, "allow_http", False),
            timeout=getattr(args, "timeout", 120),
        ) as client:
            value, code = execute(client, args)
        print(
            json.dumps(value, ensure_ascii=True, indent=None if getattr(args, "json", False) else 2)
        )
        return code
    except ClientError as error:
        if getattr(args, "json", False):
            print(json.dumps({"error": error.as_dict()}))
        else:
            print(f"{error.code}: {error.message}", file=sys.stderr)
        if isinstance(error, APIError):
            return 2 if error.status in {400, 402, 409, 422} else 1
        return (
            2
            if error.code in {"invalid_configuration", "invalid_input", "destination_exists"}
            else 1
        )
    except KeyboardInterrupt:
        print(
            "Local command interrupted. Submitted server work was not cancelled.", file=sys.stderr
        )
        return 1
