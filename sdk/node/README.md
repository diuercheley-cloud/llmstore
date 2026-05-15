# Kleber AI Node SDK

Minimal SDK for Kleber AI.

## Instalação

```bash
npm install
npm run build
```

## Uso

```javascript
import { Client } from "./sdk/node/dist/index.js";

const client = new Client({
  apiKey: "your-api-key",
  baseUrl: "http://localhost:18080"
});

// Chat
const response = await client.chat("Explique esse erro");
console.log(response.choices[0].message.content);

// Listar modelos
const models = await client.models();
console.log(models);
```
