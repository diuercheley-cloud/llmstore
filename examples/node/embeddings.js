// Exemplo de uso do endpoint /v1/embeddings com Node.js

const API_KEY = process.env.CLIENT_API_KEY || "your-api-key";
const BASE_URL = process.env.API_BASE_URL || "http://localhost:8080/v1";

async function testEmbeddings() {
  const url = `${BASE_URL}/embeddings`;
  const payload = {
    model: "text-embedding-3-small",
    input: "Generating embeddings locally is fast and secure."
  };

  console.log(`Sending request to ${url}...`);

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${API_KEY}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    if (response.ok) {
      const data = await response.json();
      console.log("Success!");
      console.log(`Model: ${data.model}`);
      console.log(`Number of embeddings: ${data.data.length}`);
      console.log(`Embedding dimension: ${data.data[0].embedding.length}`);
      console.log("Usage:", data.usage);
    } else {
      console.error(`Error: ${response.status}`);
      console.error(await response.text());
    }
  } catch (err) {
    console.error("Fetch error:", err);
  }
}

testEmbeddings();
