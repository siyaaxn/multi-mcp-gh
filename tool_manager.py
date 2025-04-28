from typing import Dict, List, Tuple, Optional, Any
from mcp import ClientSession, Tool # Make sure Tool is imported if you use its type hint

class ToolManager:
    """
    Manages tools from multiple MCP sessions.

    Responsibilities:
    - Assigns unique prefixed names to tools from different sessions.
    - Stores the mapping between the prefixed name and the original tool name + session.
    - Formats tool definitions for the AI model (e.g., Claude).
    """

    def __init__(self):
        # Stores tool definitions formatted for Claude (with prefixed names)
        self._tool_definitions_for_claude: List[Dict[str, Any]] = []

        # Stores the crucial mapping: "prefix_tool_name" -> (original_tool_name, session_object)
        self._tool_mapping: Dict[str, Tuple[str, ClientSession]] = {}
        # Removed self._session_prefixes dictionary as it caused the error and wasn't essential

    def add_session(self, session_prefix: str, session: ClientSession, tools: List[Tool]):
        """
        Adds tools from a connected MCP session to the manager.

        Args:
            session_prefix: A string prefix to identify the source session (e.g., "github").
            session: The connected ClientSession object.
            tools: A list of Tool objects provided by the session.
        """
        if not session_prefix.endswith('_'):
             session_prefix += '_' # Ensure prefix ends with underscore for clarity

        # We can still print which session's tools we are adding
        print(f"Adding tools from session with prefix '{session_prefix}'...")
        # *** The problematic line accessing session.server_info was removed from here ***

        for tool in tools:
            prefixed_name = f"{session_prefix}{tool.name}"
            print(f"  - Mapping tool: {tool.name} -> {prefixed_name}")

            # 1. Add tool definition for Claude
            # We add the prefix to the description to help Claude know the source
            self._tool_definitions_for_claude.append({
                "name": prefixed_name,
                "description": f"[{session_prefix[:-1].upper()}] {tool.description}", # e.g., "[GITHUB] Lists repositories"
                "input_schema": tool.inputSchema
            })

            # 2. Store the mapping needed to call the tool later
            # Map the new prefixed name back to the original name and the session object
            self._tool_mapping[prefixed_name] = (tool.name, session) # This mapping is crucial

    def get_all_tools_for_claude(self) -> List[Dict[str, Any]]:
        """Returns the list of all managed tools formatted for Claude's API."""
        return self._tool_definitions_for_claude

    def get_tool_call_details(self, prefixed_tool_name: str) -> Optional[Tuple[str, ClientSession]]:
        """
        Given a prefixed tool name (used by Claude), returns the original
        tool name and the ClientSession object needed to call it.

        Args:
            prefixed_tool_name: The tool name including the prefix (e.g., "github_list_repos").

        Returns:
            A tuple (original_tool_name, session_object) or None if the tool is not found.
        """
        return self._tool_mapping.get(prefixed_tool_name)

    def get_available_tool_names(self) -> List[str]:
        """Returns a list of all available prefixed tool names."""
        # Returns the keys from the mapping, which are the prefixed names
        return list(self._tool_mapping.keys())