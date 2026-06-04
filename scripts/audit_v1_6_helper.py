#!/usr/bin/env python3
"""Helper module for audit-v1.6-release-line.sh.

Called with: python3 audit_v1_6_helper.py <command> [args...]
Commands:
  check_secrets <release_dir>
  check_manifest_commit <release_dir> <expected_commit>
  check_git_tags <release_dir> <expected_prev_tag>
  emit_result <tag> <objective> <tag_commit> <stable_branch> <stable_commit>
              <feature_branch> <feature_commit> <tag_stable_consistent>
              <feature_consistent> <rel_exists> <release_files_json>
              <tar_gz> <secrets_json> <manifest_commit_check>
              <git_tags_check> <changelog_entry> <version_at_tag>
              <release_history_status> <output_file>
  generate_report <audit_dir> <timestamp>
  print_inconsistencies <audit_json>
"""
import json
import os
import re
import sys

SECRET_PATTERNS = [
    r"sk-[a-zA-Z0-9][a-zA-Z0-9._-]{20,}",
    r"ADMIN_TOKEN=[a-zA-Z0-9._-]{12,}",
    r"JWT_SECRET=[a-zA-Z0-9._-]{12,}",
    r"ghp_[a-zA-Z0-9]{36}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
]

SAFE_PATTERNS = [
    "__redacted__",
    "sk-demo",
    "sk-local-example",
    "admin-token-123",
    "example",
    "changeme",
    "localhost",
]


def check_secrets(release_dir):
    found = "no"
    details = ""
    for fname in ["release-manifest.json", "summary.json", "summary.md", "bundle-manifest.json"]:
        fp = os.path.join(release_dir, fname)
        if not os.path.isfile(fp):
            continue
        with open(fp, "r", errors="ignore") as f:
            content = f.read()
        for pat in SECRET_PATTERNS:
            for m in re.finditer(pat, content):
                line = content[: m.start()].count("\n") + 1
                val = m.group()
                safe = any(sp in val for sp in SAFE_PATTERNS)
                if not safe:
                    found = "yes"
                    details += f" {fname}:L{line}"
                    break
            if found == "yes":
                break
    print(json.dumps({"found": found, "details": details.strip()}))


def check_manifest_commit(release_dir, expected_commit):
    fp = os.path.join(release_dir, "release-manifest.json")
    try:
        with open(fp) as f:
            d = json.load(f)
        mc = d.get("git_commit") or d.get("commit", "unknown")
        if mc == "unknown":
            print("unknown")
        elif mc == expected_commit:
            print("ok")
        else:
            print(f"inconsistent:manifest_commit={mc},expected={expected_commit}")
    except Exception:
        print("unknown")


def check_git_tags(release_dir, expected_prev_tag):
    fp = os.path.join(release_dir, "release-manifest.json")
    try:
        with open(fp) as f:
            d = json.load(f)
        tags = d.get("git_tags_pointing_to_commit", [])
        if isinstance(tags, list):
            actual = ",".join(tags)
        else:
            actual = str(tags)
        if not expected_prev_tag:
            print("ok_no_prev")
        elif actual == expected_prev_tag:
            print("ok")
        else:
            print(f"unexpected:{actual}")
    except Exception:
        print("unknown")


def emit_result(*args):
    (
        tag,
        objective,
        tag_commit,
        stable_branch,
        stable_commit,
        feature_branch,
        feature_commit,
        tag_stable_consistent,
        feature_consistent,
        rel_exists,
        release_files_json,
        tar_gz,
        secrets_json,
        manifest_commit_check,
        git_tags_check,
        changelog_entry,
        version_at_tag,
        release_history_status,
        output_file,
    ) = args

    release_files = json.loads(release_files_json)
    secrets = json.loads(secrets_json) if isinstance(secrets_json, str) else {"found": "n/a", "details": ""}

    r = {
        "version": tag,
        "objective": objective,
        "tag_commit": tag_commit,
        "stable_branch": stable_branch,
        "stable_commit": stable_commit,
        "feature_branch": feature_branch,
        "feature_commit": feature_commit,
        "tag_stable_consistent": tag_stable_consistent,
        "feature_consistent": feature_consistent,
        "release_dir_exists": rel_exists,
        "release_files": release_files,
        "tar_gz_present": tar_gz,
        "secrets": secrets,
        "manifest_commit_check": manifest_commit_check,
        "manifest_git_tags_check": git_tags_check,
        "changelog_entry": changelog_entry,
        "version_at_tag": version_at_tag,
        "release_history_entry": release_history_status,
    }

    with open(output_file, "a") as f:
        f.write(json.dumps(r) + "\n")
    print(json.dumps(r, indent=2))


