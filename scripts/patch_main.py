
path = "control_plane/app/main.py"
with open(path, "r") as f:
    content = f.read()

import_statement = "from app.api.agent_tool_synthesis_admin import admin_router as tool_synthesis_admin_router, sandbox_router as tool_synthesis_sandbox_router, public_router as tool_synthesis_public_router"

# Insert import
last_api_import_idx = content.rfind("from app.api.")
if last_api_import_idx != -1:
    end_of_line = content.find("\n", last_api_import_idx)
    content = content[:end_of_line+1] + import_statement + "\n" + content[end_of_line+1:]

# Insert routers
include_admin = "app.include_router(tool_synthesis_admin_router)"
include_sandbox = "app.include_router(tool_synthesis_sandbox_router)"
include_public = "app.include_router(tool_synthesis_public_router)"

include_idx = content.rfind("app.include_router(")
if include_idx != -1:
    end_of_line = content.find("\n", include_idx)
    insert_str = f"\n    {include_admin}\n    {include_sandbox}\n    {include_public}"
    content = content[:end_of_line] + insert_str + content[end_of_line:]

with open(path, "w") as f:
    f.write(content)
