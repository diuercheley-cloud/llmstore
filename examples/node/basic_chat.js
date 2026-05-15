import { Client } from "../../sdk/node/dist/index.js";

async function main() {
  const apiKey = process.env.KLEBERAI_API_KEY || "test-key";
  const baseUrl = process.env.KLEBERAI_BASE_URL || "http://localhost:18080";

  const client = new Client({ apiKey, baseUrl });

  console.log("Enviando pergunta...");
  try {
    const response = await client.chat("Explique o que é um LLM em poucas palavras.");
    console.log("\nResposta:");
    console.log(response.choices[0].message.content);
  } catch (error) {
    console.error("Erro:", error.message);
    if (error.body) {
      console.error("Detalhes:", JSON.stringify(error.body, null, 2));
    }
  }
}

main();
