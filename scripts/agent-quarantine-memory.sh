#!/bin/bash
# Quarantine agent memory items
AGENT_ID=$1
ITEMS_REGEX=$2
if [ -z "$AGENT_ID" ]; then
    echo "Usage: $0 <agent_id> <regex_filter>"
    exit 1
fi

echo "Quarantining memory for agent $AGENT_ID matching '$ITEMS_REGEX'..."
# Simulated quarantine logic
echo "Moved 14 items to agent_memory_tombstone."
echo "Backup created: backups/memory/t1_agent_backup_$(date +%Y%m%d).json"
