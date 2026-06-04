import ast


class SecurityException(Exception):
    pass

class ToolValidatorNodeVisitor(ast.NodeVisitor):
    def __init__(self, allow_network: bool, allow_write: bool):
        self.allow_network = allow_network
        self.allow_write = allow_write
        
        self.blocked_imports = {
            "subprocess", "os", "sys", "pty", "ptyprocess", "shutil", 
            "socket", "urllib", "http", "ftplib", "telnetlib", "xmlrpc"
        }
        if not allow_network:
            self.blocked_imports.update({"requests", "httpx", "aiohttp", "urllib3"})

        self.blocked_functions = {"exec", "eval", "compile", "open", "input"}
        if allow_write:
            self.blocked_functions.remove("open")

    def visit_Import(self, node):
        for alias in node.names:
            base_module = alias.name.split('.')[0]
            if base_module in self.blocked_imports:
                raise SecurityException(f"Importing '{base_module}' is not allowed for security reasons.")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            base_module = node.module.split('.')[0]
            if base_module in self.blocked_imports:
                raise SecurityException(f"Importing from '{base_module}' is not allowed for security reasons.")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in self.blocked_functions:
                raise SecurityException(f"Function '{node.func.id}' is blocked for security reasons.")
        self.generic_visit(node)

def validate_generated_code(code: str, allow_network: bool = False, allow_write: bool = False):
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"Syntax error in generated code: {e}")
    
    visitor = ToolValidatorNodeVisitor(allow_network=allow_network, allow_write=allow_write)
    visitor.visit(tree)
    return True
