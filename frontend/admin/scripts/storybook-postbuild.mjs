import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const outputDir = resolve(process.cwd(), "storybook-static");
const customDomain = process.env.STORYBOOK_DOCS_DOMAIN?.trim();

if (!existsSync(outputDir)) {
  throw new Error(`storybook-static directory not found at ${outputDir}`);
}

if (customDomain) {
  writeFileSync(resolve(outputDir, "CNAME"), `${customDomain}\n`, "utf8");
  console.log(`Storybook CNAME written for ${customDomain}`);
}

const metadataDir = resolve(outputDir, ".well-known");
mkdirSync(metadataDir, { recursive: true });
writeFileSync(
  resolve(metadataDir, "storybook-site.json"),
  JSON.stringify(
    {
      generatedAt: new Date().toISOString(),
      customDomain: customDomain || null,
      audience: ["design", "qa"],
    },
    null,
    2
  ),
  "utf8"
);
