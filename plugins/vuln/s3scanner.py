from __future__ import annotations

from core.contracts import Artifact, Phase, RunContext, ToolPlugin, ToolResult
from core.discord_alert import stream_command_with_alerts
from core.registry import register_tool
from modules.s3scanner import build_bucket_file


@register_tool
class S3ScannerPlugin(ToolPlugin):
    name = "s3scanner"
    phase = Phase.VULN
    requires = ("clean_endpoints",)
    produces = ("s3_results",)

    def run(self, ctx: RunContext) -> ToolResult:
        vuln_dir = ctx.results_dir / "vulnerabilities"
        vuln_dir.mkdir(parents=True, exist_ok=True)
        output = vuln_dir / "s3_results.txt"
        bucket_file = build_bucket_file(ctx.get_path("clean_endpoints"), vuln_dir / "s3_buckets.txt")
        if not bucket_file.exists() or bucket_file.stat().st_size == 0:
            output.touch(exist_ok=True)
            artifact = Artifact(key="s3_results", path=output)
            return ToolResult(tool=self.name, phase=self.phase, success=True, artifacts=[artifact], message="No S3 bucket candidates found")

        cmd = ["s3scanner", "-bucket-file", str(bucket_file), "-o", str(output)]
        tool_args = ctx.config.get("tools", {}).get("tool_args", ctx.config.get("tool_args", {}))
        extra = tool_args.get(self.name, []) if isinstance(tool_args, dict) else []
        if isinstance(extra, list):
            cmd.extend(str(item) for item in extra)

        def _s3_json_parser(record: dict) -> str | None:
            bucket = record.get("bucket")
            if not isinstance(bucket, dict):
                return None

            if bucket.get("exists") != 1:
                return None

            permission_fields = [
                ("perm_all_users_read", "READ"),
                ("perm_all_users_write", "WRITE"),
                ("perm_all_users_read_acl", "READ_ACP"),
                ("perm_all_users_write_acl", "WRITE_ACP"),
                ("perm_all_users_full_control", "FULL_CONTROL"),
                ("perm_auth_users_read", "AUTH_READ"),
                ("perm_auth_users_write", "AUTH_WRITE"),
                ("perm_auth_users_read_acl", "AUTH_READ_ACP"),
                ("perm_auth_users_write_acl", "AUTH_WRITE_ACP"),
                ("perm_auth_users_full_control", "AUTH_FULL_CONTROL"),
            ]
            allowed = [label for field, label in permission_fields if bucket.get(field) == 1]
            if not allowed:
                return None

            name = bucket.get("name") or "unknown-bucket"
            region = bucket.get("region") or "unknown-region"
            return f"S3Scanner finding: {name} ({region}) => {', '.join(allowed)}"

        stream_command_with_alerts(
            cmd,
            output,
            title="S3Scanner Finding",
            color=0xE74C3C,
            jsonl_parser=_s3_json_parser,
        )
        artifact = Artifact(key="s3_results", path=output)
        return ToolResult(tool=self.name, phase=self.phase, success=True, artifacts=[artifact])