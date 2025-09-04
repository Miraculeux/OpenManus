import asyncio
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

from app.exceptions import ToolError
from app.tool.base import BaseTool, ToolResult

_BACKGROUND_CAPTURE_DESCRIPTION = """Capture stdout/stderr from background processes while they're still running.
* Real-time capture: Monitor output from long-running background processes
* Non-blocking operation: Capture output without waiting for process completion
* Stream monitoring: Continuously collect stdout and stderr streams
* Process management: Start, monitor, and terminate background processes
* Partial output retrieval: Get accumulated output at any time during execution
* Multiple process tracking: Manage multiple background processes simultaneously
* Platform compatibility: Works on both Windows and Unix/Linux systems

This tool is designed for monitoring long-running processes like:
- Build systems with progress output
- Data processing pipelines
- Server applications with logging
- Network monitoring tools
- Any process that produces continuous output

Note: This tool focuses on output capture and monitoring rather than process execution.
"""


class BackgroundCaptureTool(BaseTool):
    """A tool for capturing output from background processes while they're running."""

    name: str = "background_capture"
    description: str = _BACKGROUND_CAPTURE_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["start", "capture", "stop", "list", "status"],
                "description": "Action to perform: start a new process, capture output, stop a process, list processes, or get status",
            },
            "executable_path": {
                "type": "string",
                "description": "Path to executable (required for 'start' action)",
            },
            "arguments": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Command line arguments for the executable (for 'start' action)",
                "default": [],
            },
            "working_directory": {
                "type": "string",
                "description": "Working directory for process execution (for 'start' action)",
            },
            "environment_vars": {
                "type": "object",
                "description": "Additional environment variables (for 'start' action)",
                "additionalProperties": {"type": "string"},
                "default": {},
            },
            "process_id": {
                "type": "integer",
                "description": "Process ID for capture, stop, or status actions",
            },
            "process_name": {
                "type": "string",
                "description": "Custom name for the process (optional, for 'start' action)",
            },
            "capture_lines": {
                "type": "integer",
                "description": "Number of recent output lines to capture (default: 50, max: 1000)",
                "default": 50,
                "minimum": 1,
                "maximum": 1000,
            },
        },
        "required": ["action"],
    }

    # Track background processes with their output streams
    _background_processes: Dict[int, Dict] = {}
    _process_counter: int = 0

    def _validate_executable(self, executable_path: str) -> Path:
        """Validate that the executable exists and is accessible."""
        if sys.platform == "win32" and not executable_path.lower().endswith(
            (".exe", ".bat", ".cmd", ".com", ".ps1")
        ):
            # Try common Windows executables
            if not Path(executable_path).exists():
                for ext in [".exe", ".bat", ".cmd"]:
                    test_path = Path(f"{executable_path}{ext}")
                    if test_path.exists():
                        executable_path = str(test_path)
                        break

        path = Path(executable_path)
        if not path.is_absolute():
            path = Path.cwd() / path

        if not path.exists():
            raise ToolError(f"Executable file not found: {path}")

        if not path.is_file():
            raise ToolError(f"Path is not a file: {path}")

        return path

    def _start_output_capture_thread(
        self, process: subprocess.Popen, process_info: Dict
    ) -> None:
        """Start a thread to continuously capture output from the process."""

        def capture_output():
            stdout_lines = []
            stderr_lines = []

            try:
                # Read stdout
                if process.stdout:
                    for line in iter(process.stdout.readline, b""):
                        if line:
                            decoded_line = line.decode(
                                "utf-8", errors="replace"
                            ).rstrip()
                            stdout_lines.append(
                                f"[{time.strftime('%H:%M:%S')}] {decoded_line}"
                            )
                            process_info["stdout_lines"] = stdout_lines
                            process_info["last_output_time"] = time.time()

                        # Check if process is still running
                        if process.poll() is not None:
                            break
            except Exception as e:
                process_info["capture_error"] = str(e)

            try:
                # Read stderr
                if process.stderr:
                    for line in iter(process.stderr.readline, b""):
                        if line:
                            decoded_line = line.decode(
                                "utf-8", errors="replace"
                            ).rstrip()
                            stderr_lines.append(
                                f"[{time.strftime('%H:%M:%S')}] {decoded_line}"
                            )
                            process_info["stderr_lines"] = stderr_lines
                            process_info["last_output_time"] = time.time()

                        # Check if process is still running
                        if process.poll() is not None:
                            break
            except Exception as e:
                process_info["capture_error"] = str(e)

            # Mark capture as completed
            process_info["capture_completed"] = True
            if process.poll() is not None:
                process_info["exit_code"] = process.returncode
                process_info["completed_at"] = time.time()

        # Start capture thread
        capture_thread = threading.Thread(target=capture_output, daemon=True)
        capture_thread.start()
        process_info["capture_thread"] = capture_thread

    async def _start_process(
        self,
        executable_path: str,
        arguments: List[str],
        working_directory: Optional[str],
        environment_vars: Dict[str, str],
        process_name: Optional[str],
    ) -> ToolResult:
        """Start a new background process with output capture."""
        try:
            # Validate executable
            exe_path = self._validate_executable(executable_path)

            # Prepare working directory
            if working_directory:
                work_dir = Path(working_directory)
                if not work_dir.exists() or not work_dir.is_dir():
                    return ToolResult(
                        error=f"Invalid working directory: {working_directory}"
                    )
                cwd = str(work_dir)
            else:
                cwd = str(exe_path.parent)

            # Prepare environment
            env = os.environ.copy()
            env.update(environment_vars)

            # Prepare command
            command = [str(exe_path)] + arguments

            # Start process
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,  # Use binary mode for better control
                bufsize=0,  # Unbuffered
                creationflags=(
                    subprocess.CREATE_NEW_PROCESS_GROUP
                    if sys.platform == "win32"
                    else 0
                ),
            )

            # Create process info
            self._process_counter += 1
            process_info = {
                "process": process,
                "pid": process.pid,
                "name": process_name or f"process_{self._process_counter}",
                "command": command,
                "cwd": cwd,
                "started_at": time.time(),
                "stdout_lines": [],
                "stderr_lines": [],
                "last_output_time": time.time(),
                "capture_completed": False,
                "capture_error": None,
                "exit_code": None,
                "completed_at": None,
            }

            # Store process
            self._background_processes[process.pid] = process_info

            # Start output capture
            self._start_output_capture_thread(process, process_info)

            return ToolResult(
                output=f"Started background process: {process_info['name']}\n"
                f"Process ID: {process.pid}\n"
                f"Command: {' '.join(command)}\n"
                f"Working directory: {cwd}\n"
                f"Output capture: Active\n"
                f"Use action='capture' with process_id={process.pid} to get output"
            )

        except ToolError as e:
            return ToolResult(error=str(e))
        except Exception as e:
            return ToolResult(error=f"Failed to start process: {str(e)}")

    async def _capture_output(self, process_id: int, capture_lines: int) -> ToolResult:
        """Capture output from a running background process."""
        if process_id not in self._background_processes:
            return ToolResult(
                error=f"No background process found with ID: {process_id}"
            )

        process_info = self._background_processes[process_id]
        process = process_info["process"]

        # Get current status
        is_running = process.poll() is None
        exit_code = process.returncode if not is_running else None

        # Get recent output lines
        stdout_lines = process_info.get("stdout_lines", [])
        stderr_lines = process_info.get("stderr_lines", [])

        # Limit the number of lines returned
        recent_stdout = stdout_lines[-capture_lines:] if stdout_lines else []
        recent_stderr = stderr_lines[-capture_lines:] if stderr_lines else []

        # Format output
        status = "Running" if is_running else f"Completed (exit code: {exit_code})"
        runtime = time.time() - process_info["started_at"]
        last_output = process_info.get("last_output_time", process_info["started_at"])
        time_since_output = time.time() - last_output

        output_text = f"Process: {process_info['name']} (PID: {process_id})\n"
        output_text += f"Status: {status}\n"
        output_text += f"Runtime: {runtime:.1f} seconds\n"
        output_text += f"Time since last output: {time_since_output:.1f} seconds\n"
        output_text += f"Total stdout lines: {len(stdout_lines)}\n"
        output_text += f"Total stderr lines: {len(stderr_lines)}\n\n"

        if recent_stdout:
            output_text += f"Recent STDOUT (last {len(recent_stdout)} lines):\n"
            output_text += "\n".join(recent_stdout) + "\n\n"

        if recent_stderr:
            output_text += f"Recent STDERR (last {len(recent_stderr)} lines):\n"
            output_text += "\n".join(recent_stderr) + "\n\n"

        if not recent_stdout and not recent_stderr:
            output_text += "No output captured yet.\n"

        # Check for capture errors
        if process_info.get("capture_error"):
            output_text += f"Capture error: {process_info['capture_error']}\n"

        return ToolResult(output=output_text)

    async def _stop_process(self, process_id: int) -> ToolResult:
        """Stop a background process."""
        if process_id not in self._background_processes:
            return ToolResult(
                error=f"No background process found with ID: {process_id}"
            )

        process_info = self._background_processes[process_id]
        process = process_info["process"]

        if process.poll() is not None:
            return ToolResult(
                output=f"Process {process_id} ({process_info['name']}) has already completed with exit code: {process.returncode}"
            )

        # Terminate the process
        try:
            process.terminate()

            # Wait a bit for graceful termination
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate gracefully
                process.kill()
                process.wait()

            # Update process info
            process_info["exit_code"] = process.returncode
            process_info["completed_at"] = time.time()

            return ToolResult(
                output=f"Process {process_id} ({process_info['name']}) has been terminated\n"
                f"Exit code: {process.returncode}"
            )

        except Exception as e:
            return ToolResult(error=f"Failed to stop process {process_id}: {str(e)}")

    async def _list_processes(self) -> ToolResult:
        """List all tracked background processes."""
        if not self._background_processes:
            return ToolResult(output="No background processes currently tracked.")

        output_lines = ["Background Processes:\n"]

        for pid, info in self._background_processes.items():
            process = info["process"]
            is_running = process.poll() is None
            status = (
                "Running"
                if is_running
                else f"Completed (exit code: {process.returncode})"
            )
            runtime = time.time() - info["started_at"]

            output_lines.append(
                f"PID {pid}: {info['name']}\n"
                f"  Status: {status}\n"
                f"  Runtime: {runtime:.1f}s\n"
                f"  Command: {' '.join(info['command'][:3])}{'...' if len(info['command']) > 3 else ''}\n"
                f"  Output lines: {len(info.get('stdout_lines', []))} stdout, {len(info.get('stderr_lines', []))} stderr\n"
            )

        return ToolResult(output="\n".join(output_lines))

    async def _get_status(self, process_id: int) -> ToolResult:
        """Get detailed status of a specific process."""
        if process_id not in self._background_processes:
            return ToolResult(
                error=f"No background process found with ID: {process_id}"
            )

        process_info = self._background_processes[process_id]
        process = process_info["process"]
        is_running = process.poll() is None

        status_text = f"Process Details for PID {process_id}:\n"
        status_text += f"Name: {process_info['name']}\n"
        status_text += f"Status: {'Running' if is_running else f'Completed (exit code: {process.returncode})'}\n"
        status_text += f"Command: {' '.join(process_info['command'])}\n"
        status_text += f"Working Directory: {process_info['cwd']}\n"
        status_text += f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(process_info['started_at']))}\n"

        runtime = time.time() - process_info["started_at"]
        status_text += f"Runtime: {runtime:.1f} seconds\n"

        if process_info.get("completed_at"):
            status_text += f"Completed at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(process_info['completed_at']))}\n"

        status_text += f"Total output lines: {len(process_info.get('stdout_lines', []))} stdout, {len(process_info.get('stderr_lines', []))} stderr\n"

        last_output_time = process_info.get(
            "last_output_time", process_info["started_at"]
        )
        time_since_output = time.time() - last_output_time
        status_text += f"Time since last output: {time_since_output:.1f} seconds\n"

        if process_info.get("capture_error"):
            status_text += f"Capture error: {process_info['capture_error']}\n"

        return ToolResult(output=status_text)

    async def execute(
        self,
        action: str,
        executable_path: Optional[str] = None,
        arguments: Optional[List[str]] = None,
        working_directory: Optional[str] = None,
        environment_vars: Optional[Dict[str, str]] = None,
        process_id: Optional[int] = None,
        process_name: Optional[str] = None,
        capture_lines: int = 50,
        **kwargs,
    ) -> ToolResult:
        """
        Execute background capture operations.

        Args:
            action: Action to perform (start, capture, stop, list, status)
            executable_path: Path to executable (for start action)
            arguments: Command line arguments (for start action)
            working_directory: Working directory (for start action)
            environment_vars: Environment variables (for start action)
            process_id: Process ID (for capture, stop, status actions)
            process_name: Custom process name (for start action)
            capture_lines: Number of recent lines to capture

        Returns:
            ToolResult with operation output or error information
        """
        try:
            if action == "start":
                if not executable_path:
                    return ToolResult(
                        error="executable_path is required for 'start' action"
                    )
                return await self._start_process(
                    executable_path,
                    arguments or [],
                    working_directory,
                    environment_vars or {},
                    process_name,
                )

            elif action == "capture":
                if process_id is None:
                    return ToolResult(
                        error="process_id is required for 'capture' action"
                    )
                return await self._capture_output(process_id, capture_lines)

            elif action == "stop":
                if process_id is None:
                    return ToolResult(error="process_id is required for 'stop' action")
                return await self._stop_process(process_id)

            elif action == "list":
                return await self._list_processes()

            elif action == "status":
                if process_id is None:
                    return ToolResult(
                        error="process_id is required for 'status' action"
                    )
                return await self._get_status(process_id)

            else:
                return ToolResult(error=f"Unknown action: {action}")

        except Exception as e:
            return ToolResult(error=f"Unexpected error: {str(e)}")

    def cleanup_completed_processes(self) -> int:
        """Remove completed processes from tracking. Returns number of processes cleaned up."""
        completed_pids = []

        for pid, info in self._background_processes.items():
            process = info["process"]
            if process.poll() is not None and info.get("capture_completed", False):
                # Process completed and capture is done
                completed_pids.append(pid)

        for pid in completed_pids:
            del self._background_processes[pid]

        return len(completed_pids)
