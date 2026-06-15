# scripts/llm_harness/plugins/__init__.py
import importlib.metadata
import importlib.util
import logging
import os
import sys
from collections.abc import Callable
from typing import Dict, Type

from pydantic import BaseModel

logger = logging.getLogger("llm_harness.plugins")


class PluginMetadata(BaseModel):
    name: str
    version: str
    description: str = ""
    author: str = ""
    source: str = "unknown"


class Plugin:
    def __init__(self, metadata: PluginMetadata):
        self.metadata = metadata

    def initialize(self, registry: "PluginRegistry"):
        pass


class PluginRegistry:
    def __init__(self):
        self.plugins: dict[str, Plugin] = {}
        self.providers: dict[str, type] = {}
        self.tools: dict[str, Callable] = {}
        self.scorers: dict[str, Callable] = {}
        self.policy_rules: dict[str, Callable] = {}
        self.prompt_templates: dict[str, str] = {}
        self.loaded_sources: dict[str, str] = {}

    def register_provider(self, name: str, provider_cls: type):
        from ..providers import register_provider

        register_provider(name, provider_cls)
        self.providers[name] = provider_cls

    def register_tool(self, name: str, tool_callable: Callable, allow_overwrite: bool = False):
        core_tools = {
            "plan",
            "read_file",
            "grep",
            "ast_search",
            "find_replace",
            "insert_after",
            "apply_patch",
            "run_shell",
            "run_tests",
            "final",
            "parallel",
        }
        if name in core_tools and not allow_overwrite:
            raise ValueError(
                f"Cannot overwrite core tool '{name}' without explicit allow_overwrite flag."
            )
        self.tools[name] = tool_callable

    def register_scorer(self, name: str, scorer_fn: Callable):
        self.scorers[name] = scorer_fn

    def register_policy_rule(self, name: str, rule_fn: Callable):
        self.policy_rules[name] = rule_fn

    def register_prompt_template(self, name: str, template: str):
        self.prompt_templates[name] = template

    def list_tools(self) -> dict[str, Callable]:
        return self.tools

    def list_scorers(self) -> dict[str, Callable]:
        return self.scorers

    def list_policy_rules(self) -> dict[str, Callable]:
        return self.policy_rules

    def load_all_plugins(self, enable_plugins: bool = False, plugins_dir: str = "plugins.d"):
        if not enable_plugins:
            logger.info(
                "Plugins are disabled by default (safe mode). Use --enable-plugins to load them."
            )
            return

        # Clear existing mappings before reloading to avoid duplicate errors in tests
        self.plugins.clear()
        self.providers.clear()
        self.tools.clear()
        self.scorers.clear()
        self.policy_rules.clear()
        self.prompt_templates.clear()
        self.loaded_sources.clear()

        # 1. Discover entry points
        try:
            eps = importlib.metadata.entry_points(group="llm_harness.plugins")
        except TypeError:
            all_eps = importlib.metadata.entry_points()
            if hasattr(all_eps, "select"):
                eps = all_eps.select(group="llm_harness.plugins")
            else:
                eps = all_eps.get("llm_harness.plugins", [])  # type: ignore[attr-defined]

        for ep in eps:
            try:
                plugin_cls = ep.load()
                metadata = PluginMetadata(
                    name=ep.name,
                    version=getattr(plugin_cls, "version", "0.1.0"),
                    description=getattr(plugin_cls, "__doc__", "") or "",
                    source="entry_point",
                )
                plugin_instance = plugin_cls(metadata)
                plugin_instance.initialize(self)
                self.plugins[ep.name] = plugin_instance
                self.loaded_sources[ep.name] = "entry_point"
                logger.info(f"Loaded entrypoint plugin: {ep.name}")
            except Exception as e:
                logger.error(f"Failed to load entrypoint plugin {ep.name}: {e}")
                raise RuntimeError(f"Failed to load plugin {ep.name}: {e}") from e

        # 2. Discover local plugins from plugins.d/
        if os.path.exists(plugins_dir):
            for filename in os.listdir(plugins_dir):
                if filename.endswith(".py") and not filename.startswith("_"):
                    path = os.path.join(plugins_dir, filename)
                    module_name = f"llm_harness.plugins.dynamic.{filename[:-3]}"
                    try:
                        spec = importlib.util.spec_from_file_location(module_name, path)
                        if spec and spec.loader:
                            mod = importlib.util.module_from_spec(spec)
                            sys.modules[module_name] = mod
                            spec.loader.exec_module(mod)

                            found = False
                            for attr_name in dir(mod):
                                obj = getattr(mod, attr_name)
                                if (
                                    isinstance(obj, type)
                                    and issubclass(obj, Plugin)
                                    and obj is not Plugin
                                ):
                                    metadata = PluginMetadata(
                                        name=obj.__name__,
                                        version=getattr(obj, "version", "0.1.0"),
                                        source=path,
                                    )
                                    plugin_instance = obj(metadata)
                                    plugin_instance.initialize(self)
                                    self.plugins[obj.__name__] = plugin_instance
                                    self.loaded_sources[obj.__name__] = path
                                    found = True
                            if not found and hasattr(mod, "initialize"):

                                class DynamicPlugin(Plugin):
                                    def initialize(self, registry):
                                        mod.initialize(registry)

                                metadata = PluginMetadata(
                                    name=filename[:-3], version="0.1.0", source=path
                                )
                                plugin_instance = DynamicPlugin(metadata)
                                plugin_instance.initialize(self)
                                self.plugins[filename[:-3]] = plugin_instance
                                self.loaded_sources[filename[:-3]] = path
                                found = True
                    except Exception as e:
                        logger.error(f"Failed to load local plugin from {path}: {e}")
                        raise RuntimeError(f"Failed to load local plugin from {path}: {e}") from e


plugin_registry = PluginRegistry()
