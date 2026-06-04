import fnmatch
import glob
import os


def parse_rule_file(content: str, file_path: str | None = None) -> str | None:
    content_stripped = content.strip()
    if content_stripped.startswith("---"):
        parts = content_stripped.split("---", 2)
        if len(parts) >= 3:
            yaml_text = parts[1]
            rule_body = parts[2].strip()
            # Parse globs from yaml_text
            globs = []
            for line in yaml_text.splitlines():
                if line.strip().startswith("globs:"):
                    glob_val = line.split(":", 1)[1].strip()
                    # Remove quotes
                    glob_val = glob_val.strip("'\"")
                    # Split by comma
                    globs = [g.strip() for g in glob_val.split(",") if g.strip()]
            
            if file_path and globs:
                matched = False
                for pattern in globs:
                    if (
                        fnmatch.fnmatch(file_path, pattern) or
                        fnmatch.fnmatch(os.path.basename(file_path), pattern)
                    ):
                        matched = True
                        break
                if not matched:
                    return None
            return rule_body
    return content_stripped

def load_rules_for_path(file_path: str | None = None, workspace_root: str = ".") -> str:
    rules = []
    
    # 1. Global rules.md
    global_rules_path = os.path.join(workspace_root, ".harness", "rules.md")
    if os.path.exists(global_rules_path) and os.path.isfile(global_rules_path):
        try:
            with open(global_rules_path, "r", errors="ignore") as f:
                content = f.read()
            parsed = parse_rule_file(content, file_path)
            if parsed:
                rules.append(parsed)
        except Exception:
            pass

    # 2. .harness/rules/*.md
    harness_rules_dir = os.path.join(workspace_root, ".harness", "rules")
    if os.path.exists(harness_rules_dir) and os.path.isdir(harness_rules_dir):
        for path in glob.glob(os.path.join(harness_rules_dir, "*.md")):
            try:
                with open(path, "r", errors="ignore") as f:
                    content = f.read()
                parsed = parse_rule_file(content, file_path)
                if parsed:
                    rules.append(parsed)
            except Exception:
                pass

    # 3. .cursor/rules/*.md
    cursor_rules_dir = os.path.join(workspace_root, ".cursor", "rules")
    if os.path.exists(cursor_rules_dir) and os.path.isdir(cursor_rules_dir):
        for path in glob.glob(os.path.join(cursor_rules_dir, "*.md")):
            try:
                with open(path, "r", errors="ignore") as f:
                    content = f.read()
                parsed = parse_rule_file(content, file_path)
                if parsed:
                    rules.append(parsed)
            except Exception:
                pass

    return "\n\n".join(rules)
