import difflib
import os
import re
from typing import Any, Optional

from ..models import PatchResult
from ..patcher import Patcher
from .models import ContextBundle, InlineEditRequest
from .rules import load_rules_for_path


async def perform_inline_edit(
    request: InlineEditRequest,
    provider: Any,
    policy_engine: Any,
    workspace: Any,
    dry_run: bool = False,
    context_bundle: Optional[ContextBundle] = None
) -> dict[str, Any]:
    # 1. Evaluate file path policy
    policy_decision = policy_engine.evaluate_file_path(request.file_path)
    if not policy_decision.allowed:
        raise PermissionError(
            f"Access to file '{request.file_path}' is denied "
            f"by Policy Engine: {policy_decision.reason}"
        )

    # 2. Read file content
    workspace_root = workspace.path if workspace else "."
    full_path = os.path.join(workspace_root, request.file_path)
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise FileNotFoundError(f"Target file not found: {request.file_path}")

    with open(full_path, "r", errors="ignore") as f:
        target_file_content = f.read()

    original_lines = target_file_content.splitlines(keepends=True)
    
    # Validate range
    start_line = max(1, request.start_line)
    end_line = min(len(original_lines), request.end_line)
    if start_line > len(original_lines) or start_line > end_line:
        raise ValueError(
            f"Invalid line range: {request.start_line}-{request.end_line} "
            f"for file with {len(original_lines)} lines"
        )

    start_idx = start_line - 1
    end_idx = end_line

    # 3. Load rules for this file path
    rules = load_rules_for_path(request.file_path, workspace_root)

    # 4. Construct prompt for LLM provider
    system_prompt = (
        "You are an expert software developer assisting with inline code editing.\n"
        "Your job is to rewrite the TARGET CODE BLOCK specified by the user based "
        "on their instructions.\n"
        "Follow the Custom AI Rules and general Guidelines strictly.\n"
        "Output ONLY the new replacement code for the target block. "
        "Do not include explanation, do not include markdown backticks "
        "(unless the code itself needs them), "
        "do not include code outside the target block. Return ONLY the "
        "drop-in replacement lines."
    )
    if rules:
        system_prompt += f"\n\n## Custom AI Rules:\n{rules}"
    
    system_prompt += f"\n\n{policy_engine.describe_for_agent()}"

    # Highlight target block in entire file context
    context_file_content = ""
    for i, line in enumerate(original_lines, 1):
        if i == start_line:
            context_file_content += f">>> TARGET BLOCK START >>>\n{line}"
        elif i == end_line:
            context_file_content += f"{line}<<< TARGET BLOCK END <<<\n"
        else:
            context_file_content += line

    user_prompt = f"Target File: {request.file_path}\n"
    user_prompt += f"Target Line Range: {start_line}-{end_line}\n\n"
    user_prompt += f"### Entire File Context:\n{context_file_content}\n\n"
    user_prompt += f"### Instruction:\n{request.instruction}\n\n"

    if context_bundle and not context_bundle.is_empty():
        user_prompt += f"### Context Reference Bundle:\n{context_bundle.to_text()}\n\n"

    user_prompt += (
        "Please provide the replacement code for the block between "
        ">>> TARGET BLOCK START >>> and <<< TARGET BLOCK END <<<."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    response = await provider.chat_completion(messages)
    
    content = ""
    if response and "choices" in response and response["choices"]:
        msg = response["choices"][0].get("message", {})
        content = msg.get("content", "")

    # Clean markdown formatting if present
    if content.startswith("```"):
        lines = content.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines)

    # Preserve code indentation while trimming wrapper blank lines.
    content = content.strip("\r\n")

    # Match file endings
    line_ending = "\n"
    if original_lines:
        if original_lines[0].endswith("\r\n"):
            line_ending = "\r\n"
    
    replacement_text = content
    replacement_chunks = replacement_text.splitlines()
    if (
        start_line == end_line
        and len(replacement_chunks) == 1
        and replacement_chunks[0].strip()
        and not replacement_chunks[0][:1].isspace()
    ):
        original_target_line = original_lines[start_idx]
        indent_match = re.match(r"^(\s+)", original_target_line)
        if indent_match:
            replacement_text = f"{indent_match.group(1)}{replacement_chunks[0]}"

    replacement_lines = [line + line_ending for line in replacement_text.splitlines()]
    modified_lines = original_lines[:start_idx] + replacement_lines + original_lines[end_idx:]

    # 5. Generate patch unified diff
    diff_list = list(difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a/{request.file_path}",
        tofile=f"b/{request.file_path}",
        lineterm="\n"
    ))
    diff_text = "".join(diff_list)

    if not diff_text:
        return {
            "success": True,
            "diff": "",
            "patch_result": PatchResult(
                success=True,
                mode="check" if dry_run else "apply",
                changed_files=[]
            )
        }

    # 6. Evaluate patch policy
    patch_decision = policy_engine.evaluate_patch(diff_text)
    if not patch_decision.allowed:
        raise PermissionError(
            f"Modified patch is blocked by Policy Engine: {patch_decision.reason}"
        )

    # 7. Apply patch via existing Patcher
    patcher = Patcher(workspace, policy_engine)
    patch_result = patcher.apply_patch(diff_text, dry_run=dry_run)

    return {
        "success": patch_result.success,
        "diff": diff_text,
        "patch_result": patch_result
    }
