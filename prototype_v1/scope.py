from dataclasses import dataclass
from .guardrails import DOMAIN, canonical


@dataclass
class TerritoryRegistry:
    records: list[dict]
    verified: bool = False

    def accepts(self, code, label):
        return (
            code == DOMAIN
            or self.verified
            and any(
                r.get("code") == code
                and r.get("ancestor") == DOMAIN
                and canonical(r.get("name", "")) == canonical(label or "")
                for r in self.records
            )
        )

    def require(self, code, label):
        if not self.accepts(code, label):
            return {"error": {"code": "out_of_scope_region"}}
        return None


# Child territory content remains closed until official MFD/PIC signoff.
registry = TerritoryRegistry([])
