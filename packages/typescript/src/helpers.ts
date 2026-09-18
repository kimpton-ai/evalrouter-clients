import { link, lstat, open, rename, unlink } from "node:fs/promises";
import { randomUUID } from "node:crypto";
import { dirname, join } from "node:path";
import type { RunRecord, RunsExportParams } from "./types.js";
import {
  ClientError,
  Resource,
  checkpoint,
  pause,
  positive,
  type RequestOptions,
} from "./transport.js";

export type WaitOptions = {
  timeoutMs?: number;
  pollIntervalMs?: number;
  signal?: AbortSignal;
  onProgress?: (run: RunRecord) => void | Promise<void>;
};
const terminal = new Set(["completed", "partial", "failed", "cancelled"]);
const states = new Set([
  ...terminal,
  "queued",
  "running",
  "cancelling",
  "finalizing",
]);
export abstract class RunHelpers extends Resource {
  abstract get(runId: string, options?: RequestOptions): Promise<RunRecord>;
  abstract export(
    runId: string,
    params?: RunsExportParams,
    options?: RequestOptions,
  ): Promise<Uint8Array>;
  async wait(runId: string, options: WaitOptions = {}): Promise<RunRecord> {
    const deadline =
      performance.now() +
      positive(options.timeoutMs ?? 3_600_000, "Wait timeout");
    const interval = positive(options.pollIntervalMs ?? 2000, "Poll interval");
    while (true) {
      const run = await this.get(runId, {
        timeoutMs: checkpoint(deadline, options.signal),
        signal: options.signal,
      });
      checkpoint(deadline, options.signal);
      if (!states.has(run.status))
        throw new ClientError(
          "invalid_response",
          "API returned an unknown evaluation state.",
        );
      if (options.onProgress) await options.onProgress(run);
      checkpoint(deadline, options.signal);
      if (terminal.has(run.status)) return run;
      await pause(interval, deadline, options.signal);
    }
  }
  async exportToFile(
    runId: string,
    destination: string,
    params: RunsExportParams = {},
    options: RequestOptions & { overwrite?: boolean } = {},
  ): Promise<string> {
    if (!options.overwrite) {
      try {
        await lstat(destination);
        throw new ClientError(
          "destination_exists",
          "Export destination already exists.",
        );
      } catch (e) {
        if ((e as NodeJS.ErrnoException).code !== "ENOENT")
          throw e instanceof ClientError
            ? e
            : new ClientError(
                "export_write_failed",
                "Could not access the export destination.",
              );
      }
    }
    const bytes = await this.export(runId, params, options);
    const temporary = join(
      dirname(destination),
      `.kimpton-export-${randomUUID()}`,
    );
    try {
      const file = await open(temporary, "wx", 0o600);
      try {
        await file.writeFile(bytes);
        await file.sync();
      } finally {
        await file.close();
      }
      if (options.overwrite) await rename(temporary, destination);
      else await link(temporary, destination);
      return destination;
    } catch (e) {
      throw new ClientError(
        (e as NodeJS.ErrnoException).code === "EEXIST"
          ? "destination_exists"
          : "export_write_failed",
        "Could not write the export destination.",
      );
    } finally {
      await unlink(temporary).catch(() => undefined);
    }
  }
}