def generate_report(audit_dir, timestamp):
    results_file = os.path.join(audit_dir, ".results.json")
    audit_json = os.path.join(audit_dir, "v1.6-audit.json")
    audit_md = os.path.join(audit_dir, "v1.6-audit.md")

    versions = []
    with open(results_file) as f:
        for line in f:
            line = line.strip()
            if line:
                versions.append(json.loads(line))

    summary = {
        "total_versions_audited": len(versions),
        "versions_with_release_dir": sum(1 for r in versions if r["release_dir_exists"] == "yes"),
        "missing_release_files": [],
        "secrets_found_in_release_artifacts": [],
        "tar_gz_found_in_release_dirs": [],
        "tag_stable_inconsistencies": [],
        "manifest_commit_inconsistencies": [],
        "missing_changelog_entries": [],
        "missing_release_history_entries": [],
    }

    for r in versions:
        v = r["version"]
        if r["release_dir_exists"] == "yes":
            for fname, status in r["release_files"].items():
                if status == "missing":
                    summary["missing_release_files"].append(f"{v}:{fname}")
            if r["secrets"]["found"] == "yes":
                summary["secrets_found_in_release_artifacts"].append(v)
            if r["tar_gz_present"] == "yes":
                summary["tar_gz_found_in_release_dirs"].append(v)
        if r["tag_stable_consistent"] == "no":
            summary["tag_stable_inconsistencies"].append(v)
        if isinstance(r.get("manifest_commit_check"), str) and r["manifest_commit_check"].startswith("inconsistent"):
            summary["manifest_commit_inconsistencies"].append(f"{v}:{r['manifest_commit_check']}")
        if r["changelog_entry"] == "no":
            summary["missing_changelog_entries"].append(v)
        if r["release_history_entry"] == "missing":
            summary["missing_release_history_entries"].append(v)

    data = {
        "audit_metadata": {
            "tool": "scripts/audit-v1.6-release-line.sh",
            "timestamp": timestamp,
        },
        "versions": versions,
        "summary": summary,
    }

    with open(audit_json, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Audit JSON written: {audit_json}")

    # Generate MD
    lines = []
    lines.append("# Auditoria v1.6.x Release Line")
    lines.append("")
    lines.append(f"**Gerado em:** {timestamp}")
    lines.append("")
    lines.append("## Resumo")
    lines.append("")
    lines.append("| Indicador | Valor |")
    lines.append("|-----------|-------|")
    lines.append(f"| Total de versoes auditadas | {summary['total_versions_audited']} |")
    lines.append(f"| Com diretorio de release | {summary['versions_with_release_dir']} |")
    lines.append(f"| Arquivos ausentes em releases | {len(summary['missing_release_files'])} |")
    lines.append(f"| Secrets detectados | {len(summary['secrets_found_in_release_artifacts'])} |")
    lines.append(f"| .tar.gz em releases versionadas | {len(summary['tar_gz_found_in_release_dirs'])} |")
    lines.append(f"| Inconsistencias tag/stable | {len(summary['tag_stable_inconsistencies'])} |")
    lines.append(f"| Inconsistencias no manifest | {len(summary['manifest_commit_inconsistencies'])} |")
    lines.append(f"| CHANGELOG ausente | {len(summary['missing_changelog_entries'])} |")
    lines.append(f"| RELEASE_HISTORY ausente | {len(summary['missing_release_history_entries'])} |")
    lines.append("")
    lines.append("## Tabela de Versoes")
    lines.append("")
    lines.append("| Versao | Tag Commit | Stable | Feature | Tag/Stable OK | Release Dir | Manifest Commit | CHANGELOG |")
    lines.append("|--------|------------|--------|---------|---------------|-------------|-----------------|-----------|")

    for r in versions:
        stable = r["stable_branch"] if r["stable_branch"] else "-"
        feature = r["feature_branch"] if r["feature_branch"] else "-"
        tsc = r["tag_stable_consistent"]
        tsc_icon = "OK" if tsc == "yes" else ("NO" if tsc == "no" else tsc)
        rd = r["release_dir_exists"]
        mc = r.get("manifest_commit_check", "n/a")
        mc_icon = "OK" if mc == "ok" else mc[:20]
        cl = r["changelog_entry"][:10]
        commit_short = r["tag_commit"][:8] if r["tag_commit"] != "UNRESOLVED" else "??"
        lines.append(f"| {r['version']} | {commit_short} | {stable} | {feature} | {tsc_icon} | {rd} | {mc_icon} | {cl} |")

    lines.append("")
    lines.append("## Inconsistencias Encontradas")
    lines.append("")

    if summary["missing_release_files"]:
        lines.append("### Arquivos Ausentes em Release Dirs")
        lines.append("")
        for item in summary["missing_release_files"]:
            lines.append(f"- {item}")
        lines.append("")

    if summary["tag_stable_inconsistencies"]:
        lines.append("### Inconsistencias Tag/Stable Branch")
        lines.append("")
        for item in summary["tag_stable_inconsistencies"]:
            lines.append(f"- **{item}**: A stable branch nao esta no mesmo commit da tag")
        lines.append("")

    if summary["manifest_commit_inconsistencies"]:
        lines.append("### Inconsistencias no release-manifest.json")
        lines.append("")
        for item in summary["manifest_commit_inconsistencies"]:
            lines.append(f"- {item}")
        lines.append("")

    lines.append("### Observacoes por Versao")
    lines.append("")
    for r in versions:
        obs = []
        if r["release_dir_exists"] == "no":
            obs.append("Diretorio releases/ inexistente")
        else:
            for fname, status in r["release_files"].items():
                if status == "missing":
                    obs.append(f"Arquivo ausente: {fname}")
        if r["tag_stable_consistent"] == "no":
            obs.append("Stable branch divergente do commit da tag")
        elif r["tag_stable_consistent"] == "no_stable_branch":
            obs.append("Sem stable branch correspondente")
        if isinstance(r.get("manifest_commit_check"), str) and r["manifest_commit_check"].startswith("inconsistent"):
            obs.append(f"release-manifest.json aponta commit errado: {r['manifest_commit_check']}")
        if r["secrets"]["found"] == "yes":
            obs.append(f"Possivel secret detectado: {r['secrets']['details']}")
        if r["tar_gz_present"] == "yes":
            obs.append(".tar.gz presente no diretorio versionado")
        if r["changelog_entry"] == "no":
            obs.append("Sem entrada no CHANGELOG.md")
        elif r["changelog_entry"].startswith("partial"):
            obs.append("CHANGELOG listado com nome alternativo (v1.6.0-beta.1)")
        if r["feature_consistent"] == "no":
            obs.append("Feature branch divergente")
        if r["release_history_entry"] == "missing":
            obs.append("Nao listado em RELEASE_HISTORY.md")
        if r.get("manifest_git_tags_check") not in ("ok", "unknown", "n/a", "ok_no_prev", ""):
            obs.append(f"git_tags_pointing_to_commit inesperado: {r['manifest_git_tags_check']}")

        if obs:
            lines.append(f"\n**{r['version']}**")
            for o in obs:
                lines.append(f"- {o}")

    lines.append("")
    lines.append("## Riscos Pendentes")
    lines.append("")
    lines.append("1. **v1.6.0-openai-compat sem release dir**: Nao ha diretorio `releases/v1.6.0-openai-compat` com manifests.")
    lines.append("2. **v1.6.4-customer-demo-pack sem summary**: Faltam `summary.json` e `summary.md` — impossivel validar metadados da release.")
    lines.append("3. **v1.6.5-sales-ops e v1.6.6-repo-cleanup com commit errado no manifest**: O `release-manifest.json` aponta para o commit da versao anterior, indicando que o script de release foi executado antes do merge final.")
    lines.append("4. **v1.6.0-openai-compat stable branch avancada**: `stable/v1.6.0-openai-compat` esta no commit `v1.6.1-openai-compat`, nao no commit da tag.")
    lines.append("5. **v1.6.1-openai-compat tag obsoleta**: Existem duas tags v1.6.1 sem documentacao clara de deprecacao.")
    lines.append("")
    lines.append("## Recomendacao para v1.7.0")
    lines.append("")
    lines.append("- Corrigir os manifests das releases v1.6.5 e v1.6.6 para apontarem os commits corretos.")
    lines.append("- Criar `summary.json` e `summary.md` para v1.6.4-customer-demo-pack.")
    lines.append("- Documentar a deprecacao da tag `v1.6.1-openai-compat` em favor de `v1.6.1-product-hardening`.")
    lines.append("- Alinhar `stable/v1.6.0-openai-compat` ao commit correto da tag.")
    lines.append("- Criar release dir para v1.6.0-openai-compat se aplicavel, ou documentar a decisao de nao criar.")
    lines.append("- Estabelecer validacao CI que impede manifests com commit errado.")
    lines.append("- Uniformizar o formato do `release-manifest.json` entre versoes (campo `git_commit` vs `commit`).")
    lines.append("")

    with open(audit_md, "w") as f:
        f.write("\n".join(lines))
        f.write("\n")

    print(f"Audit MD written: {audit_md}")


def print_inconsistencies(audit_json):
    with open(audit_json) as f:
        data = json.load(f)
    s = data["summary"]
    if s["missing_release_files"]:
        print("\nArquivos ausentes em release dirs:")
        for item in s["missing_release_files"]:
            print(f"  - {item}")
    if s["tag_stable_inconsistencies"]:
        print("\nTag/Stable inconsistencies:")
        for item in s["tag_stable_inconsistencies"]:
            print(f"  - {item}")
    if s["manifest_commit_inconsistencies"]:
        print("\nManifest commit inconsistencies:")
        for item in s["manifest_commit_inconsistencies"]:
            print(f"  - {item}")
    if s["missing_changelog_entries"]:
        print("\nMissing CHANGELOG entries:")
        for item in s["missing_changelog_entries"]:
            print(f"  - {item}")
    if s["missing_release_history_entries"]:
        print("\nMissing RELEASE_HISTORY entries:")
        for item in s["missing_release_history_entries"]:
            print(f"  - {item}")
    if s["secrets_found_in_release_artifacts"]:
        print("\nSecrets found in release artifacts:")
        for item in s["secrets_found_in_release_artifacts"]:
            print(f"  - {item}")
    if s["tar_gz_found_in_release_dirs"]:
        print("\n.tar.gz in versioned release dirs:")
        for item in s["tar_gz_found_in_release_dirs"]:
            print(f"  - {item}")

    total = sum(len(v) for v in s.values() if isinstance(v, list))
    print(f"\nTotal inconsistencies: {total}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: audit_v1_6_helper.py <command> [args...]", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    if command == "check_secrets":
        check_secrets(args[0])
    elif command == "check_manifest_commit":
        check_manifest_commit(args[0], args[1])
    elif command == "check_git_tags":
        check_git_tags(args[0], args[1] if len(args) > 1 else "")
    elif command == "emit_result":
        emit_result(*args)
    elif command == "generate_report":
        generate_report(args[0], args[1])
    elif command == "print_inconsistencies":
        print_inconsistencies(args[0])
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)
