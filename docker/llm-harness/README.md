# LLM Harness Docker Container

This container provides a standalone environment for executing the LLM Harness.

## Building the Image

From the project root:
```bash
make docker-build-llm-harness
```

Or manually:
```bash
docker build -t llm-harness:latest -f docker/llm-harness/Dockerfile .
```

## Running the Container

### Get Help
```bash
make docker-run-llm-harness-help
```

### Check Health
```bash
make docker-run-llm-harness-health
```

### Execute a Task
To run a real task, you should mount your workspace and pass environment variables:

```bash
docker run --rm -it \
  -v $(pwd):/workspace \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  llm-harness:latest code --task "Fix bug in main.py"
```

## Configuration

The container follows the standard LLM Harness configuration via environment variables or CLI flags.

| Variable | Description |
| :--- | :--- |
| `LLM_HARNESS_LOCAL_ONLY` | Run only local checks in health |
| `LLM_HARNESS_VERSION_FILE` | Path to the version file |
| `OPENAI_API_KEY` | API key for OpenAI provider |
| `ANTHROPIC_API_KEY` | API key for Anthropic provider |
