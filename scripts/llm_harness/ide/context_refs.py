import ast
import os
import re

from ..sanitizer import Sanitizer
from ..tokenizer import TokenCounter
from .models import ContextBundle, ContextRef, ContextRefType


def parse_refs(text: str, workspace=None) -> list[ContextRef]:
    refs = []
    tokens = re.findall(r"@\S+", text)
    for token in tokens:
        cleaned_token = token
        while cleaned_token and cleaned_token[-1] in ".,?!;)]}":
            cleaned_token = cleaned_token[:-1]

        if not cleaned_token.startswith("@"):
            continue

        ref_str = cleaned_token[1:]

        if ref_str.startswith("file:"):
            path = ref_str[len("file:") :]
            refs.append(ContextRef(ref_type=ContextRefType.FILE, path=path))
        elif ref_str.startswith("folder:"):
            path = ref_str[len("folder:") :]
            refs.append(ContextRef(ref_type=ContextRefType.FOLDER, path=path))
        elif ref_str.startswith("symbol:"):
            symbol = ref_str[len("symbol:") :]
            refs.append(ContextRef(ref_type=ContextRefType.SYMBOL, path="", symbol=symbol))
        elif ref_str.startswith("selection:"):
            content = ref_str[len("selection:") :]
            if ":" in content:
                parts = content.rsplit(":", 1)
                path = parts[0]
                line_range = parts[1]
                start_line, end_line = 1, 1
                if "-" in line_range:
                    r_parts = line_range.split("-")
                    try:
                        start_line = int(r_parts[0])
                        end_line = int(r_parts[1])
                    except ValueError:
                        pass
                else:
                    try:
                        start_line = end_line = int(line_range)
                    except ValueError:
                        pass
                refs.append(
                    ContextRef(
                        ref_type=ContextRefType.SELECTION,
                        path=path,
                        start_line=start_line,
                        end_line=end_line,
                    )
                )
        else:
            # Short forms
            match_range = re.search(r":(\d+)(?:-(\d+))?$", ref_str)
            if match_range:
                start_line = int(match_range.group(1))
                end_line = int(match_range.group(2)) if match_range.group(2) else start_line
                path = ref_str[: match_range.start()]
                refs.append(
                    ContextRef(
                        ref_type=ContextRefType.SELECTION,
                        path=path,
                        start_line=start_line,
                        end_line=end_line,
                    )
                )
                continue

            workspace_root = workspace.path if workspace else "."
            resolved_path = os.path.join(workspace_root, ref_str)

            if os.path.isdir(resolved_path):
                refs.append(ContextRef(ref_type=ContextRefType.FOLDER, path=ref_str))
            elif os.path.isfile(resolved_path):
                refs.append(ContextRef(ref_type=ContextRefType.FILE, path=ref_str))
            else:
                if "/" in ref_str or "\\" in ref_str or "." in ref_str:
                    refs.append(ContextRef(ref_type=ContextRefType.FILE, path=ref_str))
                else:
                    refs.append(ContextRef(ref_type=ContextRefType.SYMBOL, path="", symbol=ref_str))
    return refs


