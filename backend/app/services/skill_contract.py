from __future__ import annotations

from typing import Any, Dict, List, Tuple


def validate_contract(contract: Dict[str, Any], failure_semantics: Dict[str, Any] | None = None) -> Tuple[bool, List[str]]:
    errs: List[str] = []
    if not isinstance(contract, dict):
        return False, ["contract must be an object"]
    if contract.get("type") != "object":
        errs.append("contract.type must be 'object'")
    props = contract.get("properties")
    if not isinstance(props, dict) or not props:
        errs.append("contract.properties must be a non-empty object")
    req = contract.get("required", [])
    if req is not None and not isinstance(req, list):
        errs.append("contract.required must be an array")
    if isinstance(req, list):
        for r in req:
            if not isinstance(r, str):
                errs.append("contract.required must contain strings")
                break
    if isinstance(props, dict):
        for key, spec in props.items():
            if not isinstance(spec, dict):
                errs.append(f"property '{key}' must be an object schema")
                continue
            t = spec.get("type")
            if t not in ("string", "number", "integer", "boolean", "object", "array"):
                errs.append(f"property '{key}' has unsupported type")
            enum = spec.get("enum")
            if enum is not None and not isinstance(enum, list):
                errs.append(f"property '{key}' enum must be an array")
    if failure_semantics is not None:
        if not isinstance(failure_semantics, dict):
            errs.append("failure_semantics must be an object")
        else:
            codes = failure_semantics.get("codes", [])
            if codes is not None and not isinstance(codes, list):
                errs.append("failure_semantics.codes must be an array")
            elif isinstance(codes, list):
                for item in codes:
                    if not isinstance(item, dict):
                        errs.append("each failure_semantics code must be an object")
                        continue
                    if not (item.get("code") and isinstance(item.get("code"), str)):
                        errs.append("failure_semantics code item requires string 'code'")
    return len(errs) == 0, errs


def _type_ok(value: Any, t: str) -> bool:
    if t == "string":
        return isinstance(value, str)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "boolean":
        return isinstance(value, bool)
    if t == "object":
        return isinstance(value, dict)
    if t == "array":
        return isinstance(value, list)
    return False


def validate_payload(contract: Dict[str, Any], payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errs: List[str] = []
    if not isinstance(payload, dict):
        return False, ["payload must be an object"]
    props = contract.get("properties") or {}
    req = contract.get("required") or []
    for r in req:
        if r not in payload:
            errs.append(f"missing required field: {r}")
    for k, v in payload.items():
        spec = props.get(k)
        if not spec:
            continue
        t = spec.get("type")
        if t and not _type_ok(v, t):
            errs.append(f"field '{k}' expected type {t}")
            continue
        enum = spec.get("enum")
        if isinstance(enum, list) and v not in enum:
            errs.append(f"field '{k}' not in enum")
    return len(errs) == 0, errs

