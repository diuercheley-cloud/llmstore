#!/usr/bin/env python3
import asyncio
import sys
import os

# Append workspace root and control_plane/ to sys.path so we can import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "control_plane"))

from app.db.session import SessionLocal
from app.services.security.immutable_audit import ImmutableAuditStore

async def main():
    print("Connecting to database...")
    try:
        async with SessionLocal() as db:
            print("Verifying cryptographic chain of audit logs...")
            is_valid, failed_block_id, reason = await ImmutableAuditStore.verify_chain(db)
            if is_valid:
                print("SUCCESS: Audit trail is fully verified and consistent.")
                sys.exit(0)
            else:
                print(f"FAILURE: Audit chain broken at block ID #{failed_block_id}.")
                print(f"Reason: {reason}")
                sys.exit(1)
    except Exception as e:
        print(f"Error connecting to database or verifying: {e}")
        sys.exit(2)

if __name__ == "__main__":
    asyncio.run(main())
