from __future__ import annotations


class UCLSHRefusal(ValueError):
    def __init__(self, code: str, path: str = "$", detail: str = "") -> None:
        self.code = code
        self.path = path
        self.detail = detail
        suffix = f":{detail}" if detail else ""
        super().__init__(f"{code}@{path}{suffix}")


def refuse(code: str, path: str = "$", detail: str = "") -> None:
    raise UCLSHRefusal(code, path, detail)


def require(condition: bool, code: str, path: str = "$", detail: str = "") -> None:
    if not condition:
        refuse(code, path, detail)

