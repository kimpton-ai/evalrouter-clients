"""Generated resource methods. Edit OpenAPI and client-operations.json."""

from __future__ import annotations

from typing import cast

from . import types
from ._boundary import validate_submission
from ._helpers import RunHelpers
from ._transport import RequestOptions, Resource, segment


class Catalog(Resource):
    def evals(
        self,
        *,
        params: types.CatalogEvalsParams | None = None,
        options: RequestOptions | None = None,
    ) -> types.Page_EvalRecord_:
        return cast(
            types.Page_EvalRecord_,
            self._client.request("GET", "/evals", retry=True, options=options, query=params),
        )

    def eval(self, ref: str, *, options: RequestOptions | None = None) -> types.EvalRecord:
        return cast(
            types.EvalRecord,
            self._client.request("GET", f"/evals/{segment(ref)}", retry=True, options=options),
        )

    def benchmarks(
        self,
        *,
        params: types.CatalogBenchmarksParams | None = None,
        options: RequestOptions | None = None,
    ) -> types.Page_BenchmarkRecord_:
        return cast(
            types.Page_BenchmarkRecord_,
            self._client.request(
                "GET", "/catalog/benchmarks", retry=True, options=options, query=params
            ),
        )

    def benchmark(
        self, slug: str, *, options: RequestOptions | None = None
    ) -> types.BenchmarkDetail:
        return cast(
            types.BenchmarkDetail,
            self._client.request(
                "GET", f"/catalog/benchmarks/{segment(slug)}", retry=True, options=options
            ),
        )

    def models(
        self,
        *,
        params: types.CatalogModelsParams | None = None,
        options: RequestOptions | None = None,
    ) -> types.Page_ManagedRoute_:
        return cast(
            types.Page_ManagedRoute_,
            self._client.request(
                "GET", "/catalog/models", retry=True, options=options, query=params
            ),
        )

    def execution_options(self, *, options: RequestOptions | None = None) -> types.ExecutionOptions:
        return cast(
            types.ExecutionOptions,
            self._client.request("GET", "/catalog/execution-options", retry=True, options=options),
        )

    def environments(
        self,
        *,
        params: types.CatalogEnvironmentsParams | None = None,
        options: RequestOptions | None = None,
    ) -> types.Page_EnvironmentRecord_:
        return cast(
            types.Page_EnvironmentRecord_,
            self._client.request(
                "GET", "/catalog/environments", retry=True, options=options, query=params
            ),
        )

    def environment(
        self, family: str, *, options: RequestOptions | None = None
    ) -> types.EnvironmentFamily:
        return cast(
            types.EnvironmentFamily,
            self._client.request(
                "GET", f"/catalog/environments/{segment(family)}", retry=True, options=options
            ),
        )


class Connections(Resource):
    def list(
        self,
        *,
        params: types.ConnectionsListParams | None = None,
        options: RequestOptions | None = None,
    ) -> types.Page_ConnectionRecord_:
        return cast(
            types.Page_ConnectionRecord_,
            self._client.request("GET", "/connections", retry=True, options=options, query=params),
        )

    def create(
        self, body: types.NewConnection, *, options: RequestOptions | None = None
    ) -> types.ConnectionRecord:
        return cast(
            types.ConnectionRecord,
            self._client.request("POST", "/connections", retry=False, options=options, body=body),
        )

    def check(
        self, connection_id: str, *, options: RequestOptions | None = None
    ) -> types.ConnectionRecord:
        return cast(
            types.ConnectionRecord,
            self._client.request(
                "POST", f"/connections/{segment(connection_id)}/check", retry=False, options=options
            ),
        )

    def update(
        self,
        connection_id: str,
        body: types.UpdateConnection,
        *,
        options: RequestOptions | None = None,
    ) -> types.ConnectionRecord:
        return cast(
            types.ConnectionRecord,
            self._client.request(
                "PATCH",
                f"/connections/{segment(connection_id)}",
                retry=False,
                options=options,
                body=body,
            ),
        )

    def disable(
        self, connection_id: str, *, options: RequestOptions | None = None
    ) -> types.OKResponse:
        return cast(
            types.OKResponse,
            self._client.request(
                "DELETE", f"/connections/{segment(connection_id)}", retry=False, options=options
            ),
        )


