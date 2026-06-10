#!/usr/bin/env bash
set -euo pipefail

PROFILE=${1:-appliance}
echo "Applying platform profile: $PROFILE"

export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/control_plane"
python3 -c "from app.services.platform.profile_resolver import ProfileResolver; r = ProfileResolver(); res = r.validate_profile('$PROFILE'); print(f'Validated profile {res[\"profile\"]}. Flags: {len(res[\"flags\"])}')"
