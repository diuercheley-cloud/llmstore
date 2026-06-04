# Owner: agent-platform
from typing import Any, Dict

from app.core.config import get_settings
from app.services.agents.browser.headless_browser_provider import (
    browser_click_element,
    browser_extract_page_text,
    browser_open_url,
    browser_take_screenshot,
    close_browser_session,
    get_browser_session,
)
from app.services.agents.tool_adapter_contract import ToolAdapterContract


class BrowserOpenToolAdapter(ToolAdapterContract):
    @property
    def name(self) -> str:
        return "browser_open"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to open in the browser."},
                "timeout": {"type": "integer", "default": 10, "description": "Connection timeout in seconds."}
            },
            "required": ["url"]
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "url": {"type": "string"},
                "title": {"type": "string"}
            }
        }

    @property
    def side_effect_level(self) -> str:
        return "external"

    async def execute(self, **kwargs) -> Dict[str, Any]:
        tenant_id = kwargs.get("tenant_id", "default")
        run_id = kwargs.get("run_id")
        url = kwargs["url"]
        timeout = kwargs.get("timeout", 10)

        session = get_browser_session(tenant_id, run_id)
        return await browser_open_url(session, url, timeout)

    async def dry_run(self, **kwargs) -> Dict[str, Any]:
        return {"status": "dry_run", "message": f"Would open URL: {kwargs['url']}"}

    async def rollback(self, invocation_id: str, **kwargs) -> Dict[str, Any]:
        return {"status": "success", "message": "Browser navigation has no rollback."}

    async def healthcheck(self) -> bool:
        return True


class BrowserClickToolAdapter(ToolAdapterContract):
    @property
    def name(self) -> str:
        return "browser_click"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "The CSS selector or element ID to click."}
            },
            "required": ["selector"]
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "message": {"type": "string"}
            }
        }

    @property
    def side_effect_level(self) -> str:
        return "write"

    async def execute(self, **kwargs) -> Dict[str, Any]:
        settings = get_settings()
        if not getattr(settings, "agent_browser_tool_enabled", False):
            raise ValueError("Browser tool is disabled by feature flag.")

        tenant_id = kwargs.get("tenant_id", "default")
        run_id = kwargs.get("run_id")
        selector = kwargs["selector"]

        session = get_browser_session(tenant_id, run_id)
        return await browser_click_element(session, selector)

    async def dry_run(self, **kwargs) -> Dict[str, Any]:
        return {"status": "dry_run", "message": f"Would click element: {kwargs['selector']}"}

    async def rollback(self, invocation_id: str, **kwargs) -> Dict[str, Any]:
        return {"status": "success", "message": "Browser interaction has no rollback."}

    async def healthcheck(self) -> bool:
        return True


class BrowserExtractTextToolAdapter(ToolAdapterContract):
    @property
    def name(self) -> str:
        return "browser_extract_text"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "is_untrusted": {"type": "boolean"},
                "title": {"type": "string"},
                "url": {"type": "string"}
            }
        }

    @property
    def side_effect_level(self) -> str:
        return "read"

    async def execute(self, **kwargs) -> Dict[str, Any]:
        settings = get_settings()
        if not getattr(settings, "agent_browser_tool_enabled", False):
            raise ValueError("Browser tool is disabled by feature flag.")

        tenant_id = kwargs.get("tenant_id", "default")
        run_id = kwargs.get("run_id")

        session = get_browser_session(tenant_id, run_id)
        return browser_extract_page_text(session)

    async def dry_run(self, **kwargs) -> Dict[str, Any]:
        return {"status": "dry_run", "message": "Would extract text from browser page."}

    async def rollback(self, invocation_id: str, **kwargs) -> Dict[str, Any]:
        return {"status": "success", "message": "Text extraction has no rollback."}

    async def healthcheck(self) -> bool:
        return True


class BrowserScreenshotToolAdapter(ToolAdapterContract):
    @property
    def name(self) -> str:
        return "browser_screenshot"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "screenshot_path": {"type": "string"},
                "is_untrusted": {"type": "boolean"}
            }
        }

    @property
    def side_effect_level(self) -> str:
        return "write"

    async def execute(self, **kwargs) -> Dict[str, Any]:
        tenant_id = kwargs.get("tenant_id", "default")
        run_id = kwargs.get("run_id")

        session = get_browser_session(tenant_id, run_id)
        return await browser_take_screenshot(session)

    async def dry_run(self, **kwargs) -> Dict[str, Any]:
        return {"status": "dry_run", "message": "Would capture page screenshot."}

    async def rollback(self, invocation_id: str, **kwargs) -> Dict[str, Any]:
        return {"status": "success", "message": "Screenshot generation has no rollback."}

    async def healthcheck(self) -> bool:
        return True


class BrowserCloseToolAdapter(ToolAdapterContract):
    @property
    def name(self) -> str:
        return "browser_close"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "message": {"type": "string"}
            }
        }

    @property
    def side_effect_level(self) -> str:
        return "read"

    async def execute(self, **kwargs) -> Dict[str, Any]:
        settings = get_settings()
        if not getattr(settings, "agent_browser_tool_enabled", False):
            raise ValueError("Browser tool is disabled by feature flag.")

        tenant_id = kwargs.get("tenant_id", "default")
        run_id = kwargs.get("run_id")

        close_browser_session(tenant_id, run_id)
        return {"status": "success", "message": "Browser session closed and memory cleared."}

    async def dry_run(self, **kwargs) -> Dict[str, Any]:
        return {"status": "dry_run", "message": "Would close browser session."}

    async def rollback(self, invocation_id: str, **kwargs) -> Dict[str, Any]:
        return {"status": "success", "message": "Browser session close has no rollback."}

    async def healthcheck(self) -> bool:
        return True
