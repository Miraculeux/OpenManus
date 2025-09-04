"""
Unit tests for WindowsExeTool
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add the parent directory to path to import the tool
sys.path.append(str(Path(__file__).parent.parent))

from app.exceptions import ToolError
from app.tool.windows_exe import WindowsExeTool


class TestWindowsExeTool:
    """Test cases for WindowsExeTool."""

    @pytest.fixture
    def tool(self):
        """Create a WindowsExeTool instance for testing."""
        return WindowsExeTool()

    def test_tool_properties(self, tool):
        """Test that the tool has correct properties."""
        assert tool.name == "windows_exe"
        assert "Execute Windows executable files" in tool.description
        assert "executable_path" in tool.parameters["properties"]
        assert "arguments" in tool.parameters["properties"]
        assert "timeout" in tool.parameters["properties"]
        assert "background" in tool.parameters["properties"]

    @patch("sys.platform", "linux")
    @pytest.mark.asyncio
    async def test_non_windows_platform(self, tool):
        """Test that the tool raises an error on non-Windows platforms."""
        result = await tool.execute(executable_path="test.exe")
        assert result.error is not None
        assert "only works on Windows" in result.error

    @patch("sys.platform", "win32")
    @pytest.mark.asyncio
    async def test_nonexistent_file(self, tool):
        """Test handling of nonexistent executable files."""
        result = await tool.execute(executable_path="nonexistent.exe")
        assert result.error is not None
        assert "not found" in result.error

    @patch("sys.platform", "win32")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.is_file", return_value=False)
    @pytest.mark.asyncio
    async def test_path_not_file(self, mock_is_file, mock_exists, tool):
        """Test handling when path exists but is not a file."""
        result = await tool.execute(executable_path="some_directory")
        assert result.error is not None
        assert "not a file" in result.error

    @patch("sys.platform", "win32")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.is_file", return_value=True)
    @patch("asyncio.create_subprocess_exec")
    @pytest.mark.asyncio
    async def test_successful_execution(
        self, mock_subprocess, mock_is_file, mock_exists, tool
    ):
        """Test successful execution of an executable."""
        # Mock subprocess
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"Hello World", b"")
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        result = await tool.execute(
            executable_path="test.exe", arguments=["arg1", "arg2"], timeout=10
        )

        assert result.error is None
        assert "Process completed successfully" in result.output
        assert "Hello World" in result.output

    @patch("sys.platform", "win32")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.is_file", return_value=True)
    @patch("asyncio.create_subprocess_exec")
    @pytest.mark.asyncio
    async def test_failed_execution(
        self, mock_subprocess, mock_is_file, mock_exists, tool
    ):
        """Test handling of failed execution."""
        # Mock subprocess with non-zero exit code
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"Error message")
        mock_process.returncode = 1
        mock_subprocess.return_value = mock_process

        result = await tool.execute(executable_path="test.exe")

        assert result.error is not None
        assert "Process failed with exit code: 1" in result.error
        assert "Error message" in result.error

    @patch("sys.platform", "win32")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.is_file", return_value=True)
    @patch("subprocess.Popen")
    @pytest.mark.asyncio
    async def test_background_execution(
        self, mock_popen, mock_is_file, mock_exists, tool
    ):
        """Test background execution."""
        # Mock Popen for background process
        mock_process = MagicMock()
        mock_process.pid = 1234
        mock_popen.return_value = mock_process

        result = await tool.execute(executable_path="test.exe", background=True)

        assert result.error is None
        assert "Started background process" in result.output
        assert "1234" in result.output

        # Check that process is tracked
        running = tool.get_running_processes()
        assert 1234 in running

    @patch("sys.platform", "win32")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.is_file", return_value=True)
    @patch("asyncio.create_subprocess_exec")
    @pytest.mark.asyncio
    async def test_timeout_handling(
        self, mock_subprocess, mock_is_file, mock_exists, tool
    ):
        """Test timeout handling."""
        # Mock subprocess that times out
        mock_process = MagicMock()
        mock_process.communicate.side_effect = asyncio.TimeoutError()
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()
        mock_process.wait.return_value = None
        mock_subprocess.return_value = mock_process

        result = await tool.execute(executable_path="test.exe", timeout=1)

        assert result.error is not None
        assert "timed out" in result.error
        mock_process.terminate.assert_called_once()

    def test_environment_preparation(self, tool):
        """Test environment variable preparation."""
        custom_env = {"TEST_VAR": "test_value"}
        env = tool._prepare_environment(custom_env)

        assert "TEST_VAR" in env
        assert env["TEST_VAR"] == "test_value"
        # Should also contain system environment variables
        assert len(env) > 1

    @patch("sys.platform", "win32")
    def test_validate_executable_extensions(self, tool):
        """Test validation of different executable extensions."""
        # Test valid extensions
        valid_extensions = [
            ".exe",
            ".bat",
            ".cmd",
            ".com",
            ".msi",
            ".ps1",
            ".vbs",
            ".jar",
        ]

        for ext in valid_extensions:
            with patch("pathlib.Path.exists", return_value=True), patch(
                "pathlib.Path.is_file", return_value=True
            ):

                path = tool._validate_executable(f"test{ext}")
                assert path.suffix == ext

    def test_process_management(self, tool):
        """Test process management functions."""
        # Mock a process
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Still running
        mock_process.args = ["test.exe"]

        # Add to tracking
        tool._background_processes[1234] = mock_process

        # Test getting running processes
        running = tool.get_running_processes()
        assert 1234 in running
        assert "test.exe" in running[1234]

        # Test terminating process
        terminated = tool.terminate_process(1234)
        assert terminated is True
        mock_process.terminate.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
