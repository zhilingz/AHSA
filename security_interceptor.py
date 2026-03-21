"""
Purpose: Enforce policy checks for file access, command execution, and other capabilities.
Input: Policy data plus runtime operations to validate.
Output: Allow results, audit records, or structured security exceptions.
"""

import json
import os
from datetime import datetime, timezone
from fnmatch import fnmatch


class SecurityInterceptionError(PermissionError):
    """
    Purpose: Carry structured block details back to the caller.
    Input: A blocked capability, a reason, and an optional target.
    Output: A reusable security exception instance.
    """

    def __init__(self, capability, reason, target=None):
        """
        Purpose: Store one blocked operation in a reusable exception object.
        Input: A blocked capability, a reason, and an optional target.
        Output: Initialized exception state.
        """
        self.capability = capability
        self.reason = reason
        self.target = target
        super().__init__(reason)

    def to_dict(self):
        """
        Purpose: Convert the exception into a serializable response payload.
        Input: None.
        Output: A serializable error payload for upstream callers.
        """
        return {
            "error": "Security Interception",
            "capability": self.capability,
            "reason": self.reason,
            "target": self.target,
        }


class AuditLogger:
    """
    Purpose: Persist pass or block events as append-only JSON lines.
    Input: An optional audit log path and event dictionaries.
    Output: JSONL audit records on disk when logging is enabled.
    """

    def __init__(self, path=None):
        """
        Purpose: Configure optional persistent audit logging.
        Input: An optional audit log path.
        Output: A logger configured for later writes.
        """
        self.path = path

    def log(self, event):
        """
        Purpose: Append one audit event to the log file when logging is enabled.
        Input: An audit event dictionary.
        Output: One JSON line written when logging is enabled.
        """
        if not self.path:
            return
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")


class FileSystemInterceptor:
    """
    Purpose: Validate one file operation against path rules inside the project root.
    Input: File-system policy data and file operations to check.
    Output: Allow results or file-system security exceptions.
    """

    def __init__(self, policy, project_root):
        """
        Purpose: Prepare file path enforcement against one policy scope.
        Input: File-system policy data and a project root path.
        Output: An initialized file checker.
        """
        self.policy = policy or {}
        self.project_root = os.path.realpath(project_root)

    def check(self, method, path):
        """
        Purpose: Allow or block one file operation against path rules.
        Input: A file method and a target path.
        Output: A normalized allow result or a security exception.
        """
        real_path, rel_path = self._normalize(path)
        for rule in self.policy.get("rules", []):
            methods = rule.get("method", [])
            if isinstance(methods, str):
                methods = [methods]
            if method not in methods:
                continue
            patterns = rule.get("path_glob", [])
            if isinstance(patterns, str):
                patterns = [patterns]
            if any(self._match(pattern, real_path, rel_path) for pattern in patterns):
                return {"method": method, "path": real_path}
        if self.policy.get("default_action", "deny") == "allow":
            return {"method": method, "path": real_path}
        raise SecurityInterceptionError("file_system", "Path not in allowed scope", real_path)

    def _normalize(self, path):
        """
        Purpose: Resolve a raw path into a real path and a project-relative path.
        Input: A raw path.
        Output: A real absolute path plus a project-relative path.
        """
        raw = path if os.path.isabs(path) else os.path.join(self.project_root, path)
        real_path = os.path.realpath(raw)
        if os.path.commonpath([self.project_root, real_path]) != self.project_root:
            raise SecurityInterceptionError("file_system", "Path escapes project root", real_path)
        rel = os.path.relpath(real_path, self.project_root).replace(os.sep, "/")
        rel_path = "./" if rel == "." else f"./{rel}"
        return real_path, rel_path

    def _match(self, pattern, real_path, rel_path):
        """
        Purpose: Test one normalized path against one policy glob.
        Input: One policy glob and one normalized path pair.
        Output: A boolean match result.
        """
        if pattern in {"./**", "./**/*", "**", "**/*"}:
            return True
        if pattern.startswith("./"):
            return fnmatch(rel_path, pattern)
        return fnmatch(real_path, os.path.realpath(pattern))


class ComputeInterceptor:
    """
    Purpose: Validate one command against execution allow and deny rules.
    Input: Execution policy data and commands to check.
    Output: Allow results or command security exceptions.
    """

    def __init__(self, policy):
        """
        Purpose: Prepare command enforcement against one execution policy.
        Input: Execution policy data.
        Output: An initialized command checker.
        """
        self.policy = policy or {}

    def check(self, command):
        """
        Purpose: Allow or block one command using enable flags and restricted patterns.
        Input: A command string or argv list.
        Output: A normalized allow result or a security exception.
        """
        if not self.policy.get("allowed", False):
            raise SecurityInterceptionError("exec", "Command execution disabled", self._command_text(command))
        text = self._command_text(command).lower()
        for item in self.policy.get("restricted_cmds", []):
            if item.lower() in text:
                raise SecurityInterceptionError("exec", "Command blocked by restricted list", text)
        return {"command": text}

    def _command_text(self, command):
        """
        Purpose: Normalize command input into one comparable string.
        Input: A string or iterable command.
        Output: A flat string form.
        """
        if isinstance(command, str):
            return command
        return " ".join(str(item) for item in command)


