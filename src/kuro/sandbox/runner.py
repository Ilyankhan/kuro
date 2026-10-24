import os
import subprocess
import time
from pathlib import Path
from typing import List, Optional
from kuro.models.schemas import ProbeExecutionResult


class DockerSandboxRunner:
    """Manages secure, isolated execution of untrusted binaries and synthesized code inside Docker."""

    def __init__(self, image: str = "kuro-sandbox", timeout_seconds: int = 5):
        self.image = image
        self.timeout_seconds = timeout_seconds

    def run_binary(
        self,
        host_binary_path: str,
        args: Optional[List[str]] = None,
        stdin_input: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> ProbeExecutionResult:
        """Executes a host binary inside an isolated Docker container."""
        bin_path = Path(host_binary_path).resolve()
        if not bin_path.exists():
            raise FileNotFoundError(f"Binary not found: {host_binary_path}")

        try:
            os.chmod(bin_path, 0o755)
        except Exception:
            pass

        args = args or []
        timeout = timeout or self.timeout_seconds
        parent_dir = str(bin_path.parent)
        bin_name = bin_path.name

        cmd = [
            "docker",
            "run",
            "--rm",
            "--network", "none",
            "--memory", "512m",
            "--cpus", "1.0",
            "-v", f"{parent_dir}:/workspace:ro",
            "-w", "/workspace",
            self.image,
            f"./{bin_name}",
            *args,
        ]

        start_time = time.time()
        try:
            proc = subprocess.run(
                cmd,
                input=stdin_input,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            duration = (time.time() - start_time) * 1000
            return ProbeExecutionResult(
                command_args=args,
                stdin_input=stdin_input,
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                timed_out=False,
                duration_ms=round(duration, 2),
            )
        except subprocess.TimeoutExpired:
            duration = (time.time() - start_time) * 1000
            return ProbeExecutionResult(
                command_args=args,
                stdin_input=stdin_input,
                exit_code=124,
                stdout="",
                stderr="Execution timed out",
                timed_out=True,
                duration_ms=round(duration, 2),
            )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return ProbeExecutionResult(
                command_args=args,
                stdin_input=stdin_input,
                exit_code=255,
                stdout="",
                stderr=str(e),
                timed_out=False,
                duration_ms=round(duration, 2),
            )

    def run_python_code(
        self,
        workspace_dir: str,
        entry_file: str,
        args: Optional[List[str]] = None,
        stdin_input: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> ProbeExecutionResult:
        """Executes synthesized Python code inside an isolated Docker container."""
        args = args or []
        timeout = timeout or self.timeout_seconds
        dir_path = str(Path(workspace_dir).resolve())

        cmd = [
            "docker",
            "run",
            "--rm",
            "--network", "none",
            "--memory", "512m",
            "--cpus", "1.0",
            "-v", f"{dir_path}:/workspace:ro",
            "-w", "/workspace",
            self.image,
            "python3",
            "-B",
            entry_file,
            *args,
        ]

        start_time = time.time()
        try:
            proc = subprocess.run(
                cmd,
                input=stdin_input,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            duration = (time.time() - start_time) * 1000
            return ProbeExecutionResult(
                command_args=args,
                stdin_input=stdin_input,
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                timed_out=False,
                duration_ms=round(duration, 2),
            )
        except subprocess.TimeoutExpired:
            duration = (time.time() - start_time) * 1000
            return ProbeExecutionResult(
                command_args=args,
                stdin_input=stdin_input,
                exit_code=124,
                stdout="",
                stderr="Execution timed out",
                timed_out=True,
                duration_ms=round(duration, 2),
            )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return ProbeExecutionResult(
                command_args=args,
                stdin_input=stdin_input,
                exit_code=255,
                stdout="",
                stderr=str(e),
                timed_out=False,
                duration_ms=round(duration, 2),
            )
