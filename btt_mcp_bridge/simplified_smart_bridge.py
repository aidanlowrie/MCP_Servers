#!/usr/bin/env python3
"""
Simplified Smart BetterTouchTool ↔ MCP bridge
==============================================
A version of the smart bridge without Context parameters to avoid import issues.
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid
import urllib.parse
import sys
import logging
import traceback

from fastmcp import FastMCP
from pydantic import Field

# Set up logging to stderr for Claude Desktop to capture
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("simplified_smart_bridge")

# Log Python version and module paths to help with debugging
logger.debug(f"Python version: {sys.version}")
logger.debug(f"Sys path: {sys.path}")
logger.debug(f"Starting Simplified Smart BTT Bridge initialization")

###############################################################################
# 1.  CONSTANTS & LOOK-UP TABLES                                              #
###############################################################################
# macOS virtual key codes (incomplete but covers common keys)
VK_CODES = {
    # letters
    **{chr(i): code for i, code in zip(range(ord("a"), ord("z") + 1), (
        0, 11, 8, 2, 14, 3, 5, 4, 34, 38, 40, 37, 46, 45, 31, 35, 12, 15,
        1, 17, 32, 9, 13, 7, 16, 6))},
    # digits
    **{str(i): code for i, code in zip(range(10), (18, 19, 20, 21, 23, 22, 26, 28, 25, 29))},
    # arrows
    "left": 123,
    "right": 124,
    "down": 125,
    "up": 126,
    # misc
    "return": 36,
    "enter": 76,
    "escape": 53,
    "space": 49,
    "tab": 48,
    "delete": 51,
}

# CGEventFlags bit-masks (what BTT uses in BTTShortcutModifierKeys)
MODIFIER_MASK = {
    "shift": 1 << 17,      # 131072
    "ctrl": 1 << 18,       # 262144
    "control": 1 << 18,
    "opt": 1 << 19,        # 524288
    "alt": 1 << 19,
    "cmd": 1 << 20,        # 1048576
    "command": 1 << 20,
    "fn": 1 << 23,         # 8388608 – rarely needed
}

# For BTTShortcutToSend we need the *key code* of ONE modifier key.  We pick the
# **left** variants – they're enough for 99 % of cases.
MODIFIER_KEYCODE = {
    "shift": 56,
    "ctrl": 59,
    "control": 59,
    "opt": 58,
    "alt": 58,
    "cmd": 55,
    "command": 55,
}

###############################################################################
# 2.  LOW-LEVEL HELPERS                                                       #
###############################################################################

BTT_SHARED_SECRET: str = os.getenv("BTT_SHARED_SECRET", "")
logger.debug(f"BTT_SHARED_SECRET is {'set' if BTT_SHARED_SECRET else 'not set'}")


def _build_btt_url(func: str, params: dict[str, str]) -> str:
    """Return a fully-formed btt:// URL, including shared-secret if set."""
    if BTT_SHARED_SECRET:
        params["shared_secret"] = BTT_SHARED_SECRET
    query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    url = f"btt://{func}/?{query}"
    logger.debug(f"Built BTT URL: {url[:50]}...")
    return url


def _open(url: str) -> None:
    """macOS-style 'open' on the custom URL scheme."""
    logger.info(f"Opening URL: {url[:50]}...")
    try:
        subprocess.run(["open", url], check=True)
        logger.debug("URL opened successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error opening URL: {e}")
        logger.error(f"Command output: {e.output if hasattr(e, 'output') else 'No output'}")
        raise


def _osascript(cmd: str) -> str:
    """Run AppleScript, capture stdout."""
    logger.info(f"Running AppleScript: {cmd[:50]}...")
    try:
        output = subprocess.check_output(["osascript", "-e", cmd], text=True)
        logger.debug(f"AppleScript output: {output[:100]}...")
        return output
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running AppleScript: {e}")
        logger.error(f"Command output: {e.output if hasattr(e, 'output') else 'No output'}")
        raise


###############################################################################
# 3.  PARSERS – HUMAN → BTT                                                   #
###############################################################################

