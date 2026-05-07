const BASE_URL = process.env.BASE_URL || "http://localhost:18080";
const API_KEY = process.env.CLIENT_API_KEY;

if (!API_KEY) {
  console.error("Error: CLIENT_API_KEY is not set.");
  process.exit(1);
}

async function main() {
  const question = process.argv[2] || "What is in the uploaded documents?";
  
  const url = `${BASE_URL}/v1/rag/query`;
  const headers = {
    "Authorization": `Bearer ${API_KEY}`,
    "Content-Type": "application/json"
  };
  const body = JSON.stringify({
    question: question,
    model: "default",
    top_k: 3,
    max_tokens: 500,
    temperature: 0.2
  });

  console.log(`Sending RAG query to ${url}...`);
  console.log(`Question: ${question}`);

  try {
    const response = await fetch(url, {
      method: "POST",
      headers,
      body
    });

    if (response.ok) {
      const result = await response.json();
      console.log("\nAnswer:");
      console.log(result.answer);
      
      console.log("\nSources:");
      (result.sources || []).forEach(source => {
        console.log(`- ${source.filename} (Page ${source.page}, Score: ${source.score.toFixed(4)})`);
      });
      
      console.log(`\nUsage: ${result.usage?.total_tokens} tokens`);
    } else if (response.status === 403) {
      console.error("Error: RAG is disabled or feature blocked.");
      console.error(await response.text());
    } else {
      console.error(`Error: ${response.status}`);
      console.error(await response.text());
    }
  } catch (error) {
    console.error("Request failed:", error.message);
  }
}

main();
