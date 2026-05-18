# Tokenization

The LLM Inference Stack uses a centralized `TokenizerService` to count tokens for various operations.

## Tokenization Methods

The service supports the following methods:

- **tiktoken**: Used for OpenAI-compatible models (e.g., GPT series, Claude, DeepSeek). It uses the `tiktoken` library with the appropriate encoding for the model.
- **hf_tokenizer**: Used when a local HuggingFace tokenizer is configured via `TOKENIZER_MODEL_PATH`.
- **estimated**: Fallback method used when no real tokenizer is available. It estimates tokens based on character count (approx. 4 characters per token or word-based heuristic).

## Configuration

The following environment variables control tokenization:

- `TOKENIZER_MODE`: Default `auto`.
- `TOKENIZER_MODEL_PATH`: Path to a local `tokenizer.json` or model directory for HuggingFace tokenizers.
- `TOKENIZER_STRICT`: If `true`, the system will raise an error if a real tokenizer cannot be found for a model, instead of falling back to estimation.
- `TOKENIZER_CACHE_ENABLED`: Default `true`. Caches `tiktoken` encodings for performance.

## Usage Tracking

The method used for token counting is recorded in each `usage_record` and `request_financial` entry.
The boolean field `tokens_estimated` indicates whether the count was estimated or calculated using a real tokenizer.
