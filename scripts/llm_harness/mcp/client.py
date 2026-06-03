# scripts/llm_harness/mcp/client.py
import asyncio
import atexit
import hashlib
import json
import logging
import signal
from typing import Any, Dict, List, Optional

from ..policy import PolicyEngine
from ..sanitizer import Sanitizer

logger = logging.getLogger("llm_harness.mcp")

_cleanup_registered = False


def _global_mcp_cleanup():
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(mcp_client.shutdown())
    except RuntimeError:
        pass
    except Exception:
        pass


class MCPClient:
    def __init__(
        self, enabled: bool = False, servers: Optional[List[Dict[str, Any]]] = None
    ):
        global _cleanup_registered
        self.enabled = enabled
        self.servers_config = servers or []
        self.active_processes: Dict[str, asyncio.subprocess.Process] = {}
        self.tools: Dict[str, Dict[str, Any]] = {}  # tool_name -> tool_metadata
        self.tool_to_server: Dict[str, str] = {}    # tool_name -> server_name
        self.mcp_logs: List[Dict[str, Any]] = []
        self._shutdown_timeout: float = 5.0

        if not _cleanup_registered:
            _cleanup_registered = True
            atexit.register(_global_mcp_cleanup)
            try:
                signal.signal(signal.SIGTERM, lambda *_: _global_mcp_cleanup())
                signal.signal(signal.SIGINT, lambda *_: _global_mcp_cleanup())
            except (ValueError, OSError):
                pass

    def is_enabled(self) -> bool:
        return self.enabled

    async def initialize(self):
        if not self.enabled:
            return
        
        self.mcp_logs.clear()
        for srv in self.servers_config:
            name = srv.get("name")
            cmd = srv.get("command")
            args = srv.get("args", [])
            if not name or not cmd:
                continue
            try:
                # Start subprocess
                proc = await asyncio.create_subprocess_exec(
                    cmd, *args,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL
                )
                self.active_processes[name] = proc
                logger.info(f"Started MCP Server: {name}")
                # List tools via initialize/listTools
                await self._list_tools_from_server(name)
            except Exception as e:
                logger.error(f"Failed to start MCP Server {name}: {e}")

    async def _list_tools_from_server(self, server_name: str):
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        res = await self._send_request(server_name, req)
        if res and "result" in res and "tools" in res["result"]:
            for tool in res["result"]["tools"]:
                tname = tool["name"]
                self.tools[tname] = tool
                self.tool_to_server[tname] = server_name
                logger.info(f"Discovered MCP tool '{tname}' on server '{server_name}'")

    async def _send_request(
        self, server_name: str, request: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        proc = self.active_processes.get(server_name)
        if not proc or not proc.stdin or not proc.stdout:
            return None
        try:
            line = json.dumps(request) + "\n"
            proc.stdin.write(line.encode("utf-8"))
            await proc.stdin.drain()
            
            res_line = await proc.stdout.readline()
            if not res_line:
                return None
            return json.loads(res_line.decode("utf-8"))
        except Exception as e:
            logger.error(f"MCP JSON-RPC request to {server_name} failed: {e}")
            return None

    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        return self.tools

    async def call_tool(
        self, tool_name: str, arguments: Dict[str, Any], policy_engine: PolicyEngine
    ) -> Dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("MCP is disabled.")

        server_name = self.tool_to_server.get(tool_name)
        if not server_name:
            raise ValueError(f"Unknown MCP tool: {tool_name}")

        # Check Policy: MCP desabilitado por padrão
        # exigir allow_mcp_tools=true
        allow_mcp = getattr(policy_engine, "allow_mcp_tools", False)
        if not allow_mcp:
            raise PermissionError(
                f"MCP tool '{tool_name}' call blocked: allow_mcp_tools=false in PolicyEngine"
            )

        # cada chamada MCP passa pela PolicyEngine (e.g. check paths in arguments)
        for k, v in arguments.items():
            if isinstance(v, str) and ("/" in v or "\\" in v or "." in v):
                dec = policy_engine.evaluate_file_path(v)
                if not dec.allowed:
                    raise PermissionError(
                        f"MCP tool call blocked by path policy for arg '{k}': {dec.reason}"
                    )

        # Hash input and sanitize payloads
        input_str = json.dumps(arguments)
        input_hash = hashlib.sha256(input_str.encode()).hexdigest()
        
        sanitized_arguments = Sanitizer.sanitize_data(arguments)

        req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": sanitized_arguments
            }
        }
        
        res = await self._send_request(server_name, req)
        if not res:
            raise RuntimeError(
                f"No response from MCP Server '{server_name}' for tool '{tool_name}'"
            )
        
        if "error" in res:
            err_msg = res["error"].get("message", "Unknown MCP server error")
            raise RuntimeError(f"MCP server error: {err_msg}")

        result_content = res.get("result", {})
        output_str = json.dumps(result_content)
        output_hash = hashlib.sha256(output_str.encode()).hexdigest()
        
        log_entry = {
            "tool": tool_name,
            "server": server_name,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "sanitized_arguments": sanitized_arguments,
            "sanitized_result": Sanitizer.sanitize_data(result_content)
        }
        self.mcp_logs.append(log_entry)
        
        logger.info(
            f"MCP Call Log: tool={tool_name}, server={server_name}, "
            f"input_hash={input_hash}, output_hash={output_hash}"
        )
        
        return Sanitizer.sanitize_data(result_content)

    async def shutdown(self):
        for name, proc in list(self.active_processes.items()):
            try:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=self._shutdown_timeout)
                except asyncio.TimeoutError:
                    logger.warning(
                        "MCP Server '%s' did not exit in %.1fs, killing...",
                        name, self._shutdown_timeout,
                    )
                    proc.kill()
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=2.0)
                    except asyncio.TimeoutError:
                        logger.error("Failed to kill MCP Server '%s'", name)
                logger.info(f"Stopped MCP Server: {name}")
            except ProcessLookupError:
                pass
            except Exception as exc:
                logger.warning("Error stopping MCP Server '%s': %s", name, exc)
        self.active_processes.clear()

mcp_client = MCPClient()


async def initialize_mcp_and_register_tools(policy_engine):
    from ..plugins import plugin_registry
    await mcp_client.initialize()
    for tool_name in mcp_client.list_tools().keys():
        def make_mcp_wrapper(tname):
            async def mcp_tool_wrapper(action_args, context):
                pe = (
                    context.get("coding_loop").policy_engine
                    if context.get("coding_loop")
                    else policy_engine
                )
                args = action_args.get("arguments", action_args)
                if "action_type" in args:
                    args = {k: v for k, v in args.items() if k != "action_type"}
                return await mcp_client.call_tool(tname, args, pe)
            return mcp_tool_wrapper
        
        # Register the wrapper
        plugin_registry.register_tool(f"mcp:{tool_name}", make_mcp_wrapper(tool_name))