def _split_combo(combo: str) -> tuple[list[str], str]:
    """Return (modifiers, key) from a combo like "ctrl+shift+k"."""
    logger.debug(f"Splitting key combo: {combo}")
    parts = combo.lower().replace(" ", "").split("+")
    mods = [p for p in parts if p in MODIFIER_MASK]
    keys = [p for p in parts if p not in MODIFIER_MASK]
    if len(keys) != 1:
        logger.error(f"Invalid key combo: {combo}, parts: {parts}, mods: {mods}, keys: {keys}")
        raise ValueError(f"Invalid key combo '{combo}' – could not determine the main key")
    logger.debug(f"Split result - modifiers: {mods}, key: {keys[0]}")
    return mods, keys[0]


def to_keycode(key: str) -> int:
    logger.debug(f"Converting key to keycode: {key}")
    if key in VK_CODES:
        keycode = VK_CODES[key]
        logger.debug(f"Key {key} mapped to keycode {keycode}")
        return keycode
    logger.error(f"Unsupported key: {key}")
    raise ValueError(f"Unsupported key '{key}' – add it to VK_CODES if needed")


def to_modifier_mask(mods: list[str]) -> int:
    logger.debug(f"Converting modifiers to mask: {mods}")
    mask = sum(MODIFIER_MASK[m] for m in mods)
    logger.debug(f"Modifiers {mods} mapped to mask {mask}")
    return mask


def to_shortcut_send(mods: list[str], key: str) -> str:
    logger.debug(f"Converting to shortcut send format - modifiers: {mods}, key: {key}")
    if len(mods) == 0:
        result = f"{to_keycode(key)}"
        logger.debug(f"No modifiers, shortcut: {result}")
        return result
    # Pick first modifier for the modifier keycode (left variant)
    mod_keycode = MODIFIER_KEYCODE[mods[0]]
    result = f"{mod_keycode},{to_keycode(key)}"
    logger.debug(f"With modifiers, shortcut: {result}")
    return result

###############################################################################
# 5.  MCP SERVER & TOOLS                                                      #
###############################################################################

logger.debug("Creating FastMCP instance")
mcp = FastMCP("SimplifiedSmartBTT")
logger.debug("FastMCP instance created successfully")


