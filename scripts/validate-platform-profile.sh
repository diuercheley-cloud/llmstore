#!/usr/bin/env bash
set -euo pipefail

PROFILE=${1:-appliance}
echo "Validating platform profile: $PROFILE"

export PYTHONPATH=$PYTHONPATH:$(pwd)/control_plane
python3 -c "from app.services.platform.profile_resolver import ProfileResolver; r = ProfileResolver(); res = r.resolve('$PROFILE'); print(res)"
