from dataclasses import dataclass
from typing import Any, Callable

DOMAIN = "1306"


_TYPE_NAMES = {str: "string", int: "integer", bool: "boolean", float: "number"}


@dataclass(frozen=True)
class Tool:
    name: str
    handler: Callable[..., dict]
    fields: dict[str, type | dict[str, Any]]
    inject_domain: bool = False


class ToolRegistry:
    def __init__(self):
        self.tools: dict[str, Tool] = {}

    def register(self, name, handler, fields, *, inject_domain=False):
        normalized = fields if isinstance(fields, dict) else {field: object for field in fields}
        self.tools[name] = Tool(name, handler, dict(normalized), inject_domain)

    def schemas(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "strict": True,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            name: spec if isinstance(spec, dict) else {"type": _TYPE_NAMES.get(spec, "object")}
                            for name, spec in tool.fields.items()
                        },
                        "required": list(tool.fields),
                        "additionalProperties": False,
                    },
                },
            }
            for tool in self.tools.values()
        ]

    def dispatch(self, name, args, context=None):
        tool = self.tools.get(name)
        if tool is None:
            return {"error": {"code": "unknown_tool"}}
        if not isinstance(args, dict) or set(args) != set(tool.fields) or "domain" in args:
            return {"error": {"code": "invalid_arguments"}}
        if any(not _valid(args[field], spec) for field, spec in tool.fields.items()):
            return {"error": {"code": "invalid_arguments"}}
        runtime_args = dict(args)
        if context is not None:
            runtime_args["context"] = context
        if tool.inject_domain:
            runtime_args["domain"] = DOMAIN
        try:
            result = tool.handler(**runtime_args)
            return result if isinstance(result, dict) else {"error": {"code": "internal_error"}}
        except Exception:
            return {"error": {"code": "internal_error"}}

    def dispatch_many(self, calls, context=None):
        return [self.dispatch(name, args, context) for name, args in calls]


def _valid(value, spec):
    if isinstance(spec, type):
        return isinstance(value, spec) and not (spec is int and isinstance(value, bool))
    expected = {"string": str, "integer": int, "boolean": bool, "number": (int, float)}.get(spec.get("type"))
    if expected is None or not isinstance(value, expected) or spec.get("type") == "integer" and isinstance(value, bool):
        return False
    return spec.get("minimum", value) <= value <= spec.get("maximum", value)
