"""
Test script for WindowsFinderTool
This script demonstrates how to use the WindowsFinderTool to find Windows by title.
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to path to import the tool
sys.path.append(str(Path(__file__).parent))

from app.tool.windows_finder import WindowsFinderTool


async def test_windows_finder_tool():
    """Test the WindowsFinderTool with various scenarios."""

    # Check if we're on Windows
    if sys.platform != "win32":
        print("❌ This tool only works on Windows systems")
        return

    try:
        tool = WindowsFinderTool()
    except Exception as e:
        print(f"❌ Failed to initialize WindowsFinderTool: {e}")
        return

    print("=" * 60)
    print("Testing WindowsFinderTool")
    print("=" * 60)

    # Test 1: List all visible windows
    print("\n1. Listing all visible windows...")
    result = await tool.execute(list_all=True)

    if result.error:
        print(f"❌ Error: {result.error}")
    else:
        # Show first 10 windows to avoid too much output
        lines = result.output.split("\n")
        if len(lines) > 50:  # Limit output for readability
            print("\n".join(lines[:50]))
            print(f"... (output truncated, showing first 50 lines)")
        else:
            print(result.output)

    # Test 2: Search for Notepad (if running)
    print("\n2. Searching for Notepad windows...")
    result = await tool.execute(title="Notepad")

    if result.error:
        print(f"❌ Error: {result.error}")
    else:
        print(f"✅ Result: {result.output}")

    # Test 3: Search for Visual Studio Code windows
    print("\n3. Searching for Visual Studio Code windows...")
    result = await tool.execute(title="Visual Studio Code")

    if result.error:
        print(f"❌ Error: {result.error}")
    else:
        print(f"✅ Result: {result.output}")

    # Test 4: Search for any window containing "Microsoft"
    print("\n4. Searching for windows containing 'Microsoft'...")
    result = await tool.execute(title="Microsoft", exact_match=False)

    if result.error:
        print(f"❌ Error: {result.error}")
    else:
        print(f"✅ Result: {result.output}")

    # Test 5: Search with exact match
    print("\n5. Searching for exact match 'Calculator'...")
    result = await tool.execute(title="Calculator", exact_match=True)

    if result.error:
        print(f"❌ Error: {result.error}")
    else:
        print(f"✅ Result: {result.output}")

    # Test 6: Include hidden windows in search
    print("\n6. Searching for any window (including hidden) containing 'Windows'...")
    result = await tool.execute(title="Windows", include_hidden=True)

    if result.error:
        print(f"❌ Error: {result.error}")
    else:
        # Limit output for readability
        lines = result.output.split("\n")
        if len(lines) > 30:
            print("\n".join(lines[:30]))
            print(f"... (output truncated)")
        else:
            print(result.output)

    # Test 7: Test convenience methods
    print("\n7. Testing convenience methods...")
    try:
        # Find windows by title using convenience method
        windows = tool.find_window_by_title("Code")
        print(f"Found {len(windows)} windows with 'Code' in title:")
        for hwnd, title in windows[:5]:  # Show first 5
            print(f"  - HWND: 0x{hwnd:08X}, Title: {title}")

        # Get all visible windows using convenience method
        all_windows = tool.get_all_visible_windows()
        print(f"\nTotal visible windows: {len(all_windows)}")

    except Exception as e:
        print(f"❌ Error testing convenience methods: {e}")

    # Test 8: Case sensitive search
    print("\n8. Testing case sensitive search...")
    result = await tool.execute(title="notepad", case_sensitive=True)

    if result.error:
        print(f"❌ Error: {result.error}")
    else:
        print(f"✅ Result (case sensitive): {result.output}")

    # Test 9: Case insensitive search
    print("\n9. Testing case insensitive search...")
    result = await tool.execute(title="notepad", case_sensitive=False)

    if result.error:
        print(f"❌ Error: {result.error}")
    else:
        print(f"✅ Result (case insensitive): {result.output}")

    print("\n" + "=" * 60)
    print("WindowsFinderTool testing completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_windows_finder_tool())
