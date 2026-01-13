"""
Smart BetterTouchTool bridge with minimal changes from server.py.
"""

import json
import os
import subprocess
import urllib.parse
import sys
import logging
from typing import List, Dict, Any, Union

from fastmcp import FastMCP, Context
from pydantic import Field

# Set up logging to stderr for Claude Desktop to capture
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("basic_smart_bridge")

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------

# macOS virtual key codes (just a few examples)
VK_CODES = {
    "a": 0, "b": 11, "c": 8, "d": 2, "e": 14, "f": 3,
    "space": 49, "return": 36, "escape": 53,
    "left": 123, "right": 124, "up": 126, "down": 125,
}

# Modifier masks
MODIFIER_MASK = {
    "shift": 131072,
    "ctrl": 262144,
    "control": 262144,
    "opt": 524288,
    "alt": 524288,
    "cmd": 1048576,
    "command": 1048576,
}

# Modifier keycodes
MODIFIER_KEYCODE = {
    "shift": 56,
    "ctrl": 59,
    "control": 59,
    "opt": 58,
    "alt": 58,
    "cmd": 55,
    "command": 55,
}

# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------

BTT_SHARED_SECRET: str = os.getenv("BTT_SHARED_SECRET", "")
mcp = FastMCP("SmartBTT")

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
    logger.info(f"Opening URL: {url[:50]}...")
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


def _split_combo(combo: str) -> tuple[list[str], str]:
    """Return (modifiers, key) from a combo like "ctrl+shift+k"."""
    parts = combo.lower().replace(" ", "").split("+")
    mods = [p for p in parts if p in MODIFIER_MASK]
    keys = [p for p in parts if p not in MODIFIER_MASK]
    if len(keys) != 1:
        raise ValueError(f"Invalid key combo '{combo}' – could not determine the main key")
    return mods, keys[0]


# ----------------------------------------------------------------------
# MCP tools
# ----------------------------------------------------------------------


@mcp.tool()
def add_hotkey(
    trigger: str,
    send_keys: Union[str, None] = None,
    predefined_action: Union[str, None] = None,
    script: Union[str, None] = None,
    ctx: Union[Context, None] = None
) -> str:
    """Create a keyboard shortcut trigger with either `send_keys` or a simple predefined action.
    
    Args:
        trigger: Keyboard shortcut that activates the trigger, e.g. "shift+cmd+k"
        send_keys: Keys to send when triggered, e.g. "ctrl+right"; mutually exclusive with predefined_action
        predefined_action: One of: move_right_space, move_left_space, run_script
        script: Shell or AppleScript when predefined_action == 'run_script'
    """
    
    # Log the raw values for debugging
    logger.debug(f"add_hotkey raw values: trigger={trigger!r}, send_keys={send_keys!r}, predefined_action={predefined_action!r}, script={script!r}")
    
    # Simple validation: exactly one of send_keys or predefined_action must be provided
    has_send_keys = send_keys is not None
    has_predefined = predefined_action is not None
    
    logger.debug(f"Has send_keys: {has_send_keys}, Has predefined: {has_predefined}")
    
    if not (has_send_keys ^ has_predefined):  # XOR operator
        raise ValueError("Specify exactly one of send_keys or predefined_action")

    if ctx:
        ctx.info(f"Adding hotkey trigger: {trigger}")
    
    logger.info(f"Adding hotkey trigger: {trigger}")

    # Parse trigger (what user presses)
    mods, key = _split_combo(trigger)

    # Build the trigger JSON
    trigger_json = {
        "BTTTriggerBelongsToPreset": "Default",
        "BTTActionCategory": 0,
        "BTTUUID": os.urandom(16).hex().upper(),
        "BTTTriggerType": 0,
        "BTTTriggerClass": "BTTTriggerTypeKeyboardShortcut",
        "BTTKeyboardShortcutKeyboardType": 0,
        "BTTTriggerOnDown": 1,
        "BTTLayoutIndependentChar": key,
        "BTTShortcutKeyCode": VK_CODES.get(key, 0),
        "BTTShortcutModifierKeys": sum(MODIFIER_MASK[m] for m in mods),
        "BTTEnabled": 1,
        "BTTEnabled2": 1,
        "BTTAutoAdaptToKeyboardLayout": 0,
        "BTTBelongsToApp": "Global",
    }

    # Action
    if has_send_keys:
        # Parse send_keys to get modifiers and key
        a_mods, a_key = _split_combo(send_keys)
        
        # For shortcut to send, we need a different format
        if len(a_mods) == 0:
            shortcut_to_send = f"{VK_CODES.get(a_key, 0)}"
        else:
            mod_keycode = MODIFIER_KEYCODE[a_mods[0]]
            shortcut_to_send = f"{mod_keycode},{VK_CODES.get(a_key, 0)}"
            
        trigger_json.update({
            "BTTPredefinedActionType": 110,  # "Send Shortcut"
            "BTTPredefinedActionName": "Send Shortcut",
            "BTTShortcutToSend": shortcut_to_send,
        })
    else:
        if predefined_action == "move_right_space":
            trigger_json.update({
                "BTTPredefinedActionType": 114,
                "BTTPredefinedActionName": "Move Right a Space",
            })
        elif predefined_action == "move_left_space":
            trigger_json.update({
                "BTTPredefinedActionType": 113,
                "BTTPredefinedActionName": "Move Left a Space",
            })
        elif predefined_action == "run_script":
            if not script:
                raise ValueError("'script' must be provided when predefined_action == 'run_script'")
            trigger_json.update({
                "BTTPredefinedActionType": 206,  # Execute Shell Script or Task
                "BTTPredefinedActionName": "Execute Shell Script  or  Task",
                "BTTShellTaskActionScript": script,
                "BTTShellTaskActionConfig": "/bin/bash:::-c:::-:::",
            })
        else:
            raise ValueError(f"Unsupported predefined_action: {predefined_action}")

    # Send to BTT
    json_payload = json.dumps(trigger_json, ensure_ascii=False)
    _open(_build_btt_url("add_new_trigger", {"json": json_payload}))
    return f"Trigger {trigger_json['BTTUUID']} added"


@mcp.tool()
def list_triggers(ctx: Union[Context, None] = None) -> List[Dict[str, Any]]:
    """Return the current BTT trigger list."""
    if ctx:
        ctx.info("Listing all BTT triggers")
    
    logger.info("Listing all BTT triggers")
    raw = _osascript('tell application "BetterTouchTool" to get_triggers')
    triggers = json.loads(raw)
    logger.info(f"Found {len(triggers)} triggers")
    return triggers


@mcp.tool()
def delete_trigger(uuid: str, ctx: Union[Context, None] = None) -> str:
    """Delete a trigger by UUID."""
    if ctx:
        ctx.info(f"Deleting trigger {uuid}")
    
    logger.info(f"Deleting trigger {uuid}")
    _open(_build_btt_url("delete_trigger", {"uuid": uuid}))
    return f"Trigger {uuid} deleted"


if __name__ == "__main__":
    # Set explicit log message so Claude can see the error messages
    logger.info("Starting Basic Smart BTT Bridge...")
    # Run over stdio so Claude Desktop and similar clients can spawn it locally.
    try:
        mcp.run()
    except Exception as e:
        logger.error(f"Error running MCP server: {e}", exc_info=True)
        sys.exit(1) 