import ast
from typing import Any

from .symbol_index import LanguageParser


class PythonASTParser(LanguageParser):
    def parse(self, content: str) -> dict[str, Any]:
        try:
            tree = ast.parse(content)
        except Exception:
            return {"classes": [], "functions": [], "imports": []}

        classes = []
        functions = []
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                docstring = ast.get_docstring(node) or ""
                methods = []
                class_start = node.lineno
                class_end = getattr(node, "end_lineno", class_start)

                for subnode in node.body:
                    if isinstance(subnode, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_doc = ast.get_docstring(subnode) or ""
                        method_start = subnode.lineno
                        method_end = getattr(subnode, "end_lineno", method_start)
                        args = [arg.arg for arg in subnode.args.args]
                        methods.append(
                            {
                                "name": subnode.name,
                                "start_line": method_start,
                                "end_line": method_end,
                                "docstring": method_doc,
                                "args": args,
                            }
                        )
                classes.append(
                    {
                        "name": node.name,
                        "start_line": class_start,
                        "end_line": class_end,
                        "docstring": docstring,
                        "methods": methods,
                    }
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                docstring = ast.get_docstring(node) or ""
                func_start = node.lineno
                func_end = getattr(node, "end_lineno", func_start)
                args = [arg.arg for arg in node.args.args]
                functions.append(
                    {
                        "name": node.name,
                        "start_line": func_start,
                        "end_line": func_end,
                        "docstring": docstring,
                        "args": args,
                    }
                )
        return {"classes": classes, "functions": functions, "imports": list(set(imports))}
