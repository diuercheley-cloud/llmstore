import pytest
import httpx
from app.main import app

@pytest.mark.asyncio
async def test_landing_page_local_commercial_content():
    """
    Verifica se a landing page local contém os elementos comerciais e links
    especificados para a demonstração do produto local.
    """
    # Usamos o transport ASGITransport para testar o app FastAPI diretamente
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        content = response.text
        
        # 1. Seções comerciais e destaques
        assert "LLM Local para Empresas" in content
        assert "API compatível com OpenAI" in content
        assert "RAG com documentos internos" in content
        assert "Controle de Clientes e Uso" in content
        assert "Admin Lab p/ Modelos Locais" in content
        assert "Operação em Localhost" in content
        
        # 2. Demonstração local (links e títulos)
        assert "Demonstração Local" in content
        assert "Client Portal Demo" in content
        assert 'href="/portal/"' in content
        assert 'href="/admin/"' in content
        assert 'href="/docs"' in content
        
        # 3. Fora do escopo (limitações claras para evitar falsas promessas)
        assert "Fora do escopo nesta versão" in content
        assert "Pagamentos Reais (PSP/PIX)" in content
        assert "SLA de Disponibilidade Pública" in content
        assert "Domínio Público Obrigatório" in content
        
        # 4. Casos de Uso
        assert "Casos de Uso" in content
        assert "Escritórios e Consultoria" in content
        assert "Imobiliárias e Contabilidade" in content
        assert "Suporte Interno" in content
        
        # 5. CTAs Principais
        assert "Abrir Admin Dashboard" in content
        assert "Abrir Client Portal" in content
        assert "Ver Documentação" in content
        assert "Rodar validação local" in content
        
        # 6. Rodapé e Branding
        assert "LLM Inference Stack • Local Production Edition" in content
        assert "© 2026" in content
