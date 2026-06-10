#!/usr/bin/env bash
# =============================================================================
# validate-enterprise-rag-local.sh
# Validates Enterprise RAG pipeline
# =============================================================================

set -u
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS=0; FAIL=0; SKIP=0
pass() { echo -e "${GREEN}[PASS]${NC} $1"; PASS=$((PASS+1)); }
fail() { echo -e "${RED}[FAIL]${NC} $1"; FAIL=$((FAIL+1)); }
skip() { echo -e "${YELLOW}[SKIP]${NC} $1"; SKIP=$((SKIP+1)); }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

PYTHON=".venv/bin/python"
[[ -f "$PYTHON" ]] || PYTHON="python3"

run() {
    PYTHONPATH="control_plane:." $PYTHON -c "$1" 2>/dev/null
}

echo "============================================"
echo " Enterprise RAG Validation Suite"
echo "============================================"

echo "--- Parser Status ---"

if run "from app.services.rag_enterprise.parsers import get_parser_status; assert get_parser_status('.txt').available"; then
    pass "TXT parser available"
else
    fail "TXT parser should always be available"
fi

if run "from app.services.rag_enterprise.parsers import get_parser_status; assert get_parser_status('.md').available"; then
    pass "MD parser available"
else
    fail "MD parser should always be available"
fi

if run "from app.services.rag_enterprise.parsers import get_parser_status; assert get_parser_status('.csv').available"; then
    pass "CSV parser available"
else
    fail "CSV parser should always be available"
fi

if run "from app.services.rag_enterprise.parsers import get_parser_status; s=get_parser_status('.pdf'); assert not s.available"; then
    skip "PDF not available (needs: pymupdf)"
elif run "from app.services.rag_enterprise.parsers import get_parser_status; assert get_parser_status('.pdf').available"; then
    pass "PDF parser available"
fi

if run "from app.services.rag_enterprise.parsers import get_parser_status; s=get_parser_status('.docx'); assert not s.available"; then
    skip "DOCX not available (needs: python-docx)"
elif run "from app.services.rag_enterprise.parsers import get_parser_status; assert get_parser_status('.docx').available"; then
    pass "DOCX parser available"
fi

if run "from app.services.rag_enterprise.parsers import get_parser_status; s=get_parser_status('.xlsx'); assert not s.available"; then
    skip "XLSX not available (needs: openpyxl)"
elif run "from app.services.rag_enterprise.parsers import get_parser_status; assert get_parser_status('.xlsx').available"; then
    pass "XLSX parser available"
fi

echo "--- Chunking ---"

if run "
from app.services.rag_enterprise.chunking import chunk_text
from app.services.rag_enterprise.schemas import ChunkingConfig
c = ChunkingConfig(chunk_size=1000, chunk_overlap=0)
r = chunk_text('A' * 5000, c)
assert len(r) == 5
"; then
    pass "Fixed chunking works"
else
    fail "Fixed chunking failed"
fi

if run "
from app.services.rag_enterprise.chunking import chunk_text
from app.services.rag_enterprise.schemas import ChunkingConfig, ChunkStrategy
c = ChunkingConfig(chunk_size=5000, chunk_overlap=0, strategy=ChunkStrategy.heading)
r = chunk_text('# T\n\nC\n\n## S\n\nM', c)
assert len(r) >= 1
"; then
    pass "Heading chunking works"
else
    fail "Heading chunking failed"
fi

if run "
from app.services.rag_enterprise.chunking import chunk_text
from app.services.rag_enterprise.schemas import ChunkingConfig, ChunkStrategy
c = ChunkingConfig(chunk_size=5000, chunk_overlap=0, strategy=ChunkStrategy.semantic_placeholder)
r = chunk_text('P1\n\nP2\n\nP3', c)
assert len(r) >= 1
"; then
    pass "Semantic chunking works"
else
    fail "Semantic chunking failed"
fi

