import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

from app.exceptions import ToolError
from app.tool.base import BaseTool, CLIResult, ToolResult

_WINDOWS_EXE_DESCRIPTION = """Execute Windows executable files (.exe) and other executable formats on Windows.
* File execution: Run executable files with optional command line arguments
* Working directory: Can specify a custom working directory for the execution
* Environment variables: Can pass custom environment variables to the process
* Timeout control: Commands have a configurable timeout to prevent hanging
* Output capture: Captures both stdout and stderr from the executed process
* Background execution: Option to run processes in the background without blocking
* Process management: Can terminate running processes if needed

Note: This tool only works on Windows systems and requires the executable file to exist and be accessible.
The tool will validate file existence and permissions before attempting execution.
"""


class WindowsExeTool(BaseTool):
    """A tool for executing Windows executable files with various options."""

    name: str = "windows_exe"
    description: str = _WINDOWS_EXE_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "executable_path": {
                "type": "string",
                "description": "The full path to the Windows executable file (.exe, .bat, .cmd, .com, .msi, etc.)",
            },
            "arguments": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Command line arguments to pass to the executable",
                "default": [],
            },
            "working_directory": {
                "type": "string",
                "description": "Working directory for the process execution. If not specified, uses the directory containing the executable",
            },
            "environment_vars": {
                "type": "object",
                "description": "Additional environment variables to set for the process",
                "additionalProperties": {"type": "string"},
                "default": {},
            },
            "timeout": {
                "type": "integer",
                "description": "Maximum execution time in seconds (default: 30, max: 300)",
                "default": 30,
                "minimum": 1,
                "maximum": 300,
            },
            "background": {
                "type": "boolean",
                "description": "Run the process in background without waiting for completion",
                "default": False,
            },
            "capture_output": {
                "type": "boolean",
                "description": "Whether to capture stdout and stderr (ignored if background=True)",
                "default": True,
            },
        },
        "required": ["executable_path"],
    }

    # Track running background processes
    _background_processes: Dict[int, subprocess.Popen] = {}

    def _validate_executable(self, executable_path: str) -> Path:
        """Validate that the executable exists and is accessible."""
        if sys.platform != "win32":
            raise ToolError("This tool only works on Windows systems")

        path = Path(executable_path)

        # Handle relative paths by making them absolute
        if not path.is_absolute():
            path = Path.cwd() / path

        if not path.exists():
            raise ToolError(f"Executable file not found: {path}")

        if not path.is_file():
            raise ToolError(f"Path is not a file: {path}")

        # Check if file has an executable extension
        executable_extensions = {
            ".exe",
            ".bat",
            ".cmd",
            ".com",
            ".msi",
            ".ps1",
            ".vbs",
            ".jar",
        }
        if path.suffix.lower() not in executable_extensions:
            # Still allow execution, but warn
            pass

        return path

    def _prepare_environment(self, custom_env: Dict[str, str]) -> Dict[str, str]:
        """Prepare environment variables for the process."""
        env = os.environ.copy()
        env.update(custom_env)
        return env

    def _prepare_working_directory(
        self, working_directory: Optional[str], exe_path: Path
    ) -> tuple[str, Optional[ToolResult]]:
        """
        Prepare and validate the working directory.

        Returns:
            tuple[str, Optional[ToolResult]]: (working_directory_path, error_result)
            If error_result is not None, the execution should stop with that error.
        """
        if working_directory:
            work_dir = Path(working_directory)
            if not work_dir.exists():
                return "", ToolResult(error=f"Working directory not found: {work_dir}")
            if not work_dir.is_dir():
                return "", ToolResult(
                    error=f"Working directory path is not a directory: {work_dir}"
                )
            return str(work_dir), None
        else:
            return str(exe_path.parent), None

    async def _execute_background_process(
        self,
        command: list[str],
        cwd: str,
        env: Dict[str, str],
        exe_path: Path,
        capture_output: bool = False,
    ) -> ToolResult:
        """Execute a process in the background without waiting for completion."""
        try:
            # Configure output capture for background processes
            stdout_config = subprocess.PIPE if capture_output else None
            stderr_config = subprocess.PIPE if capture_output else None

            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=env,
                stdout=stdout_config,
                stderr=stderr_config,
                creationflags=(
                    subprocess.CREATE_NEW_PROCESS_GROUP
                    if sys.platform == "win32"
                    else 0
                ),
            )

            # Store process for potential future management
            self._background_processes[process.pid] = process

            output_msg = (
                f"Started background process: {exe_path.name}\n"
                f"Process ID: {process.pid}\n"
                f"Command: {' '.join(command)}\n"
                f"Working directory: {cwd}\n"
                f"Output capture: {'Enabled' if capture_output else 'Disabled'}"
            )

            if capture_output:
                output_msg += f"\nNote: Use get_background_process_output({process.pid}) to retrieve output when process completes"

            return ToolResult(output=output_msg)

        except Exception as e:
            return ToolResult(error=f"Failed to start background process: {str(e)}")

    async def _handle_process_timeout(
        self,
        process: asyncio.subprocess.Process,
        timeout: int,
        command: list[str],
        cwd: str,
    ) -> ToolResult:
        """Handle process timeout by terminating the process."""
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=5)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()

        return ToolResult(
            error=f"Process timed out after {timeout} seconds and was terminated\n"
            f"Command: {' '.join(command)}\n"
            f"Working directory: {cwd}"
        )

    def _format_process_result(
        self,
        returncode: int,
        command: list[str],
        cwd: str,
        stdout_text: str,
        stderr_text: str,
    ) -> ToolResult:
        """Format the process execution result."""
        base_info = f"Command: {' '.join(command)}\nWorking directory: {cwd}\n\n"

        if returncode == 0:
            output_info = f"STDOUT:\n{stdout_text}"
            if stderr_text:
                output_info += f"\nSTDERR:\n{stderr_text}"

            return ToolResult(
                output=f"Process completed successfully (exit code: {returncode})\n"
                f"{base_info}{output_info}"
            )
        else:
            return ToolResult(
                error=f"Process failed with exit code: {returncode}\n"
                f"{base_info}STDOUT:\n{stdout_text}\nSTDERR:\n{stderr_text}"
            )

    async def _execute_with_output_capture(
        self, command: list[str], cwd: str, env: Dict[str, str], timeout: int
    ) -> ToolResult:
        """Execute process with output capture and wait for completion."""
        result = await asyncio.create_subprocess_exec(
            *command,
            cwd=cwd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                result.communicate(), timeout=timeout
            )

            stdout_text = stdout.decode("utf-8", errors="replace") if stdout else ""
            stderr_text = stderr.decode("utf-8", errors="replace") if stderr else ""

            return self._format_process_result(
                result.returncode, command, cwd, stdout_text, stderr_text
            )

        except asyncio.TimeoutError:
            return await self._handle_process_timeout(result, timeout, command, cwd)

    async def _execute_without_output_capture(
        self, command: list[str], cwd: str, env: Dict[str, str], timeout: int
    ) -> ToolResult:
        """Execute process without output capture and wait for completion."""
        result = await asyncio.create_subprocess_exec(*command, cwd=cwd, env=env)

        try:
            await asyncio.wait_for(result.wait(), timeout=timeout)

            return ToolResult(
                output=f"Process completed (exit code: {result.returncode})\n"
                f"Command: {' '.join(command)}\n"
                f"Working directory: {cwd}\n"
                f"Note: Output capture was disabled"
            )

        except asyncio.TimeoutError:
            return await self._handle_process_timeout(result, timeout, command, cwd)

    async def _execute_foreground_process(
        self,
        command: list[str],
        cwd: str,
        env: Dict[str, str],
        timeout: int,
        capture_output: bool,
    ) -> ToolResult:
        """Execute a process in the foreground, collect output after 30 seconds even if not finished."""
        try:
            if not capture_output:
                # If no output capture needed, use the original method
                return await self._execute_without_output_capture(
                    command, cwd, env, timeout
                )

            # Start process in background with output capture
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=(
                    subprocess.CREATE_NEW_PROCESS_GROUP
                    if sys.platform == "win32"
                    else 0
                ),
            )

            # Wait for 30 seconds or until process completes
            await asyncio.sleep(30)

            # Check if process is still running
            if process.poll() is None:
                # Process is still running - collect partial output
                try:
                    # Try to read available output without blocking
                    stdout_data = b""
                    stderr_data = b""

                    # For Windows, we'll use a different approach
                    if sys.platform == "win32":
                        # On Windows, try to read with a timeout using threading
                        import queue
                        import threading

                        def read_stream(stream, result_queue, stream_name):
                            try:
                                if stream and not stream.closed:
                                    data = stream.read()
                                    result_queue.put(
                                        (stream_name, data if data else b"")
                                    )
                                else:
                                    result_queue.put((stream_name, b""))
                            except Exception as e:
                                result_queue.put((stream_name, b""))

                        # Create queues for results
                        result_queue = queue.Queue()

                        # Start reading threads
                        threads = []
                        if process.stdout:
                            stdout_thread = threading.Thread(
                                target=read_stream,
                                args=(process.stdout, result_queue, "stdout"),
                            )
                            stdout_thread.daemon = True
                            stdout_thread.start()
                            threads.append(stdout_thread)

                        if process.stderr:
                            stderr_thread = threading.Thread(
                                target=read_stream,
                                args=(process.stderr, result_queue, "stderr"),
                            )
                            stderr_thread.daemon = True
                            stderr_thread.start()
                            threads.append(stderr_thread)

                        # Wait for results with timeout
                        results = {}
                        for _ in threads:
                            try:
                                stream_name, data = result_queue.get(timeout=2.0)
                                results[stream_name] = data
                            except queue.Empty:
                                pass

                        stdout_data = results.get("stdout", b"")
                        stderr_data = results.get("stderr", b"")
                    else:
                        # Unix-like systems - use select
                        import select

                        if process.stdout and process.stderr:
                            ready, _, _ = select.select(
                                [process.stdout, process.stderr], [], [], 0.5
                            )
                            if process.stdout in ready:
                                stdout_data = process.stdout.read()
                            if process.stderr in ready:
                                stderr_data = process.stderr.read()

                    stdout_text = stdout_data.decode("utf-8", errors="replace")
                    stderr_text = stderr_data.decode("utf-8", errors="replace")

                    # Check if we need to terminate due to timeout
                    if timeout <= 30:
                        # Timeout reached, terminate the process
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()

                        return ToolResult(
                            error=(
                                f"Process timed out after {timeout} seconds and was terminated\n"
                                f"Command: {' '.join(command)}\n"
                                f"Working directory: {cwd}\n\n"
                                f"Partial output collected:\n"
                                f"STDOUT:\n{stdout_text}\n"
                                f"STDERR:\n{stderr_text}"
                                if stderr_text
                                else f"STDOUT:\n{stdout_text}"
                            )
                        )
                    else:
                        # Process is still running but we collected partial output
                        return ToolResult(
                            output=(
                                f"Process still running after 30 seconds\n"
                                f"Command: {' '.join(command)}\n"
                                f"Working directory: {cwd}\n"
                                f"Process ID: {process.pid}\n\n"
                                f"Partial output collected (after 30 seconds):\n"
                                f"STDOUT:\n{stdout_text}\n"
                                f"STDERR:\n{stderr_text}"
                                if stderr_text
                                else f"STDOUT:\n{stdout_text}"
                            )
                        )

                except Exception as e:
                    # If we can't read partial output, just return status
                    return ToolResult(
                        output=f"Process still running after 30 seconds\n"
                        f"Command: {' '.join(command)}\n"
                        f"Working directory: {cwd}\n"
                        f"Process ID: {process.pid}\n"
                        f"Note: Could not collect partial output: {str(e)}"
                    )
            else:
                # Process completed within 30 seconds - get full output
                try:
                    stdout_data, stderr_data = process.communicate()
                    stdout_text = (
                        stdout_data.decode("utf-8", errors="replace")
                        if stdout_data
                        else ""
                    )
                    stderr_text = (
                        stderr_data.decode("utf-8", errors="replace")
                        if stderr_data
                        else ""
                    )

                    return self._format_process_result(
                        process.returncode, command, cwd, stdout_text, stderr_text
                    )
                except Exception as e:
                    return ToolResult(
                        error=f"Process completed but failed to read output: {str(e)}"
                    )

        except Exception as e:
            return ToolResult(error=f"Failed to execute process: {str(e)}")

    async def execute(
        self,
        executable_path: str,
        arguments: Optional[list] = None,
        working_directory: Optional[str] = None,
        environment_vars: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        background: bool = False,
        capture_output: bool = True,
        **kwargs,
    ) -> ToolResult:
        """
        Execute a Windows executable file.

        Args:
            executable_path: Path to the executable file
            arguments: Command line arguments for the executable
            working_directory: Working directory for execution
            environment_vars: Additional environment variables
            timeout: Maximum execution time in seconds
            background: Run in background without waiting
            capture_output: Whether to capture stdout/stderr

        Returns:
            ToolResult with execution output, error information, or process info
        """
        try:
            # Validate inputs
            exe_path = self._validate_executable(executable_path)
            arguments = arguments or []
            environment_vars = environment_vars or {}

            # Prepare command
            command = [str(exe_path)] + arguments

            # Prepare working directory
            cwd, error_result = self._prepare_working_directory(
                working_directory, exe_path
            )
            if error_result:
                return error_result

            # Prepare environment
            env = self._prepare_environment(environment_vars)

            # Execute based on background flag
            if background:
                return await self._execute_background_process(
                    command, cwd, env, exe_path, capture_output
                )
            else:
                return await self._execute_foreground_process(
                    command, cwd, env, timeout, capture_output
                )

        except ToolError as e:
            return ToolResult(error=str(e))
        except Exception as e:
            return ToolResult(error=f"Unexpected error: {str(e)}")

    def get_running_processes(self) -> Dict[int, str]:
        """Get information about running background processes."""
        running = {}
        # Clean up terminated processes
        terminated_pids = []

        for pid, process in self._background_processes.items():
            if process.poll() is None:  # Process is still running
                running[pid] = (
                    f"Running (started: {process.args[0] if process.args else 'unknown'})"
                )
            else:
                terminated_pids.append(pid)

        # Remove terminated processes from tracking
        for pid in terminated_pids:
            del self._background_processes[pid]

        return running

    def get_background_process_output(self, pid: int) -> ToolResult:
        """Get output from a background process (only works if process was started with capture_output=True)."""
        if pid not in self._background_processes:
            return ToolResult(error=f"No background process found with PID: {pid}")

        process = self._background_processes[pid]

        # Check if process has finished
        if process.poll() is None:
            return ToolResult(
                error=f"Process {pid} is still running. Wait for completion before retrieving output."
            )

        # Check if output capture was enabled
        if process.stdout is None and process.stderr is None:
            return ToolResult(
                error=f"Process {pid} was started without output capture. Cannot retrieve output."
            )

        try:
            # Get the output (this will be available since process has finished)
            stdout_data = process.stdout.read() if process.stdout else b""
            stderr_data = process.stderr.read() if process.stderr else b""

            stdout_text = stdout_data.decode("utf-8", errors="replace")
            stderr_text = stderr_data.decode("utf-8", errors="replace")

            # Clean up the process from tracking
            del self._background_processes[pid]

            # Format the result
            result_info = f"Background process {pid} completed (exit code: {process.returncode})\n\n"

            if stdout_text:
                result_info += f"STDOUT:\n{stdout_text}\n"

            if stderr_text:
                result_info += f"STDERR:\n{stderr_text}\n"

            if not stdout_text and not stderr_text:
                result_info += "No output captured.\n"

            if process.returncode == 0:
                return ToolResult(output=result_info)
            else:
                return ToolResult(
                    error=f"Process failed with exit code {process.returncode}\n{result_info}"
                )

        except Exception as e:
            return ToolResult(
                error=f"Failed to retrieve output from process {pid}: {str(e)}"
            )

    def terminate_process(self, pid: int) -> bool:
        """Terminate a background process by PID."""
        if pid in self._background_processes:
            process = self._background_processes[pid]
            if process.poll() is None:  # Still running
                process.terminate()
                return True
        return False
