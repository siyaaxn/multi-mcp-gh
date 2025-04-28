import asyncio
import sys
import os # Import os to potentially check file existence
from typing import Optional, List, Dict, Any
from contextlib import AsyncExitStack

# MCP Imports
from mcp import ClientSession, StdioServerParameters # Ensure StdioServerParameters is imported
from mcp.client.stdio import stdio_client

# Anthropic Import
from anthropic import Anthropic
from anthropic.types import MessageParam, ToolParam # Use ToolParam type hint

# Local Imports
import config # Load configuration (API keys, paths)
import mcp_setup # Get server parameters
from tool_manager import ToolManager # Use the fixed ToolManager

class MultiMCPClient:
    """
    Connects to multiple MCP servers (GitHub official and Actions),
    manages their tools, and interacts with Claude using the combined toolset.
    """
    def __init__(self):
        print("Initializing MultiMCPClient...")

        # Load configuration
        self.anthropic_api_key = config.ANTHROPIC_API_KEY
        self.github_token = config.GITHUB_TOKEN
        self.actions_server_script_path = config.ACTIONS_SERVER_SCRIPT_PATH
        self.claude_model = config.CLAUDE_MODEL_NAME

        # Initialize Anthropic client
        self.anthropic: Anthropic = Anthropic(api_key=self.anthropic_api_key)

        # Async context manager for cleanup
        self.exit_stack = AsyncExitStack()

        # Tool manager instance (using the corrected version)
        self.tool_manager = ToolManager()

        # Dictionary to hold active sessions (key: prefix, value: ClientSession)
        # Although ToolManager holds sessions now, keeping this might be useful for direct access if needed
        self.sessions: Dict[str, ClientSession] = {}

        # Flag to track connection status
        self.connected = False

        print("MultiMCPClient Initialized.")

    async def _connect_single_server(self, prefix: str, server_params: StdioServerParameters) -> bool:
        """Attempts to connect to a single MCP server and register its tools."""
        print(f"\nAttempting to connect to server with prefix '{prefix}'...")
        try:
            # Establish stdio connection using parameters from mcp_setup
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            stdio_reader, stdio_writer = stdio_transport

            # Create and initialize the MCP session
            session = await self.exit_stack.enter_async_context(ClientSession(stdio_reader, stdio_writer))

            # <<<--- START CHANGE --->>>
            # Initialize the session. The result object's structure might vary or lack expected fields.
            init_result = await session.initialize()

            # We won't try to access init_result.server_name as it causes an error.
            # Simply print using the prefix we already have.
            print(f"MCP Session initialized for prefix '{prefix}'.")
            # <<<--- END CHANGE --->>>

            # List tools available from this server
            response = await session.list_tools()
            if response and response.tools:
                print(f"Found {len(response.tools)} tools for '{prefix}'.")
                # Add the session and its tools to the ToolManager
                self.tool_manager.add_session(prefix, session, response.tools)
                self.sessions[prefix] = session # Store session for potential direct access
                return True
            else:
                print(f"Warning: No tools listed by the server for '{prefix}'. Server might be running but has no tools defined.")
                # Even if no tools, keep the session maybe? Or handle as failure?
                # For now, let's consider it a partial success but log a warning.
                self.sessions[prefix] = session # Still store session
                # Return True because connection succeeded, even if no tools.
                # If tools are mandatory, change this to return False
                return True # Or False, depending on requirements

        except Exception as e:
            print(f"\n--- ERROR connecting to server '{prefix}' ---")
            # Print traceback for more detailed debugging info
            import traceback
            traceback.print_exc()
            print(f"Error details: {e}") # Keep original error message too
            # Provide specific hints based on prefix
            if prefix == "github":
                 print("Hints: Ensure Docker daemon is running.")
                 print("       Ensure the image 'ghcr.io/github/github-mcp-server' can be pulled (check internet connection/Docker Hub access).")
                 print("       Check if GITHUB_PERSONAL_ACCESS_TOKEN is valid.")
            elif prefix == "actions":
                 print(f"Hints: Ensure Node.js is installed and accessible via the 'node' command.")
                 print(f"       Verify the script path in .env (ACTIONS_SERVER_SCRIPT_PATH):")
                 print(f"         Current path: {self.actions_server_script_path}")
                 print(f"       Does the file exist? {'Yes' if os.path.isfile(self.actions_server_script_path) else 'NO!'}")
                 print(f"       Did you run 'npm install' and 'npm run build' in the actions server directory?")
                 print(f"       Try running the server manually: node {self.actions_server_script_path}")
                 print(f"       Check if GITHUB_PERSONAL_ACCESS_TOKEN is valid.")
            print("----------------------------------------------")
            # Ensure context cleanup for this failed connection attempt if necessary
            # The exit_stack handles this automatically when the exception propagates
            return False

    async def connect_to_servers(self):
        """Connects to all configured MCP servers."""
        print("\n--- Starting Server Connections ---")

        # 1. Connect to Official GitHub MCP Server (Docker)
        github_params = mcp_setup.get_github_server_params(self.github_token)
        github_connected = await self._connect_single_server("github", github_params)

        # 2. Connect to GitHub Actions MCP Server (Node.js)
        actions_params = mcp_setup.get_actions_server_params(self.github_token, self.actions_server_script_path)
        actions_connected = await self._connect_single_server("actions", actions_params)

        print("\n--- Connection Summary ---")
        print(f"Official GitHub Server ('github_'): {'Connected' if github_connected else 'FAILED'}")
        print(f"GitHub Actions Server ('actions_'): {'Connected' if actions_connected else 'FAILED'}")

        # Check if at least one connection was successful AND yielded tools
        available_tools = self.tool_manager.get_available_tool_names()
        if not self.sessions:
             print("\nFatal Error: Could not establish a connection with ANY MCP servers. Exiting.")
             # No need to call cleanup here, finally block in main will handle it
             sys.exit(1)
        elif not available_tools:
            print("\nWarning: Connected to server(s), but NO tools were found/registered from any server.")
            print("The chat loop will start, but Claude won't be able to use any GitHub/Actions tools.")
            # Decide whether to proceed or exit
            # sys.exit(1) # Uncomment to exit if no tools are available
        else:
             print("\nSuccessfully connected and gathered tools from at least one server.")
             print("Available tools (prefixed):")
             for tool_name in sorted(available_tools):
                 print(f"  - {tool_name}")

        self.connected = True # Mark as connected if at least one session is up
        print("-----------------------------")


    async def process_query(self, query: str) -> str:
        """Sends a query to Claude, handles tool calls via MCP, and returns the final response."""

        if not self.connected or not self.anthropic:
            return "Error: Client is not connected to servers or Anthropic client not initialized."

        tools_for_claude = self.tool_manager.get_all_tools_for_claude()
        if not tools_for_claude:
            print("Warning: No tools available to send to Claude.")
            # Proceed without tools, Claude will respond based on its general knowledge
            # return "Error: No tools available from connected servers." # Alternative: return error

        print(f"\nSending query to Claude (Model: {self.claude_model})...")
        if tools_for_claude:
             print(f"Providing {len(tools_for_claude)} tools to Claude.")

        messages: List[MessageParam] = [
            {"role": "user", "content": query}
        ]

        try:
            # Initial call to Claude
            response = self.anthropic.messages.create(
                model=self.claude_model,
                max_tokens=2048, # Allow ample space for response and tool use
                messages=messages,
                tools=tools_for_claude # Pass the combined, prefixed tool list
            )

            # Loop to handle sequential tool calls if Claude requests them
            while response.stop_reason == "tool_use":
                assistant_messages_so_far: List[Any] = [] # Content blocks from this assistant turn
                tool_results_for_claude: List[MessageParam] = [] # Results to send back in the next turn

                print("Claude responded with tool use request(s). Processing...")

                # Iterate through Claude's response blocks (can be text or tool_use)
                for content_block in response.content:
                    assistant_messages_so_far.append(content_block) # Record this part of assistant's turn

                    if content_block.type == "text":
                        print(f"Assistant (text): {content_block.text}")
                        # We'll collect final text at the end, no need to add here yet

                    elif content_block.type == "tool_use":
                        prefixed_tool_name = content_block.name
                        tool_input = content_block.input
                        tool_use_id = content_block.id # Crucial ID to link result back
                        print(f"Assistant requests tool: {prefixed_tool_name} (ID: {tool_use_id})")
                        print(f"Tool Input: {tool_input}")

                        # --- Find the correct session and original tool name using ToolManager ---
                        tool_details = self.tool_manager.get_tool_call_details(prefixed_tool_name)

                        if tool_details:
                            original_tool_name, target_session = tool_details
                            print(f"Routing to session for prefix '{prefixed_tool_name.split('_')[0]}'. Calling original tool: {original_tool_name}")

                            # --- Execute the tool call on the correct MCP session ---
                            tool_result_content = None
                            is_error = False
                            try:
                                tool_call_response = await target_session.call_tool(original_tool_name, tool_input)
                                # Process successful result
                                # Ensure content is serializable (e.g., convert complex objects to dict/str)
                                if isinstance(tool_call_response.content, (dict, list, str, int, float, bool)) or tool_call_response.content is None:
                                     tool_result_content = tool_call_response.content
                                else:
                                     # Attempt conversion if not a basic type
                                     try:
                                         tool_result_content = str(tool_call_response.content)
                                         print(f"Warning: Tool '{prefixed_tool_name}' result converted to string.")
                                     except Exception as conversion_err:
                                          print(f"Error: Failed to convert tool '{prefixed_tool_name}' result to string: {conversion_err}")
                                          tool_result_content = f"Error: Result object of type {type(tool_call_response.content).__name__} could not be serialized."
                                          is_error = True

                                # Log truncated result for debugging
                                result_str_preview = str(tool_result_content)
                                print(f"Tool '{prefixed_tool_name}' result (truncated): {result_str_preview[:300]}{'...' if len(result_str_preview) > 300 else ''}")

                            except Exception as tool_call_error:
                                # Handle errors during the tool call itself
                                print(f"--- ERROR calling tool {prefixed_tool_name} ---")
                                print(f"Error: {tool_call_error}")
                                tool_result_content = f"Error executing tool '{prefixed_tool_name}': {str(tool_call_error)}"
                                is_error = True

                            # --- Prepare the result message for Claude ---
                            tool_results_for_claude.append({
                                "role": "user", # Role must be 'user' for tool_result type
                                "content": [{
                                    "type": "tool_result",
                                    "tool_use_id": tool_use_id,
                                    "content": tool_result_content, # Send the actual result or error message
                                    "is_error": is_error # Explicitly mark if it's an error
                                }]
                            })

                        else:
                            # --- Handle case where Claude hallucinates a tool name ---
                            print(f"--- ERROR: Claude requested unknown tool '{prefixed_tool_name}' ---")
                            tool_results_for_claude.append({
                                "role": "user",
                                "content": [{
                                    "type": "tool_result",
                                    "tool_use_id": tool_use_id,
                                    "content": f"Client error: Tool '{prefixed_tool_name}' is not recognized or available.",
                                    "is_error": True
                                }]
                            })

                # --- Send results back to Claude ---
                # Append the assistant's turn (containing text and tool requests) to history
                messages.append({"role": "assistant", "content": assistant_messages_so_far})
                # Append the tool results (as a user turn) to history
                messages.extend(tool_results_for_claude)

                print("\nSending tool results back to Claude...")
                response = self.anthropic.messages.create(
                    model=self.claude_model,
                    max_tokens=2048,
                    messages=messages, # Send the updated history
                    tools=tools_for_claude # Must provide tools again
                )
            # --- End while loop for tool use ---

            # --- Process the final response from Claude (should not be tool_use) ---
            final_text_parts = []
            if response.content:
                print("\nClaude's final response:")
                for content_block in response.content:
                     if content_block.type == "text":
                         print(f"Assistant (final text): {content_block.text}")
                         final_text_parts.append(content_block.text)
                     # Handle other potential final block types if necessary
            else:
                print("Warning: Claude's final response had no content.")

            # Combine final text parts into a single string
            final_response = "\n".join(final_text_parts).strip()
            return final_response if final_response else "Claude did not provide a final text response."

        except Exception as e:
            print(f"\n--- An error occurred during query processing with Claude ---")
            import traceback
            traceback.print_exc() # Print detailed traceback for debugging
            return f"Error interacting with Claude or processing tools: {str(e)}"

    async def chat_loop(self):
        """Runs the interactive command-line chat loop."""
        if not self.connected:
            print("Error: Cannot start chat loop - client is not connected to any servers.")
            return

        print("\n--- Multi MCP Client Ready ---")
        if not self.tool_manager.get_available_tool_names():
             print("Warning: No tools are available. Interaction will be text-only.")
        else:
             print("Ask Claude to use tools prefixed with 'github_' or 'actions_'.")
             print("Examples:")
             print("  'Use github_list_repos for the authenticated user.'")
             print("  'What workflows are in the repo 'owner/repo_name'?' (Claude should use actions_list_workflows)")
             print("  'Summarize the README for github/github-mcp-server' (Claude should use github_get_readme)")
        print("Type 'quit' or 'exit' to end.")

        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() in ['quit', 'exit']:
                    print("Exiting...")
                    break
                if not query:
                    continue

                # Process the query using Claude and MCP tools
                response_text = await self.process_query(query)

                # Print Claude's final response
                print("\nClaude:")
                print(response_text)

            except KeyboardInterrupt:
                print("\nExiting due to KeyboardInterrupt...")
                break
            except EOFError: # Handle Ctrl+D
                print("\nExiting due to EOF...")
                break
            except Exception as e:
                print(f"\n--- An error occurred in the chat loop ---")
                import traceback
                traceback.print_exc()
                print("-----------------------------------------")
                # Decide whether to continue or break on loop errors
                # break # Uncomment to exit on loop error

    async def cleanup(self):
        """Closes connections and cleans up resources using AsyncExitStack."""
        print("\nCleaning up resources...")
        # The AsyncExitStack automatically calls the __aexit__ methods
        # of the contexts it entered (stdio_client, ClientSession) in reverse order.
        # This handles closing stdin/stdout pipes and potentially signaling servers.
        await self.exit_stack.aclose()
        self.connected = False
        self.sessions.clear() # Clear the session dictionary
        print("Cleanup complete.")

# --- Main Execution ---
async def main():
    """Main async function to initialize the client, connect, and run the chat."""
    print("Starting Multi-MCP Client application...")
    client = MultiMCPClient()
    try:
        # Connect to both servers and gather tools
        await client.connect_to_servers()

        # Start the interactive chat loop if connections were established
        # (connect_to_servers handles exiting if no connection is possible)
        if client.connected:
            await client.chat_loop()
        else:
            # This case might occur if connections succeeded but yielded no tools,
            # and we decided not to exit in connect_to_servers.
            print("Client connected but no tools available. Chat loop skipped.")

    except Exception as e:
         print(f"\n--- A critical error occurred during client execution ---")
         import traceback
         traceback.print_exc()
    finally:
        # Ensure cleanup runs regardless of errors during connect/chat
        await client.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nClient interrupted by user (Ctrl+C).")
    except Exception as e:
         # Catch any unexpected errors during asyncio.run or initial setup
         print(f"\n--- Unhandled top-level exception ---")
         import traceback
         traceback.print_exc()
         print("Exiting due to unexpected error.")