class Quotes(Resource):
    def create(
        self, body: types.NewQuote, *, options: RequestOptions | None = None
    ) -> types.QuoteRecord:
        validate_submission("quotes", body)
        return cast(
            types.QuoteRecord,
            self._client.request("POST", "/quotes", retry=False, options=options, body=body),
        )

    def get(self, quote_id: str, *, options: RequestOptions | None = None) -> types.QuoteRecord:
        return cast(
            types.QuoteRecord,
            self._client.request(
                "GET", f"/quotes/{segment(quote_id)}", retry=True, options=options
            ),
        )


class Runs(RunHelpers):
    def create(
        self, body: types.NewRun, *, idempotency_key: str, options: RequestOptions | None = None
    ) -> types.RunRecord:
        return cast(
            types.RunRecord,
            self._client.request(
                "POST",
                "/runs",
                retry=True,
                options=options,
                body=body,
                idempotency_key=idempotency_key,
            ),
        )

    def list(
        self, *, params: types.RunsListParams | None = None, options: RequestOptions | None = None
    ) -> types.Page_RunRecord_:
        return cast(
            types.Page_RunRecord_,
            self._client.request("GET", "/runs", retry=True, options=options, query=params),
        )

    def get(self, run_id: str, *, options: RequestOptions | None = None) -> types.RunRecord:
        return cast(
            types.RunRecord,
            self._client.request("GET", f"/runs/{segment(run_id)}", retry=True, options=options),
        )

    def receipt(self, run_id: str, *, options: RequestOptions | None = None) -> types.RunReceipt:
        return cast(
            types.RunReceipt,
            self._client.request(
                "GET", f"/runs/{segment(run_id)}/receipt", retry=True, options=options
            ),
        )

    def executions(
        self,
        run_id: str,
        *,
        params: types.RunsExecutionsParams | None = None,
        options: RequestOptions | None = None,
    ) -> types.SandboxExecutionPage:
        return cast(
            types.SandboxExecutionPage,
            self._client.request(
                "GET",
                f"/runs/{segment(run_id)}/executions",
                retry=True,
                options=options,
                query=params,
            ),
        )

    def events(
        self,
        run_id: str,
        *,
        params: types.RunsEventsParams | None = None,
        options: RequestOptions | None = None,
    ) -> types.EventPage:
        return cast(
            types.EventPage,
            self._client.request(
                "GET", f"/runs/{segment(run_id)}/events", retry=True, options=options, query=params
            ),
        )

    def cancel(self, run_id: str, *, options: RequestOptions | None = None) -> types.RunRecord:
        return cast(
            types.RunRecord,
            self._client.request(
                "POST", f"/runs/{segment(run_id)}/cancel", retry=True, options=options
            ),
        )

    def results(
        self,
        run_id: str,
        *,
        params: types.RunsResultsParams | None = None,
        options: RequestOptions | None = None,
    ) -> types.ResultRecord:
        return cast(
            types.ResultRecord,
            self._client.request(
                "GET", f"/runs/{segment(run_id)}/results", retry=True, options=options, query=params
            ),
        )

    def export(
        self,
        run_id: str,
        *,
        params: types.RunsExportParams | None = None,
        options: RequestOptions | None = None,
    ) -> bytes:
        return cast(
            bytes,
            self._client.request(
                "GET",
                f"/runs/{segment(run_id)}/export",
                retry=True,
                options=options,
                query=params,
                binary=True,
            ),
        )


class Evals(Resource):
    def list(
        self, *, params: types.EvalsListParams | None = None, options: RequestOptions | None = None
    ) -> types.Page_EvalRecord_:
        return cast(
            types.Page_EvalRecord_,
            self._client.request("GET", "/evals", retry=True, options=options, query=params),
        )

    def get(self, ref: str, *, options: RequestOptions | None = None) -> types.EvalRecord:
        return cast(
            types.EvalRecord,
            self._client.request("GET", f"/evals/{segment(ref)}", retry=True, options=options),
        )


class Evaluations(Resource):
    def create(
        self,
        body: types.NewEvaluation,
        *,
        idempotency_key: str,
        options: RequestOptions | None = None,
    ) -> types.RunRecord:
        validate_submission("evaluations", body)
        return cast(
            types.RunRecord,
            self._client.request(
                "POST",
                "/evaluations",
                retry=True,
                options=options,
                body=body,
                idempotency_key=idempotency_key,
            ),
        )

    def get(self, evaluation_id: str, *, options: RequestOptions | None = None) -> types.RunRecord:
        return cast(
            types.RunRecord,
            self._client.request(
                "GET", f"/evaluations/{segment(evaluation_id)}", retry=True, options=options
            ),
        )
