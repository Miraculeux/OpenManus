#!/usr/bin/env python3
"""
Test script to demonstrate WindowsExeTool integration with both local execution and MCP.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to sys.path to enable imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.agent.manus import Manus
from app.logger import logger
from app.tool.windows_exe import WindowsExeTool


async def test_windows_exe_tool_direct():
    """Test WindowsExeTool directly."""
    print("\n" + "=" * 60)
    print("Testing WindowsExeTool directly")
    print("=" * 60)

    tool = WindowsExeTool()

    # Test 1: Simple command execution (echo)
    print("\nTest 1: Running echo command...")
    result = await tool.execute(
        executable_path="cmd.exe",
        arguments=["/c", "echo", "Hello from WindowsExeTool!"],
        timeout=10,
    )
    print(f"Result: {result.output if result.output else result.error}")

    # Test 2: Directory listing
    print("\nTest 2: Directory listing...")
    result = await tool.execute(
        executable_path="cmd.exe",
        arguments=["/c", "dir", "/b"],
        working_directory=str(project_root),
        timeout=10,
    )
    print(f"Result: {result.output[:200] if result.output else result.error}")

    # Test 3: System information
    print("\nTest 3: System information...")
    result = await tool.execute(executable_path="systeminfo.exe", timeout=15)
    if result.output:
        # Show only first few lines of system info
        lines = result.output.split("\n")[:10]
        print(f"Result (first 10 lines): {''.join(lines)}")
    else:
        print(f"Error: {result.error}")


async def test_manus_agent_with_windows_exe():
    """Test WindowsExeTool through Manus agent."""
    print("\n" + "=" * 60)
    print("Testing WindowsExeTool through Manus Agent")
    print("=" * 60)

    try:
        # Create Manus agent (which includes WindowsExeTool)
        agent = await Manus.create()

        # Test that WindowsExeTool is available
        available_tools = [tool.name for tool in agent.available_tools.tools]
        print(f"\nAvailable tools: {available_tools}")

        if "windows_exe" in available_tools:
            print("✓ WindowsExeTool is available in Manus agent")

            # You can add more complex agent interaction tests here
            # For now, just verify the tool is properly integrated
            windows_exe_tool = None
            for tool in agent.available_tools.tools:
                if tool.name == "windows_exe":
                    windows_exe_tool = tool
                    break

            if windows_exe_tool:
                print(
                    f"✓ WindowsExeTool found: {windows_exe_tool.description[:100]}..."
                )
        else:
            print("✗ WindowsExeTool is NOT available in Manus agent")

        # Cleanup
        await agent.cleanup()

    except Exception as e:
        logger.error(f"Error testing Manus agent: {e}")
        print(f"Error testing Manus agent: {e}")


async def test_tool_parameters():
    """Test WindowsExeTool parameter validation."""
    print("\n" + "=" * 60)
    print("Testing WindowsExeTool Parameter Validation")
    print("=" * 60)

    tool = WindowsExeTool()

    # Test 1: Invalid executable path
    print("\nTest 1: Invalid executable path...")
    result = await tool.execute(executable_path="nonexistent.exe")
    print(f"Expected error: {result.error}")

    # Test 2: Valid executable with timeout
    print("\nTest 2: Command with timeout...")
    result = await tool.execute(
        executable_path="cmd.exe",
        arguments=["/c", "echo", "Test with 5 second timeout"],
        timeout=5,
    )
    print(f"Result: {result.output if result.output else result.error}")

    # Test 3: Background execution
    print("\nTest 3: Background execution...")
    result = await tool.execute(
        executable_path="cmd.exe",
        arguments=["/c", "echo", "Background process"],
        background=True,
    )
    print(f"Background result: {result.output if result.output else result.error}")


def print_integration_summary():
    """Print summary of how WindowsExeTool integrates with the system."""
    print("\n" + "=" * 60)
    print("WindowsExeTool Integration Summary")
    print("=" * 60)

    print(
        """
1. DIRECT INTEGRATION:
   - WindowsExeTool inherits from BaseTool
   - Implements required methods: name, description, parameters, execute()
   - Uses async/await pattern for non-blocking execution
   - Returns ToolResult objects with output/error information

2. MANUS AGENT INTEGRATION:
   - Added to Manus.available_tools collection in __init__
   - Automatically available when Manus agent is created
   - Can be used by the agent for task execution

3. MCP SERVER INTEGRATION:
   - Added to MCPServer.tools dictionary in server.py
   - Exposed as an MCP tool for remote clients
   - Can be called through Model Context Protocol

4. TOOL FEATURES:
   - Executes Windows executables (.exe, .bat, .cmd, etc.)
   - Supports command line arguments
   - Configurable working directory and environment variables
   - Timeout control and background execution
   - Process management for background tasks

5. PARAMETER SCHEMA:
   - JSON Schema validation for parameters
   - Required: executable_path
   - Optional: arguments, working_directory, environment_vars, timeout, background, capture_output

6. ERROR HANDLING:
   - Validates executable existence and permissions
   - Platform check (Windows only)
   - Timeout handling with process termination
   - Comprehensive error reporting
"""
    )


async def main():
    """Run all tests."""
    print("Starting WindowsExeTool Integration Tests...")

    # Check if we're on Windows
    if sys.platform != "win32":
        print("Skipping tests - WindowsExeTool only works on Windows")
        return

    try:
        # Test direct tool usage
        await test_windows_exe_tool_direct()

        # Test parameter validation
        await test_tool_parameters()

        # Test Manus agent integration
        await test_manus_agent_with_windows_exe()

        # Print integration summary
        print_integration_summary()

        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)

    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        print(f"Test execution failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