@mcp.tool()
def add_hotkey(
    trigger: str,
    send_keys = None,
    predefined_action = None,
    script = None,
) -> str:
    """Create a keyboard shortcut trigger with either `send_keys` or a simple predefined action.
    
    Args:
        trigger: Keyboard shortcut that activates the trigger, e.g. "shift+cmd+k"
        send_keys: Keys to send when triggered, e.g. "ctrl+right"; mutually exclusive with predefined_action
        predefined_action: One of: move_right_space, move_left_space, run_script
        script: Shell or AppleScript when predefined_action == 'run_script'
    """
    
    # Log the raw values for debugging
    logger.debug(f"add_hotkey raw values: trigger={trigger!r}, send_keys={send_keys!r}, predefined_action={predefined_action!r}, script={repr(script) if script else None}")
    
    # Simple validation: exactly one of send_keys or predefined_action must be provided
    has_send_keys = send_keys is not None
    has_predefined = predefined_action is not None
    
    logger.debug(f"Has send_keys: {has_send_keys}, Has predefined: {has_predefined}")
    
    if not (has_send_keys ^ has_predefined):  # XOR operator
        logger.error(f"Validation error: Both or neither of send_keys and predefined_action were provided")
        raise ValueError("Specify exactly one of send_keys or predefined_action")

    logger.info(f"Adding hotkey trigger: {trigger} -> {'sending keys: ' + send_keys if send_keys else 'action: ' + predefined_action}")

    # Parse trigger (what user presses)
    try:
        mods, key = _split_combo(trigger)
    except ValueError as e:
        logger.error(f"Error parsing trigger: {e}")
        logger.error(traceback.format_exc())
        raise

    trigger_json = {
        "BTTTriggerBelongsToPreset": "Default",
        "BTTActionCategory": 0,
        "BTTUUID": str(uuid.uuid4()).upper(),
        "BTTTriggerType": 0,
        "BTTTriggerClass": "BTTTriggerTypeKeyboardShortcut",
        "BTTKeyboardShortcutKeyboardType": 0,
        "BTTTriggerOnDown": 1,
        "BTTLayoutIndependentChar": key,
        "BTTShortcutKeyCode": to_keycode(key),
        "BTTShortcutModifierKeys": to_modifier_mask(mods),
        "BTTEnabled": 1,
        "BTTEnabled2": 1,
        "BTTAutoAdaptToKeyboardLayout": 0,
        "BTTBelongsToApp": "Global",
    }

    # Action
    if has_send_keys:
        try:
            a_mods, a_key = _split_combo(send_keys)
        except ValueError as e:
            logger.error(f"Error parsing send_keys: {e}")
            logger.error(traceback.format_exc())
            raise
            
        trigger_json.update({
            "BTTPredefinedActionType": 110,  # "Send Shortcut"
            "BTTPredefinedActionName": "Send Shortcut",
            "BTTShortcutToSend": to_shortcut_send(a_mods, a_key),
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
                logger.error("Missing script for run_script action")
                raise ValueError("'script' must be provided when predefined_action == 'run_script'")
            trigger_json.update({
                "BTTPredefinedActionType": 206,  # Execute Shell Script or Task
                "BTTPredefinedActionName": "Execute Shell Script  or  Task",
                "BTTShellTaskActionScript": script,
                "BTTShellTaskActionConfig": "/bin/bash:::-c:::-:::",
            })
        else:
            logger.error(f"Unsupported predefined_action: {predefined_action}")
            raise ValueError(f"Unsupported predefined_action: {predefined_action}")

    # Send to BTT
    try:
        json_payload = json.dumps(trigger_json, ensure_ascii=False)
        logger.debug(f"Trigger JSON: {json_payload[:100]}...")
        _open(_build_btt_url("add_new_trigger", {"json": json_payload}))
        return f"Trigger {trigger_json['BTTUUID']} added"
    except Exception as e:
        logger.error(f"Error adding trigger: {e}")
        logger.error(traceback.format_exc())
        raise


@mcp.tool()
def list_triggers() -> list:
    """Return the current BTT trigger list."""
    logger.debug("list_triggers called")
    
    logger.info("Listing all BTT triggers")
    try:
        raw = _osascript('tell application "BetterTouchTool" to get_triggers')
        triggers = json.loads(raw)
        logger.debug(f"Found {len(triggers)} triggers")
        return triggers
    except Exception as e:
        logger.error(f"Error listing triggers: {e}")
        logger.error(traceback.format_exc())
        raise


@mcp.tool()
def delete_trigger(uuid: str) -> str:
    """Delete a trigger by UUID."""
    logger.debug(f"delete_trigger called with uuid={uuid}")
    
    logger.info(f"Deleting trigger {uuid}")
    try:
        _open(_build_btt_url("delete_trigger", {"uuid": uuid}))
        return f"Trigger {uuid} deleted"
    except Exception as e:
        logger.error(f"Error deleting trigger: {e}")
        logger.error(traceback.format_exc())
        raise


# Also provide the original low-level tools for backward compatibility
@mcp.tool()
def add_btt_trigger(trigger_json: str) -> str:
    """
    Create a brand-new BTT trigger using raw JSON.
    
    Args:
        trigger_json: Full JSON definition of a BTT trigger (e.g. as copied via BTT → 'Copy JSON').
    """
    logger.debug(f"add_btt_trigger called with raw JSON")
        
    logger.info(f"Adding new BTT trigger with raw JSON: {trigger_json[:50]}...")
    try:
        _open(_build_btt_url("add_new_trigger", {"json": trigger_json}))
        return "Trigger added successfully."
    except Exception as e:
        logger.error(f"Error adding trigger with raw JSON: {e}")
        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    # Set explicit log message so Claude can see the error messages
    logger.info("Starting Simplified Smart BTT MCP Bridge...")
    # Run over stdio so Claude Desktop and similar clients can spawn it locally.
    try:
        logger.debug("Attempting to run MCP server")
        mcp.run()
    except Exception as e:
        logger.error(f"Error running MCP server: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1) 