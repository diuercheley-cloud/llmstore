import os
import re
import sys


def validate_internal_security():
    print("Executing internal security review scan...")
    
    # Prohibited patterns
    prohibited = [
        (r'(?<!redis\.)\beval\(', "UNSAFE: eval() found (not redis.eval)"),
        (r'\bexec\(', "UNSAFE: exec() found"),
        (r'\bos\.system\(', "UNSAFE: os.system() found"),
        (r'subprocess\.Popen\(.*shell=True', "UNSAFE: shell=True in subprocess"),
        (r'\bpickle\.', "UNSAFE: pickle serialization found"),
        (r'open\(.*\.format\(', "UNSAFE: Potential path traversal in open()"),
        (r'password\s*=\s*["\'][^"\'_]+["\']', "UNSAFE: Potential hardcoded password"),
        (r'api_key\s*=\s*["\'][^"\'_]{10,}["\']', "UNSAFE: Potential hardcoded API key (min 10 chars)")
    ]
    
    root_dir = os.path.join(os.path.dirname(__file__), "..", "control_plane")
    issues = 0
    
    for root, dirs, files in os.walk(root_dir):
        if "tests" in root: # Skip tests for these checks
            continue
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    for pattern, msg in prohibited:
                        match = re.search(pattern, content)
                        if match:
                            # Find the line
                            line_no = content.count('\n', 0, match.start()) + 1
                            line_content = content.split('\n')[line_no-1].strip()
                            if "# nosec" in line_content:
                                continue
                            print(f"SECURITY ALERT: {msg} in {path}:{line_no}")
                            print(f"  > {line_content}")
                            issues += 1
                            
    if issues > 0:
        print(f"\nInternal security review FAILED with {issues} issues.")
        return False
        
    print("\nInternal security review PASSED.")
    return True

if __name__ == "__main__":
    if not validate_internal_security():
        sys.exit(1)
