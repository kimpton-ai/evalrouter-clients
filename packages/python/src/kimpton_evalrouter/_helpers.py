"""Local waiting and explicit export destinations; neither starts evaluations."""

from __future__ import annotations

import os
import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path

from . import types
from ._transport import ClientError, RequestOptions, Resource, checkpoint, pause, positive

TERMINAL = {"completed", "partial", "failed", "cancelled"}
STATES = TERMINAL | {"queued", "running", "cancelling", "finalizing"}


class RunHelpers(Resource):
    def get(self, run_id: str, *, options: RequestOptions | None = None) -> types.RunRecord:
        raise NotImplementedError

    def export(
        self,
        run_id: str,
        *,
        params: types.RunsExportParams | None = None,
        options: RequestOptions | None = None,
    ) -> bytes:
        raise NotImplementedError

    def wait(
        self,
        run_id: str,
        *,
        timeout: float = 3600,
        poll_interval: float = 2,
        cancel_event: threading.Event | None = None,
        on_progress: Callable[[types.RunRecord], None] | None = None,
    ) -> types.RunRecord:
        deadline = time.monotonic() + positive(timeout, "Wait timeout")
        interval = positive(poll_interval, "Poll interval")
        while True:
            remaining = checkpoint(deadline, cancel_event)
            run = self.get(
                run_id, options=RequestOptions(timeout=remaining, cancel_event=cancel_event)
            )
            checkpoint(deadline, cancel_event)
            if run.get("status") not in STATES:
                raise ClientError("invalid_response", "API returned an unknown evaluation state.")
            if on_progress:
                on_progress(run)
            checkpoint(deadline, cancel_event)
            if run["status"] in TERMINAL:
                return run
            pause(interval, deadline, cancel_event)

    def export_to_file(
        self,
        run_id: str,
        destination: str | Path,
        *,
        params: types.RunsExportParams | None = None,
        options: RequestOptions | None = None,
        overwrite: bool = False,
    ) -> Path:
        path = Path(destination)
        if not overwrite and path.exists():
            raise ClientError("destination_exists", "Export destination already exists.")
        data = self.export(run_id, params=params, options=options)
        return save_export(data, path, overwrite=overwrite)


def save_export(data: bytes, destination: str | Path, *, overwrite: bool = False) -> Path:
    path = Path(destination)
    if not overwrite and path.exists():
        raise ClientError("destination_exists", "Export destination already exists.")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=".kimpton-export-", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)
            temporary.unlink()
        return path
    except FileExistsError:
        raise ClientError("destination_exists", "Export destination already exists.") from None
    except OSError:
        raise ClientError(
            "export_write_failed", "Could not write the export destination."
        ) from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
