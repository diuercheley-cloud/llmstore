import glob
import os
import subprocess


def test_no_secrets_in_report():
    output_dir = "artifacts/pytest-checklists-security"
    result = subprocess.run(
        [
            "./scripts/validators/pre-client-checklist-local.sh",
            "--client-install",
            "--skip-lmstudio",
            "--skip-rag",
            "--skip-tts",
            "--output-dir",
            output_dir,
        ],
        capture_output=True,
        text=True,
    )

    dirs = glob.glob(f"{output_dir}/*/")
    assert len(dirs) > 0, "No output directory was created"

    latest_dir = max(dirs, key=os.path.getmtime)

    json_file = os.path.join(latest_dir, "checklist.json")
    md_file = os.path.join(latest_dir, "checklist.md")

    # Simple heuristic to ensure secrets aren't dumped into the report
    forbidden_terms = ["password=", "secret=", "private_key"]

    for file_path in [json_file, md_file]:
        if os.path.exists(file_path):
            with open(file_path) as f:
                content = f.read().lower()
                for term in forbidden_terms:
                    assert term not in content, f"Found forbidden term '{term}' in {file_path}"
