#!/usr/bin/env bash
# Generate consolidated release history from tags, branches, and releases/ metadata.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_DIR="${PROJECT_ROOT}/artifacts/release-history/${TIMESTAMP}"
OUTPUT_MD="${PROJECT_ROOT}/docs/RELEASE_HISTORY.md"
OUTPUT_JSON="${REPORT_DIR}/release-history.json"

mkdir -p "${REPORT_DIR}"

# Generate Python script to a temp file and execute it
PY_SCRIPT=$(mktemp)
cat > "$PY_SCRIPT" << 'PYEOF'
import json, os, subprocess, re, sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(sys.argv[1])
OUTPUT_MD = sys.argv[2]
OUTPUT_JSON = sys.argv[3]
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
VERSION_FILE = PROJECT_ROOT / 'VERSION'
CHANGELOG_FILE = PROJECT_ROOT / 'CHANGELOG.md'

current_version = ''
if VERSION_FILE.exists():
    current_version = VERSION_FILE.read_text().strip()

# Collect all version tags
result = subprocess.run(
    ['git', 'tag', '-l', 'v*', '--sort=version:refname'],
    capture_output=True, text=True, cwd=PROJECT_ROOT
)
tags = [t.strip() for t in result.stdout.splitlines() if t.strip()]

releases = []
for tag in tags:
    # Get commit and date
    log_result = subprocess.run(
        ['git', 'log', '-1', '--format=%h|%cs', tag],
        capture_output=True, text=True, cwd=PROJECT_ROOT
    )
    parts = log_result.stdout.strip().split('|')
    commit = parts[0] if len(parts) > 0 else '?'
    date = parts[1] if len(parts) > 1 else '?'

    # Check for stable branch
    stable_branch = 'stable/' + tag
    branch_check = subprocess.run(
        ['git', 'rev-parse', '--verify', stable_branch],
        capture_output=True, cwd=PROJECT_ROOT
    )
    if branch_check.returncode != 0:
        stable_branch = None

    # Check for releases/ metadata
    release_dir = PROJECT_ROOT / 'releases' / tag
    has_rel = release_dir.is_dir()
    summary_json = release_dir / 'summary.json'
    
    scope = ''
    pytest_summary = ''
    if summary_json.exists():
        try:
            sd = json.loads(summary_json.read_text())
            scope = sd.get('validation_scope', '')
            pp = sd.get('pytest_passed', '?')
            pt = sd.get('pytest_total', '?')
            pytest_summary = f'{pp}/{pt}'
        except Exception:
            pass

    # Extract features from CHANGELOG
    features = ''
    if CHANGELOG_FILE.exists():
        content = CHANGELOG_FILE.read_text()
        esc_tag = re.escape(tag)
        pattern = r'## \[' + esc_tag + r'\](.*?)(?=## \[|\Z)'
        m = re.search(pattern, content, re.DOTALL)
        if m:
            section = m.group(1)
            lines = []
            for line in section.split('\n'):
                stripped = line.strip()
                if stripped.startswith('-'):
                    item = stripped.lstrip('- ').strip()
                    if item:
                        lines.append(item)
            features = '; '.join(lines[:5])

    # Determine category
    category = 'Legacy'
    status = 'archived'
    
    if tag.startswith('v1.5.'):
        if 'local-production' in tag or 'local-ops' in tag:
            category = 'Local Production / Ops'
        elif 'security' in tag:
            category = 'Security'
        elif 'runtime' in tag:
            category = 'Runtime'
        else:
            category = 'Local Production'
    elif tag.startswith('v1.6.0'):
        category = 'OpenAI Compatibility'
    elif tag.startswith('v1.6.1'):
        category = 'Product Hardening'
    elif tag.startswith('v1.6.2'):
        category = 'Installer Polish'
    elif tag.startswith('v1.6.3'):
        category = 'Readiness Cleanup'
    elif tag.startswith('v1.6.4'):
        category = 'Customer Demo Pack'
    elif tag.startswith('v1.6.5'):
        category = 'Sales Ops'

    if tag == current_version:
        status = 'current'
    elif tag in ('v1.6.4-customer-demo-pack', 'v1.6.5-sales-ops'):
        status = 'active'

    objective = (scope or features or '')[:80]

    releases.append({
        'tag': tag,
        'version': tag.lstrip('v'),
        'commit': commit,
        'date': date,
        'stable_branch': stable_branch,
        'has_releases_dir': has_rel,
        'category': category,
        'status': status,
        'objective': objective,
        'features': (features or '')[:120],
        'pytest_summary': pytest_summary,
    })

def sort_key(r):
    try:
        parts = r['version'].split('.')
        major = int(parts[0])
        minor = int(parts[1])
        patch_str = parts[2].split('-')[0]
        patch = int(patch_str) if patch_str.isdigit() else 0
        suffix = parts[2][len(patch_str):] if len(parts[2]) > len(patch_str) else ''
        return (major, minor, patch, suffix)
    except (IndexError, ValueError):
        return (0, 0, 0, r['version'])

releases.sort(key=sort_key)

output = {'generated_at': TIMESTAMP, 'releases': releases}
with open(OUTPUT_JSON, 'w') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