async def build_context_bundle(
    refs: list[ContextRef], workspace, policy_engine, token_budget: int = 4000
) -> ContextBundle:
    bundle = ContextBundle()
    tokenizer = TokenCounter(method="auto")
    running_tokens = 0

    def truncate_to_tokens(content: str, budget: int) -> str:
        if budget <= 0:
            return ""
        char_len = budget * 4
        truncated = content[:char_len]
        while tokenizer.count_tokens(truncated) > budget and len(truncated) > 0:
            char_len = int(char_len * 0.9)
            truncated = content[:char_len]
        return truncated + "\n... [TRUNCATED] ..."

    workspace_root = workspace.path if workspace else "."

    for ref in refs:
        if running_tokens >= token_budget:
            break

        # Validate path
        if ref.ref_type in (ContextRefType.FILE, ContextRefType.FOLDER, ContextRefType.SELECTION):
            # Check for path traversal or absolute escapes
            normalized_path = os.path.normpath(ref.path)
            if normalized_path.startswith("..") or normalized_path.startswith("/"):
                raise PermissionError("Path traversal or absolute path detected")

            decision = policy_engine.evaluate_file_path(ref.path)
            if not decision.allowed:
                raise PermissionError(
                    f"Access to path '{ref.path}' blocked by policy: {decision.reason}"
                )

        if ref.ref_type == ContextRefType.FILE:
            full_path = os.path.join(workspace_root, ref.path)
            if os.path.exists(full_path) and os.path.isfile(full_path):
                with open(full_path, errors="ignore") as f:
                    content = f.read()
                sanitized = Sanitizer.sanitize_text(content)
                tokens = tokenizer.count_tokens(sanitized)
                if running_tokens + tokens <= token_budget:
                    bundle.files.append({"path": ref.path, "content": sanitized})
                    running_tokens += tokens
                else:
                    rem = token_budget - running_tokens
                    if rem > 50:
                        trunc = truncate_to_tokens(sanitized, rem)
                        bundle.files.append({"path": ref.path, "content": trunc})
                        running_tokens = token_budget
                    else:
                        break

        elif ref.ref_type == ContextRefType.SELECTION:
            full_path = os.path.join(workspace_root, ref.path)
            if os.path.exists(full_path) and os.path.isfile(full_path):
                with open(full_path, errors="ignore") as f:
                    lines = f.readlines()
                start = max(1, ref.start_line or 1)
                end = min(len(lines), ref.end_line or len(lines))
                content = "".join(lines[start - 1 : end])
                sanitized = Sanitizer.sanitize_text(content)
                tokens = tokenizer.count_tokens(sanitized)
                if running_tokens + tokens <= token_budget:
                    bundle.selections.append(
                        {
                            "path": ref.path,
                            "start_line": start,
                            "end_line": end,
                            "content": sanitized,
                        }
                    )
                    running_tokens += tokens
                else:
                    rem = token_budget - running_tokens
                    if rem > 50:
                        trunc = truncate_to_tokens(sanitized, rem)
                        bundle.selections.append(
                            {
                                "path": ref.path,
                                "start_line": start,
                                "end_line": end,
                                "content": trunc,
                            }
                        )
                        running_tokens = token_budget
                    else:
                        break

        elif ref.ref_type == ContextRefType.FOLDER:
            full_dir = os.path.join(workspace_root, ref.path)
            files_to_add = []
            if os.path.exists(full_dir) and os.path.isdir(full_dir):
                for root, dirs, files in os.walk(full_dir):
                    dirs[:] = [d for d in dirs if not d.startswith(".")]
                    for file in files:
                        if file.startswith("."):
                            continue
                        rel_path = os.path.relpath(os.path.join(root, file), workspace_root)
                        normalized_rel = os.path.normpath(rel_path)
                        if normalized_rel.startswith("..") or normalized_rel.startswith("/"):
                            continue
                        decision = policy_engine.evaluate_file_path(rel_path)
                        if decision.allowed:
                            files_to_add.append(rel_path)
            files_to_add.sort()

            for file_path in files_to_add:
                if running_tokens >= token_budget:
                    break
                full_file = os.path.join(workspace_root, file_path)
                if os.path.exists(full_file) and os.path.isfile(full_file):
                    with open(full_file, errors="ignore") as f:
                        content = f.read()
                    sanitized = Sanitizer.sanitize_text(content)
                    tokens = tokenizer.count_tokens(sanitized)
                    if running_tokens + tokens <= token_budget:
                        bundle.files.append({"path": file_path, "content": sanitized})
                        running_tokens += tokens
                    else:
                        rem = token_budget - running_tokens
                        if rem > 50:
                            trunc = truncate_to_tokens(sanitized, rem)
                            bundle.files.append({"path": file_path, "content": trunc})
                            running_tokens = token_budget
                        else:
                            break

        elif ref.ref_type == ContextRefType.SYMBOL:
            symbol_name = ref.symbol
            matches = []
            for root, dirs, files in os.walk(workspace_root):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for file in files:
                    if not file.endswith(".py"):
                        continue
                    rel_path = os.path.relpath(os.path.join(root, file), workspace_root)
                    normalized_rel = os.path.normpath(rel_path)
                    if normalized_rel.startswith("..") or normalized_rel.startswith("/"):
                        continue
                    decision = policy_engine.evaluate_file_path(rel_path)
                    if not decision.allowed:
                        continue

                    full_file = os.path.join(root, file)
                    try:
                        with open(full_file, errors="ignore") as f:
                            source = f.read()
                        tree = ast.parse(source)
                        for node in ast.walk(tree):
                            if isinstance(
                                node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)
                            ):
                                if node.name == symbol_name:
                                    lines = source.splitlines(keepends=True)
                                    start = node.lineno
                                    end = getattr(node, "end_lineno", len(lines))
                                    body = "".join(lines[start - 1 : end])
                                    matches.append(
                                        {"name": symbol_name, "path": rel_path, "content": body}
                                    )
                    except Exception:
                        pass

            for m in matches:
                if running_tokens >= token_budget:
                    break
                sanitized = Sanitizer.sanitize_text(m["content"])
                tokens = tokenizer.count_tokens(sanitized)
                if running_tokens + tokens <= token_budget:
                    bundle.symbols.append(
                        {"name": m["name"], "path": m["path"], "content": sanitized}
                    )
                    running_tokens += tokens
                else:
                    rem = token_budget - running_tokens
                    if rem > 50:
                        trunc = truncate_to_tokens(sanitized, rem)
                        bundle.symbols.append(
                            {"name": m["name"], "path": m["path"], "content": trunc}
                        )
                        running_tokens = token_budget
                    else:
                        break

    bundle.token_count = running_tokens
    return bundle
