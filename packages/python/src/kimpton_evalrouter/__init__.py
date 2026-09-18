"""Typed API client. This package is independent of the API and native runners."""

from functools import cached_property as _cached_property

from . import types
from ._resources import Catalog as _Catalog
from ._resources import Connections as _Connections
from ._resources import Evals as _Evals
from ._resources import Evaluations as _Evaluations
from ._resources import Quotes as _Quotes
from ._resources import Runs as _Runs
from ._transport import APIError, ClientError, RequestOptions, RequestTimeout, WaitCancelled
from ._transport import Transport as _Transport

__all__ = [
    "Client",
    "EvalRouter",
    "APIError",
    "ClientError",
    "RequestOptions",
    "RequestTimeout",
    "WaitCancelled",
    "types",
]
__version__ = "0.1.0"


class Client(_Transport):
    @_cached_property
    def catalog(self) -> _Catalog:
        return _Catalog(self)

    @_cached_property
    def connections(self) -> _Connections:
        return _Connections(self)

    @_cached_property
    def quotes(self) -> _Quotes:
        return _Quotes(self)

    @_cached_property
    def runs(self) -> _Runs:
        return _Runs(self)

    @_cached_property
    def evals(self) -> _Evals:
        return _Evals(self)

    @_cached_property
    def evaluations(self) -> _Evaluations:
        return _Evaluations(self)

    def run(
        self,
        *,
        model: str,
        eval: str,
        budget_usd: str | float | None = None,
        max_charge_microusd: str | None = None,
        provider: str | None = None,
        coverage: dict | None = None,
        name: str = "Evaluation",
        metadata: dict[str, str] | None = None,
        idempotency_key: str | None = None,
        wait: bool = True,
        timeout: float = 3600,
        poll_interval: float = 2,
    ) -> "types.RunRecord":
        """The canonical call: route `eval` to whichever provider owns it and run it.

        `model` is a managed route id or `connection:<uuid>`;
        `eval` is `eval://provider/name/version` or `name@version`. Returns the
        terminal run when `wait` is true, otherwise the admitted run.
        """
        from uuid import uuid4

        body: dict = {"model": model, "eval": eval, "name": name, "metadata": metadata or {}}
        if provider:
            body["provider"] = provider
        if coverage:
            body["coverage"] = coverage
        if max_charge_microusd is not None:
            body["max_charge_microusd"] = max_charge_microusd
        else:
            body["budget_usd"] = str(budget_usd)
        run = self.evaluations.create(body, idempotency_key=idempotency_key or f"run-{uuid4()}")
        if not wait:
            return run
        return self.runs.wait(str(run["id"]), timeout=timeout, poll_interval=poll_interval)


EvalRouter = Client
