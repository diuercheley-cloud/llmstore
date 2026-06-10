#!/bin/bash
# scripts/dev/agent-test.sh
# Entry point for running agent tests and tasks.
# Supports legacy mode (direct agent_harness.py) and code subcommand (CLI delegation).

set -e

PYTHON=".venv/bin/python3"

usage() {
    cat <<EOF
Usage: $0 <command> [options]

Commands:
  run          Legacy mode: run agent task directly via agent_harness.py
  code         Delegate to llm_harness CLI for coding tasks
  --help       Show this help message

Options for 'run':
  --agent-id ID      ID of the agent to use
  --task TASK        Task description for the agent
  --workspace DIR    Custom workspace directory
  --timeout SEC      Execution timeout in seconds

Options for 'code':
  --task TASK        Task description (required)
  --agent-id ID      Agent ID (default: default-coder)
  --provider TYPE    Provider: openai-compatible or stub
  --allow-stub       Allow stub provider without real LLM

Examples:
  $0 run --agent-id my-agent --task "Fix bug in main.py"
  $0 code --task "Add tests for auth" --agent-id coder-1
  $0 --help
EOF
    exit 0
}

# No args or --help -> show usage
if [[ $# -eq 0 || "$1" == "--help" ]]; then
    usage
fi

COMMAND="$1"
shift

case "$COMMAND" in
    run)
        AGENT_ID=""
        TASK=""
        WORKSPACE=""
        TIMEOUT=300

        while [[ "$#" -gt 0 ]]; do
            case $1 in
                --agent-id) AGENT_ID="$2"; shift ;;
                --task) TASK="$2"; shift ;;
                --workspace) WORKSPACE="$2"; shift ;;
                --timeout) TIMEOUT="$2"; shift ;;
                --help) usage ;;
                *) echo "Unknown parameter: $1"; usage; exit 1 ;;
            esac
            shift
        done

        if [[ -z "$AGENT_ID" || -z "$TASK" ]]; then
            echo "Error: --agent-id and --task are required."
            usage
            exit 1
        fi

        echo "--- Starting Agent Task (Legacy Mode) ---"
        echo "Agent: $AGENT_ID"
        echo "Task: $TASK"
        echo "---"

        PYTHONPATH=. "$PYTHON" -m scripts.llm_harness.legacy_runner \
            --agent-id "$AGENT_ID" \
            --task "$TASK" \
            --timeout "$TIMEOUT" \
            ${WORKSPACE:+--workspace "$WORKSPACE"}

        echo "--- Agent Task Completed ---"
        ;;
    code)
        # Delegate to llm_harness.cli
        PYTHONPATH=. "$PYTHON" -m scripts.llm_harness.cli code "$@"
        ;;
    *)
        echo "Unknown command: $COMMAND"
        usage
        exit 1
        ;;
esac
