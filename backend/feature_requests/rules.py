"""Input rules for a feature request, shared by the assistant tool, the REST endpoints
and the admin form. Errors are ``{"path", "code", "message"}``; a personal-data error
never echoes the value it found."""

import re

from django.apps import apps

from assistant.pii import free_text_kind
from events.event_spec import CAPABILITIES, JSON_SCHEMA
from events.event_spec._issues import MESSAGES

from .models import COSTS, SEVERITIES

LIMITS = {
    "title": 100,
    "problem": 600,
    "desired": 600,
    "brief_fragment": 300,
    "tried_item": 300,
    "tried": 5,
    "workaround_used": 400,
    "touches": 12,
    "touch": 120,
}
INPUT_KEYS = (
    "title",
    "problem",
    "brief_fragment",
    "tried",
    "workaround",
    "desired",
    "touches",
    "severity",
)
# The primary term of a dedupe key: first one found in this order.
KEY_PRIORITY = ("cap", "new", "code", "field", "spec", "admin")
REACH_THRESHOLDS = ((5, "most_events"), (2, "some_events"))  # else few_events

_NEW = re.compile(r"new:[a-z][a-z0-9_]{1,60}")
_ADMIN = re.compile(r"admin:[a-z][a-z0-9_]{1,60}")
_CODE = re.compile(r"code:[a-z][a-z0-9_]{1,60}")
_CAP = re.compile(r"cap:[a-z][a-z0-9_]{1,60}")
_FIELD = re.compile(r"field:([A-Za-z]{1,40})\.([a-z][a-z0-9_]{0,60})")
_SPEC = re.compile(r"spec:[a-z_][a-z0-9_\[\].]{0,200}")

CAPABILITY_IDS = frozenset(
    c["id"] for c in CAPABILITIES["supported"] + CAPABILITIES["unsupported"]
)
CODES = frozenset(MESSAGES)
_CAP_TERMS = frozenset(f"cap:{i}" for i in CAPABILITY_IDS)


class FeatureRequestError(Exception):
    def __init__(self, errors: list[dict]):
        self.errors = errors
        super().__init__("; ".join(f"{e['path']}: {e['message']}" for e in errors))


def _err(path: str, code: str, message: str) -> dict:
    return {"path": path, "code": code, "message": message}


def _schema_resolve(node: dict) -> dict:
    """Follow ``$ref`` and pick the non-null branch of an Optional."""
    while True:
        if "$ref" in node:
            node = JSON_SCHEMA["$defs"][node["$ref"].rsplit("/", 1)[-1]]
        elif "anyOf" in node:
            node = next(
                (o for o in node["anyOf"] if o.get("type") != "null"), node["anyOf"][0]
            )
        else:
            return node


def spec_path_exists(path: str) -> bool:
    """``spec:`` paths use ``[]`` for lists, e.g. ``ticket_types[].requires_ticket_type``."""
    node = _schema_resolve(JSON_SCHEMA)
    for segment in path.split("."):
        is_list = segment.endswith("[]")
        name = segment[:-2] if is_list else segment
        props = node.get("properties", {})
        if name not in props:
            return False
        node = _schema_resolve(props[name])
        if is_list:
            if "items" not in node:
                return False
            node = _schema_resolve(node["items"])
    return True


def field_exists(model_name: str, field: str) -> bool:
    try:
        model = apps.get_model("events", model_name)
    except LookupError:
        return False
    return any(f.name == field for f in model._meta.get_fields())


def touch_problem(term: str) -> str | None:
    """Why a ``touches`` term is not in the vocabulary, or None. Names no value."""
    if not isinstance(term, str) or len(term) > LIMITS["touch"]:
        return "must be a short vocabulary term"
    if _CAP.fullmatch(term):
        return None if term in _CAP_TERMS else "is not a capability id"
    if _NEW.fullmatch(term) or _ADMIN.fullmatch(term):
        return None
    if _CODE.fullmatch(term):
        return None if term[len("code:") :] in CODES else "is not a validator code"
    if m := _FIELD.fullmatch(term):
        return None if field_exists(m.group(1), m.group(2)) else "is not a field"
    if _SPEC.fullmatch(term):
        return None if spec_path_exists(term[len("spec:") :]) else "is not a spec path"
    return "must start with cap:, code:, field:, spec:, admin: or new:"


def _clean_touches(raw, errors: list[dict]) -> list[str]:
    if not isinstance(raw, list) or not 1 <= len(raw) <= LIMITS["touches"]:
        errors.append(
            _err(
                "touches", "invalid", f"Give 1 to {LIMITS['touches']} vocabulary terms."
            )
        )
        return []
    out = []
    for i, term in enumerate(raw):
        why = touch_problem(term)
        if why:
            # A new: id is the maintainer's to curate, so it only needs the shape.
            errors.append(_err(f"touches[{i}]", "unknown_term", f"Term {why}."))
        elif pii := personal_data_errors(f"touches[{i}]", term):
            # new: and admin: ids are free-form, and the term becomes the dedupe key.
            errors.extend(pii)
        elif term not in out:
            out.append(term)
    return out


