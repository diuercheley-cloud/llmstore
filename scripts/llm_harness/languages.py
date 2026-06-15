import os
from dataclasses import dataclass


@dataclass
class LanguageProfile:
    name: str
    extensions: list[str]
    test_command: str
    lint_command: str
    comment_style: str
    parser: str


LANGUAGES: dict[str, LanguageProfile] = {
    "python": LanguageProfile(
        name="Python",
        extensions=[".py"],
        test_command="pytest",
        lint_command="ruff check",
        comment_style="#",
        parser="ast",
    ),
    "javascript": LanguageProfile(
        name="JavaScript",
        extensions=[".js", ".jsx", ".mjs", ".cjs"],
        test_command="npm test",
        lint_command="eslint",
        comment_style="//",
        parser="regex",
    ),
    "typescript": LanguageProfile(
        name="TypeScript",
        extensions=[".ts", ".tsx"],
        test_command="npm test",
        lint_command="eslint",
        comment_style="//",
        parser="regex",
    ),
    "java": LanguageProfile(
        name="Java",
        extensions=[".java"],
        test_command="mvn test",
        lint_command="mvn checkstyle:check",
        comment_style="//",
        parser="regex",
    ),
    "csharp": LanguageProfile(
        name="C#",
        extensions=[".cs"],
        test_command="dotnet test",
        lint_command="dotnet format --verify-no-changes",
        comment_style="//",
        parser="regex",
    ),
}


def detect_language_by_filename(filename: str) -> LanguageProfile | None:
    if not filename:
        return None
    basename = os.path.basename(filename)
    if "." not in basename:
        return None
    ext = f".{basename.split('.')[-1]}".lower()
    for profile in LANGUAGES.values():
        if ext in profile.extensions:
            return profile
    return None


def detect_primary_language_in_workspace(workspace_root: str) -> LanguageProfile | None:
    if not workspace_root or not os.path.exists(workspace_root):
        return LANGUAGES["python"]

    # Check project files
    if os.path.exists(os.path.join(workspace_root, "package.json")):
        if os.path.exists(os.path.join(workspace_root, "tsconfig.json")):
            return LANGUAGES["typescript"]
        return LANGUAGES["javascript"]

    if (
        os.path.exists(os.path.join(workspace_root, "requirements.txt"))
        or os.path.exists(os.path.join(workspace_root, "pyproject.toml"))
        or os.path.exists(os.path.join(workspace_root, "setup.py"))
    ):
        return LANGUAGES["python"]

    if os.path.exists(os.path.join(workspace_root, "pom.xml")) or os.path.exists(
        os.path.join(workspace_root, "build.gradle")
    ):
        return LANGUAGES["java"]

    # Check for C# files (csproj, sln)
    try:
        for f in os.listdir(workspace_root):
            if f.endswith((".csproj", ".sln")):
                return LANGUAGES["csharp"]
    except Exception:
        pass

    # Scan file extensions in workspace directory
    ext_counts: dict[str, int] = {}
    try:
        for root, dirs, files in os.walk(workspace_root):
            # Ignore common cache / build / env dirs
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d not in ("node_modules", "venv", ".venv", "build", "dist")
            ]
            for f in files:
                if "." in f:
                    ext = f".{f.split('.')[-1]}".lower()
                    ext_counts[ext] = ext_counts.get(ext, 0) + 1
    except Exception:
        pass

    best_lang = None
    max_count = 0
    for profile in LANGUAGES.values():
        count = sum(ext_counts.get(ext, 0) for ext in profile.extensions)
        if count > max_count:
            max_count = count
            best_lang = profile

    return best_lang or LANGUAGES["python"]
