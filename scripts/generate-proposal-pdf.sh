#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

show_help() {
    cat <<EOF
generate-proposal-pdf.sh — Generate PDF from proposal Markdown

Usage:
  ./scripts/generate-proposal-pdf.sh --input <file.md> [--output <file.pdf>]

Options:
  --input   FILE     Markdown file to convert (required)
  --output  FILE     Output PDF path (default: <input>.pdf in proposals/generated/)
  --help             Show this help

Description:
  Detects available PDF tools (pandoc, wkhtmltopdf, google-chrome) and
  generates a PDF from the given Markdown file. All processing is local.
  No data is sent to the internet.

  If no PDF tool is available, prints a helpful message and exits with 0
  (non-failure) so that CI pipelines and test suites are not blocked.

Examples:
  ./scripts/generate-proposal-pdf.sh \\
    --input proposals/TECHNICAL_PROPOSAL_TEMPLATE.md \\
    --output proposals/generated/proposta-tecnica.pdf

  ./scripts/generate-proposal-pdf.sh --help
EOF
}

INPUT=""
OUTPUT=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --input)
            INPUT="$2"
            shift 2
            ;;
        --output)
            OUTPUT="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option: $1"
            echo "Use --help for usage."
            exit 1
            ;;
    esac
done

# Validate required args
if [ -z "$INPUT" ]; then
    echo "ERROR: --input is required"
    echo "Use --help for usage."
    exit 1
fi

if [ ! -f "$INPUT" ]; then
    echo "ERROR: Input file not found: $INPUT"
    exit 1
fi

# Set default output path
if [ -z "$OUTPUT" ]; then
    BASENAME="$(basename "$INPUT" .md)"
    OUTPUT="$ROOT_DIR/proposals/generated/${BASENAME}.pdf"
fi

# Create output directory
OUTPUT_DIR="$(dirname "$OUTPUT")"
mkdir -p "$OUTPUT_DIR"

echo "=> Generating PDF from: $INPUT"
echo "=> Output: $OUTPUT"

# Detect available PDF tools
USE_PANDOC=false
USE_WKHTMLTOPDF=false
USE_CHROME=false

if command -v pandoc &>/dev/null; then
    USE_PANDOC=true
fi

if command -v wkhtmltopdf &>/dev/null; then
    USE_WKHTMLTOPDF=true
fi

# Check for chromium-based browser
if command -v google-chrome &>/dev/null; then
    USE_CHROME=true
elif command -v chromium-browser &>/dev/null; then
    USE_CHROME=true
elif command -v chromium &>/dev/null; then
    USE_CHROME=true
fi

# Check if we got no available tools
if ! $USE_PANDOC && ! $USE_WKHTMLTOPDF && ! $USE_CHROME; then
    echo ""
    echo "============================================="
    echo " WARNING: No PDF generation tool detected."
    echo " Install one of the following:"
    echo "   - pandoc (recommended): apt install pandoc"
    echo "   - wkhtmltopdf: apt install wkhtmltopdf"
    echo "   - google-chrome: already installed in some environments"
    echo ""
    echo " No PDF was generated, but the Markdown source"
    echo " is available at: $INPUT"
    echo "============================================="
    exit 0
fi

# Generate PDF
GENERATED=false

if $USE_PANDOC; then
    echo "=> Using pandoc..."
    if command -v weasyprint &>/dev/null; then
        pandoc "$INPUT" -o "$OUTPUT" --pdf-engine=weasyprint
    else
        pandoc "$INPUT" -o "$OUTPUT" --pdf-engine-opt=--print-media-type 2>/dev/null || \
        pandoc "$INPUT" -o "$OUTPUT" 2>/dev/null || {
            echo "WARNING: pandoc failed, trying next tool..."
            USE_PANDOC=false
        }
    fi
    if [ -f "$OUTPUT" ]; then
        GENERATED=true
    fi
fi

if ! $GENERATED && $USE_WKHTMLTOPDF; then
    echo "=> Using wkhtmltopdf..."
    wkhtmltopdf --encoding UTF-8 \
        --margin-top 15mm --margin-bottom 15mm \
        --margin-left 15mm --margin-right 15mm \
        "$INPUT" "$OUTPUT" 2>/dev/null || true
    wkhtmltopdf --encoding UTF-8 \
        --margin-top 15mm --margin-bottom 15mm \
        --margin-left 15mm --margin-right 15mm \
        <(echo "<html><body><pre>$(cat "$INPUT")</pre></body></html>") \
        "$OUTPUT" 2>/dev/null || true
    if [ -f "$OUTPUT" ]; then
        GENERATED=true
    fi
fi

if ! $GENERATED && $USE_CHROME; then
    echo "=> Using google-chrome headless..."
    # Determine which chrome binary
    CHROME_BIN=""
    if command -v google-chrome &>/dev/null; then
        CHROME_BIN="google-chrome"
    elif command -v chromium-browser &>/dev/null; then
        CHROME_BIN="chromium-browser"
    elif command -v chromium &>/dev/null; then
        CHROME_BIN="chromium"
    fi

    # Convert markdown to HTML first, then use chrome to print to PDF
    TMP_HTML="$(mktemp /tmp/proposal-XXXXX.html)"
    trap 'rm -f "$TMP_HTML"' EXIT

    # Simple markdown to HTML conversion using python markdown if available
    if python3 -c "import markdown" 2>/dev/null; then
        python3 -c "
import markdown, sys
with open('$INPUT', 'r') as f:
    html = markdown.markdown(f.read(), extensions=['extra', 'codehilite'])
with open('$TMP_HTML', 'w') as f:
    f.write('''<!DOCTYPE html>
<html><head><meta charset=\"utf-8\">
<style>
body { font-family: sans-serif; margin: 2em; line-height: 1.6; }
pre { background: #f4f4f4; padding: 1em; border-radius: 4px; overflow-x: auto; }
code { background: #f4f4f4; padding: 0.2em 0.4em; border-radius: 3px; }
table { border-collapse: collapse; width: 100%%; }
th, td { border: 1px solid #ccc; padding: 0.5em; text-align: left; }
th { background: #eee; }
</style></head><body>''')
    f.write(html)
    f.write('</body></html>')
"
    else
        # Fallback: wrap in pre
        cat > "$TMP_HTML" <<EOF
<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body { font-family: monospace; margin: 2em; white-space: pre-wrap; line-height: 1.5; }
</style></head><body>
$(cat "$INPUT" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g')
</body></html>
EOF
    fi

    "$CHROME_BIN" --headless --disable-gpu --no-sandbox \
        --print-to-pdf="$OUTPUT" \
        "file://$TMP_HTML" 2>/dev/null || true

    if [ -f "$OUTPUT" ]; then
        GENERATED=true
    fi
fi

if $GENERATED; then
    SIZE="$(du -h "$OUTPUT" | cut -f1)"
    echo ""
    echo "============================================="
    echo " SUCCESS: PDF generated successfully!"
    echo "   File: $OUTPUT"
    echo "   Size: $SIZE"
    echo "============================================="
else
    echo ""
    echo "WARNING: Could not generate PDF."
    echo "Markdown source is at: $INPUT"
fi
