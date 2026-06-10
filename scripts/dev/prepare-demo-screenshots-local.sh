#!/bin/bash
# prepare-demo-screenshots-local.sh
# Gera screenshots da demonstração local ou cria plano de captura manual.
# Uso: ./scripts/dev/prepare-demo-screenshots-local.sh [--placeholders-only] [--help]

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

BASE_URL="${BASE_URL:-http://localhost:18080}"
TIMESTAMP=$(date +%Y%m%dT%H%M%S)
OUT_DIR="artifacts/demo-screenshots/${TIMESTAMP}"
PLACEHOLDER_DIR="docs/demo-visual-guide/placeholders"

SCREENS=(
    "landing-page:/"
    "capabilities:/capabilities"
    "admin-dashboard:/admin-dashboard"
    "admin-lab:/admin-lab"
    "client-portal:/client-portal"
    "pricing:/pricing"
)

show_help() {
    cat <<EOF
Uso: $0 [--placeholders-only] [--help]

Gera screenshots da demonstração local ou cria plano de captura manual.

Opções:
  --placeholders-only  Gera apenas placeholders SVG (não requer navegador)
  --help               Exibe esta ajuda

Variáveis de ambiente:
  BASE_URL   URL base do sistema (padrão: http://localhost:18080)

Sem opções, tenta captura com Playwright/Chromium.
Se Playwright não estiver disponível, gera plano de captura manual.
Nunca falha por falta de navegador.
EOF
    exit 0
}

check_playwright() {
    if python3 -c "import playwright" 2>/dev/null; then
        if python3 -c "from playwright.sync_api import sync_playwright; p = sync_playwright(); p.start(); p.stop()" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

generate_placeholder_svg() {
    local name="$1"
    local label="$2"
    local file="${PLACEHOLDER_DIR}/${name}.svg"

    cat > "$file" <<SVGEOF
<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="800" viewBox="0 0 1280 800">
  <rect width="1280" height="800" fill="#f0f4f8"/>
  <rect x="40" y="40" width="1200" height="60" rx="8" fill="#d0d8e0"/>
  <text x="640" y="78" font-family="monospace" font-size="20" fill="#333" text-anchor="middle" font-weight="bold">Local AI Appliance — ${label}</text>
  <rect x="40" y="120" width="1200" height="640" rx="8" fill="#ffffff" stroke="#d0d8e0" stroke-width="2"/>
  <text x="640" y="460" font-family="monospace" font-size="16" fill="#888" text-anchor="middle">${label}</text>
  <text x="640" y="490" font-family="monospace" font-size="14" fill="#aaa" text-anchor="middle">placeholder — dados fictícios</text>
</svg>
SVGEOF
    echo -e "${GREEN}[PLACEHOLDER]${NC} $file"
}

generate_capture_plan() {
    local plan_file="${OUT_DIR}/capture-plan.md"

    mkdir -p "$OUT_DIR"

    cat > "$plan_file" <<EOF
# Capture Plan — ${TIMESTAMP}

## Screenshots Web

$(for entry in "${SCREENS[@]}"; do
    name="${entry%%:*}"
    path="${entry##*:}"
    echo "- [ ] **${name}**: ${BASE_URL}${path}"
done)

## API Responses

- [ ] **api-chat**: POST ${BASE_URL}/v1/chat/completions
- [ ] **rag-query**: POST ${BASE_URL}/v1/rag/query
- [ ] **tts-demo**: POST ${BASE_URL}/pocket-tts/tts
- [ ] **models-list**: GET ${BASE_URL}/v1/models

## Reports

- [ ] **security-report**: \`./scripts/validators/security-report-local.sh\`
- [ ] **production-readiness**: \`./scripts/dev/production-readiness-local.sh\`
- [ ] **meeting-ready**: \`make meeting-ready\`
- [ ] **proposal-generation**: \`make generate-proposal COMPANY_NAME="Cliente Demo"\`

## Screenshots Capturados

$(ls "${OUT_DIR}"/*.png 2>/dev/null | sed 's/^/- /' || echo "(nenhum screenshot capturado)")

---

Gerado por: \`scripts/dev/prepare-demo-screenshots-local.sh\`
Timestamp: ${TIMESTAMP}
EOF
    echo -e "${GREEN}[PLAN]${NC} Capture plan gerado: $plan_file"
}

capture_with_playwright() {
    mkdir -p "$OUT_DIR"

    python3 <<PYEOF
import sys, os
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("[PLAYWRIGHT] biblioteca nao disponivel")
    sys.exit(1)

BASE = os.environ.get("BASE_URL", "http://localhost:18080")
OUT = os.environ.get("OUT_DIR", "${OUT_DIR}")

screens = [
    ("landing-page", "/"),
    ("capabilities", "/capabilities"),
    ("admin-dashboard", "/admin-dashboard"),
    ("admin-lab", "/admin-lab"),
    ("client-portal", "/client-portal"),
    ("pricing", "/pricing"),
]

captured = []
failed = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    page = context.new_page()

    for name, path in screens:
        url = BASE + path
        out_path = os.path.join(OUT, f"{name}.png")
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.screenshot(path=out_path, full_page=True)
            captured.append(name)
            print(f"[CAPTURED] {name} -> {out_path}")
        except Exception as e:
            failed.append(name)
            print(f"[FAILED] {name}: {e}")

    browser.close()

print(f"\nResumo: {len(captured)} capturados, {len(failed)} falhas")
if failed:
    print(f"Falhas: {', '.join(failed)}")
    print("Dica: verifique se a stack esta rodando em ${BASE}")
PYEOF
}

generate_placeholders() {
    mkdir -p "$PLACEHOLDER_DIR"
    for entry in "${SCREENS[@]}"; do
        name="${entry%%:*}"
        label="${name//-/ }"
        label="${label^}"
        generate_placeholder_svg "$name" "$label"
    done
    # Additional screens
    for extra in "rag-demo:RAG Demo" "tts-demo:TTS Demo" "api-examples:API Examples" "security-report:Security Report" "production-readiness:Production Readiness" "meeting-ready:Meeting Ready" "proposal-output:Proposal/Quote/SOW"; do
        name="${extra%%:*}"
        label="${extra##*:}"
        generate_placeholder_svg "$name" "$label"
    done
    echo -e "${GREEN}[DONE]${NC} Placeholders gerados em ${PLACEHOLDER_DIR}/"
}

# --- Main ---

if [ $# -gt 0 ]; then
    case "$1" in
        --help|-h)
            show_help
            ;;
        --placeholders-only)
            generate_placeholders
            exit 0
            ;;
        *)
            echo "Opcao desconhecida: $1"
            echo "Use --help para ajuda."
            exit 1
            ;;
    esac
fi

echo -e "${YELLOW}[SCREENSHOT PREP]${NC} Timestamp: ${TIMESTAMP}"
echo -e "${YELLOW}[SCREENSHOT PREP]${NC} Output dir: ${OUT_DIR}"
echo ""

# Generate capture plan
generate_capture_plan

# Check Playwright
if check_playwright; then
    echo ""
    echo -e "${GREEN}[PLAYWRIGHT]${NC} Detectado. Iniciando captura de screenshots..."
    echo -e "${YELLOW}[AVISO]${NC} Certifique-se de que a stack esta rodando em ${BASE_URL}"
    echo ""
    capture_with_playwright
    echo ""
    echo -e "${GREEN}[DONE]${NC} Screenshots em ${OUT_DIR}/"
    echo -e "${YELLOW}[AVISO]${NC} Nao commitar screenshots com dados reais!"
else
    echo ""
    echo -e "${YELLOW}[SKIP]${NC} Playwright/Chromium nao disponivel."
    echo -e "${YELLOW}[SKIP]${NC} Plano de captura gerado em ${OUT_DIR}/capture-plan.md"
    echo -e "${YELLOW}[SKIP]${NC} Para captura manual, veja docs/demo-visual-guide/CAPTURE_COMMANDS.md"
    echo ""
    echo -e "${GREEN}[PLACEHOLDER]${NC} Gerando placeholders..."
    generate_placeholders
fi

echo ""
echo -e "${YELLOW}[INFO]${NC} Screenshots capturados:"
ls -la "${OUT_DIR}/"*.png 2>/dev/null || echo "  (nenhum screenshot capturado)"
echo ""
echo "Para captura manual:"
echo "  playwright screenshot --viewport-size=\"1280,800\" <url> <output>"
echo "  ou veja docs/demo-visual-guide/CAPTURE_COMMANDS.md"
