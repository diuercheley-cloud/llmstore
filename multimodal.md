# Multimodal Core

## Overview
Added support for multiple input/output modalities for LLM and Agent workflows.

## Features
- **Vision Input:** Image processing, document OCR.
- **Image Generation:** Generation of assets for agents.
- **Audio/Speech:** Speech-to-Text and continuous audio ingestion.

## Governance
All multimodal features are safely guarded by the `MULTIMODAL_ENABLED` flag (defaults to `false`). No external providers are forced; developers can use local models.
