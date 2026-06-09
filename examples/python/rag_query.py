import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../../sdk/python"))

from kleberai import Client


def main():
    api_key = os.getenv("CLIENT_API_KEY") or os.getenv("KLEBERAI_API_KEY", "test-key")
    base_url = os.getenv("KLEBERAI_BASE_URL", "http://localhost:18080")
    
    client = Client(api_key=api_key, base_url=base_url)
    
    print("Executando consulta RAG...")
    try:
        # Se você tiver IDs de documentos específicos, passe aqui: file_ids=["uuid1", "uuid2"]
        response = client.rag_query("Como configurar o stack?")
        print("\nResposta RAG:")
        print(response["answer"])
        print("\nFontes:")
        for source in response.get("sources", []):
            print(f"- {source['filename']} (pág {source['page']})")
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
