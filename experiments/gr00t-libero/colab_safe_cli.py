"""Run Colab CLI 0.6 without persisting HTTP credentials or cell history."""
from __future__ import annotations

import contextlib
import importlib.metadata
import io
import json
import logging
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import uuid
from urllib.parse import urlparse


class PrivateScopeError(RuntimeError):
    pass


class RecoveryUnconfirmed(RuntimeError):
    pass


class _ContentsRequestsProxy:
    """Replace only contents.py's module binding, never the requests module.

    The 10s connect/25s read limits fit the parent's 45s polling ceiling for
    an ordinary request. They are per-operation timeouts, not a total deadline;
    the parent still enforces the overall command and experiment deadlines.
    """

    def __init__(self, original, result):
        self.original = original
        self.result = result

    def request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", (10, 25))
        started = time.monotonic()
        safe_method = method.upper() if method.upper() in {"GET", "PUT", "DELETE"} else "OTHER"
        diagnostic = {"host": urlparse(url).hostname, "method": safe_method,
                      "phase": {"GET": "contents_get", "PUT": "contents_put",
                                "DELETE": "contents_delete"}.get(safe_method, "contents_other"),
                      "type": None, "status_code": None, "elapsed_s": None}
        try:
            response = self.original.request(method, url, **kwargs)
        except BaseException as error:
            diagnostic["type"] = type(error).__name__
            status = getattr(getattr(error, "response", None), "status_code", None)
            diagnostic["status_code"] = status if type(status) is int else None
            diagnostic["elapsed_s"] = round(max(0, time.monotonic() - started), 3)
            self.result["request_failure"] = diagnostic
            self.result["contents_request"] = dict(diagnostic)
            raise
        status = getattr(response, "status_code", None)
        diagnostic["status_code"] = status if type(status) is int else None
        diagnostic["elapsed_s"] = round(max(0, time.monotonic() - started), 3)
        self.result["contents_request"] = diagnostic
        if type(status) is int and status >= 400:
            # Preserve native 404/raise_for_status handling. This records the
            # HTTP response fact without inventing an exception type.
            self.result["request_failure"] = dict(diagnostic)
        return response


def _option(arguments, *names):
    values = []
    for index, argument in enumerate(arguments):
        for name in names:
            if argument == name:
                if index + 1 >= len(arguments):
                    raise PrivateScopeError("missing option value")
                values.append(arguments[index + 1])
            elif argument.startswith(name + "="):
                values.append(argument.split("=", 1)[1])
    if len(values) > 1:
        raise PrivateScopeError("duplicate scoped option")
    return values[0] if values else None


def _command(arguments):
    takes_value = {"--config", "--auth", "-c", "--client-oauth-config"}
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument in takes_value:
            index += 2
        elif argument.startswith("-"):
            index += 1
        else:
            return argument
    return None


def _scope(arguments):
    config = _option(arguments, "--config")
    name = _option(arguments, "-s", "--session")
    if not config or not name or not Path(config).is_absolute():
        raise PrivateScopeError("explicit private config and session required")
    path = Path(config)
    parent = path.parent.stat()
    if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.geteuid()
            or stat.S_IMODE(parent.st_mode) & 0o077):
        raise PrivateScopeError("session directory must be private and owned")
    if path.exists() or path.is_symlink():
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) & 0o077):
            raise PrivateScopeError("session state must be private and owned")
    return path, name


def intent_path(config):
    return config.with_name(config.name + ".assignment-intent.json")


