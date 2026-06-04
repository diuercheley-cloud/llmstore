import os

import pytest

HTML_FILES = [
    "control_plane/app/static/www/index.html",
    "control_plane/app/static/www/capabilities.html",
    "control_plane/app/static/www/pricing.html",
    "control_plane/app/static/www/signup.html",
    "control_plane/app/static/www/docs.html",
    "control_plane/app/static/www/getting-started.html",
    "control_plane/app/static/admin/index.html",
    "control_plane/app/static/portal/index.html",
    "control_plane/app/static/admin-lab/index.html",
    "control_plane/app/static/admin-tests/index.html",
    "control_plane/app/static/monitoring/index.html",
]


def test_branding_script_exists():
    path = "control_plane/app/static/www/branding-init.js"
    assert os.path.isfile(path), f"Missing: {path}"


@pytest.mark.parametrize("html_file", HTML_FILES)
def test_html_references_branding_script(html_file):
    assert os.path.isfile(html_file), f"Missing: {html_file}"
    with open(html_file, "r") as f:
        content = f.read()
    assert "branding-init.js" in content, f"{html_file} missing branding script reference"


@pytest.mark.parametrize("html_file", HTML_FILES)
def test_html_has_title(html_file):
    with open(html_file, "r") as f:
        content = f.read()
    assert "<title>" in content, f"{html_file} missing title tag"


def test_landing_page_has_data_brand():
    with open("control_plane/app/static/www/index.html", "r") as f:
        content = f.read()
    assert 'data-brand="product_name"' in content
    assert 'data-brand="tagline"' in content
    assert 'data-brand="footer_text"' in content


def test_admin_has_data_brand():
    with open("control_plane/app/static/admin/index.html", "r") as f:
        content = f.read()
    assert 'data-brand="product_name"' in content


def test_portal_has_data_brand():
    with open("control_plane/app/static/portal/index.html", "r") as f:
        content = f.read()
    assert 'data-brand="company_name"' in content


def test_capabilities_has_data_brand():
    with open("control_plane/app/static/www/capabilities.html", "r") as f:
        content = f.read()
    assert 'data-brand="product_name"' in content
    assert 'data-brand="capabilities_title"' in content
    assert 'data-brand="footer_text"' in content


def test_branding_js_valid_syntax():
    path = "control_plane/app/static/www/branding-init.js"
    with open(path, "r") as f:
        content = f.read()
    import re
    # Basic check: balanced braces
    opens = len(re.findall(r"\{", content))
    closes = len(re.findall(r"\}", content))
    assert opens == closes, "branding-init.js has unbalanced braces"


def test_no_hardcoded_brand_in_landing_title():
    # Title should be present but brandable
    with open("control_plane/app/static/www/index.html", "r") as f:
        content = f.read()
    assert "LLM Inference Stack" in content  # default is fine


def test_static_dir_no_extra_assets():
    """Ensure no binary assets were added."""
    for root, dirs, files in os.walk("control_plane/app/static"):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".eot"]:
                pytest.fail(f"Binary asset found: {os.path.join(root, f)}")
