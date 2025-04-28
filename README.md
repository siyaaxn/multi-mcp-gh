# Multi-MCP Client for GitHub Tools

A client that connects to multiple MCP servers simultaneously. It integrates with Anthropic's Claude model to allow natural language interaction with GitHub repositories and actions via MCP tools.

This client connects to:

1.  The official **GitHub MCP Server** (run via Docker).
2.  The **GitHub Actions MCP Server** (run via Node.js, from [github/github-actions-mcp-server](https://github.com/github/github-actions-mcp-server)).

It uses a `ToolManager` to prefix tool names based on their source server (e.g., `github_list_repos`, `actions_list_workflows`), enabling Claude to distinguish and correctly invoke tools from different servers.

## Features

- Connects to multiple MCP servers using `mcp-client`'s stdio transport.
- Manages tools from different servers with clear prefixes.
- Integrates with Anthropic's Claude (specifically tested with Claude 3.5 Sonnet) for tool usage via natural language.
- Handles sequential tool calls requested by Claude.
- Provides an interactive chat loop for querying Claude.
- Uses `python-dotenv` for easy configuration management.

## Prerequisites

Before you begin, ensure you have the following installed and configured:

- **Python:** Version 3.8 or higher.
- **Git:** For cloning repositories.
- **Docker:** Required to run the official GitHub MCP server. Ensure the Docker daemon is running.
- **Node.js and npm:** Required to build and run the GitHub Actions MCP server.
- **Anthropic API Key:** Obtain from the [Anthropic Console](https://console.anthropic.com/settings/keys).
- **GitHub Personal Access Token (PAT):** Create one from [GitHub Tokens settings](https://github.com/settings/tokens). Grant it appropriate scopes (e.g., `repo`, `workflow`) depending on the tools you need Claude to use.
- **Local Clone of `github-actions-mcp-server`:** You need to clone the [github/github-actions-mcp-server](https://github.com/github/github-actions-mcp-server) repository separately and build it.

## Setup

1.  **Clone this repository:**

    ```bash
    git clone <your-repository-url> # Replace with the URL after you create it on GitHub
    cd github-multi-mcp-client
    ```

2.  **Clone and build the Actions MCP Server:**
    (If you haven't already done so)

    ```bash
    # Navigate to where you want to store the actions server project
    cd ..
    git clone https://github.com/github/github-actions-mcp-server.git
    cd github-actions-mcp-server
    npm install
    npm run build
    # Note the full path to the generated dist/index.js file
    cd ../github-multi-mcp-client # Navigate back to this project
    ```

3.  **Create and activate a virtual environment:**

    ```bash
    # Recommended: Create a virtual environment
    python -m venv venv

    # Activate the virtual environment
    # On Windows:
    # .\venv\Scripts\activate
    # On Linux/macOS:
    # source venv/bin/activate
    ```

4.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

5.  **Configure environment variables:**
    - Copy the example file: `cp .env.example .env` (or `copy .env.example .env` on Windows).
    - Edit the `.env` file with your actual credentials and **the correct full path** to the `index.js` file of your built `github-actions-mcp-server`.
      ```dotenv
      ANTHROPIC_API_KEY=your_anthropic_api_key_here
      GITHUB_PERSONAL_ACCESS_TOKEN=your_github_pat_here
      ACTIONS_SERVER_SCRIPT_PATH=/full/path/to/your/github-actions-mcp-server/dist/index.js
      # CLAUDE_MODEL_NAME=claude-3-5-sonnet-20240620 # Optional
      ```
    - **Important:** Ensure `ACTIONS_SERVER_SCRIPT_PATH` is the correct _absolute_ path. The client will fail to start the Actions server if this path is wrong.

## Running the Client

Ensure Docker daemon is running and your virtual environment is activated. Then run:

```bash
python client.py
```
