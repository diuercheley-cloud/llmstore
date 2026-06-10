#!/usr/bin/env bash

# Alembic Integrity Check: Ensures exactly one head.

cd control_plane
HEADS=$(alembic heads | wc -l)

if [ "$HEADS" -ne 1 ]; then
    echo "ERROR: Multiple or zero Alembic heads detected: $HEADS"
    alembic heads
    exit 1
else
    echo "PASS: Exactly one Alembic head found."
    exit 0
fi
