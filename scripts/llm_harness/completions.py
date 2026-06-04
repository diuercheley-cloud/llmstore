import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from .policy import PolicyEngine
from .providers import create_code_agent
from .sanitizer import Sanitizer

logger = logging.getLogger(__name__)


class CompletionSuggestion(BaseModel):
    text: str
    confidence: Optional[float] = None
    range: Optional[Dict[str, Any]] = None
    explanation: Optional[str] = None


class CompletionRequest(BaseModel):
    file_path: str
    cursor_line: int
    cursor_column: int
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    language: Optional[str] = None
    context_refs: Optional[List[str]] = Field(default_factory=list)


def split_file_at_cursor(
    file_content: str, cursor_line: int, cursor_column: int
) -> Tuple[str, str]:
    lines = file_content.splitlines(keepends=True)
    if cursor_line <= 0 or cursor_line > len(lines):
        return file_content, ""
        
    line_idx = cursor_line - 1
    target_line = lines[line_idx]
    col_idx = min(cursor_column, len(target_line))
    
    prefix = "".join(lines[:line_idx]) + target_line[:col_idx]
    suffix = target_line[col_idx:] + "".join(lines[line_idx + 1:])
    return prefix, suffix


async def get_completion_suggestions(
    request: CompletionRequest,
    workspace_root: str,
    provider_name: str,
    config_overrides: Optional[Dict[str, Any]] = None
) -> List[CompletionSuggestion]:
    # 1. Boundary / Safety Checks
    abs_workspace = os.path.abspath(workspace_root)
    if os.path.isabs(request.file_path):
        abs_path = os.path.abspath(request.file_path)
    else:
        abs_path = os.path.abspath(os.path.join(abs_workspace, request.file_path))

    # Reject if outside repository
    if not abs_path.startswith(abs_workspace):
        raise PermissionError("Access blocked: File is outside the workspace repository.")

    # Validate file path with PolicyEngine using relative path
    pe = PolicyEngine()
    try:
        rel_path = os.path.relpath(abs_path, abs_workspace)
    except ValueError:
        rel_path = request.file_path

    dec = pe.evaluate_file_path(rel_path)
    if not dec.allowed:
        raise PermissionError(f"Access blocked by policy: {dec.reason}")

    # Load prefix and suffix from file if not provided
    if request.prefix is None or request.suffix is None:
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"File not found: {request.file_path}")
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        prefix, suffix = split_file_at_cursor(content, request.cursor_line, request.cursor_column)
        request.prefix = prefix
        request.suffix = suffix

    # Detect language profile if possible
    try:
        from .languages import (
            detect_language_by_filename,
            detect_primary_language_in_workspace,
        )
        profile = detect_language_by_filename(request.file_path)
        if not profile:
            profile = detect_primary_language_in_workspace(workspace_root)
        if profile and not request.language:
            request.language = profile.name
    except Exception:
        profile = None

    # Sanitize prefix and suffix to redact secrets
    request.prefix = Sanitizer.sanitize_text(request.prefix)
    request.suffix = Sanitizer.sanitize_text(request.suffix)

    # 2. Fake / Stub provider bypass
    if provider_name in ("fake", "stub"):
        return [
            CompletionSuggestion(
                text="    print('hello world')",
                confidence=0.95,
                range={
                    "start_line": request.cursor_line,
                    "start_column": request.cursor_column
                },
                explanation="Autocomplete print statement"
            )
        ]

    # 3. Retrieve Context from Index
    retrieved_context = ""
    search_term = os.path.basename(request.file_path)
    try:
        from .indexing import get_retrieved_context
        retrieved_context = get_retrieved_context(
            search_term, workspace_root=workspace_root, max_tokens=1000
        )
    except Exception:
        pass

    # 4. Formulate Prompt
    pref_lines = (request.prefix or "").splitlines()
    suff_lines = (request.suffix or "").splitlines()
    local_prefix = "\n".join(pref_lines[-100:])
    local_suffix = "\n".join(suff_lines[:100])

    prompt = (
        "You are a code completion engine (FIM - Fill-in-the-Middle style).\n"
        "Given the PREFIX and SUFFIX of a file, generate the code that "
        "should be inserted at the cursor position.\n"
        "Respond ONLY with the code to insert, wrapped in a JSON object "
        "with this schema:\n"
        '{"text": "code to insert", "confidence": 0.9, '
        '"range": {"start_line": 20, "start_column": 5}, '
        '"explanation": "short optional explanation"}\n\n'
        "Return EXACTLY one JSON object, no other text or explanation.\n\n"
    )
    if retrieved_context:
        prompt += f"## Retrieved Context:\n{retrieved_context}\n\n"
        
    prompt += f"## File Path: {request.file_path}\n"
    prompt += f"## Language: {request.language or 'unknown'}\n"
    if profile:
        prompt += f"## Comment Style: {profile.comment_style}\n"
    prompt += (
        f"## Cursor Position: Line {request.cursor_line}, "
        f"Column {request.cursor_column}\n\n"
    )
    prompt += f"## PREFIX:\n{local_prefix}\n\n"
    prompt += f"## SUFFIX:\n{local_suffix}\n\n"

    # Limit LLM output tokens to 512
    cfg_dict = config_overrides or {}
    cfg_dict["max_tokens"] = 512

    # Instantiate Agent and get completion
    agent = create_code_agent(provider_name, cfg_dict)
    response = await agent.chat_completion([{"role": "user", "content": prompt}])

    content = ""
    if response and "choices" in response and response["choices"]:
        msg = response["choices"][0].get("message", {})
        content = msg.get("content", "").strip()

    try:
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            return [
                CompletionSuggestion(
                    text=data.get("text", ""),
                    confidence=data.get("confidence"),
                    range=data.get("range"),
                    explanation=data.get("explanation")
                )
            ]
    except Exception:
        pass

    return [
        CompletionSuggestion(
            text=content,
            confidence=0.5,
            range={"start_line": request.cursor_line, "start_column": request.cursor_column}
        )
    ]
