"""a permission in CAPMAS's training format, shared by its scorer and its training export so both see the same text."""


def capmas_text(candidate):
    permission, _, meaning = candidate.partition(" (")
    service, operation, resource = (permission.split(":", 2) + ["", ""])[:3]
    scope = "" if resource in ("skill", "tool", "") else f" on '{resource}'"
    return f"Using service environment '{service}', execute capacity '{operation}'{scope} to: {meaning.rstrip(')') or operation}"
