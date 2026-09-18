import { ClientError } from "./transport.js";

/** Validate supported evaluation inputs before issuing a request. */
export function validateSubmission(resource: "quotes" | "evaluations", input: unknown): void {
  const object = (value: unknown): value is Record<string, unknown> =>
    value !== null && typeof value === "object" && !Array.isArray(value);
  const allowed = new Set(resource === "quotes"
    ? ["selection", "model", "coverage", "max_charge_microusd"]
    : ["model", "eval", "budget_usd", "max_charge_microusd", "provider", "coverage", "name", "metadata", "split"]);
  const fail = () => { throw new ClientError("unsupported_feature", "Choose an admitted eval and a managed model or checked connection."); };
  if (!object(input) || Object.keys(input).some((key) => !allowed.has(key))) return fail();
  const model = input.model;
  if (typeof model === "string" && resource === "evaluations") {
    if (!model || /^(checkpoint|agent|artifact):/.test(model)) return fail();
  } else if (object(model)) {
    const keys = model.kind === "managed" ? ["kind", "route_id"] : model.kind === "connection" ? ["kind", "connection_id"] : [];
    if (keys.length === 0 || Object.keys(model).length !== keys.length || keys.some((key) => !(key in model))) return fail();
  } else return fail();
  if (resource === "quotes") {
    const selection = input.selection;
    if (!object(selection)) return fail();
    const keys = Object.keys(selection);
    if (!(keys.length === 1 && keys[0] === "profile_ids") &&
        !("eval" in selection && keys.every((key) => ["eval", "provider", "split"].includes(key)))) return fail();
  }
}
