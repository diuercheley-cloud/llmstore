import json
from collections import defaultdict

with open("scratch/ruff_errors.json", encoding="utf-8") as f:
    data = json.load(f)

# Group by code
errors_by_code = defaultdict(list)
for error in data:
    errors_by_code[error["code"]].append(error)

# Rule mapping/description
rules_description = {
    # Safety / Security
    "E722": ("High", "Safety / Security", "do not use bare `except`"),
    "B030": (
        "High",
        "Safety / Security",
        "except handlers must catch BaseException-derived classes",
    ),
    "B023": ("High", "Safety / Security", "function closure uses loop variable"),
    "F821": ("High", "Safety / Security", "undefined name"),
    "F811": ("High", "Safety / Security", "redefined-while-unused"),
    # Imports
    "E402": ("Medium", "Imports", "module level import not at top of file"),
    "F401": ("Medium", "Imports", "unused import"),
    "F403": ("Medium", "Imports", "star imports used"),
    "UP035": ("Medium", "Imports", "deprecated import"),
    # Typing
    "UP045": ("Medium", "Typing", "non-pep604-annotation-optional"),
    "UP042": ("Medium", "Typing", "replace-str-enum"),
    "E711": ("Medium", "Typing", "comparison to None should be `cond is None`"),
    "E712": ("Medium", "Typing", "comparison to True/False should be `cond` or `not cond`"),
    # Quality / Maintainability
    "F841": ("Low", "Maintainability", "local variable assigned but never used"),
    "SIM105": ("Low", "Maintainability", "use contextlib.suppress instead of try-except-pass"),
    "B007": ("Low", "Maintainability", "loop control variable not used within loop body"),
    "B011": ("Low", "Maintainability", "do not assert False"),
    "ARG005": ("Low", "Maintainability", "unused lambda argument"),
    "E741": ("Low", "Maintainability", "ambiguous variable name"),
    "SIM115": ("Low", "Maintainability", "use a context manager for opening files"),
    "B905": ("Low", "Maintainability", "`zip()` without an explicit `strict=` parameter"),
    "SIM103": ("Low", "Maintainability", "needless boolean control flow"),
    "N806": ("Low", "Maintainability", "variable name in function should be lowercase"),
    "SIM108": ("Low", "Maintainability", "use ternary operator instead of if-else"),
    "ARG004": ("Low", "Maintainability", "unused static method argument"),
    "N818": ("Low", "Maintainability", "exception name should end with Error"),
    "W293": ("Low", "Maintainability", "blank line contains whitespace"),
    "SIM110": ("Low", "Maintainability", "reimplemented builtin `any` or `all`"),
    "N801": ("Low", "Maintainability", "class name should use CapWords convention"),
    "B017": ("Low", "Maintainability", "asserting on too broad/blind exceptions"),
    "ARG003": ("Low", "Maintainability", "unused class method argument"),
    "B006": ("Low", "Maintainability", "do not use mutable data structures for argument defaults"),
    "SIM118": ("Low", "Maintainability", "use key in dict instead of key in dict.keys()"),
    "W291": ("Low", "Maintainability", "trailing whitespace"),
    "SIM201": ("Low", "Maintainability", "negate-equal-op"),
    "SIM116": ("Low", "Maintainability", "if-else block instead of dictionary lookup"),
    "SIM211": ("Low", "Maintainability", "if-expr-with-false-true"),
    "SIM212": ("Low", "Maintainability", "if-expr-with-twisted-arms"),
    "E731": ("Low", "Maintainability", "do not assign a lambda expression, use a def"),
    "SIM109": ("Low", "Maintainability", "compare with tuple"),
    "SIM113": ("Low", "Maintainability", "use enumerate in for loop"),
    "SIM210": ("Low", "Maintainability", "if-expr-with-true-false"),
    "SIM222": ("Low", "Maintainability", "expression or True"),
}

