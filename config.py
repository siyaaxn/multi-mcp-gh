import os
import sys
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists
load_dotenv()

print("Loading configuration...")
# --- Anthropic API Key ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    print("Error: ANTHROPIC_API_KEY not found in environment variables or .env file.")
    print("Please add it to your .env file.")
    sys.exit(1)

# --- GitHub Personal Access Token ---
GITHUB_TOKEN = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
if not GITHUB_TOKEN:
    print("Error: GITHUB_PERSONAL_ACCESS_TOKEN not found in environment variables or .env file.")
    print("Please add it to your .env file.")
    sys.exit(1)

# --- GitHub Actions MCP Server Script Path ---
# IMPORTANT: This needs to be the FULL path to the compiled JS file
# Example: /home/user/projects/github-actions-mcp-server/dist/index.js
# Example: C:\Users\user\Documents\github-actions-mcp-server\dist\index.js
ACTIONS_SERVER_SCRIPT_PATH = os.getenv("ACTIONS_SERVER_SCRIPT_PATH")
if not ACTIONS_SERVER_SCRIPT_PATH:
    print("Error: ACTIONS_SERVER_SCRIPT_PATH not found in environment variables or .env file.")
    print("Please define the full path to the github-actions-mcp-server/dist/index.js script.")
    print("Example (Linux/macOS): ACTIONS_SERVER_SCRIPT_PATH=/path/to/github-actions-mcp-server/dist/index.js")
    print("Example (Windows): ACTIONS_SERVER_SCRIPT_PATH=C:\\path\\to\\github-actions-mcp-server\\dist\\index.js")
    sys.exit(1)
elif not os.path.isfile(ACTIONS_SERVER_SCRIPT_PATH):
     print(f"Error: ACTIONS_SERVER_SCRIPT_PATH points to a non-existent file:")
     print(f"  Path: {ACTIONS_SERVER_SCRIPT_PATH}")
     print("Please ensure the path is correct and the Actions server has been built (`npm run build`).")
     sys.exit(1)

# --- Claude Model Name ---
CLAUDE_MODEL_NAME = os.getenv("CLAUDE_MODEL_NAME", "claude-3-5-sonnet-20240620")

print("Configuration loaded successfully.")
print(f" - Anthropic Key: {'Loaded'}")
print(f" - GitHub Token: {'Loaded'}")
print(f" - Actions Server Path: {ACTIONS_SERVER_SCRIPT_PATH}")
print(f" - Claude Model: {CLAUDE_MODEL_NAME}")