import ctypes
import ctypes.wintypes
import sys
from typing import Dict, List, Optional, Tuple

from app.exceptions import ToolError
from app.tool.base import BaseTool, ToolResult

_WINDOWS_FINDER_DESCRIPTION = """Find Windows by title or partial title match on Windows systems.
* Window enumeration: Lists all visible windows on the desktop
* Title search: Find windows with exact or partial title matches
* Window information: Returns window handle, title, process ID, and visibility status
* Case-insensitive search: Supports case-insensitive title matching
* Pattern matching: Supports partial matches and wildcard-like searches

This tool uses Windows API to enumerate all top-level windows and filter them based on title criteria.
It's useful for finding specific applications, dialog boxes, or windows for automation purposes.

Note: This tool only works on Windows systems and requires Windows API access.
"""


class WindowsFinderTool(BaseTool):
    """A tool for finding Windows by title using Windows API."""

    name: str = "windows_finder"
    description: str = _WINDOWS_FINDER_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "The window title to search for. Can be exact match or partial match.",
            },
            "exact_match": {
                "type": "boolean",
                "description": "Whether to perform exact title matching (case-insensitive) or partial matching",
                "default": False,
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Whether the search should be case-sensitive",
                "default": False,
            },
            "include_hidden": {
                "type": "boolean",
                "description": "Whether to include hidden/invisible windows in the search",
                "default": False,
            },
            "list_all": {
                "type": "boolean",
                "description": "List all windows instead of searching for a specific title",
                "default": False,
            },
        },
        "required": [],
    }

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._validate_platform()
        self._user32 = None
        self._kernel32 = None
        self._setup_windows_api()

    def _validate_platform(self):
        """Validate that this tool is running on Windows."""
        if sys.platform != "win32":
            raise ToolError("This tool only works on Windows systems")

    def _setup_windows_api(self):
        """Setup Windows API function signatures."""
        try:
            # Define Windows API functions
            import ctypes.wintypes

            self._user32 = ctypes.windll.user32
            self._kernel32 = ctypes.windll.kernel32

            # Define function signatures
            self._user32.EnumWindows.argtypes = [
                ctypes.WINFUNCTYPE(
                    ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
                ),
                ctypes.wintypes.LPARAM,
            ]
            self._user32.EnumWindows.restype = ctypes.wintypes.BOOL

            self._user32.GetWindowTextW.argtypes = [
                ctypes.wintypes.HWND,
                ctypes.wintypes.LPWSTR,
                ctypes.c_int,
            ]
            self._user32.GetWindowTextW.restype = ctypes.c_int

            self._user32.GetWindowTextLengthW.argtypes = [ctypes.wintypes.HWND]
            self._user32.GetWindowTextLengthW.restype = ctypes.c_int

            self._user32.IsWindowVisible.argtypes = [ctypes.wintypes.HWND]
            self._user32.IsWindowVisible.restype = ctypes.wintypes.BOOL

            self._user32.GetWindowThreadProcessId.argtypes = [
                ctypes.wintypes.HWND,
                ctypes.POINTER(ctypes.wintypes.DWORD),
            ]
            self._user32.GetWindowThreadProcessId.restype = ctypes.wintypes.DWORD

        except Exception as e:
            raise ToolError(f"Failed to setup Windows API: {str(e)}")

    def _get_window_text(self, hwnd: int) -> str:
        """Get the title text of a window."""
        try:
            length = self._user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return ""

            buffer = ctypes.create_unicode_buffer(length + 1)
            self._user32.GetWindowTextW(hwnd, buffer, length + 1)
            return buffer.value
        except Exception:
            return ""

    def _get_window_process_id(self, hwnd: int) -> int:
        """Get the process ID that owns the window."""
        try:
            process_id = ctypes.wintypes.DWORD()
            self._user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
            return process_id.value
        except Exception:
            return 0

    def _is_window_visible(self, hwnd: int) -> bool:
        """Check if a window is visible."""
        try:
            return bool(self._user32.IsWindowVisible(hwnd))
        except Exception:
            return False

    def _enumerate_all_windows(self) -> List[Dict]:
        """Enumerate all top-level windows."""
        windows_list = []

        try:
            # Create callback function
            def enum_callback(hwnd, lparam):
                try:
                    title = self._get_window_text(hwnd)
                    is_visible = self._is_window_visible(hwnd)
                    process_id = self._get_window_process_id(hwnd)

                    # Store window information
                    windows_list.append(
                        {
                            "hwnd": hwnd,
                            "title": title,
                            "visible": is_visible,
                            "process_id": process_id,
                        }
                    )

                    return True  # Continue enumeration
                except Exception:
                    return True  # Continue enumeration even if there's an error

            # Define callback type
            callback_type = ctypes.WINFUNCTYPE(
                ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
            )
            callback = callback_type(enum_callback)

            # Enumerate windows
            self._user32.EnumWindows(callback, 0)

            return windows_list
        except Exception as e:
            raise ToolError(f"Failed to enumerate windows: {str(e)}")

    def _filter_windows(
        self,
        windows: List[Dict],
        title: Optional[str] = None,
        exact_match: bool = False,
        case_sensitive: bool = False,
        include_hidden: bool = False,
    ) -> List[Dict]:
        """Filter windows based on search criteria."""
        filtered_windows = []

        for window in windows:
            # Filter by visibility
            if not include_hidden and not window["visible"]:
                continue

            # Filter by title if specified
            if title:
                window_title = window["title"]
                search_title = title

                # Apply case sensitivity
                if not case_sensitive:
                    window_title = window_title.lower()
                    search_title = search_title.lower()

                # Apply matching criteria
                if exact_match:
                    if window_title != search_title:
                        continue
                else:
                    if search_title not in window_title:
                        continue

            filtered_windows.append(window)

        return filtered_windows

    def _format_window_info(self, windows: List[Dict]) -> str:
        """Format window information for display."""
        if not windows:
            return "No windows found matching the criteria."

        result_lines = [f"Found {len(windows)} window(s):\n"]

        for i, window in enumerate(windows, 1):
            hwnd = window["hwnd"]
            title = window["title"] or "(No Title)"
            visible = "Visible" if window["visible"] else "Hidden"
            process_id = window["process_id"]

            result_lines.append(
                f"{i}. Window Handle: 0x{hwnd:08X} ({hwnd})\n"
                f"   Title: {title}\n"
                f"   Status: {visible}\n"
                f"   Process ID: {process_id}\n"
            )

        return "".join(result_lines)

    async def execute(
        self,
        title: Optional[str] = None,
        exact_match: bool = False,
        case_sensitive: bool = False,
        include_hidden: bool = False,
        list_all: bool = False,
        **kwargs,
    ) -> ToolResult:
        """
        Find windows by title or list all windows.

        Args:
            title: The window title to search for
            exact_match: Whether to perform exact title matching
            case_sensitive: Whether the search should be case-sensitive
            include_hidden: Whether to include hidden windows
            list_all: List all windows instead of searching

        Returns:
            ToolResult containing window information
        """
        try:
            # Enumerate all windows
            all_windows = self._enumerate_all_windows()

            if list_all:
                # Return all windows (filtered by visibility if needed)
                filtered_windows = self._filter_windows(
                    all_windows, include_hidden=include_hidden
                )
                result_text = self._format_window_info(filtered_windows)
                return ToolResult(output=result_text)

            elif title:
                # Search for windows with specific title
                filtered_windows = self._filter_windows(
                    all_windows,
                    title=title,
                    exact_match=exact_match,
                    case_sensitive=case_sensitive,
                    include_hidden=include_hidden,
                )
                result_text = self._format_window_info(filtered_windows)
                return ToolResult(output=result_text)

            else:
                return ToolResult(
                    error="Either provide a 'title' to search for or set 'list_all' to True"
                )

        except ToolError as e:
            return ToolResult(error=str(e))
        except Exception as e:
            return ToolResult(error=f"Unexpected error: {str(e)}")

    def find_window_by_title(
        self, title: str, exact_match: bool = False
    ) -> List[Tuple[int, str]]:
        """
        Convenience method to find windows and return just the HWND and title.

        Args:
            title: The window title to search for
            exact_match: Whether to perform exact title matching

        Returns:
            List of tuples containing (hwnd, title) for matching windows
        """
        try:
            all_windows = self._enumerate_all_windows()
            filtered_windows = self._filter_windows(
                all_windows,
                title=title,
                exact_match=exact_match,
                case_sensitive=False,
                include_hidden=False,
            )

            return [(window["hwnd"], window["title"]) for window in filtered_windows]
        except Exception:
            return []

    def get_all_visible_windows(self) -> List[Dict]:
        """
        Convenience method to get all visible windows.

        Returns:
            List of dictionaries containing window information
        """
        try:
            all_windows = self._enumerate_all_windows()
            return self._filter_windows(all_windows, include_hidden=False)
        except Exception:
            return []
