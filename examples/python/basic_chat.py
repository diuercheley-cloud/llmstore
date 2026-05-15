import os
import sys

# Adiciona o diretório do SDK ao path para teste local
sys.path.append(os.path.join(os.path.dirname(__file__), "../../sdk/python"))

from kleberai import Client

def main():
    api_key = os.getenv("KLEBERAI_API_KEY", "test-key")
    base_url = os.getenv("KLEBERAI_BASE_URL", "http://localhost:18080")
    
    client = Client(api_key=api_key, base_url=base_url)
    
    print("Enviando pergunta...")
    try:
        response = client.chat("Explique o que é RAG em poucas palavras.")
        print("\nResposta:")
        print(response["choices"][0]["message"]["content"])
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
