"""
Expose key BetterTouchTool scripting commands as MCP tools.

Start the server with:
    pip install -r requirements.txt
    python direct_runner.py    # or: python server.py
"""

import json
import os
import subprocess
import urllib.parse
import sys
import logging
from typing import List, Optional

from fastmcp import FastMCP, Context
from pydantic import Field

# Set up logging to stderr for Claude Desktop to capture
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("btt_server")

# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------

BTT_SHARED_SECRET: str = os.getenv("BTT_SHARED_SECRET", "")
mcp = FastMCP("BTTBridge")

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------


def _build_btt_url(function: str, params: dict[str, str]) -> str:
    """Return a fully-formed btt:// URL, including shared-secret if set."""
    if BTT_SHARED_SECRET:
        params["shared_secret"] = BTT_SHARED_SECRET
    query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    return f"btt://{function}/?{query}"


def _open(url: str) -> None:
    """macOS-style 'open' on the custom URL scheme."""
    logger.info(f"Opening URL: {url}")
    try:
        subprocess.run(["open", url], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error opening URL: {e}")
        raise


def _osascript(source: str) -> str:
    """Run AppleScript, capture stdout."""
    logger.info(f"Running AppleScript: {source[:50]}...")
    try:
        return subprocess.check_output(["osascript", "-e", source], text=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running AppleScript: {e}")
        raise


# ----------------------------------------------------------------------
# MCP tools
# ----------------------------------------------------------------------


@mcp.tool()
def add_btt_trigger(trigger_json: str, ctx: Context = None) -> str:
    """
    Create a brand-new BTT trigger.
    
    Args:
        trigger_json: Full JSON definition of a BTT trigger (e.g. as copied via BTT → 'Copy JSON').
    """
    if ctx:
        ctx.info(f"Adding new trigger: {trigger_json[:50]}...")
        
    logger.info(f"Adding new BTT trigger: {trigger_json[:50]}...")
    _open(_build_btt_url("add_new_trigger", {"json": trigger_json}))
    return "Trigger added successfully."


@mcp.tool()
def update_btt_trigger(uuid: str, patch_json: str, ctx: Context = None) -> str:
    """
    Update an existing trigger identified by its UUID.
    
    Args:
        uuid: UUID of the existing trigger
        patch_json: JSON patch with the fields you want to change.
    """
    if ctx:
        ctx.info(f"Updating trigger {uuid} with patch: {patch_json[:50]}...")
        
    logger.info(f"Updating BTT trigger {uuid} with patch: {patch_json[:50]}...")
    _open(
        _build_btt_url(
            "update_trigger",
            {"uuid": uuid, "json": patch_json},
        )
    )
    return "Trigger updated."


@mcp.tool()
def delete_btt_trigger(uuid: str, ctx: Context = None) -> str:
    """
    Delete a trigger by UUID.
    
    Args:
        uuid: UUID of the trigger to delete
    """
    if ctx:
        ctx.info(f"Deleting trigger {uuid}...")
        
    logger.info(f"Deleting BTT trigger {uuid}")
    _open(_build_btt_url("delete_trigger", {"uuid": uuid}))
    return "Trigger deleted."


@mcp.tool()
def list_btt_triggers(app_bundle_id: Optional[str] = None, ctx: Context = None) -> List[dict]:
    """
    Return the current trigger list as JSON.

    Args:
        app_bundle_id: If supplied, the list is filtered to that bundle id.
    """
    if ctx:
        ctx.info(f"Listing BTT triggers {f'for app: {app_bundle_id}' if app_bundle_id else ''}")
        
    logger.info(f"Listing BTT triggers {f'for app: {app_bundle_id}' if app_bundle_id else ''}")
    raw = _osascript('tell application "BetterTouchTool" to get_triggers')
    triggers = json.loads(raw)  # BTT returns valid JSON
    
    if app_bundle_id:
        triggers = [
            t for t in triggers if t.get("BTTAppBundleIdentifier") == app_bundle_id
        ]
    
    logger.info(f"Found {len(triggers)} triggers")
    return triggers


if __name__ == "__main__":
    # Set explicit log message so Claude can see the error messages
    logger.info("Starting BTT MCP Bridge server directly...")
    # Run over stdio so Claude Desktop and similar clients can spawn it locally.
    try:
        mcp.run()
    except Exception as e:
        logger.error(f"Error running MCP server: {e}", exc_info=True)
        sys.exit(1)
