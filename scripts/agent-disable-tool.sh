#!/bin/bash
# Disable a tool for an agent or globally
TOOL_NAME=$1
AGENT_ID=$2
if [ -z "$TOOL_NAME" ]; then
    echo "Usage: $0 <tool_name> [agent_id]"
    exit 1
fi

if [ -z "$AGENT_ID" ]; then
    echo "Disabling tool $TOOL_NAME globally..."
else
    echo "Disabling tool $TOOL_NAME for agent $AGENT_ID..."
fi
# Simulated disable logic
echo "Tool $TOOL_NAME is now disabled."
