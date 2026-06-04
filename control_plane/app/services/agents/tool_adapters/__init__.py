from app.services.agents.browser.browser_tool import (
    BrowserClickToolAdapter,
    BrowserCloseToolAdapter,
    BrowserExtractTextToolAdapter,
    BrowserOpenToolAdapter,
    BrowserScreenshotToolAdapter,
)
from app.services.agents.tool_adapter_registry import adapter_registry
from app.services.agents.tool_adapters.admin_readiness_tool import AdminReadinessToolAdapter
from app.services.agents.tool_adapters.compliance_evidence_tool import ComplianceEvidenceToolAdapter
from app.services.agents.tool_adapters.database_read_tool import DatabaseReadToolAdapter
from app.services.agents.tool_adapters.echo_tool import EchoToolAdapter
from app.services.agents.tool_adapters.filesystem_tools import (
    DeleteFileToolAdapter,
    ListDirectoryToolAdapter,
    ReadFileToolAdapter,
    StatFileToolAdapter,
    WriteFileToolAdapter,
)
from app.services.agents.tool_adapters.http_get_tool import HttpGetToolAdapter
from app.services.agents.tool_adapters.notification_tools import (
    NotifyEmailToolAdapter,
    NotifyPushToolAdapter,
)
from app.services.agents.tool_adapters.rag_search_tool import RagSearchToolAdapter
from app.services.agents.tool_adapters.shell_command_tool import ShellCommandToolAdapter
from app.services.agents.tool_adapters.support_bundle_tool import SupportBundleToolAdapter
from app.services.agents.tools.web_search_tool import WebSearchToolAdapter


def register_all_adapters():
    """Initializes and registers all built-in tool adapters."""
    adapter_registry.register(EchoToolAdapter())
    adapter_registry.register(HttpGetToolAdapter())
    adapter_registry.register(RagSearchToolAdapter())
    adapter_registry.register(AdminReadinessToolAdapter())
    adapter_registry.register(SupportBundleToolAdapter())
    adapter_registry.register(ComplianceEvidenceToolAdapter())
    adapter_registry.register(DatabaseReadToolAdapter())
    adapter_registry.register(ShellCommandToolAdapter())
    adapter_registry.register(WebSearchToolAdapter())
    adapter_registry.register(ReadFileToolAdapter())
    adapter_registry.register(WriteFileToolAdapter())
    adapter_registry.register(ListDirectoryToolAdapter())
    adapter_registry.register(DeleteFileToolAdapter())
    adapter_registry.register(StatFileToolAdapter())
    adapter_registry.register(BrowserOpenToolAdapter())
    adapter_registry.register(BrowserClickToolAdapter())
    adapter_registry.register(BrowserExtractTextToolAdapter())
    adapter_registry.register(BrowserScreenshotToolAdapter())
    adapter_registry.register(BrowserCloseToolAdapter())
    adapter_registry.register(NotifyEmailToolAdapter())
    adapter_registry.register(NotifyPushToolAdapter())
