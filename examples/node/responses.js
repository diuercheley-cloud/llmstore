const BASE_URL = process.env.BASE_URL || "http://localhost:18080";
const API_KEY = process.env.CLIENT_API_KEY;

if (!API_KEY) {
  console.error("Error: CLIENT_API_KEY is not set.");
  process.exit(1);
}

async function main() {
  const url = `${BASE_URL}/v1/responses`;
  const headers = {
    "Authorization": `Bearer ${API_KEY}`,
    "Content-Type": "application/json"
  };
  const body = JSON.stringify({
    model: "default",
    input: "Why is the sky blue?",
    instructions: "Explain like I'm five.",
    temperature: 0.7,
    metadata: { example: "node" }
  });

  console.log(`Sending request to ${url}...`);
  try {
    const response = await fetch(url, {
      method: "POST",
      headers,
      body
    });

    if (response.ok) {
      const data = await response.json();
      console.log("Response received:");
      console.log(JSON.stringify(data, null, 2));
    } else {
      console.error(`Error: ${response.status}`);
      console.error(await response.text());
    }
  } catch (error) {
    console.error("Request failed:", error.message);
  }
}

main();
