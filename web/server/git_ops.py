"""Safe, non-interactive git status and fast-forward pull helpers for LED Matrix Studio."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import pwd
except ImportError:  # pragma: no cover - non-POSIX
    pwd = None  # type: ignore[assignment]


GIT_COMMAND_TIMEOUT = 30.0
BUILD_COMMAND_TIMEOUT = 240.0
MAX_DIRTY_FILES = 20
MAX_CHANGED_FILES = 50
MAX_OUTPUT_CHARS = 2000

_URL_CREDENTIALS_RE = re.compile(r"(https?://)([^/\s@]+@)")


class GitOperationError(RuntimeError):
    """Raised when a git operation cannot be completed safely."""

    def __init__(self, message: str, *, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def _sanitize_text(text: str) -> str:
    """Strip any embedded HTTP(S) credentials before returning git output to clients."""
    cleaned = _URL_CREDENTIALS_RE.sub(r"\1***@", text or "")
    cleaned = cleaned.strip()
    if len(cleaned) > MAX_OUTPUT_CHARS:
        return cleaned[:MAX_OUTPUT_CHARS] + "\n... (truncated)"
    return cleaned


class GitRepoUpdater:
    """Thread-safe git status and fast-forward pull controller for a repository root."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self._lock = threading.Lock()

    def _build_subprocess_kwargs(self) -> Tuple[Dict[str, str], Dict[str, Any]]:
        env = dict(os.environ)
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["LC_ALL"] = "C"

        extra: Dict[str, Any] = {}
        # When running as root under systemd on Raspberry Pi while the repo is owned
        # by the Pi user (e.g. `nlewis`), drop privileges for git commands so pulled
        # files and `.git/objects` keep normal ownership and avoid dubious-ownership errors.
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            try:
                st = self.repo_root.stat()
            except OSError:
                st = None
            if st is not None and st.st_uid != 0:
                extra["user"] = st.st_uid
                extra["group"] = st.st_gid
                extra["extra_groups"] = []
                if pwd is not None:
                    try:
                        pw = pwd.getpwuid(st.st_uid)
                        env["HOME"] = pw.pw_dir
                        env["USER"] = pw.pw_name
                    except KeyError:
                        pass
        return env, extra

    def _run_git(
        self, args: List[str], *, timeout: float = GIT_COMMAND_TIMEOUT
    ) -> subprocess.CompletedProcess[str]:
        git_bin = shutil.which("git")
        if not git_bin:
            raise GitOperationError("git is not installed on this device.", status=500)

        env, extra = self._build_subprocess_kwargs()
        cmd = [git_bin, "-c", f"safe.directory={self.repo_root}", *args]
        try:
            return subprocess.run(
                cmd,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                **extra,
            )
        except subprocess.TimeoutExpired as exc:
            raise GitOperationError(
                f"git command timed out after {int(timeout)}s.", status=504
            ) from exc
        except OSError as exc:
            raise GitOperationError(f"Failed to execute git: {exc}", status=500) from exc

    def _is_git_repo(self) -> bool:
        try:
            proc = self._run_git(["rev-parse", "--is-inside-work-tree"], timeout=5.0)
        except GitOperationError:
            return False
        return proc.returncode == 0 and proc.stdout.strip() == "true"

    def _resolve_branch_and_upstream(self) -> Tuple[Optional[str], bool, Optional[str], Optional[str], Optional[str]]:
        """Return (branch, detached, upstream_ref, remote_name, remote_branch)."""
        branch_proc = self._run_git(["symbolic-ref", "--short", "HEAD"], timeout=5.0)
        if branch_proc.returncode == 0 and branch_proc.stdout.strip():
            branch = branch_proc.stdout.strip()
            detached = False
        else:
            branch = None
            detached = True

        upstream_ref: Optional[str] = None
        remote_name: Optional[str] = None
        remote_branch: Optional[str] = None

        if not detached and branch:
            up_proc = self._run_git(
                ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
                timeout=5.0,
            )
            if up_proc.returncode == 0 and up_proc.stdout.strip():
                upstream_ref = up_proc.stdout.strip()
                if "/" in upstream_ref:
                    remote_name, remote_branch = upstream_ref.split("/", 1)
            else:
                # Fallback when branch was created via `git checkout -B <branch> FETCH_HEAD`
                # without setting upstream tracking: use `origin/<branch>` if origin exists.
                origin_proc = self._run_git(["remote", "get-url", "origin"], timeout=5.0)
                if origin_proc.returncode == 0 and origin_proc.stdout.strip():
                    remote_name = "origin"
                    remote_branch = branch
                    check_ref = self._run_git(
                        ["rev-parse", "--verify", f"refs/remotes/origin/{branch}"],
                        timeout=5.0,
                    )
                    if check_ref.returncode == 0:
                        upstream_ref = f"origin/{branch}"

        return branch, detached, upstream_ref, remote_name, remote_branch

    def _get_status_unlocked(self, *, fetch: bool = False) -> Dict[str, Any]:
        if not self._is_git_repo():
            return {
                "isGitRepo": False,
                "branch": None,
                "detached": False,
                "commit": None,
                "commitMessage": None,
                "commitDate": None,
                "remoteUrl": None,
                "upstream": None,
                "dirty": False,
                "dirtyFiles": [],
                "ahead": None,
                "behind": None,
                "fetchError": None,
            }

        branch, detached, upstream_ref, remote_name, remote_branch = (
            self._resolve_branch_and_upstream()
        )

        fetch_error: Optional[str] = None
        if fetch:
            if remote_name and remote_branch:
                refspec = f"+refs/heads/{remote_branch}:refs/remotes/{remote_name}/{remote_branch}"
                fetch_proc = self._run_git(
                    ["fetch", "--quiet", "--", remote_name, refspec]
                )
            else:
                fetch_proc = self._run_git(["fetch", "--quiet"])
            if fetch_proc.returncode != 0:
                fetch_error = _sanitize_text(
                    fetch_proc.stderr or fetch_proc.stdout or "git fetch failed."
                )
            else:
                # Re-resolve upstream in case `refs/remotes/origin/<branch>` just appeared
                branch, detached, upstream_ref, remote_name, remote_branch = (
                    self._resolve_branch_and_upstream()
                )

        commit_proc = self._run_git(["rev-parse", "--short", "HEAD"], timeout=5.0)
        commit = commit_proc.stdout.strip() if commit_proc.returncode == 0 else None

        msg_proc = self._run_git(["log", "-1", "--pretty=%s"], timeout=5.0)
        commit_message = msg_proc.stdout.strip() if msg_proc.returncode == 0 else None

        date_proc = self._run_git(["log", "-1", "--pretty=%cI"], timeout=5.0)
        commit_date = date_proc.stdout.strip() if date_proc.returncode == 0 else None

        remote_to_query = remote_name or "origin"
        remote_proc = self._run_git(["remote", "get-url", remote_to_query], timeout=5.0)
        remote_url = (
            _sanitize_text(remote_proc.stdout)
            if remote_proc.returncode == 0 and remote_proc.stdout.strip()
            else None
        )

        # Only check tracked files so gitignored or local media/config files don't look "dirty"
        status_proc = self._run_git(
            ["status", "--porcelain", "--untracked-files=no"], timeout=5.0
        )
        dirty_files: List[str] = []
        if status_proc.returncode == 0:
            for line in status_proc.stdout.splitlines():
                if len(line) >= 4:
                    dirty_files.append(line[3:].strip())
        dirty = len(dirty_files) > 0

        ahead: Optional[int] = None
        behind: Optional[int] = None
        if upstream_ref:
            lr_proc = self._run_git(
                ["rev-list", "--left-right", "--count", f"HEAD...{upstream_ref}"],
                timeout=5.0,
            )
            if lr_proc.returncode == 0:
                parts = lr_proc.stdout.strip().split()
                if len(parts) == 2:
                    try:
                        ahead = int(parts[0])
                        behind = int(parts[1])
                    except ValueError:
                        pass

        return {
            "isGitRepo": True,
            "branch": branch,
            "detached": detached,
            "commit": commit,
            "commitMessage": commit_message,
            "commitDate": commit_date,
            "remoteUrl": remote_url,
            "upstream": upstream_ref,
            "dirty": dirty,
            "dirtyFiles": dirty_files[:MAX_DIRTY_FILES],
            "ahead": ahead,
            "behind": behind,
            "fetchError": fetch_error,
        }

    def get_status(self, *, fetch: bool = False) -> Dict[str, Any]:
        with self._lock:
            return self._get_status_unlocked(fetch=fetch)

    def _resolve_python_executable(self) -> str:
        for candidate in (
            self.repo_root / ".venv" / "bin" / "python",
            self.repo_root / "venv" / "bin" / "python",
        ):
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
        return sys.executable

    def _run_tool(
        self,
        cmd: List[str],
        *,
        cwd: Path,
        timeout: float = BUILD_COMMAND_TIMEOUT,
        extra_env: Optional[Dict[str, str]] = None,
    ) -> Tuple[bool, str]:
        env, extra = self._build_subprocess_kwargs()
        if extra_env:
            env.update(extra_env)
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                **extra,
            )
        except subprocess.TimeoutExpired:
            return False, f"Timed out after {int(timeout)}s."
        except OSError as exc:
            return False, f"Failed to run {cmd[0]}: {exc}"

        output = _sanitize_text(
            "\n".join(part for part in (proc.stdout.strip(), proc.stderr.strip()) if part)
        )
        if proc.returncode != 0:
            lines = [ln for ln in output.splitlines() if ln.strip()]
            tail = "\n".join(lines[-8:]) if lines else f"Exited with code {proc.returncode}."
            return False, tail
        return True, output

    def _run_conditional_rebuilds(
        self,
        *,
        python_deps_changed: bool,
        node_deps_changed: bool,
        client_files_changed: bool,
    ) -> List[Dict[str, str]]:
        steps: List[Dict[str, str]] = []

        if python_deps_changed:
            req_file = self.repo_root / "requirements.txt"
            if req_file.is_file():
                py_bin = self._resolve_python_executable()
                ok, detail = self._run_tool(
                    [py_bin, "-m", "pip", "install", "-r", str(req_file)],
                    cwd=self.repo_root,
                    extra_env={"PIP_DISABLE_PIP_VERSION_CHECK": "1"},
                )
                steps.append(
                    {
                        "name": "python-deps",
                        "status": "ok" if ok else "failed",
                        "detail": (
                            "Installed updated Python requirements."
                            if ok
                            else detail
                        ),
                    }
                )

        if node_deps_changed or client_files_changed:
            client_dir = self.repo_root / "web" / "client"
            pkg_json = client_dir / "package.json"
            if client_dir.is_dir() and pkg_json.is_file():
                npm_bin = shutil.which("npm")
                has_frontend_install = (client_dir / "node_modules").is_dir() or (
                    client_dir / "dist"
                ).is_dir()
                if not npm_bin:
                    steps.append(
                        {
                            "name": "frontend-build",
                            "status": "skipped",
                            "detail": "npm not installed (skipped on headless Pi).",
                        }
                    )
                elif not has_frontend_install:
                    steps.append(
                        {
                            "name": "frontend-build",
                            "status": "skipped",
                            "detail": "Frontend not installed on this device.",
                        }
                    )
                else:
                    deps_ok = True
                    if node_deps_changed or not (client_dir / "node_modules").is_dir():
                        use_ci = (client_dir / "package-lock.json").is_file()
                        ok, detail = self._run_tool(
                            [npm_bin, "ci" if use_ci else "install"],
                            cwd=client_dir,
                        )
                        deps_ok = ok
                        steps.append(
                            {
                                "name": "node-deps",
                                "status": "ok" if ok else "failed",
                                "detail": (
                                    "Installed updated frontend dependencies."
                                    if ok
                                    else detail
                                ),
                            }
                        )
                    if deps_ok:
                        ok, detail = self._run_tool(
                            [npm_bin, "run", "build"],
                            cwd=client_dir,
                        )
                        steps.append(
                            {
                                "name": "frontend-build",
                                "status": "ok" if ok else "failed",
                                "detail": (
                                    "Rebuilt React frontend bundle."
                                    if ok
                                    else detail
                                ),
                            }
                        )

        return steps

    def pull(self, *, auto_rebuild: bool = True) -> Dict[str, Any]:
        """Fetch, fast-forward (`--ff-only`), and conditionally rebuild changed deps/UI."""
        with self._lock:
            if not self._is_git_repo():
                raise GitOperationError(
                    "This installation is not a git repository.", status=400
                )

            branch, detached, upstream_ref, remote_name, remote_branch = (
                self._resolve_branch_and_upstream()
            )
            if detached or not branch:
                raise GitOperationError(
                    "Repository is in detached HEAD state. Check out a branch before pulling.",
                    status=400,
                )
            if not remote_name or not remote_branch:
                raise GitOperationError(
                    "No git remote ('origin' or upstream) is configured for this branch.",
                    status=400,
                )

            # Reject if tracked files have uncommitted local modifications
            dirty_proc = self._run_git(
                ["status", "--porcelain", "--untracked-files=no"], timeout=5.0
            )
            if dirty_proc.returncode != 0:
                detail = _sanitize_text(
                    dirty_proc.stderr or dirty_proc.stdout or "git status failed."
                )
                raise GitOperationError(f"git status failed: {detail}", status=500)
            dirty_lines = [
                line[3:].strip()
                for line in dirty_proc.stdout.splitlines()
                if len(line) >= 4
            ]
            if dirty_lines:
                preview = ", ".join(dirty_lines[:5])
                suffix = f" (+{len(dirty_lines) - 5} more)" if len(dirty_lines) > 5 else ""
                raise GitOperationError(
                    f"Cannot pull with uncommitted local changes in tracked files: {preview}{suffix}.",
                    status=409,
                )

            before_full = self._run_git(["rev-parse", "HEAD"], timeout=5.0).stdout.strip()
            before_short = self._run_git(
                ["rev-parse", "--short", "HEAD"], timeout=5.0
            ).stdout.strip()

            refspec = f"+refs/heads/{remote_branch}:refs/remotes/{remote_name}/{remote_branch}"
            fetch_proc = self._run_git(["fetch", "--", remote_name, refspec])
            if fetch_proc.returncode != 0:
                detail = _sanitize_text(
                    fetch_proc.stderr or fetch_proc.stdout or "git fetch failed."
                )
                raise GitOperationError(f"git fetch failed: {detail}", status=502)

            merge_target = f"refs/remotes/{remote_name}/{remote_branch}"
            merge_proc = self._run_git(["merge", "--ff-only", merge_target])
            if merge_proc.returncode != 0:
                detail = _sanitize_text(
                    merge_proc.stderr
                    or merge_proc.stdout
                    or "Fast-forward merge failed (branch may have diverged)."
                )
                raise GitOperationError(
                    f"git pull (--ff-only) failed: {detail}", status=409
                )

            after_full = self._run_git(["rev-parse", "HEAD"], timeout=5.0).stdout.strip()
            after_short = self._run_git(
                ["rev-parse", "--short", "HEAD"], timeout=5.0
            ).stdout.strip()

            updated = bool(before_full and after_full and before_full != after_full)
            changed_files: List[str] = []
            if updated:
                diff_proc = self._run_git(
                    ["diff", "--name-only", f"{before_full}..{after_full}"],
                    timeout=5.0,
                )
                if diff_proc.returncode == 0:
                    changed_files = [
                        ln.strip() for ln in diff_proc.stdout.splitlines() if ln.strip()
                    ]

            server_files_changed = any(
                f.startswith("web/server/") for f in changed_files
            )
            client_files_changed = any(
                f.startswith("web/client/") for f in changed_files
            )
            playback_files_changed = any(f.startswith("src/") for f in changed_files)
            python_deps_changed = any(
                f in ("requirements.txt", "pyproject.toml")
                or f.endswith("/requirements.txt")
                for f in changed_files
            )
            node_deps_changed = any(
                f in ("web/client/package.json", "web/client/package-lock.json")
                for f in changed_files
            )

            rebuild_steps: List[Dict[str, str]] = []
            if updated and auto_rebuild:
                rebuild_steps = self._run_conditional_rebuilds(
                    python_deps_changed=python_deps_changed,
                    node_deps_changed=node_deps_changed,
                    client_files_changed=client_files_changed,
                )

            combined_out = _sanitize_text(
                "\n".join(
                    part for part in (merge_proc.stdout.strip(), merge_proc.stderr.strip()) if part
                )
            )
            status = self._get_status_unlocked(fetch=False)

            return {
                "updated": updated,
                "beforeCommit": before_short,
                "afterCommit": after_short,
                "changedFiles": changed_files[:MAX_CHANGED_FILES],
                "totalChangedFiles": len(changed_files),
                "serverFilesChanged": server_files_changed,
                "clientFilesChanged": client_files_changed,
                "playbackFilesChanged": playback_files_changed,
                "pythonDepsChanged": python_deps_changed,
                "nodeDepsChanged": node_deps_changed,
                "rebuildSteps": rebuild_steps,
                "rebuilt": any(s["status"] == "ok" for s in rebuild_steps),
                "rebuildFailed": any(s["status"] == "failed" for s in rebuild_steps),
                "output": combined_out or ("Already up to date." if not updated else "Updated."),
                "status": status,
            }
