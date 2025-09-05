"""
Test script to verify WindowsFinderTool is properly integrated into MCP server
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to path to import the server
sys.path.append(str(Path(__file__).parent))

from app.mcp.server import MCPServer


async def test_mcp_server_windows_finder():
    """Test that WindowsFinderTool is properly registered in MCP server."""

    print("=" * 60)
    print("Testing WindowsFinderTool integration in MCP Server")
    print("=" * 60)

    try:
        # Initialize MCP server
        server = MCPServer("test_server")

        # Check if windows_finder tool is registered
        print(f"\n1. Checking registered tools...")
        registered_tools = list(server.tools.keys())
        print(f"   Registered tools: {registered_tools}")

        if "windows_finder" in server.tools:
            print("   ✅ WindowsFinderTool is registered")
        else:
            print("   ❌ WindowsFinderTool is NOT registered")
            return

        # Check tool type and basic properties
        finder_tool = server.tools["windows_finder"]
        print(f"\n2. Tool details:")
        print(f"   Tool type: {type(finder_tool).__name__}")
        print(f"   Tool name: {finder_tool.name}")
        print(f"   Tool description: {finder_tool.description[:100]}...")

        # Check if we're on Windows before testing functionality
        if sys.platform != "win32":
            print(f"\n3. Platform check: Running on {sys.platform} (not Windows)")
            print(
                "   ⚠️  WindowsFinderTool requires Windows, skipping functionality test"
            )
            return

        print(f"\n3. Platform check: Running on Windows ✅")

        # Test basic functionality
        print(f"\n4. Testing basic functionality...")
        try:
            # Test listing all windows (limit output for readability)
            result = await finder_tool.execute(list_all=True)

            if result.error:
                print(f"   ❌ Error: {result.error}")
            else:
                # Count windows found
                lines = result.output.split("\n")
                window_count = 0
                for line in lines:
                    if "Window Handle:" in line:
                        window_count += 1

                print(f"   ✅ Successfully found {window_count} windows")
                print(f"   Sample output: {lines[0] if lines else 'No output'}")

        except Exception as e:
            print(f"   ❌ Functionality test failed: {e}")

        # Test tool parameters
        print(f"\n5. Checking tool parameters...")
        tool_params = finder_tool.parameters
        if tool_params and "properties" in tool_params:
            props = tool_params["properties"]
            print(f"   Available parameters: {list(props.keys())}")
            print("   ✅ Tool parameters are properly defined")
        else:
            print("   ❌ Tool parameters not found")

        # Test tool registration method
        print(f"\n6. Testing tool registration...")
        try:
            # This would normally be called by register_all_tools()
            server.register_tool(finder_tool)
            print("   ✅ Tool registration method works")
        except Exception as e:
            print(f"   ❌ Tool registration failed: {e}")

    except Exception as e:
        print(f"❌ MCP Server test failed: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
    print("MCP Server WindowsFinderTool integration test completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_mcp_server_windows_finder())
