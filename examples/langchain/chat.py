import os

from langchain_openai import ChatOpenAI

# Configuração da API
# Substitua pela sua chave real se necessário, ou use a demo padrão
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "demo-default")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "http://localhost:18080/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "unsloth/gemma-4-E4B-it-GGUF")

def main():
    print(f"Conectando ao modelo {MODEL_NAME} em {OPENAI_API_BASE}...")
    
    llm = ChatOpenAI(
        openai_api_base=OPENAI_API_BASE,
        openai_api_key=OPENAI_API_KEY,
        model_name=MODEL_NAME,
        temperature=0.7
    )

    messages = [
        ("system", "Você é um assistente prestativo e conciso."),
        ("user", "O que é o llm-inference-stack?")
    ]

    print("\nEnviando pergunta...")
    try:
        response = llm.invoke(messages)
        print("\nResposta:")
        print(response.content)
    except Exception as e:
        print(f"\nErro ao conectar: {e}")
        print("Certifique-se de que a stack está rodando (scripts/up.sh).")

if __name__ == "__main__":
    main()
