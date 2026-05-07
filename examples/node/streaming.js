const BASE_URL = process.env.BASE_URL || "http://localhost:18080";
const API_KEY = process.env.CLIENT_API_KEY;

if (!API_KEY) {
  console.error("Error: CLIENT_API_KEY is not set.");
  process.exit(1);
}

async function main() {
  const url = `${BASE_URL}/v1/chat/completions`;
  const headers = {
    "Authorization": `Bearer ${API_KEY}`,
    "Content-Type": "application/json"
  };
  const body = JSON.stringify({
    model: "default",
    messages: [
      { role: "user", content: "Tell me a story about a brave robot in 3 paragraphs." }
    ],
    stream: true,
    temperature: 0.7
  });

  console.log(`Sending streaming request to ${url}...`);
  try {
    const response = await fetch(url, {
      method: "POST",
      headers,
      body
    });

    if (!response.ok) {
      console.error(`Error: ${response.status}`);
      console.error(await response.text());
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    console.log("Response stream:");
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split("\n");
      
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6);
          if (data === "[DONE]") continue;
          
          try {
            const json = JSON.parse(data);
            const content = json.choices[0]?.delta?.content;
            if (content) {
              process.stdout.write(content);
            }
          } catch (e) {
            // Ignore parse errors for incomplete JSON
          }
        }
      }
    }
    console.log("\nStream finished.");
  } catch (error) {
    console.error("Request failed:", error.message);
  }
}

main();
