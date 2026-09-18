"""Validate supported evaluation inputs before issuing a request."""

from ._transport import ClientError


def validate_submission(resource, body):
    allowed = (
        {"selection", "model", "coverage", "max_charge_microusd"}
        if resource == "quotes"
        else {
            "model",
            "eval",
            "budget_usd",
            "max_charge_microusd",
            "provider",
            "coverage",
            "name",
            "metadata",
            "split",
        }
    )
    if not isinstance(body, dict) or set(body) - allowed:
        raise ClientError(
            "unsupported_feature", "This submission contains unsupported input fields."
        )
    model = body.get("model")
    if isinstance(model, str) and resource == "evaluations":
        valid = bool(model) and not model.startswith(("checkpoint:", "agent:", "artifact:"))
    elif isinstance(model, dict):
        keys = {"managed": {"kind", "route_id"}, "connection": {"kind", "connection_id"}}
        kind = model.get("kind")
        valid = isinstance(kind, str) and kind in keys and set(model) == keys[kind]
    else:
        valid = False
    if resource == "quotes":
        selection = body.get("selection")
        valid = (
            valid
            and isinstance(selection, dict)
            and (
                set(selection) == {"profile_ids"}
                or "eval" in selection
                and not set(selection) - {"eval", "provider", "split"}
            )
        )
    if not valid:
        raise ClientError(
            "unsupported_feature",
            "Choose an admitted eval and a managed model or checked connection.",
        )
