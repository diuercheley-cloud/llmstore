import glob
import re


def test_no_secrets_in_customer_docs():
    secret_patterns = [r"sk-[a-zA-Z0-9]{32,}", r"password\s*=\s*['\"][^'\"]+['\"]"]

    docs = glob.glob("docs/CUSTOMER_*.md")
    for doc in docs:
        with open(doc, encoding="utf-8") as f:
            content = f.read()
            for pattern in secret_patterns:
                match = re.search(pattern, content)
                assert not match, f"Found potential secret in {doc}"
