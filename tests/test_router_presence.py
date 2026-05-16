import pytest
from app.main import app

def test_required_routers_are_present():
    """
    Testa se as rotas obrigatórias do sistema estão presentes no app principal, incluindo os métodos HTTP esperados.
    Garante que remoções acidentais de routers (como ocorreu com o admin_router) sejam detectadas imediatamente no boot/CI.
    """
    routes_map = {}
    for route in app.routes:
        if hasattr(route, "path"):
            path = route.path
            methods = getattr(route, "methods", set())
            
            if path not in routes_map:
                routes_map[path] = set()
                
            if methods:
                routes_map[path].update(methods)
            
    required_endpoints = [
        ("/admin-tests", "GET"),
        ("/admin/tests/auth/whoami", "GET"),
        ("/health", "GET"),
        ("/ready", "GET"),
        ("/v1/chat/completions", "POST"),
        ("/admin/governance/deterministic-policies", "GET"),
    ]
    
    for path, method in required_endpoints:
        assert path in routes_map, f"Rota crítica ausente: {path}. Verifique o main.py e a importação dos routers."
        assert method in routes_map[path], f"Método {method} ausente para a rota {path}. Métodos encontrados: {routes_map[path]}"
    
    # Verifica também se existem endpoints baseados no admin base de forma genérica
    # Pois /admin engloba várias rotas
    admin_routes_present = any(p.startswith("/admin/") and "tests" not in p for p in routes_map.keys())
    assert admin_routes_present, "Nenhuma rota administrativa (/admin/*) encontrada! admin_router não foi incluído?"