def persist_intent(config, name, notebook_hash, variant, accelerator):
    payload = {"schema_version": 1, "session": name,
               "notebook_hash": str(uuid.UUID(str(notebook_hash))),
               "variant": variant.value if variant is not None else "DEFAULT",
               "accelerator": accelerator.value if accelerator is not None else "NONE"}
    # O_EXCL refuses accidental second allocation in the same private scope;
    # the exact hash survives even if assign's POST response never returns.
    fd = os.open(intent_path(config), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(json.dumps(payload) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        # Retain any created file for diagnosis; do not allocate on failure.
        raise
    return payload


def load_intent(config, name):
    path = intent_path(config)
    if not path.exists() and not path.is_symlink():
        return None
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o600 or not 1 <= info.st_size <= 4096):
            raise PrivateScopeError("invalid private assignment intent")
        value = json.loads(os.read(fd, 4097))
    finally:
        os.close(fd)
    if (not isinstance(value, dict) or value.get("schema_version") != 1
            or value.get("session") != name):
        raise PrivateScopeError("assignment intent does not match this scope")
    value["notebook_hash"] = str(uuid.UUID(value["notebook_hash"]))
    return value


def main() -> int:
    logging.disable(sys.maxsize)
    result = {"exit_code": 0, "error_type": None, "unassign_completed": False}
    contents_module = None
    contents_original = None
    # Native commands sometimes echo exception URLs before handling them. Keep
    # those strings in memory and expose only a fixed classification.
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        try:
            if importlib.metadata.version("google-colab-cli") != "0.6.0":
                raise RuntimeError("Review logging and lifecycle hooks before changing CLI version")
            from colab_cli import cli, common
            from colab_cli.client import Client, Assignment, Variant, Accelerator
            from colab_cli.commands import session, run

            class NoHistory:
                def log_event(self, *args, **kwargs):
                    pass

            common.state._history = NoHistory()
            cli.setup_logging = lambda *args, **kwargs: None
            cli.auto_update.run_background_check = lambda: None
            original_unassign = Client.unassign
            original_request = Client._issue_request

            def request(self, endpoint, method="GET", **kwargs):
                kwargs.setdefault("timeout", (20, 60))
                try:
                    return original_request(self, endpoint, method=method, **kwargs)
                except BaseException as error:
                    response = getattr(error, "response", None)
                    path = urlparse(endpoint).path
                    phase = ("assign_" + method.lower() if path.endswith("/assign") else
                             "keepalive" if path.endswith("/keep-alive/") else
                             "list_assignments" if path.endswith("/assignments") else "other")
                    result["request_failure"] = {"host": urlparse(endpoint).hostname,
                                                 "method": method, "type": type(error).__name__,
                                                 "phase": phase,
                                                 "status_code": getattr(response, "status_code", None)}
                    raise

            Client._issue_request = request
            command = _command(sys.argv[1:])
            if command in {"upload", "download", "ls", "rm"}:
                from colab_cli import contents
                contents_module = contents
                contents_original = contents.requests
                contents.requests = _ContentsRequestsProxy(contents_original, result)
            scope = _scope(sys.argv[1:]) if command in {"new", "stop"} else None
            if command == "new":
                from colab_cli.state import SessionState
                original_assign = Client.assign
                config, name = scope

                def assign(self, notebook_hash, variant=None, accelerator=None):
                    if common.state.store.get(name) is not None:
                        raise PrivateScopeError("owned session already exists")
                    persist_intent(config, name, notebook_hash, variant, accelerator)
                    value = original_assign(self, notebook_hash, variant=variant, accelerator=accelerator)
                    proxy = getattr(value, "runtime_proxy_info", None)
                    # Persist identity before the native keep-alive preflight,
                    # so failures there still leave an exact cleanup target.
                    common.state.store.add(SessionState(
                        name=name, endpoint=value.endpoint,
                        token=proxy.token if proxy is not None else getattr(value, "runtime_proxy_token", ""),
                        url=proxy.url if proxy is not None else "",
                        variant=variant.value if variant is not None else "DEFAULT",
                        accelerator=accelerator.value if accelerator is not None else "NONE"))
                    return value

                Client.assign = assign

            def unassign(self, *args, **kwargs):
                value = original_unassign(self, *args, **kwargs)
                result["unassign_completed"] = True
                return value

            Client.unassign = unassign

            def spawn_safe(endpoint, session_name, auth_provider=None, config_path=None):
                command = [sys.executable, str(Path(__file__).resolve())]
                if auth_provider is not None:
                    command.append("--auth=" + auth_provider.value)
                if config_path is not None:
                    command.extend(["--config", str(config_path)])
                command.extend(["keep-alive", endpoint, session_name])
                return subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                        start_new_session=True).pid

            session.spawn_keep_alive = spawn_safe
            run.spawn_keep_alive = spawn_safe
            if command == "stop":
                config, name = scope
                common.state.config_path = str(config)
                auth = _option(sys.argv[1:], "--auth")
                if auth is not None:
                    from colab_cli.auth import AuthProvider
                    common.state.auth_provider = AuthProvider(auth)
                oauth_config = _option(sys.argv[1:], "-c", "--client-oauth-config")
                if oauth_config is not None:
                    common.state.client_oauth_config = oauth_config
                saved = common.state.store.get(name)
                if saved is not None and saved.endpoint:
                    endpoint = saved.endpoint
                else:
                    intent = load_intent(config, name)
                    if intent is None:
                        result["recovery_lookup"] = "unknown"
                        raise RecoveryUnconfirmed("no owned assignment identity")
                    # This GET is the only recovery request. Never call assign,
                    # POST /assign, list_assignments, or choose another session.
                    found = common.state.client._get_assignment(
                        uuid.UUID(intent["notebook_hash"]),
                        Variant(intent["variant"]), Accelerator(intent["accelerator"]))
                    if not isinstance(found, Assignment) or not isinstance(found.endpoint, str) or not found.endpoint:
                        result["recovery_lookup"] = "absent_or_unrecognized"
                        raise RecoveryUnconfirmed("owned assignment not confirmed")
                    endpoint = found.endpoint
                    result["recovery_lookup"] = "owned_assignment_found"
                common.state.client.unassign(endpoint)
                if saved is not None and saved.keep_alive_pid:
                    from colab_cli.common import kill_process
                    kill_process(saved.keep_alive_pid)
                common.state.store.remove(name)
                intent_path(config).unlink(missing_ok=True)
            elif sys.argv[-1] == "check-connection":
                if "--config" in sys.argv:
                    common.state.config_path = sys.argv[sys.argv.index("--config") + 1]
                assignments = common.state.client.list_assignments()
                result.update(connection_verified=True, active_assignments=len(assignments))
            else:
                cli.main()
        except SystemExit as error:
            result["exit_code"] = error.code if isinstance(error.code, int) else 1
        except KeyboardInterrupt:
            result.update(exit_code=130, error_type="KeyboardInterrupt")
        except BaseException as error:
            result.update(exit_code=1, error_type=type(error).__name__)
        finally:
            if contents_module is not None:
                contents_module.requests = contents_original
    if result["exit_code"]:
        message = sink.getvalue().lower()
        categories = (("quota", "quota"), ("not available", "gpu_unavailable"),
                      ("authentication", "authentication"), ("credentials", "authentication"),
                      ("permission", "permission"), ("no active", "missing_session"),
                      ("timed out", "timeout"), ("connect", "connection"))
        result["error_category"] = next((category for needle, category in categories if needle in message), "other")
    sink.close()
    print(json.dumps(result), flush=True)
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
