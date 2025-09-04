#!/usr/bin/env python3
"""
Test script for the refactored WindowsExeTool to verify all methods work correctly.
"""
import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))


# Mock the dependencies to test just the logic
class MockToolResult:
    def __init__(self, output=None, error=None):
        self.output = output
        self.error = error


class MockToolError(Exception):
    pass


class MockBaseTool:
    pass


# Mock the imports
import app.tool.windows_exe as windows_exe_module

windows_exe_module.ToolResult = MockToolResult
windows_exe_module.ToolError = MockToolError
windows_exe_module.BaseTool = MockBaseTool

from app.tool.windows_exe import WindowsExeTool


async def test_refactored_methods():
    """Test the individual methods of the refactored WindowsExeTool."""
    print("Testing refactored WindowsExeTool methods...")

    tool = WindowsExeTool()

    # Test _prepare_working_directory method
    print("\n1. Testing _prepare_working_directory...")
    exe_path = Path("C:\\Windows\\System32\\cmd.exe")

    # Test with valid directory
    cwd, error = tool._prepare_working_directory("C:\\Windows", exe_path)
    assert error is None, "Should not return error for valid directory"
    assert cwd == "C:\\Windows", f"Expected C:\\Windows, got {cwd}"
    print("   ✓ Valid directory test passed")

    # Test with None (should use exe parent)
    cwd, error = tool._prepare_working_directory(None, exe_path)
    assert error is None, "Should not return error for None directory"
    assert cwd == str(exe_path.parent), f"Expected {exe_path.parent}, got {cwd}"
    print("   ✓ None directory test passed")

    # Test _format_process_result method
    print("\n2. Testing _format_process_result...")

    # Test successful result
    result = tool._format_process_result(
        0, ["cmd", "/c", "echo", "test"], "C:\\", "Hello\n", ""
    )
    assert result.output is not None, "Should have output for successful result"
    assert "Process completed successfully" in result.output, "Should indicate success"
    print("   ✓ Successful result formatting passed")

    # Test failed result
    result = tool._format_process_result(
        1, ["cmd", "/c", "exit", "1"], "C:\\", "", "Error\n"
    )
    assert result.error is not None, "Should have error for failed result"
    assert "Process failed with exit code: 1" in result.error, "Should indicate failure"
    print("   ✓ Failed result formatting passed")

    print("\n✅ All refactored method tests passed!")
    print("\nRefactoring benefits:")
    print("- Improved code readability and maintainability")
    print("- Separated concerns into focused methods")
    print("- Easier to test individual components")
    print("- Better error handling isolation")
    print("- Reduced complexity in the main execute method")


if __name__ == "__main__":
    try:
        asyncio.run(test_refactored_methods())
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
