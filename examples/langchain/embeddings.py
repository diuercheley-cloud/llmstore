import os

from langchain_openai import OpenAIEmbeddings

# Configuração da API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "demo-default")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "http://localhost:18080/v1")
# No llm-inference-stack, o modelo de embedding padrão pode variar ou ser mockado
MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-3-small")

def main():
    print(f"Gerando embeddings usando {MODEL_NAME} em {OPENAI_API_BASE}...")
    
    embeddings = OpenAIEmbeddings(
        openai_api_base=OPENAI_API_BASE,
        openai_api_key=OPENAI_API_KEY,
        model=MODEL_NAME
    )

    text = "O llm-inference-stack permite rodar modelos locais com API compatível com OpenAI."
    
    try:
        vector = embeddings.embed_query(text)
        print("\nEmbedding gerado com sucesso!")
        print(f"Dimensões: {len(vector)}")
        print(f"Primeiros 5 valores: {vector[:5]}")
    except Exception as e:
        print(f"\nErro ao gerar embeddings: {e}")
        print("Certifique-se de que EMBEDDINGS_ENABLED=true no seu .env.")

if __name__ == "__main__":
    main()