lines = []
lines.append('# Release History')
lines.append('')
lines.append('Historico consolidado das versoes estaveis do LLM Inference Stack.')
lines.append('')
lines.append('**Gerado em:** ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
lines.append('')
lines.append('## Visao Geral')
lines.append('')
lines.append('O projeto evolui de uma prova de conceito (v1.0.0-beta) atraves de releases focadas em')
lines.append('producao local (v1.4.x-v1.5.x), compatibilidade com OpenAI (v1.6.0), hardening de produto')
lines.append('(v1.6.1), polimento do instalador (v1.6.2), cleanup de readiness (v1.6.3),')
lines.append('demo pack comercial (v1.6.4) e fluxos de sales ops (v1.6.5).')
lines.append('')
lines.append('## Linha do Tempo')
lines.append('')
lines.append('```mermaid')
lines.append('timeline')
lines.append('    title LLM Inference Stack Releases')
for r in releases:
    lines.append('    %s : %s : %s' % (r['date'], r['version'], r['category']))
lines.append('```')
lines.append('')
lines.append('## Releases')
lines.append('')
lines.append('| Versao | Tag | Branch Stable | Commit | Data | Categoria | Status | Objetivo |')
lines.append('|--------|-----|---------------|--------|------|-----------|--------|----------|')
for r in releases:
    stable = r['stable_branch'] or '—'
    obj = (r['objective'] or '—')[:60]
    lines.append('| %s | `%s` | %s | `%s` | %s | %s | %s | %s |' % (
        r['version'], r['tag'], stable, r['commit'], r['date'],
        r['category'], r['status'], obj))
lines.append('')
lines.append('## Releases Recomendadas')
lines.append('')
lines.append('| Versao | Motivo |')
lines.append('|--------|--------|')
lines.append('| `v1.6.5-sales-ops` | **Atual.** Fluxos comerciais: CRM, propostas, orcamentos, contratos, white-label. |')
lines.append('| `v1.6.4-customer-demo-pack` | Demo pack comercial com 5 cenarios, meeting ready check, capabilities page. |')
lines.append('| `v1.6.3-readiness-cleanup` | Readiness final com correcao de warnings, probe chat/SSE/TTS/CORS. |')
lines.append('')
lines.append('## Releases Antigas / Legado')
lines.append('')
lines.append('| Periodo | Versoes | Descricao |')
lines.append('|---------|---------|-----------|')
lines.append('| v1.0.x - v1.4.x | v1.0.0-beta ate v1.4.7-local-demo | Fundacao: modelo SaaS, admin-lab, model management, RAG, billing local, DR. |')
lines.append('| v1.5.0 - v1.5.1 | v1.5.0-local-production, v1.5.1-local-production | Local production release com Pocket TTS. |')
lines.append('| v1.5.2 | v1.5.3-local-ops (tag) | Ops: production readiness report, security report, retention, release bundle. |')
lines.append('| v1.5.4 | v1.5.4-security-cleanup | Security cleanup: report workflow, artifact validation, permissions, gitignore. |')
lines.append('| v1.5.5 | v1.5.5-security-artifacts-clean | Artifact redaction, secret diagnosis, stronger validation. |')
lines.append('| v1.5.6 | v1.5.6-runtime-hardening | Runtime health, TTS governance, upgrade/rollback, benchmark. |')
lines.append('| v1.6.0 | v1.6.0-openai-compat | OpenAI-compatible responses e embeddings APIs. |')
lines.append('| v1.6.1 | v1.6.1-product-hardening | Makefile, system control center, migrations hardening, multi-tenant, abuse protection. |')
lines.append('| v1.6.2 | v1.6.2-installer-polish | Instalador local, wizard, checklist, backup/upgrade, validacao pos-instalacao. |')
lines.append('')
lines.append('## Como Restaurar uma Versao')
lines.append('')
lines.append('```bash')
lines.append('# Listar tags disponiveis')
lines.append('git tag -l "v*" --sort=-version:refname')
lines.append('')
lines.append('# Restaurar via tag')
lines.append('git checkout tags/v1.6.5-sales-ops -b restore/v1.6.5-sales-ops')
lines.append('')
lines.append('# Ou via stable branch')
lines.append('git checkout stable/v1.6.5-sales-ops')
lines.append('')
lines.append('# Verificar versao')
lines.append('cat VERSION')
lines.append('```')
lines.append('')
lines.append('## Como Criar uma Nova Release')
lines.append('')
lines.append('1. Crie uma branch feature a partir da ultima stable:')
lines.append('   ```bash')
lines.append('   git checkout stable/v<versao-anterior>')
lines.append('   git checkout -b feature/v<versao>-<descricao>')
lines.append('   ```')
lines.append('2. Desenvolva e valide localmente com `make validate`.')
lines.append('3. Crie a tag: `git tag v<versao>-<descricao>`')
lines.append('4. Crie a branch stable: `git branch stable/v<versao>-<descricao> <tag>`')
lines.append('5. Envie as mudancas: `git push origin <tag> stable/v<versao>-<descricao>`')
lines.append('6. Gere relatorio de release.')
lines.append('')
lines.append('## Politica de Branches / Tags')
lines.append('')
lines.append('- **feature/***: Branches de desenvolvimento. Sao eliminadas apos estabilizacao.')
lines.append('- **stable/***: Branches de release estavel. Nao devem ser deletadas.')
lines.append('- **Tags v***: Marcam pontos de release no git. Sao imutaveis.')
lines.append('- **VERSION**: Arquivo na raiz do repositorio apontando a versao atual.')
lines.append('- **CHANGELOG.md**: Mantido manualmente para cada release.')
lines.append('- **releases/<version>/summary.json**: Gerado automaticamente durante validacao da release.')
lines.append('')

with open(OUTPUT_MD, 'w') as f:
    f.write('\n'.join(lines))

print('Generated: ' + OUTPUT_MD)
print('JSON:      ' + OUTPUT_JSON)
print('')
print('Releases found: %d' % len(releases))
for r in releases:
    meta = str(r['has_releases_dir']).lower()
    print('  %-30s status=%-10s metadata=%s' % (r['tag'], r['status'], meta))
PYEOF

python3 "$PY_SCRIPT" "$PROJECT_ROOT" "$OUTPUT_MD" "$OUTPUT_JSON"
rm -f "$PY_SCRIPT"
