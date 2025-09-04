"""
Test script for WindowsExeTool
This script demonstrates how to use the WindowsExeTool to execute Windows executables.
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to path to import the tool
sys.path.append(str(Path(__file__).parent.parent))

from app.tool.windows_exe import WindowsExeTool


async def test_windows_exe_tool():
    """Test the WindowsExeTool with various scenarios."""

    tool = WindowsExeTool()

    print("=" * 60)
    print("Testing WindowsExeTool")
    print("=" * 60)

    # Test 1: Simple command - dir (using cmd.exe)
    print("\n1. Testing simple dir command...")
    result = await tool.execute(
        executable_path="cmd.exe", arguments=["/c", "dir", "C:\\"], timeout=10
    )

    if result.error:
        print(f"❌ Error: {result.error}")
    else:
        print(f"✅ Success: {result.output[:200]}...")

    # Test 2: Test with PowerShell
    print("\n2. Testing PowerShell command...")
    result = await tool.execute(
        executable_path="powershell.exe", arguments=["-Command", "Get-Date"], timeout=10
    )

    if result.error:
        print(f"❌ Error: {result.error}")
    else:
        print(f"✅ Success: {result.output}")

    # Test 3: Test with custom working directory
    print("\n3. Testing with custom working directory...")
    result = await tool.execute(
        executable_path="cmd.exe",
        arguments=["/c", "echo", "%CD%"],
        working_directory="C:\\Windows",
        timeout=5,
    )

    if result.error:
        print(f"❌ Error: {result.error}")
    else:
        print(f"✅ Success: {result.output}")

    # Test 4: Test background execution
    print("\n4. Testing background execution...")
    result = await tool.execute(executable_path="notepad.exe", background=True)

    if result.error:
        print(f"❌ Error: {result.error}")
    else:
        print(f"✅ Success: {result.output}")

        # Check running processes
        running = tool.get_running_processes()
        print(f"Running processes: {running}")

        # Terminate the process we just started
        if running:
            pid = list(running.keys())[0]
            terminated = tool.terminate_process(pid)
            print(f"Terminated process {pid}: {terminated}")

    # Test 5: Test invalid executable
    print("\n5. Testing invalid executable...")
    result = await tool.execute(executable_path="nonexistent.exe", timeout=5)

    if result.error:
        print(f"✅ Expected error: {result.error}")
    else:
        print(f"❌ Unexpected success: {result.output}")

    # Test 6: Test environment variables
    print("\n6. Testing with environment variables...")
    result = await tool.execute(
        executable_path="cmd.exe",
        arguments=["/c", "echo", "%CUSTOM_VAR%"],
        environment_vars={"CUSTOM_VAR": "Hello from WindowsExeTool!"},
        timeout=5,
    )

    if result.error:
        print(f"❌ Error: {result.error}")
    else:
        print(f"✅ Success: {result.output}")

    print("\n" + "=" * 60)
    print("WindowsExeTool testing completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_windows_exe_tool())