class PolicyEngine:
    """
    Purpose: Route one runtime operation to the correct policy checker and audit the result.
    Input: Policy data, runtime context, and operations to validate.
    Output: Allow results, audit records, or structured security exceptions.
    """

    def __init__(self, policy, project_root=".", audit_log_path=None):
        """
        Purpose: Assemble all checkers needed to enforce one policy.
        Input: Policy data and runtime paths.
        Output: An initialized policy engine.
        """
        self.policy = policy
        self.project_root = os.path.realpath(project_root)
        permissions = policy.get("permissions", {})
        self.file_system = FileSystemInterceptor(permissions.get("file_system", {}), self.project_root)
        self.compute = ComputeInterceptor(permissions.get("exec", {}))
        self.audit = AuditLogger(audit_log_path)

    @classmethod
    def from_file(cls, path, project_root=".", audit_log_path=None):
        """
        Purpose: Load a policy from disk and build a ready-to-use engine.
        Input: A policy file path and optional runtime paths.
        Output: An initialized policy engine instance.
        """
        with open(path, "r", encoding="utf-8") as f:
            return cls(json.load(f), project_root=project_root, audit_log_path=audit_log_path)

    def check_file(self, method, path):
        """
        Purpose: Run one audited file-system policy check.
        Input: A file method and a path.
        Output: An allow result dictionary or a security exception.
        """
        return self._record("file_system", path, lambda: self.file_system.check(method, path))

    def check_exec(self, command):
        """
        Purpose: Run one audited command policy check.
        Input: A command string or argv list.
        Output: An allow result dictionary or a security exception.
        """
        return self._record("exec", self._command_text(command), lambda: self.compute.check(command))

    def check_capability(self, capability, target=None):
        """
        Purpose: Run one audited non-file, non-exec capability check.
        Input: A named capability and an optional target.
        Output: An allow result dictionary or a security exception.
        """

        def run():
            """
            Purpose: Validate one capability against enabled flags and target scope.
            Input: Closed-over capability context.
            Output: An allow result dictionary or a security exception.
            """
            policy = self.policy.get("permissions", {}).get(capability)
            if not policy or not policy.get("allowed", False):
                raise SecurityInterceptionError(capability, "Capability disabled", target)
            self._check_target(capability, policy, target)
            return {"capability": capability, "target": target}

        return self._record(capability, target, run)

    def intercept(self, capability, target=None, method=None):
        """
        Purpose: Dispatch a generic operation to the correct checker.
        Input: A generic capability call.
        Output: The result from the matching checker.
        """
        if capability == "file_system":
            return self.check_file(method, target)
        if capability == "exec":
            return self.check_exec(target)
        return self.check_capability(capability, target)

    def _check_target(self, capability, policy, target):
        """
        Purpose: Enforce optional target scope rules for one capability.
        Input: Capability policy data and a target.
        Output: Successful validation or a security exception.
        """
        if target is None:
            return
        keys = ["allowed_targets", "allowed_hosts", "allowed_scope"]
        for key in keys:
            items = policy.get(key)
            if not items:
                continue
            if isinstance(items, str):
                items = [items]
            if not any(item == "*" or fnmatch(str(target), item) for item in items):
                raise SecurityInterceptionError(capability, "Target not in allowed scope", target)

    def _command_text(self, command):
        """
        Purpose: Normalize command input into one comparable string.
        Input: A string or iterable command.
        Output: A flat string form.
        """
        if isinstance(command, str):
            return command
        return " ".join(str(item) for item in command)

    def _record(self, capability, target, action):
        """
        Purpose: Wrap one policy check with pass or block audit logging.
        Input: Capability metadata and an action callback.
        Output: Logged audit state and the action output or exception.
        """
        event = {
            "time": datetime.now(timezone.utc).isoformat(),
            "cluster_type": self.policy.get("cluster_type"),
            "capability": capability,
            "target": target,
        }
        try:
            result = action()
            event["decision"] = "pass"
            self.audit.log(event)
            return result
        except SecurityInterceptionError as e:
            event["decision"] = "block"
            event["reason"] = e.reason
            self.audit.log(event)
            raise
