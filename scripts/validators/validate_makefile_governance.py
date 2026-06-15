#!/usr/bin/env python3
"""Validate Makefile governance structure, safety and deterministic aggregates."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MAKEFILE_PATH = REPO_ROOT / "Makefile"

TARGET_RE = re.compile(r"^([A-Za-z0-9_.%/-][A-Za-z0-9_.%/\-\s]*)\s*:(.*)$")
VARIABLE_RE = re.compile(r"^([A-Z0-9_]+)\s*:?=\s*(.*)$")
MAKE_CALL_RE = re.compile(r"\$\(MAKE\)\s+--no-print-directory\s+([A-Za-z0-9_.%/-]+)")
VARIABLE_REF_RE = re.compile(r"^\$\(([A-Z0-9_]+)\)$")

PHASE_TARGETS_VARIABLE = "VALIDATE_PHASE_TARGETS"
AGGREGATE_VARIABLES = {
    "validate-architecture": "ARCHITECTURE_VALIDATION_TARGETS",
    "validate-governance": "GOVERNANCE_VALIDATION_TARGETS",
    "validate-runtime": "RUNTIME_VALIDATION_TARGETS",
    "validate-federation": "FEDERATION_VALIDATION_TARGETS",
    "validate-plugin": "PLUGIN_VALIDATION_TARGETS",
    "validate-compatibility": "COMPATIBILITY_VALIDATION_TARGETS",
    "validate-documentation": "DOCUMENTATION_VALIDATION_TARGETS",
    "validate-security": "SECURITY_VALIDATION_TARGETS",
    "validate-platform": "PLATFORM_VALIDATION_TARGETS",
    "validate-all": "ALL_VALIDATION_TARGETS",
}
OFFICIAL_AGGREGATORS = tuple(AGGREGATE_VARIABLES)
REQUIRED_SECTION_COMMENTS = (
    "# --- Core Validation ---",
    "# --- Governance Validation ---",
    "# --- Runtime Validation ---",
    "# --- Federation Validation ---",
    "# --- Plugin Validation ---",
    "# --- Compatibility Validation ---",
    "# --- Documentation Validation ---",
    "# --- Security Validation ---",
)
REQUIRED_DOCS = (
    REPO_ROOT / "docs" / "governance" / "makefile_governance.md",
    REPO_ROOT / "docs" / "governance" / "makefile_governance_summary.md",
)
REQUIRED_TARGETS = (
    "validate-makefile-governance",
    *OFFICIAL_AGGREGATORS,
)
STRUCTURED_TARGETS = (
    "validate-makefile-governance",
    *OFFICIAL_AGGREGATORS,
)
DANGEROUS_RECIPE_FRAGMENTS = (
    "curl ",
    "wget ",
    "sudo ",
    "rm -rf",
    "eval ",
    "bash -c",
    "sh -c",
    "`",
)


@dataclass
class TargetDefinition:
    name: str
    lineno: int
    raw: str
    prerequisites: list[str] = field(default_factory=list)
    recipe_lines: list[str] = field(default_factory=list)

    @property
    def has_recipe(self) -> bool:
        return bool(self.recipe_lines)

    @property
    def is_alias(self) -> bool:
        return len(self.prerequisites) == 1 and not self.has_recipe


@dataclass
class ParsedMakefile:
    targets: dict[str, list[TargetDefinition]]
    phony_entries: list[str]
    variables: dict[str, list[str]]
    content: str

    @property
    def unique_targets(self) -> dict[str, TargetDefinition]:
        return {name: definitions[0] for name, definitions in self.targets.items() if definitions}


def _split_words(value: str) -> list[str]:
    return [token for token in value.strip().split() if token != "\\"]


def expand_variable_tokens(
    variables: dict[str, list[str]], name: str, seen: set[str] | None = None
) -> list[str]:
    seen = set() if seen is None else set(seen)
    if name in seen:
        return []
    seen.add(name)

    expanded: list[str] = []
    for token in variables.get(name, []):
        match = VARIABLE_REF_RE.match(token)
        if match:
            expanded.extend(expand_variable_tokens(variables, match.group(1), seen))
        else:
            expanded.append(token)
    return expanded


def parse_makefile(path: Path = MAKEFILE_PATH) -> ParsedMakefile:
    targets: dict[str, list[TargetDefinition]] = {}
    phony_entries: list[str] = []
    variables: dict[str, list[str]] = {}

    lines = path.read_text(encoding="utf-8").splitlines()
    current_targets: list[TargetDefinition] = []
    continuing_var: str | None = None
    continuing_parts: list[str] = []

    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()

        if continuing_var is not None:
            value = stripped
            if value.endswith("\\"):
                continuing_parts.append(value[:-1].strip())
                continue
            continuing_parts.append(value)
            variables[continuing_var] = _split_words(" ".join(continuing_parts))
            continuing_var = None
            continuing_parts = []
            current_targets = []
            continue

        if line.startswith("\t"):
            for target in current_targets:
                target.recipe_lines.append(line[1:])
            continue

        current_targets = []

        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith(".PHONY:"):
            phony_entries.extend(_split_words(stripped.split(":", 1)[1]))
            continue

        variable_match = VARIABLE_RE.match(line)
        if variable_match and not line.startswith("\t"):
            name, value = variable_match.groups()
            value = value.strip()
            if value.endswith("\\"):
                continuing_var = name
                continuing_parts = [value[:-1].strip()]
            else:
                variables[name] = _split_words(value)
            continue

        target_match = TARGET_RE.match(line)
        if not target_match or line.startswith("."):
            continue

        names_raw, raw_prereqs = target_match.groups()
        names = [name for name in names_raw.split() if name]
        prereqs = _split_words(raw_prereqs.split("#", 1)[0])
        for name in names:
            definition = TargetDefinition(
                name=name,
                lineno=lineno,
                raw=line.rstrip(),
                prerequisites=prereqs,
            )
            targets.setdefault(name, []).append(definition)
            current_targets.append(definition)

    return ParsedMakefile(
        targets=targets,
        phony_entries=phony_entries,
        variables=variables,
        content=path.read_text(encoding="utf-8"),
    )


def _failure(path: str, issue: str) -> dict[str, str]:
    return {"path": path, "issue": issue}


def find_duplicate_targets(parsed: ParsedMakefile) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for name, definitions in sorted(parsed.targets.items()):
        if len(definitions) > 1:
            locations = ", ".join(str(definition.lineno) for definition in definitions)
            failures.append(
                _failure("Makefile", f"duplicate target definition for {name} at lines {locations}")
            )
    return failures


def find_duplicate_phony_entries(parsed: ParsedMakefile) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    for entry in parsed.phony_entries:
        if entry in seen and entry not in duplicates:
            duplicates.append(entry)
        seen.add(entry)
    for duplicate in duplicates:
        failures.append(_failure("Makefile", f"duplicate .PHONY entry for {duplicate}"))
    return failures


def find_missing_targets(parsed: ParsedMakefile) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for target in REQUIRED_TARGETS:
        if target not in parsed.targets:
            failures.append(_failure("Makefile", f"missing required target: {target}"))
    return failures


def find_missing_phase_registrations(parsed: ParsedMakefile) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    registered = parsed.variables.get(PHASE_TARGETS_VARIABLE)
    if not registered:
        return [_failure("Makefile", f"missing variable: {PHASE_TARGETS_VARIABLE}")]

    defined_phase_targets = sorted(
        name for name in parsed.targets if name.startswith("validate-phase-")
    )
    if sorted(registered) != defined_phase_targets:
        failures.append(
            _failure(
                "Makefile",
                f"{PHASE_TARGETS_VARIABLE} does not match defined phase targets: registered={registered}, defined={defined_phase_targets}",
            )
        )
    return failures


def find_missing_aggregate_variables(parsed: ParsedMakefile) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for target, variable in AGGREGATE_VARIABLES.items():
        if variable not in parsed.variables:
            failures.append(
                _failure("Makefile", f"missing aggregate variable {variable} for {target}")
            )
            continue
        if not expand_variable_tokens(parsed.variables, variable):
            failures.append(
                _failure("Makefile", f"aggregate variable {variable} for {target} is empty")
            )
    return failures


def find_orphaned_aggregate_entries(parsed: ParsedMakefile) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    valid_targets = set(parsed.targets)
    for target, variable in AGGREGATE_VARIABLES.items():
        for dependency in expand_variable_tokens(parsed.variables, variable):
            if dependency not in valid_targets:
                failures.append(
                    _failure(
                        "Makefile",
                        f"{target} references missing aggregate entry {dependency} via {variable}",
                    )
                )
    return failures


def find_structural_comments(parsed: ParsedMakefile) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for comment in REQUIRED_SECTION_COMMENTS:
        if comment not in parsed.content:
            failures.append(_failure("Makefile", f"missing structural comment: {comment}"))
    return failures


def find_missing_docs() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for doc in REQUIRED_DOCS:
        if not doc.exists():
            failures.append(
                _failure(str(doc.relative_to(REPO_ROOT)), "missing governance documentation")
            )
    return failures


def find_shadowing_and_overrides(parsed: ParsedMakefile) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for name, definitions in sorted(parsed.targets.items()):
        if len(definitions) > 1:
            continue
        definition = definitions[0]
        if (
            not definition.has_recipe
            and name.startswith("validate-")
            and not definition.prerequisites
        ):
            failures.append(
                _failure("Makefile", f"validate target {name} has no recipe or alias prerequisite")
            )
    return failures


def _aggregate_edges(parsed: ParsedMakefile) -> dict[str, list[str]]:
    edges: dict[str, list[str]] = {}
    unique_targets = parsed.unique_targets
    for target, variable in AGGREGATE_VARIABLES.items():
        edges[target] = [
            entry
            for entry in expand_variable_tokens(parsed.variables, variable)
            if entry in unique_targets
        ]
    for name, definition in unique_targets.items():
        if definition.is_alias:
            edges.setdefault(name, []).extend(
                prereq for prereq in definition.prerequisites if prereq in unique_targets
            )
    return edges


def find_simple_loops(parsed: ParsedMakefile) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    edges = _aggregate_edges(parsed)
    for source, dependencies in sorted(edges.items()):
        for dependency in dependencies:
            reverse = edges.get(dependency, [])
            if source in reverse:
                failures.append(
                    _failure(
                        "Makefile", f"simple dependency loop between {source} and {dependency}"
                    )
                )
    return failures


def find_unsafe_recipes(parsed: ParsedMakefile) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    unique_targets = parsed.unique_targets
    for target in STRUCTURED_TARGETS:
        definition = unique_targets.get(target)
        if not definition:
            continue
        for recipe in definition.recipe_lines:
            for fragment in DANGEROUS_RECIPE_FRAGMENTS:
                if fragment in recipe:
                    failures.append(
                        _failure(
                            "Makefile",
                            f"unsafe recipe fragment {fragment!r} found in target {target}",
                        )
                    )
            normalized = recipe.strip()
            if normalized in {"do \\", "done"}:
                continue
            if (
                target in AGGREGATE_VARIABLES
                and normalized
                and "$(MAKE)" not in recipe
                and "echo " not in recipe
                and "set -e;" not in recipe
            ):
                failures.append(
                    _failure(
                        "Makefile",
                        f"aggregate target {target} contains non-deterministic direct shell recipe: {normalized}",
                    )
                )
    return failures


def find_aggregate_recipe_mismatches(parsed: ParsedMakefile) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    unique_targets = parsed.unique_targets
    for target, variable in AGGREGATE_VARIABLES.items():
        definition = unique_targets.get(target)
        if not definition:
            continue
        expected_targets = expand_variable_tokens(parsed.variables, variable)
        recipe_targets = [
            match.group(1)
            for line in definition.recipe_lines
            for match in [MAKE_CALL_RE.search(line)]
            if match is not None
        ]
        if recipe_targets and recipe_targets != expected_targets:
            failures.append(
                _failure(
                    "Makefile",
                    f"recipe order for {target} does not match {variable}: recipe={recipe_targets}, variable={expected_targets}",
                )
            )
    return failures


def validate() -> list[dict[str, str]]:
    parsed = parse_makefile()
    return [
        *find_duplicate_targets(parsed),
        *find_duplicate_phony_entries(parsed),
        *find_missing_targets(parsed),
        *find_missing_phase_registrations(parsed),
        *find_missing_aggregate_variables(parsed),
        *find_orphaned_aggregate_entries(parsed),
        *find_shadowing_and_overrides(parsed),
        *find_simple_loops(parsed),
        *find_missing_docs(),
        *find_structural_comments(parsed),
        *find_unsafe_recipes(parsed),
        *find_aggregate_recipe_mismatches(parsed),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit failures as JSON.")
    args = parser.parse_args()

    failures = validate()
    if args.json:
        print(json.dumps(failures, indent=2, sort_keys=True))
    elif failures:
        print("Makefile governance validation failed:")
        for failure in failures:
            print(f"- {failure['path']}: {failure['issue']}")
    else:
        print("Makefile governance validation passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
