"""
Integration test demonstrating Windows tools working together
This script shows how WindowsExeTool and WindowsFinderTool can be used together
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to path to import the tools
sys.path.append(str(Path(__file__).parent))

from app.tool.windows_exe import WindowsExeTool
from app.tool.windows_finder import WindowsFinderTool


async def test_windows_tools_integration():
    """Test integration between WindowsExeTool and WindowsFinderTool."""

    # Check if we're on Windows
    if sys.platform != "win32":
        print("❌ These tools only work on Windows systems")
        return

    print("=" * 60)
    print("Testing Windows Tools Integration")
    print("=" * 60)

    try:
        # Initialize both tools
        exe_tool = WindowsExeTool()
        finder_tool = WindowsFinderTool()

        # Test 1: Launch an application using WindowsExeTool
        print("\n1. Launching Notepad using WindowsExeTool...")
        result = await exe_tool.execute(
            executable_path="C:\\Windows\\System32\\notepad.exe", background=True
        )

        if result.error:
            print(f"❌ Error launching Notepad: {result.error}")
            return
        else:
            print(f"✅ Successfully launched Notepad: {result.output}")

        # Wait a moment for the application to fully load
        await asyncio.sleep(2)

        # Test 2: Find the launched application using WindowsFinderTool
        print("\n2. Finding Notepad windows using WindowsFinderTool...")
        result = await finder_tool.execute(title="Notepad")

        if result.error:
            print(f"❌ Error finding Notepad: {result.error}")
        else:
            print(f"✅ Found Notepad windows: {result.output}")

        # Test 3: Find windows for a specific application type
        print("\n3. Finding all Microsoft applications...")
        result = await finder_tool.execute(title="Microsoft")

        if result.error:
            print(f"❌ Error: {result.error}")
        else:
            print(f"✅ Microsoft applications: {result.output}")

        # Test 4: Use convenience method to get window handles
        print("\n4. Getting window handles for VS Code...")
        code_windows = finder_tool.find_window_by_title("Visual Studio Code")
        print(f"Found {len(code_windows)} VS Code windows:")
        for hwnd, title in code_windows:
            print(f"  - HWND: 0x{hwnd:08X}, Title: {title}")

        # Test 5: List running processes from WindowsExeTool
        print("\n5. Checking running background processes...")
        running_processes = exe_tool.get_running_processes()
        print(f"Background processes managed by WindowsExeTool: {running_processes}")

        # Test 6: Demonstrate finding and potentially interacting with specific windows
        print("\n6. Demonstrating practical usage - finding calculator...")
        result = await finder_tool.execute(title="Calculator")

        if result.error:
            print(f"❌ Error: {result.error}")
        else:
            print(f"✅ Calculator search result: {result.output}")

        # If calculator not found, try to launch it
        if "No windows found" in result.output:
            print("\n   Calculator not found, trying to launch it...")
            calc_result = await exe_tool.execute(
                executable_path="C:\\Windows\\System32\\calc.exe", background=True
            )

            if calc_result.error:
                print(f"❌ Error launching Calculator: {calc_result.error}")
            else:
                print(f"✅ Successfully launched Calculator: {calc_result.output}")

                # Wait and try to find it again
                await asyncio.sleep(2)
                result = await finder_tool.execute(title="Calculator")
                print(f"✅ Calculator after launch: {result.output}")

        # Test 7: Clean up - terminate processes we started
        print("\n7. Cleaning up launched processes...")
        running = exe_tool.get_running_processes()
        for pid in running.keys():
            success = exe_tool.terminate_process(pid)
            print(f"   Terminated process {pid}: {success}")

    except Exception as e:
        print(f"❌ Integration test failed: {e}")

    print("\n" + "=" * 60)
    print("Windows Tools Integration Test Completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_windows_tools_integration())