def personal_data_errors(path: str, text: str) -> list[dict]:
    kind = free_text_kind(text)
    if kind is None:
        return []
    return [
        _err(
            path,
            "personal_data",
            f"Looks like {kind}. Describe the rule or shape, not a person, date or reference.",
        )
    ]


def clean_input(data) -> dict:
    """The validated, normalised input, or FeatureRequestError with every problem."""
    if not isinstance(data, dict):
        raise FeatureRequestError([_err("", "invalid", "Must be a JSON object.")])
    errors: list[dict] = []
    for key in data:
        if key not in INPUT_KEYS:
            errors.append(_err(str(key)[:40], "extra_forbidden", "Not a field."))
    out: dict = {}

    def text(name, limit, required=True):
        value = data.get(name)
        if value is None and not required:
            return None
        if not isinstance(value, str) or (required and not value.strip()):
            errors.append(_err(name, "invalid", "Must be non-empty text."))
            return ""
        value = value.strip()
        if len(value) > limit:
            errors.append(_err(name, "too_long", f"At most {limit} characters."))
        errors.extend(personal_data_errors(name, value))
        return value

    out["title"] = text("title", LIMITS["title"])
    out["problem"] = text("problem", LIMITS["problem"])
    out["desired"] = text("desired", LIMITS["desired"])
    out["brief_fragment"] = text("brief_fragment", LIMITS["brief_fragment"], False)

    tried = data.get("tried") or []
    if not isinstance(tried, list) or len(tried) > LIMITS["tried"]:
        errors.append(_err("tried", "invalid", f"At most {LIMITS['tried']} items."))
        tried = []
    out["tried"] = []
    for i, item in enumerate(tried):
        if not isinstance(item, str) or not item.strip():
            errors.append(_err(f"tried[{i}]", "invalid", "Must be non-empty text."))
            continue
        item = item.strip()
        if len(item) > LIMITS["tried_item"]:
            errors.append(
                _err(
                    f"tried[{i}]",
                    "too_long",
                    f"At most {LIMITS['tried_item']} characters.",
                )
            )
        errors.extend(personal_data_errors(f"tried[{i}]", item))
        out["tried"].append(item)

    workaround = data.get("workaround")
    out["workaround"] = None
    if workaround is not None:
        if not isinstance(workaround, dict) or set(workaround) - {"used", "cost"}:
            errors.append(_err("workaround", "invalid", "Give used and cost, or null."))
        else:
            used = workaround.get("used")
            cost = workaround.get("cost")
            if not isinstance(used, str) or not used.strip():
                errors.append(
                    _err("workaround.used", "invalid", "Must be non-empty text.")
                )
                used = ""
            used = used.strip()
            if len(used) > LIMITS["workaround_used"]:
                errors.append(
                    _err(
                        "workaround.used",
                        "too_long",
                        f"At most {LIMITS['workaround_used']} characters.",
                    )
                )
            errors.extend(personal_data_errors("workaround.used", used))
            if cost not in dict(COSTS):
                errors.append(
                    _err(
                        "workaround.cost", "invalid", "Must be one of the cost values."
                    )
                )
            out["workaround"] = {"used": used, "cost": cost}

    if data.get("severity") not in dict(SEVERITIES):
        errors.append(
            _err("severity", "invalid", "Must be one of the severity values.")
        )
    out["severity"] = data.get("severity")
    out["touches"] = _clean_touches(data.get("touches"), errors)
    if errors:
        raise FeatureRequestError(errors)
    return out


PRIORITY_ORDER = {prefix: i for i, prefix in enumerate(KEY_PRIORITY)}


def dedupe_key(touches: list[str]) -> str:
    """The highest-priority term; the first of its kind when several."""
    return min(touches, key=lambda t: PRIORITY_ORDER.get(t.split(":", 1)[0], 99))


def derive(cleaned: dict) -> dict:
    """Fields the assistant does not send: key, validator, layers, evidence. Reach is
    counted from the stored requests, see services.py."""
    touches = cleaned["touches"]
    layers = set()
    evidence = []
    for term in touches:
        prefix = term.split(":", 1)[0]
        if prefix in ("cap", "new", "field", "spec"):
            layers.add("model")
        if prefix == "code":
            layers.add("validator")
            evidence.append({"kind": "validation_code", "ref": term})
        elif prefix == "spec":
            evidence.append({"kind": "spec_path", "ref": term})
        elif prefix == "admin":
            layers.add("admin_ui")
    return {
        "dedupe_key": dedupe_key(touches),
        "validator": "existing"
        if any(t.startswith("code:") for t in touches)
        else "no",
        "layers": sorted(layers),
        "evidence": evidence,
    }
