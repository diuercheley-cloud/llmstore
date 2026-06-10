import os
import re

main_py = "control_plane/app/main.py"
with open(main_py, "r") as f:
    content = f.read()

import_regex = re.compile(r"from (app\.api\.[a-zA-Z0-9_]+) import .*router as ([a-zA-Z0-9_]+router)")
imports = {}
for match in import_regex.finditer(content):
    module_path = match.group(1)
    router_alias = match.group(2)
    imports[router_alias] = module_path.replace(".", "/") + ".py"

include_regex = re.compile(r'app\.include_router\(([\w_]+)(?:,\s*prefix="(.*?)")?(?:,\s*tags=\[(.*?)\])?\)')

modifications = 0
for match in include_regex.finditer(content):
    alias = match.group(1)
    prefix = match.group(2)
    tags = match.group(3)

    if alias in imports and (prefix or tags):
        file_path = "control_plane/" + imports[alias]
        if not os.path.exists(file_path):
            continue
        
        with open(file_path, "r") as r:
            f_content = r.read()
        
        # Simple string replacement for APIRouter()
        # Find router = APIRouter(...) or admin_router = APIRouter(...)
        # We look for the exact instantiation line. Since these files are standard, it's usually `router = APIRouter()`
        
        original = f_content
        
        # if the file has APIRouter()
        if "APIRouter()" in f_content:
            new_args = []
            if prefix:
                new_args.append(f'prefix="{prefix}"')
            if tags:
                new_args.append(f'tags=[{tags}]')
            
            replacement = f"APIRouter({', '.join(new_args)})"
            f_content = f_content.replace("APIRouter()", replacement)
            
            if f_content != original:
                with open(file_path, "w") as w:
                    w.write(f_content)
                modifications += 1
                print(f"Patched {file_path} with {replacement}")
print(f"Total modifications: {modifications}")
