from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.contracts import Phase, RunContext, ToolResult
from core.registry import iter_plugins, load_builtin_plugins, load_external_plugins


@dataclass
class PhasePlan:
    name: Phase
    tools: list[str]
    parallel: bool = True


class Orchestrator:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.logger = logging.getLogger("recon.orchestrator")
        load_builtin_plugins()

    def _phase_order(self) -> list[PhasePlan]:
        phase_defs = self.config.get("pipeline", {}).get("phases", [])
        plans: list[PhasePlan] = []
        for item in phase_defs:
            if isinstance(item, str):
                plans.append(PhasePlan(name=Phase(item), tools=[]))
                continue
            plans.append(
                PhasePlan(
                    name=Phase(item["name"]),
                    tools=list(item.get("tools", [])),
                    parallel=bool(item.get("parallel", True)),
                )
            )
        return plans

    def run(self, ctx: RunContext) -> list[ToolResult]:
        results: list[ToolResult] = []
        plugin_paths = self.config.get("plugins", {}).get("paths", [])
        load_external_plugins(plugin_paths, base_path=ctx.workspace)
        all_plugins = {plugin.name: plugin for plugin in iter_plugins(None)}

        enabled = self.config.get("tools", {}).get("enabled")
        if enabled is None:
            enabled_names = set(all_plugins.keys())
        else:
            enabled_names = {name for name in enabled if name in all_plugins}

        run_overrides = self.config.get("tools", {}).get("run", {})
        if isinstance(run_overrides, dict):
            for name, value in run_overrides.items():
                if name not in all_plugins:
                    continue
                if bool(value):
                    enabled_names.add(name)
                else:
                    enabled_names.discard(name)

        available = {name: all_plugins[name] for name in enabled_names}
        parallel_overrides = self.config.get("tools", {}).get("parallel_safe", {})
        if isinstance(parallel_overrides, dict):
            for name, value in parallel_overrides.items():
                plugin = available.get(name)
                if plugin is not None:
                    plugin.parallel_safe = bool(value)

        for plan in self._phase_order():
            phase_tools = [available[name] for name in plan.tools if name in available]
            if not phase_tools:
                phase_tools = [plugin for plugin in available.values() if plugin.phase == plan.name]

            remaining = list(phase_tools)
            while remaining:
                ready = [plugin for plugin in remaining if self._requirements_satisfied(plugin, ctx)]
                if not ready:
                    skipped = ", ".join(plugin.name for plugin in remaining)
                    self.logger.warning("No runnable tools left in %s phase: %s", plan.name, skipped)
                    break

                serial_tools = [plugin for plugin in ready if not plugin.parallel_safe or not plan.parallel]
                parallel_tools = [plugin for plugin in ready if plugin.parallel_safe and plan.parallel]

                if serial_tools:
                    self.logger.info("Serial batch (%s): %s", plan.name, ", ".join(plugin.name for plugin in serial_tools))
                for plugin in serial_tools:
                    results.append(self._run_plugin(plugin, ctx))
                    remaining.remove(plugin)

                if parallel_tools:
                    self.logger.info("Parallel batch (%s): %s", plan.name, ", ".join(plugin.name for plugin in parallel_tools))
                    workers = int(self.config.get("execution", {}).get("workers", 4))
                    with ThreadPoolExecutor(max_workers=workers) as executor:
                        for result in executor.map(lambda plugin: self._run_plugin(plugin, ctx), parallel_tools):
                            results.append(result)
                    for plugin in parallel_tools:
                        remaining.remove(plugin)

        return results

    def _requirements_satisfied(self, plugin, ctx: RunContext) -> bool:
        return all(key in ctx.artifacts for key in getattr(plugin, "requires", ()))

    def _run_plugin(self, plugin, ctx: RunContext) -> ToolResult:
        self.logger.info("Running %s", plugin.name)
        missing = [key for key in getattr(plugin, "requires", ()) if key not in ctx.artifacts]
        if missing:
            message = f"Skipping {plugin.name}; missing artifacts: {', '.join(missing)}"
            self.logger.warning(message)
            return ToolResult(tool=plugin.name, phase=plugin.phase, success=False, message=message)

        result = plugin.run(ctx)
        for artifact in result.artifacts:
            ctx.publish(artifact)
        ctx.data.setdefault("results", []).append(result)
        return result


def build_context(target: str, config: dict[str, Any], workspace: Path) -> RunContext:
    return RunContext(target=target, workspace=workspace, config=config)