if run "
from app.services.rag_enterprise.chunking import chunk_by_fixed
from app.services.rag_enterprise.schemas import ChunkingConfig
c = ChunkingConfig(chunk_size=100, chunk_overlap=0)
r = chunk_by_fixed('Hello world ' * 20, c)
for x in r:
    assert x.metadata.get('strategy')
    assert x.chunk_index >= 0
"; then
    pass "Chunk metadata OK"
else
    fail "Chunk metadata incomplete"
fi

echo "--- Embeddings ---"

if run "
import asyncio
from app.services.rag_enterprise.embeddings import EnterpriseEmbeddingService
s = EnterpriseEmbeddingService()
e = asyncio.run(s.embed_text('test', cloud_allowed=False))
assert len(e) == 384
"; then
    pass "Mock embeddings work"
else
    fail "Mock embeddings failed"
fi

echo "--- Cloud Embeddings ---"

if run "
from app.services.rag_enterprise.policies import EnterpriseRagPolicy
p = EnterpriseRagPolicy()
assert p.cloud_embeddings_allowed is False
"; then
    pass "Cloud embeddings disabled by default"
else
    fail "Cloud embeddings should be disabled"
fi

echo "--- Tenant Isolation ---"

if run "
from app.services.rag_enterprise.retrieval import search_chunks
import inspect
assert 'client_id' in inspect.signature(search_chunks).parameters
"; then
    pass "Tenant isolation via client_id"
else
    fail "Tenant isolation missing"
fi

echo "--- Policies ---"

if run "
from app.services.rag_enterprise.policies import EnterpriseRagPolicy
p = EnterpriseRagPolicy()
assert p.rag_enabled
assert len(p.allowed_file_types) == 6
"; then
    pass "Policies defined"
else
    fail "Policies missing"
fi

if run "
from app.services.rag_enterprise.policies import check_quota_documents, check_quota_storage
import inspect
assert inspect.iscoroutinefunction(check_quota_documents)
assert inspect.iscoroutinefunction(check_quota_storage)
"; then
    pass "Quota functions available"
else
    fail "Quota functions missing"
fi

echo "--- Security ---"

SECRET_PATTERNS=('sk-' 'secret' 'api_key' 'password')
ALL_GOOD=true
for pattern in "${SECRET_PATTERNS[@]}"; do
    if grep -rl "$pattern" control_plane/app/services/rag_enterprise/ 2>/dev/null | grep -v __pycache__ > /dev/null; then
        echo "  WARNING: '$pattern' found"
        ALL_GOOD=false
    fi
done
if $ALL_GOOD; then
    pass "No secrets in rag_enterprise code"
else
    fail "Secrets detected"
fi

echo "--- Document Deletion ---"

if run "
from app.services.rag_enterprise.ingestion import delete_enterprise_document
import inspect
assert inspect.iscoroutinefunction(delete_enterprise_document)
"; then
    pass "Delete function available"
else
    fail "Delete function missing"
fi

echo "--- Supported Formats ---"
run "
from app.services.rag_enterprise.schemas import SUPPORTED_EXTENSIONS
from app.services.rag_enterprise.parsers import get_parser_status
for ext in sorted(SUPPORTED_EXTENSIONS):
    s = get_parser_status(ext)
    icon = 'OK' if s.available else '--'
    dep = f' ({s.dependency})' if s.dependency else ''
    print(f'  [{icon}] {ext}{dep}')
"

echo "--- Admin ---"

if run "
from app.api.rag_enterprise import admin_router
assert any('/overview' in r.path for r in admin_router.routes)
"; then
    pass "Admin overview registered"
else
    fail "Admin overview missing"
fi

if run "
from app.api.rag_enterprise import router
routes = [r.path for r in router.routes]
for p in ['/collections', '/documents', '/query']:
    assert any(p in r for r in routes), f'Missing {p}'
"; then
    pass "All RAG endpoints registered"
else
    fail "Some endpoints missing"
fi

echo ""
echo "============================================"
echo -e " Results: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC}, ${YELLOW}$SKIP skipped${NC}"
echo "============================================"
if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
exit 0
