# MCP Server Tool Integration

This document shows the available tools in the OpenManus MCP server, including the newly added WindowsFinderTool.

## Available Tools

The MCP server includes the following tools:

### Core Tools
- **bash**: Execute bash/shell commands
- **editor**: String replacement editor for file editing
- **terminate**: Terminate operations
- **browser**: Browser automation tool
- **background_capture**: Background screen capture functionality

### Windows-Specific Tools
- **windows_exe**: Execute Windows executable files with comprehensive process management
- **windows_finder**: Find and enumerate Windows by title (NEW)

## WindowsFinderTool Integration

The `windows_finder` tool has been successfully integrated into the MCP server with the following capabilities:

### Tool Registration
```python
# In app/mcp/server.py
from app.tool.windows_finder import WindowsFinderTool

class MCPServer:
    def __init__(self, name: str = "openmanus"):
        # ... other initialization ...
        self.tools["windows_finder"] = WindowsFinderTool()
```

### Available Parameters
- `title` (string): The window title to search for
- `exact_match` (boolean): Whether to perform exact title matching (default: False)
- `case_sensitive` (boolean): Whether the search should be case-sensitive (default: False)
- `include_hidden` (boolean): Whether to include hidden windows (default: False)
- `list_all` (boolean): List all windows instead of searching (default: False)

### Example Usage via MCP

```json
{
  "method": "tools/call",
  "params": {
    "name": "windows_finder",
    "arguments": {
      "title": "Notepad",
      "exact_match": false,
      "case_sensitive": false
    }
  }
}
```

### Integration Benefits

1. **Consistent API**: Follows the same pattern as other MCP tools
2. **Async Support**: Full async/await compatibility
3. **Error Handling**: Proper error responses via ToolResult
4. **Parameter Validation**: Automatic parameter validation and documentation
5. **Logging**: Integrated logging for debugging and monitoring

### Platform Compatibility

- **Windows Only**: The tool only works on Windows systems
- **Automatic Detection**: Gracefully handles non-Windows platforms
- **Error Reporting**: Clear error messages for platform mismatches

### Testing

The integration has been tested and verified to work correctly:
- ✅ Tool registration in MCP server
- ✅ Parameter validation and schema
- ✅ Basic functionality on Windows
- ✅ Error handling for unsupported platforms
- ✅ Async operation compatibility

## Usage with Other Tools

The WindowsFinderTool can be used in combination with other tools for comprehensive Windows automation:

1. **With windows_exe**: Launch applications and then find their windows
2. **With browser**: Find browser windows for specific automation tasks
3. **With background_capture**: Capture screenshots of specific windows

This integration makes the OpenManus MCP server a powerful platform for Windows-based automation and management tasks.