markdown_output = []
markdown_output.append("# Remaining Lint Violations Report (LINT_REMAINING.md)\n")
markdown_output.append(
    "This document outlines the remaining lint violations in the codebase, categorized by category, priority, and rule. These violations require manual review and correction.\n"
)

# Summarize totals
markdown_output.append("## Summary of Violations\n")
markdown_output.append("| Rule Code | Category | Priority | Description | Count |")
markdown_output.append("|---|---|---|---|---|")

sorted_codes = sorted(
    errors_by_code.keys(),
    key=lambda c: (
        rules_description.get(c, ("Low", "Other", ""))[0],  # Priority (High/Medium/Low)
        rules_description.get(c, ("Low", "Other", ""))[1],  # Category
        -len(errors_by_code[c]),  # Count descending
    ),
)

for code in sorted_codes:
    desc = rules_description.get(code, ("Low", "Other", "Unknown rule"))
    priority, category, detail = desc
    count = len(errors_by_code[code])
    markdown_output.append(f"| `{code}` | {category} | **{priority}** | {detail} | {count} |")

markdown_output.append("\n---\n")

# Detailed list by priority
markdown_output.append("## Detailed Rules & Affected Files\n")

# High priority
markdown_output.append("### 1. High Priority (Safety & Security)\n")
high_codes = [c for c in sorted_codes if rules_description.get(c, ("Low", "", ""))[0] == "High"]
if not high_codes:
    markdown_output.append("No high priority violations found.\n")
else:
    for code in high_codes:
        desc = rules_description[code]
        errors = errors_by_code[code]
        markdown_output.append(f"#### `{code}`: {desc[2]} ({len(errors)} occurrences)\n")
        # List top 15 unique files
        files = sorted(list(set(f"{e['filename']}:{e['location']['row']}" for e in errors)))
        for f in files[:15]:
            markdown_output.append(f"- [ ] `{f}`")
        if len(files) > 15:
            markdown_output.append(f"- ... and {len(files) - 15} more occurrences.")
        markdown_output.append("")

# Medium priority
markdown_output.append("### 2. Medium Priority (Imports & Typing)\n")
medium_codes = [c for c in sorted_codes if rules_description.get(c, ("Low", "", ""))[0] == "Medium"]
if not medium_codes:
    markdown_output.append("No medium priority violations found.\n")
else:
    for code in medium_codes:
        desc = rules_description[code]
        errors = errors_by_code[code]
        markdown_output.append(f"#### `{code}`: {desc[2]} ({len(errors)} occurrences)\n")
        files = sorted(list(set(f"{e['filename']}:{e['location']['row']}" for e in errors)))
        for f in files[:15]:
            markdown_output.append(f"- [ ] `{f}`")
        if len(files) > 15:
            markdown_output.append(f"- ... and {len(files) - 15} more occurrences.")
        markdown_output.append("")

# Low priority
markdown_output.append("### 3. Low Priority (Style & Maintainability)\n")
low_codes = [c for c in sorted_codes if rules_description.get(c, ("Low", "", ""))[0] == "Low"]
if not low_codes:
    markdown_output.append("No low priority violations found.\n")
else:
    for code in low_codes:
        desc = rules_description.get(code, ("Low", "Other", "Unknown rule"))
        errors = errors_by_code[code]
        markdown_output.append(f"#### `{code}`: {desc[2]} ({len(errors)} occurrences)\n")
        files = sorted(list(set(f"{e['filename']}:{e['location']['row']}" for e in errors)))
        for f in files[:10]:
            markdown_output.append(f"- [ ] `{f}`")
        if len(files) > 10:
            markdown_output.append(f"- ... and {len(files) - 10} more occurrences.")
        markdown_output.append("")

with open("docs/LINT_REMAINING.md", "w", encoding="utf-8") as f:
    f.write("\n".join(markdown_output))

print("Markdown generated successfully at docs/LINT_REMAINING.md")
