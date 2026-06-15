import abc
import re
from typing import Any


class LanguageParser(abc.ABC):
    @abc.abstractmethod
    def parse(self, content: str) -> dict[str, Any]:
        pass


class RegexFallbackParser(LanguageParser):
    def parse(self, content: str) -> dict[str, Any]:
        classes: list[dict[str, Any]] = []
        functions: list[dict[str, Any]] = []
        imports: list[str] = []

        class_matches = re.finditer(r"\b(?:class|interface)\s+([a-zA-Z_][a-zA-Z0-9_]*)", content)
        for match in class_matches:
            name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1
            classes.append(
                {
                    "name": name,
                    "start_line": line_num,
                    "end_line": line_num,
                    "docstring": "",
                    "methods": [],
                }
            )

        func_matches = re.finditer(
            r"\b(?:function\s+([a-zA-Z_][a-zA-Z0-9_]*)|"
            r"([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*\{)",
            content,
        )
        for match in func_matches:
            name = match.group(1) or match.group(2)
            if name and name not in {"if", "for", "while", "switch", "catch", "class", "interface"}:
                line_num = content[: match.start()].count("\n") + 1
                functions.append(
                    {
                        "name": name,
                        "start_line": line_num,
                        "end_line": line_num,
                        "docstring": "",
                        "args": [],
                    }
                )

        imports_found = []
        # require('...') or require("...")
        for m in re.finditer(r"\brequire\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", content):
            imports_found.append(m.group(1))
        # import ... from '...' or import '...'
        for m in re.finditer(r"\bimport\s+(?:[^'\"]+\bfrom\s+)?['\"]([^'\"]+)['\"]", content):
            imports_found.append(m.group(1))
        for m in re.finditer(r"\bimport\s+['\"]([^'\"]+)['\"]", content):
            imports_found.append(m.group(1))

        for imp in imports_found:
            imports.append(imp)

        return {"classes": classes, "functions": functions, "imports": list(set(imports))}
