from mcp import StdioServerParameters
import os # Import os for environment variables if needed elsewhere

def get_github_server_params(github_token: str) -> StdioServerParameters:
    """Defines parameters to run the official GitHub MCP Server via Docker."""
    print("Defining parameters for official GitHub MCP Server (Docker)...")
    return StdioServerParameters(
        command="docker",
        args=[
            "run",
            "-i", # Interactive mode (connects stdin/stdout)
            "--rm", # Automatically remove the container when it exits
            "-e", "GITHUB_PERSONAL_ACCESS_TOKEN", # Pass token as env var
            "ghcr.io/github/github-mcp-server" # The official server image
        ],
        env={
            # The environment variables for the Docker command itself
            "GITHUB_PERSONAL_ACCESS_TOKEN": github_token
        }
    )

def get_actions_server_params(github_token: str, script_path: str) -> StdioServerParameters:
    """Defines parameters to run the Actions MCP Server via Node.js."""
    print(f"Defining parameters for GitHub Actions MCP Server (Node.js script: {script_path})...")
    return StdioServerParameters(
        command="node", # Command to run the Node.js runtime
        args=[
            script_path # The path to the compiled server script
        ],
        env={
            # Environment variables needed by the Node.js script itself
            "GITHUB_PERSONAL_ACCESS_TOKEN": github_token
            # Add any other environment variables the Actions server might need
        }
    )