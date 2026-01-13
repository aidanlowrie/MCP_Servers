#!/usr/bin/env python3
"""
Thoughts MCP Server

This script implements a Model Context Protocol (MCP) server that allows Claude
to interact with the thoughts embedding and search functionality.

Usage:
    python mcp_server.py
"""

import os
import sys
import json
import logging
import argparse
import datetime
import math
import re
import sqlite3
import time
from typing import List, Dict, Any, Optional, Tuple, Union, Set, Iterable
from pathlib import Path

# Import FastMCP
try:
    from mcp.server.fastmcp import FastMCP, Context
    _MCP_AVAILABLE = True
except Exception:
    _MCP_AVAILABLE = False
    class _DummyContext:
        def info(self, *_args, **_kwargs):
            pass
    class _DummyMCP:
        def __init__(self, *_args, **_kwargs):
            pass
        def tool(self, *_args, **_kwargs):
            def deco(fn):
                return fn
            return deco
        def resource(self, *_args, **_kwargs):
            def deco(fn):
                return fn
            return deco
        def run(self):
            pass
    FastMCP = _DummyMCP  # type: ignore
    Context = _DummyContext  # type: ignore

# Import thought embedding functionality (tolerate missing deps when only SR tools are used)
try:
    # Prefer package-relative when imported as a module
    from .build_embeddings import embed_text  # type: ignore
    from .search_thoughts import search_thoughts, load_embeddings, cosine_similarity, get_document_content  # type: ignore
except Exception:
    try:
        # Fallback to same-dir absolute imports when run directly
        from build_embeddings import embed_text  # type: ignore
        from search_thoughts import search_thoughts, load_embeddings, cosine_similarity, get_document_content  # type: ignore
    except Exception:
        # Provide no-op stubs so SR tools can be imported without embedding deps
        def embed_text(_text: str):
            return []
        def load_embeddings(_path: str):
            return []
        def cosine_similarity(_a, _b) -> float:
            return 0.0
        def get_document_content(path: str) -> str:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception:
                return ''
        class _SearchThoughtsStub:
            @staticmethod
            def search_thoughts(query: str, max_results: int = 5, use_titles: bool = False):
                return []
        search_thoughts = _SearchThoughtsStub()  # type: ignore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("thoughts_mcp")

# Constants
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BODY_EMBEDDINGS_FILE = os.path.join(SCRIPT_DIR, "thought_embeddings.csv")
TITLE_EMBEDDINGS_FILE = os.path.join(SCRIPT_DIR, "title_embeddings.csv")
THOUGHTS_DIR = "/Users/aidanlowrie/Library/Mobile Documents/iCloud~md~obsidian/Documents/My Brain/1 - Thoughts"
VAULT_ROOT = Path(THOUGHTS_DIR).resolve().parent

# Create FastMCP server
mcp = FastMCP("Thoughts Assistant")

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------

def _ensure_embeddings_exist() -> bool:
    """Check if embedding files exist, return True if they do."""
    title_exists = Path(TITLE_EMBEDDINGS_FILE).exists()
    body_exists = Path(BODY_EMBEDDINGS_FILE).exists()
    
    if not title_exists or not body_exists:
        logger.warning(f"Embedding files missing: title={title_exists}, body={body_exists}")
        return False
    return True

# ----------------------------------------------------------------------
# MCP tools
# ----------------------------------------------------------------------

@mcp.tool()
def build_thought_embeddings(ctx: Context = None) -> str:
    """
    Build embeddings for all markdown files in the thoughts directory.
    This can take a few minutes depending on the number of files.
    """
    if ctx:
        ctx.info("Building thought embeddings...")
    
    logger.info("Building thought embeddings...")
    
    try:
        # Import here to avoid circular imports
        import build_embeddings
        
        # Set the output file paths in build_embeddings
        build_embeddings.TITLE_EMBEDDINGS_FILE = TITLE_EMBEDDINGS_FILE
        build_embeddings.BODY_EMBEDDINGS_FILE = BODY_EMBEDDINGS_FILE
        
        # Run the build_embeddings main function
        build_embeddings.main()
        
        return "Thought embeddings built successfully"
    except PermissionError as e:
        error_msg = f"Permission error: {str(e)}. Please run the build_embeddings.py script manually from the terminal."
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error building embeddings: {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
def search_by_content(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search thoughts by content using semantic similarity.
    
    Args:
        query: The search query
        max_results: Maximum number of results to return (default: 5)
        
    Returns:
        List of matching thoughts with path, title, similarity score, and snippet
    """
    # Check if embeddings exist
    if not os.path.exists(BODY_EMBEDDINGS_FILE):
        return {"error": "Embedding files not found. Please run build_thought_embeddings first."}
    
    try:
        # Import locally to avoid circular imports
        import search_thoughts
        
        # Set the file paths in search_thoughts
        search_thoughts.BODY_EMBEDDINGS_FILE = BODY_EMBEDDINGS_FILE
        search_thoughts.TITLE_EMBEDDINGS_FILE = TITLE_EMBEDDINGS_FILE
        
        # Call the search_thoughts function with correct parameters
        results = search_thoughts.search_thoughts(
            query=query,
            max_results=max_results,
            use_titles=False
        )
        
        # Format the results with content
        formatted_results = []
        for file_path, similarity in results:
            content = search_thoughts.get_document_content(file_path)
            
            # Try to extract the title from the content
            title = Path(file_path).stem
            content_lines = content.split('\n')
            if content_lines and content_lines[0].startswith('#'):
                title = content_lines[0].lstrip('#').strip()
                
            # Create a snippet (first 200 characters)
            snippet = content[:200] + "..." if len(content) > 200 else content
            
            formatted_results.append({
                "path": file_path,
                "title": title,
                "similarity": similarity,
                "snippet": snippet,
                "content": content
            })
        
        return formatted_results
    except Exception as e:
        logger.error(f"Error in search_by_content: {e}")
        return [{"error": str(e)}]


@mcp.tool()
def search_by_title(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search thoughts by title using semantic similarity.
    
    Args:
        query: The search query
        max_results: Maximum number of results to return (default: 5)
        
    Returns:
        List of matching thoughts with path, title, and similarity score
    """
    # Check if embeddings exist
    if not os.path.exists(TITLE_EMBEDDINGS_FILE):
        return {"error": "Embedding files not found. Please run build_thought_embeddings first."}
    
    try:
        # Import locally to avoid circular imports
        import search_thoughts
        
        # Set the file paths in search_thoughts
        search_thoughts.BODY_EMBEDDINGS_FILE = BODY_EMBEDDINGS_FILE
        search_thoughts.TITLE_EMBEDDINGS_FILE = TITLE_EMBEDDINGS_FILE
        
        # Call the search_thoughts function with correct parameters
        results = search_thoughts.search_thoughts(
            query=query,
            max_results=max_results,
            use_titles=True
        )
        
        # Format the results
        formatted_results = []
        for file_path, similarity in results:
            content = search_thoughts.get_document_content(file_path)
            
            # Try to extract the title from the content
            title = Path(file_path).stem
            content_lines = content.split('\n')
            if content_lines and content_lines[0].startswith('#'):
                title = content_lines[0].lstrip('#').strip()
            
            formatted_results.append({
                "path": file_path,
                "title": title,
                "similarity": similarity
            })
        
        return formatted_results
    except Exception as e:
        logger.error(f"Error in search_by_title: {e}")
        return [{"error": str(e)}]


@mcp.tool()
def get_thought_content(file_path: str, ctx: Context = None) -> str:
    """
    Get the full content of a specific thought file.
    
    Args:
        file_path: The path to the thought file
    
    Returns:
        The content of the thought file
    """
    if ctx:
        ctx.info(f"Getting content for: {file_path}")
    
    logger.info(f"Getting content for: {file_path}")
    
    try:
        content = get_document_content(file_path)
        return content
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return f"Error: Could not read file {file_path}"


@mcp.tool()
def compare_thoughts(thought1_path: str, thought2_path: str, ctx: Context = None) -> Dict[str, Any]:
    """
    Compare two thoughts and calculate their semantic similarity.
    
    Args:
        thought1_path: Path to the first thought file
        thought2_path: Path to the second thought file
    
    Returns:
        Dictionary with similarity score and contents of both thoughts
    """
    if ctx:
        ctx.info(f"Comparing thoughts: {thought1_path} and {thought2_path}")
    
    logger.info(f"Comparing thoughts: {thought1_path} and {thought2_path}")
    
    try:
        # Get content of both thoughts
        content1 = get_document_content(thought1_path)
        content2 = get_document_content(thought2_path)
        
        # Generate embeddings for both thoughts
        embedding1 = embed_text(content1)
        embedding2 = embed_text(content2)
        
        # Calculate similarity
        similarity = cosine_similarity(embedding1, embedding2)
        
        return {
            "similarity": similarity,
            "thought1": {
                "path": thought1_path,
                "content": content1
            },
            "thought2": {
                "path": thought2_path,
                "content": content2
            }
        }
    except Exception as e:
        logger.error(f"Error comparing thoughts: {e}")
        return {"error": str(e)}


@mcp.tool()
def list_recent_thoughts(limit: int = 5, ctx: Context = None) -> List[Dict[str, Any]]:
    """
    List the most recently modified thought files.
    
    Args:
        limit: Maximum number of thoughts to return (default: 5)
    
    Returns:
        List of recent thoughts with path and modification time
    """
    if ctx:
        ctx.info(f"Listing {limit} recent thoughts")
    
    logger.info(f"Listing {limit} recent thoughts")
    
    # Get all markdown files in the thoughts directory
    md_files = list(Path(THOUGHTS_DIR).glob("**/*.md"))
    
    # Sort by modification time (newest first)
    md_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    # Limit the results
    md_files = md_files[:limit]
    
    # Format the results
    results = []
    for file_path in md_files:
        mtime = file_path.stat().st_mtime
        content = get_document_content(file_path)
        
        # Try to extract the title from the content
        title = file_path.stem
        content_lines = content.split('\n')
        if content_lines and content_lines[0].startswith('#'):
            title = content_lines[0].lstrip('#').strip()
        
        results.append({
            "path": str(file_path),
            "title": title,
            "modified_timestamp": mtime,
            "content": content
        })
    
    return results


@mcp.tool()
def write_note(content: str, title: str = None, frontmatter: Dict[str, Any] = None, folder_path: str = None, ctx: Context = None) -> Dict[str, Any]:
    """
    Write a new note to the Obsidian vault.
    
    IMPORTANT GUIDELINES:
    1. DO NOT include 'tags' or 'topics' in the frontmatter.
       These will be handled by other systems.
    2. Follow the "Atomic Notes" philosophy - one note should contain one main idea or concept.
    3. Focus purely on ideas and concepts - never reference "the author" or attribute thoughts to anyone.
       Write directly about the concepts themselves without mentioning who is thinking them.
    4. Use Obsidian links to reference other notes rather than duplicating content:
       - Internal links: [[Note Title]] or [[Note Title|Display Text]]
       - Section links: [[Note Title#Section]]
    5. Use British English (spellings) at all times.
    6. Create clear, concise titles that follow good naming conventions:
       - Use specific, descriptive titles with capitalized words and spaces (e.g., "Spaced Repetition")
       - Titles should use spaces between words, not dashes (e.g., "Cats are Despicable Creatures" not "Cats-are-Despicable-Creatures")
       - Avoid vague titles like "Thoughts" or "Notes"
       - Good examples: "Spaced Repetition", "Decision Making Framework", "Cognitive Biases"
    7. ALWAYS repeat the full note content in your chat response after creating the note.
    
    Args:
        content: The main body content of the note (markdown)
        title: The title for the note (also used for filename)
        frontmatter: Optional dictionary of frontmatter properties to include
        folder_path: Optional folder path within the vault (relative to vault root; defaults to '1 - Thoughts')
    
    Returns:
        Dictionary with file path and status information
    """
    if ctx:
        ctx.info("Writing new note to vault")
    
    logger.info("Writing new note to vault")
    
    try:
        # Determine target directory
        if not folder_path or not str(folder_path).strip():
            target_dir = Path(THOUGHTS_DIR)
        else:
            clean_folder = str(folder_path).strip()
            
            # Treat leading slash as vault-relative unless it's the full vault path
            if clean_folder.startswith("/"):
                absolute_candidate = Path(clean_folder).expanduser()
                resolved_absolute = absolute_candidate.resolve(strict=False)
                if str(resolved_absolute).startswith(str(VAULT_ROOT)):
                    candidate_dir = resolved_absolute
                else:
                    candidate_dir = (VAULT_ROOT / Path(clean_folder.lstrip("/"))).resolve(strict=False)
            else:
                folder_candidate = Path(clean_folder).expanduser()
                if folder_candidate.is_absolute():
                    candidate_dir = folder_candidate.resolve(strict=False)
                else:
                    candidate_dir = (VAULT_ROOT / folder_candidate).resolve(strict=False)
            
            try:
                candidate_dir.relative_to(VAULT_ROOT)
            except ValueError:
                error_msg = f"Requested folder '{candidate_dir}' is outside the vault root '{VAULT_ROOT}'"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "message": error_msg
                }
            
            target_dir = candidate_dir
        
        # Create folder if it doesn't exist
        os.makedirs(target_dir, exist_ok=True)
        
        # Generate filename from title or timestamp
        if title:
            # Convert title to filename-friendly format
            # Keep spaces, only replace problematic characters
            filename = title.replace('/', ' ').replace('\\', ' ').replace(':', ' ')
            # Remove any other invalid filename characters
            for char in ['<', '>', ':', '"', '|', '?', '*']:
                filename = filename.replace(char, '')
            # Add extension
            filename = f"{filename}.md"
        else:
            # Fallback to timestamp if no title provided
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"ai-generated-{timestamp}.md"
        
        file_path = target_dir / filename
        resolved_file_path = file_path.resolve(strict=False)
        try:
            resolved_file_path.relative_to(VAULT_ROOT)
        except ValueError:
            error_msg = f"Resolved note path '{resolved_file_path}' is outside the vault root '{VAULT_ROOT}'"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
        
        # Prepare frontmatter
        if frontmatter is None:
            frontmatter = {}
        
        # Always mark as AI generated
        frontmatter['ai_generated'] = True
        
        # Add title to frontmatter if provided
        if title and 'title' not in frontmatter:
            frontmatter['title'] = title
        
        # Remove reserved frontmatter properties that should be handled by other systems
        for reserved in ['tags', 'topics', 'aliases']:
            if reserved in frontmatter:
                logger.warning(f"Removing reserved frontmatter property: {reserved}")
                del frontmatter[reserved]
        
        # Create the YAML frontmatter
        yaml_frontmatter = "---\n"
        for key, value in frontmatter.items():
            if isinstance(value, list):
                yaml_frontmatter += f"{key}:\n"
                for item in value:
                    yaml_frontmatter += f"  - {item}\n"
            elif isinstance(value, bool):
                yaml_frontmatter += f"{key}: {str(value).lower()}\n"
            else:
                yaml_frontmatter += f"{key}: {value}\n"
        yaml_frontmatter += "---\n\n"
        
        # Write the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(yaml_frontmatter)
            f.write(content)
        
        logger.info(f"Successfully wrote note to {file_path}")
        
        return {
            "status": "success",
            "file_path": str(file_path),
            "title": title if title else filename,
            "content": content,
            "message": f"Note successfully written to {file_path}"
        }
        
    except Exception as e:
        error_msg = f"Error writing note: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg
        }


@mcp.tool()
def keyword_search(query: str, max_results: int = 10, case_sensitive: bool = False, folder_path: str = None, ctx: Context = None) -> List[Dict[str, Any]]:
    """
    Search thoughts for keyword matches (non-semantic text search).
    
    NOTE: Only use this when explicitly requested for keyword/text search.
    Semantic search (search_by_content/search_by_title) should be preferred for most queries.
    
    Args:
        query: Text or regex pattern to search for
        max_results: Maximum number of results to return (default: 10)
        case_sensitive: Whether to perform case-sensitive matching (default: False)
        folder_path: Optional subfolder to limit search scope (default: entire thoughts dir)
        
    Returns:
        List of matching thoughts with path, title, matched text and context
    """
    if ctx:
        ctx.info(f"Performing keyword search for: {query}")
    
    logger.info(f"Performing keyword search for: {query}")
    
    try:
        # Determine search directory
        if not folder_path:
            search_dir = Path(THOUGHTS_DIR)
        else:
            # Clean up folder path to ensure it's relative
            folder_path = folder_path.strip('/')
            search_dir = Path(THOUGHTS_DIR) / folder_path
        
        if not search_dir.exists():
            return [{"error": f"Search directory not found: {search_dir}"}]
        
        # Find all markdown files in the specified directory
        md_files = list(search_dir.glob("**/*.md"))
        
        if not md_files:
            return [{"error": f"No markdown files found in {search_dir}"}]
        
        # Convert query to lowercase if not case sensitive
        search_query = query if case_sensitive else query.lower()
        
        # Results container
        results = []
        
        # Search through files
        for file_path in md_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Perform search based on case sensitivity
                searchable_content = content if case_sensitive else content.lower()
                
                if search_query in searchable_content:
                    # Extract title from content
                    title = file_path.stem
                    content_lines = content.split('\n')
                    if content_lines and content_lines[0].startswith('#'):
                        title = content_lines[0].lstrip('#').strip()
                    
                    # Find context around the match
                    match_index = searchable_content.find(search_query)
                    start_index = max(0, match_index - 100)
                    end_index = min(len(content), match_index + len(search_query) + 100)
                    
                    # Extract context
                    if start_index > 0:
                        context = "..." + content[start_index:end_index] + "..."
                    else:
                        context = content[start_index:end_index] + "..."
                    
                    # Highlight match in context (preserve original case)
                    match_text = content[match_index:match_index + len(search_query)]
                    highlighted_context = context.replace(match_text, f"**{match_text}**")
                    
                    results.append({
                        "path": str(file_path),
                        "title": title,
                        "match_context": highlighted_context,
                        "full_content": content
                    })
                    
                    # Break early if we've reached max results
                    if len(results) >= max_results:
                        break
            except Exception as e:
                logger.error(f"Error searching file {file_path}: {e}")
                continue
        
        if not results:
            return [{"message": f"No matches found for query: {query}"}]
        
        return results
    
    except Exception as e:
        error_msg = f"Error performing keyword search: {e}"
        logger.error(error_msg)
        return [{"error": error_msg}]


# SR helpers and tool
PLUGIN_DIR = os.getenv("AUTO_TAGGER_PLUGIN_DIR", os.path.abspath(os.path.join(SCRIPT_DIR, "..")))
SR_DB_PATH = os.path.join(PLUGIN_DIR, "spaced_repetition.sqlite")
SETTINGS_PATH = os.path.join(PLUGIN_DIR, "data.json")
BOOLEAN_TRUE = 1
BOOLEAN_FALSE = 0
DB_VERSION = 3

def _js_style_hash(text: str) -> str:
    h = 0
    for ch in text:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return f"card_{h:08x}"

def _normalize_note_path(path: str) -> str:
    if path is None:
        return ""
    norm = os.path.normpath(str(path)).replace("\\", "/").strip()
    if norm.startswith("./"):
        norm = norm[2:]
    return norm

def _sr_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(SR_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    _sr_initialize_schema(conn)
    _sr_ensure_meta_defaults(conn)
    _sr_ensure_deck(conn, "default", "Default")
    return conn

def _sr_initialize_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS decks (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            folder_path TEXT NOT NULL DEFAULT '',
            is_composite INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    _sr_ensure_deck_schema(conn)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cards (
            id TEXT PRIMARY KEY,
            note_path TEXT NOT NULL,
            block_id TEXT,
            type TEXT NOT NULL,
            front TEXT NOT NULL,
            back TEXT NOT NULL,
            irreversible INTEGER NOT NULL DEFAULT 0,
            examples_json TEXT,
            choices_json TEXT,
            correct_choice_id TEXT,
            correct_choice_ids_json TEXT,
            shuffle_choices INTEGER NOT NULL DEFAULT 0,
            multi_select INTEGER NOT NULL DEFAULT 0,
            ease REAL NOT NULL DEFAULT 2.5,
            interval REAL NOT NULL DEFAULT 0,
            repetitions INTEGER NOT NULL DEFAULT 0,
            lapses INTEGER NOT NULL DEFAULT 0,
            due INTEGER NOT NULL,
            suspended INTEGER NOT NULL DEFAULT 0,
            fsrs_stability REAL,
            fsrs_difficulty REAL,
            fsrs_card_json TEXT,
            reviews_json TEXT,
            verb_stats_json TEXT,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS card_decks (
            card_id TEXT NOT NULL,
            deck_id TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(card_id, deck_id),
            FOREIGN KEY(card_id) REFERENCES cards(id) ON DELETE CASCADE,
            FOREIGN KEY(deck_id) REFERENCES decks(id) ON DELETE CASCADE
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS deck_children (
            parent_id TEXT NOT NULL,
            child_id TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(parent_id, child_id),
            FOREIGN KEY(parent_id) REFERENCES decks(id) ON DELETE CASCADE,
            FOREIGN KEY(child_id) REFERENCES decks(id) ON DELETE CASCADE
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS note_deck_links (
            note_path TEXT NOT NULL,
            deck_id TEXT NOT NULL,
            PRIMARY KEY(note_path, deck_id),
            FOREIGN KEY(deck_id) REFERENCES decks(id) ON DELETE CASCADE
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cards_due ON cards(due);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_card_decks_deck ON card_decks(deck_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_card_decks_card ON card_decks(card_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_note_links_note ON note_deck_links(note_path);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_deck_children_parent ON deck_children(parent_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_deck_children_child ON deck_children(child_id);")

def _sr_ensure_deck_schema(conn: sqlite3.Connection) -> None:
    try:
        rows = conn.execute("PRAGMA table_info(decks)").fetchall()
        has_folder = False
        has_composite = False
        for row in rows:
            name = row["name"] if isinstance(row, sqlite3.Row) else row[1]
            if name == "folder_path":
                has_folder = True
            if name == "is_composite":
                has_composite = True
        if not has_folder:
            conn.execute("ALTER TABLE decks ADD COLUMN folder_path TEXT NOT NULL DEFAULT ''")
        if not has_composite:
            conn.execute("ALTER TABLE decks ADD COLUMN is_composite INTEGER NOT NULL DEFAULT 0")
    except Exception as err:
        logger.error("Failed to ensure deck schema: %s", err)

def _sr_today_rollover_timestamp() -> int:
    now = datetime.datetime.now()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(midnight.timestamp() * 1000)

def _sr_get_meta(conn: sqlite3.Connection, key: str) -> Optional[str]:
    row = conn.execute("SELECT value FROM meta WHERE key = ? LIMIT 1", (key,)).fetchone()
    if not row:
        return None
    return str(row["value"])

def _sr_set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )

def _sr_ensure_meta_defaults(conn: sqlite3.Connection) -> None:
    version = _sr_get_meta(conn, "version")
    if version != str(DB_VERSION):
        _sr_set_meta(conn, "version", str(DB_VERSION))
    last_rollover = _sr_get_meta(conn, "lastRollover")
    if not last_rollover:
        _sr_set_meta(conn, "lastRollover", str(_sr_today_rollover_timestamp()))

def _sr_deck_exists(conn: sqlite3.Connection, deck_id: str) -> bool:
    row = conn.execute("SELECT 1 FROM decks WHERE id = ? LIMIT 1", (deck_id,)).fetchone()
    return bool(row)

def _sr_ensure_deck(conn: sqlite3.Connection, deck_id: Optional[str], name: Optional[str] = None) -> str:
    did = (deck_id or "default").strip() or "default"
    if _sr_deck_exists(conn, did):
        return did
    now_ms = int(time.time() * 1000)
    deck_name = (name or ("Default" if did == "default" else did)).strip() or did
    conn.execute(
        "INSERT INTO decks (id, name, created_at, folder_path, is_composite) VALUES (?, ?, ?, ?, 0)",
        (did, deck_name, now_ms, ""),
    )
    return did

def _sr_find_deck_by_name(conn: sqlite3.Connection, name: str) -> Optional[str]:
    clean = (name or "").strip()
    if not clean:
        return None
    row = conn.execute(
        "SELECT id FROM decks WHERE name = ? COLLATE NOCASE LIMIT 1",
        (clean,),
    ).fetchone()
    return str(row["id"]) if row else None

def _sr_generate_deck_id_from_name(conn: sqlite3.Connection, name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (name or "deck").lower()).strip("-") or "deck"
    candidate = base
    suffix = 2
    while _sr_deck_exists(conn, candidate):
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate

def _sr_ensure_deck_by_name(conn: sqlite3.Connection, name: str) -> str:
    clean = (name or "Deck").strip()
    existing = _sr_find_deck_by_name(conn, clean)
    if existing:
        return existing
    deck_id = _sr_generate_deck_id_from_name(conn, clean)
    _sr_ensure_deck(conn, deck_id, clean)
    return deck_id

def _sr_get_composite_children(conn: sqlite3.Connection, deck_id: str) -> List[str]:
    rows = conn.execute(
        "SELECT child_id FROM deck_children WHERE parent_id = ? ORDER BY position",
        (deck_id,),
    ).fetchall()
    return [str(row["child_id"]) for row in rows]


def _sr_get_deck(conn: sqlite3.Connection, deck_id: str) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT id, name, folder_path, is_composite FROM decks WHERE id = ? LIMIT 1",
        (deck_id,),
    ).fetchone()
    if not row:
        return None
    return {
        "id": str(row["id"]),
        "name": str(row["name"]),
        "folderPath": str(row["folder_path"] or ""),
        "isComposite": bool(row["is_composite"]),
        "children": _sr_get_composite_children(conn, deck_id),
    }

def _sr_sanitize_deck_ids(deck_ids: Iterable[Any]) -> List[str]:
    seen: Set[str] = set()
    result: List[str] = []
    for did in deck_ids:
        if not isinstance(did, str):
            continue
        clean = did.strip()
        if not clean:
            continue
        if clean not in seen:
            seen.add(clean)
            result.append(clean)
    return result

def _sr_dump_json(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return None

def _sr_parse_json(payload: Optional[str]) -> Any:
    if not payload:
        return None
    try:
        return json.loads(payload)
    except Exception:
        return None

def _sr_float(value: Any, default: float) -> float:
    if isinstance(value, (int, float)) and math.isfinite(value):
        return float(value)
    return float(default)

def _sr_optional_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and math.isfinite(value):
        return float(value)
    return None

def _sr_int(value: Any, default: int) -> int:
    if isinstance(value, (int, float)) and math.isfinite(value):
        return int(value)
    return int(default)

def _sr_get_deck_ids_for_card(conn: sqlite3.Connection, card_id: str) -> List[str]:
    rows = conn.execute(
        "SELECT deck_id FROM card_decks WHERE card_id = ? ORDER BY position",
        (card_id,),
    ).fetchall()
    return [str(row["deck_id"]) for row in rows]

def _sr_upsert_card(conn: sqlite3.Connection, card: Dict[str, Any]) -> Dict[str, Any]:
    normalized_path = _normalize_note_path(card.get("notePath", card.get("note_path", "")))
    deck_id_candidates: List[str] = []
    for raw in card.get("deckIds") or []:
        if isinstance(raw, str) and raw.strip():
            deck_id_candidates.append(_sr_ensure_deck(conn, raw.strip()))
    if not deck_id_candidates:
        single = card.get("deckId") or card.get("deck_id")
        if isinstance(single, str) and single.strip():
            deck_id_candidates.append(_sr_ensure_deck(conn, single.strip()))
    deck_id_candidates = _sr_sanitize_deck_ids(deck_id_candidates)
    if not deck_id_candidates:
        deck_id_candidates = [_sr_ensure_deck(conn, "default", "Default")]
    primary_deck = deck_id_candidates[0]

    front = str(card.get("front", "")).strip()
    back = str(card.get("back", "")).strip()
    if not front:
        raise ValueError("Card is missing required 'front' text")
    if back == "":
        back = "..."

    existing_row = conn.execute(
        "SELECT created_at FROM cards WHERE id = ? LIMIT 1",
        (card.get("id"),),
    ).fetchone() if card.get("id") else None
    generated_id = _js_style_hash(f"{primary_deck}\n{card.get('type', 'basic')}\n{front}\n{back}")
    card_id = str(card.get("id") or generated_id)
    now_ms = int(time.time() * 1000)
    created_source = card.get("createdAt", card.get("created_at"))
    if created_source is None and existing_row is not None:
        created_source = existing_row["created_at"]
    created_at = _sr_int(created_source, now_ms)
    updated_at = _sr_int(card.get("updatedAt", card.get("updated_at")), now_ms)
    if updated_at <= 0:
        updated_at = now_ms

    conn.execute(
        """
        INSERT INTO cards (
            id, note_path, block_id, type, front, back, irreversible, examples_json, choices_json,
            correct_choice_id, correct_choice_ids_json, shuffle_choices, multi_select, ease, interval,
            repetitions, lapses, due, suspended, fsrs_stability, fsrs_difficulty, fsrs_card_json,
            reviews_json, verb_stats_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            note_path = excluded.note_path,
            block_id = excluded.block_id,
            type = excluded.type,
            front = excluded.front,
            back = excluded.back,
            irreversible = excluded.irreversible,
            examples_json = excluded.examples_json,
            choices_json = excluded.choices_json,
            correct_choice_id = excluded.correct_choice_id,
            correct_choice_ids_json = excluded.correct_choice_ids_json,
            shuffle_choices = excluded.shuffle_choices,
            multi_select = excluded.multi_select,
            ease = excluded.ease,
            interval = excluded.interval,
            repetitions = excluded.repetitions,
            lapses = excluded.lapses,
            due = excluded.due,
            suspended = excluded.suspended,
            fsrs_stability = excluded.fsrs_stability,
            fsrs_difficulty = excluded.fsrs_difficulty,
            fsrs_card_json = excluded.fsrs_card_json,
            reviews_json = excluded.reviews_json,
            verb_stats_json = excluded.verb_stats_json,
            updated_at = excluded.updated_at
        """,
        (
            card_id,
            normalized_path,
            card.get("blockId", card.get("block_id")),
            str(card.get("type", "basic") or "basic"),
            front,
            back,
            BOOLEAN_TRUE if card.get("irreversible") else BOOLEAN_FALSE,
            _sr_dump_json(card.get("examples")),
            _sr_dump_json(card.get("choices")),
            card.get("correctChoiceId", card.get("correct_choice_id")),
            _sr_dump_json(card.get("correctChoiceIds", card.get("correct_choice_ids"))),
            BOOLEAN_TRUE if card.get("shuffleChoices") or card.get("shuffle_choices") else BOOLEAN_FALSE,
            BOOLEAN_TRUE if card.get("multiSelect") or card.get("multi_select") else BOOLEAN_FALSE,
            _sr_float(card.get("ease"), 2.5),
            _sr_float(card.get("interval"), 0),
            _sr_int(card.get("repetitions"), 0),
            _sr_int(card.get("lapses"), 0),
            _sr_int(card.get("due"), now_ms),
            BOOLEAN_TRUE if card.get("suspended") else BOOLEAN_FALSE,
            _sr_optional_float(card.get("fsrsStability")),
            _sr_optional_float(card.get("fsrsDifficulty")),
            _sr_dump_json(card.get("fsrsCard")),
            _sr_dump_json(card.get("reviews")),
            _sr_dump_json(card.get("verbPrepositionStats") or card.get("verb_stats")),
            created_at,
            updated_at,
        ),
    )
    conn.execute("DELETE FROM card_decks WHERE card_id = ?", (card_id,))
    for position, did in enumerate(deck_id_candidates):
        conn.execute(
            "INSERT INTO card_decks (card_id, deck_id, position) VALUES (?, ?, ?)",
            (card_id, did, position),
        )
    is_new = existing_row is None
    return {
        "id": card_id,
        "deckIds": deck_id_candidates,
        "notePath": normalized_path,
        "isNew": is_new,
    }

def _sr_link_note_to_deck_sql(conn: sqlite3.Connection, note_path: str, deck_id: str, allow_multiple: bool) -> List[str]:
    normalized = _normalize_note_path(note_path)
    if not normalized:
        return []
    _sr_ensure_deck(conn, deck_id)
    if not allow_multiple:
        conn.execute("DELETE FROM note_deck_links WHERE note_path = ?", (normalized,))
    conn.execute(
        "INSERT OR IGNORE INTO note_deck_links (note_path, deck_id) VALUES (?, ?)",
        (normalized, deck_id),
    )
    rows = conn.execute(
        "SELECT deck_id FROM note_deck_links WHERE note_path = ? ORDER BY rowid",
        (normalized,),
    ).fetchall()
    return [str(row["deck_id"]) for row in rows]

def _sr_unlink_note_from_deck_sql(conn: sqlite3.Connection, note_path: str, deck_id: Optional[str]) -> List[str]:
    normalized = _normalize_note_path(note_path)
    if not normalized:
        return []
    if deck_id:
        conn.execute(
            "DELETE FROM note_deck_links WHERE note_path = ? AND deck_id = ?",
            (normalized, deck_id),
        )
    else:
        conn.execute("DELETE FROM note_deck_links WHERE note_path = ?", (normalized,))
    rows = conn.execute(
        "SELECT deck_id FROM note_deck_links WHERE note_path = ? ORDER BY rowid",
        (normalized,),
    ).fetchall()
    return [str(row["deck_id"]) for row in rows]

def _sr_map_row_to_card(row: sqlite3.Row, deck_ids: List[str], include_reviews: bool) -> Dict[str, Any]:
    card: Dict[str, Any] = {
        "id": str(row["id"]),
        "deckIds": deck_ids,
        "deckId": deck_ids[0] if deck_ids else None,
        "notePath": str(row["note_path"]),
        "type": str(row["type"]),
        "front": str(row["front"]),
        "back": str(row["back"]),
        "ease": float(row["ease"]),
        "interval": float(row["interval"]),
        "repetitions": int(row["repetitions"]),
        "lapses": int(row["lapses"]),
        "due": int(row["due"]),
        "suspended": bool(row["suspended"]),
        "createdAt": int(row["created_at"]),
        "updatedAt": int(row["updated_at"]),
    }
    if row["block_id"]:
        card["blockId"] = str(row["block_id"])
    card["irreversible"] = bool(row["irreversible"])
    examples = _sr_parse_json(row["examples_json"])
    if examples is not None:
        card["examples"] = examples
    choices = _sr_parse_json(row["choices_json"])
    if choices is not None:
        card["choices"] = choices
    if row["correct_choice_id"]:
        card["correctChoiceId"] = str(row["correct_choice_id"])
    correct_ids = _sr_parse_json(row["correct_choice_ids_json"])
    if correct_ids is not None:
        card["correctChoiceIds"] = correct_ids
    card["shuffleChoices"] = bool(row["shuffle_choices"])
    card["multiSelect"] = bool(row["multi_select"])
    fsrs_stability = row["fsrs_stability"]
    if fsrs_stability is not None:
        card["fsrsStability"] = float(fsrs_stability)
    fsrs_difficulty = row["fsrs_difficulty"]
    if fsrs_difficulty is not None:
        card["fsrsDifficulty"] = float(fsrs_difficulty)
    fsrs_card = _sr_parse_json(row["fsrs_card_json"])
    if fsrs_card is not None:
        card["fsrsCard"] = fsrs_card
    if include_reviews:
        reviews = _sr_parse_json(row["reviews_json"])
        if reviews is not None:
            card["reviews"] = reviews
    verb_stats = _sr_parse_json(row["verb_stats_json"])
    if verb_stats is not None:
        card["verbPrepositionStats"] = verb_stats
    return card

def _load_settings() -> Dict[str, Any]:
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_settings(st: Dict[str, Any]) -> None:
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save settings: {e}")

def _sr_normalize_choices(choices: Any) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    if not isinstance(choices, list):
        return out
    for i, it in enumerate(choices):
        if isinstance(it, str):
            text = it.strip()
            if text:
                out.append({"id": str(i), "text": text})
        elif isinstance(it, dict):
            text = str(it.get("text", "")).strip()
            if text:
                raw_id = it.get("id")
                cid = str(raw_id).strip() if isinstance(raw_id, (str, int)) and str(raw_id).strip() else str(i)
                out.append({"id": cid, "text": text})
    return out

def _sr_create_card_objects(deck_id: str, cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    now_ms = int(time.time() * 1000)
    out: List[Dict[str, Any]] = []
    for c in cards:
        ctype = str(c.get("type", "basic")).strip() or "basic"
        front = str(c.get("front", "")).strip()
        back_src = c.get("back", c.get("answer", ""))
        back = str(back_src).strip() if back_src is not None else ""
        if not front:
            continue
        if back == "":
            back = "..."
        cid = _js_style_hash(f"{deck_id}\n{ctype}\n{front}\n{back}")
        deck_ids = []
        if isinstance(c.get("deckIds"), list):
            for entry in c["deckIds"]:
                if isinstance(entry, str) and entry.strip():
                    deck_ids.append(entry.strip())
        if not deck_ids:
            deck_ids = [deck_id]
        base: Dict[str, Any] = {
            "id": c.get("id", cid),
            "deckId": deck_id,
            "deckIds": deck_ids,
            "notePath": "",
            "type": ctype,
            "front": front,
            "back": back,
            "irreversible": bool(c.get("irreversible", False)) if ctype == "basic" else False,
            "examples": c.get("examples", []) if ctype == "basic" else c.get("examples"),
            "ease": 2.5,
            "interval": 0,
            "repetitions": 0,
            "lapses": 0,
            "due": now_ms,
            "suspended": False,
            "createdAt": c.get("createdAt", now_ms),
            "updatedAt": c.get("updatedAt", now_ms),
            "fsrsStability": c.get("fsrsStability"),
            "fsrsDifficulty": c.get("fsrsDifficulty"),
            "fsrsCard": c.get("fsrsCard"),
            "reviews": c.get("reviews"),
            "verbPrepositionStats": c.get("verbPrepositionStats"),
        }
        note_path = c.get("notePath", c.get("note_path"))
        if isinstance(note_path, str) and note_path.strip():
            base["notePath"] = _normalize_note_path(note_path)
        block_id = c.get("blockId", c.get("block_id"))
        if isinstance(block_id, str) and block_id.strip():
            base["blockId"] = block_id.strip()
        if ctype == "multiple-choice":
            choices = _sr_normalize_choices(c.get("choices"))
            choice_ids = {ch.get("id") for ch in choices if isinstance(ch.get("id"), str)}
            correct_id: Optional[str] = None
            correct_ids: List[str] = []

            single_candidate = c.get("correctChoiceId")
            if single_candidate is None:
                single_candidate = c.get("answerId") or c.get("answer_id")
            if isinstance(single_candidate, (str, int)):
                single_str = str(single_candidate).strip()
                if single_str and single_str in choice_ids:
                    correct_id = single_str

            multi_candidate = c.get("correctChoiceIds")
            if isinstance(multi_candidate, list):
                seen: Set[str] = set()
                for entry in multi_candidate:
                    if isinstance(entry, (str, int)):
                        sid = str(entry).strip()
                        if sid and sid in choice_ids and sid not in seen:
                            seen.add(sid)
                            correct_ids.append(sid)

            if not correct_id and not correct_ids:
                answer = c.get("answer")
                if isinstance(answer, str):
                    ans = answer.strip()
                    for ch in choices:
                        if ch.get("text") == ans:
                            correct_id = ch.get("id")
                            break
                elif isinstance(answer, list):
                    for item in answer:
                        if isinstance(item, str):
                            ans = item.strip()
                            for ch in choices:
                                if ch.get("text") == ans and ch.get("id") not in correct_ids:
                                    correct_ids.append(ch.get("id"))
                    if correct_ids:
                        correct_id = None

            multi_select = bool(c.get("multiSelect")) or len(correct_ids) > 1
            mc_payload: Dict[str, Any] = {"choices": choices, "shuffleChoices": bool(c.get("shuffle", True))}
            if correct_ids:
                if not multi_select and len(correct_ids) == 1:
                    correct_id = correct_ids[0]
                    correct_ids = []
                else:
                    mc_payload["correctChoiceIds"] = correct_ids
            if correct_id:
                mc_payload["correctChoiceId"] = correct_id
            if multi_select:
                mc_payload["multiSelect"] = True
            base.update(mc_payload)
        out.append(base)
    return out

@mcp.tool()
def create_sr_cards(cards: List[Dict[str, Any]], deck_id: Optional[str] = None, ctx: Context = None) -> Dict[str, Any]:
    """Create SR cards directly in the plugin store."""
    if ctx:
        ctx.info("Creating SR cards")
    created: List[str] = []
    linked_notes: Dict[str, Set[str]] = {}
    with _sr_connect() as conn:
        default_did = _sr_ensure_deck(conn, deck_id)
        for raw in cards or []:
            if not isinstance(raw, dict):
                continue
            deck_candidates: List[str] = []
            if isinstance(raw.get('deckIds'), list):
                for entry in raw['deckIds']:
                    if isinstance(entry, str) and entry.strip():
                        deck_candidates.append(_sr_ensure_deck(conn, entry.strip()))
            if isinstance(raw.get('deckId'), str) and raw['deckId'].strip():
                deck_candidates.append(_sr_ensure_deck(conn, raw['deckId'].strip()))
            deck_name = raw.get('deck')
            if isinstance(deck_name, str) and deck_name.strip():
                deck_candidates.append(_sr_ensure_deck_by_name(conn, deck_name.strip()))
            deck_candidates = _sr_sanitize_deck_ids(deck_candidates)
            if not deck_candidates:
                deck_candidates = [default_did]
            enriched = dict(raw)
            enriched['deckId'] = deck_candidates[0]
            enriched['deckIds'] = deck_candidates
            card_objects = _sr_create_card_objects(deck_candidates[0], [enriched])
            for card in card_objects:
                card['deckIds'] = deck_candidates
                try:
                    result = _sr_upsert_card(conn, card)
                except Exception as err:
                    logger.error("Failed to upsert SR card: %s", err)
                    continue
                if result.get('isNew'):
                    created.append(result['id'])
                note_path = result.get('notePath')
                if note_path:
                    for did in result.get('deckIds', []):
                        _sr_link_note_to_deck_sql(conn, note_path, did, allow_multiple=True)
                        linked_notes.setdefault(note_path, set()).add(did)
        conn.commit()
    linked_notes_out: Dict[str, Union[str, List[str]]] = {}
    for path, ids in linked_notes.items():
        ordered = sorted(ids)
        if len(ordered) == 1:
            linked_notes_out[path] = ordered[0]
        else:
            linked_notes_out[path] = ordered
    if os.getenv('SR_DEBUG_LOGS', '0') == '1':
        try:
            print(f"[SR MCP] create_sr_cards: deck={deck_id or 'default'} created={len(created)}", file=sys.stderr)
        except Exception:
            pass
    return {"createdCount": len(created), "createdIds": created, "deckId": deck_id or default_did, "linkedNotes": linked_notes_out}

@mcp.tool()
def list_sr_decks(ctx: Context = None) -> Dict[str, Any]:
    """List SR decks with id, name, and card counts."""
    with _sr_connect() as conn:
        rows = conn.execute(
            """
            SELECT d.id, d.name, COUNT(cd.card_id) AS count
            FROM decks d
            LEFT JOIN card_decks cd ON cd.deck_id = d.id
            GROUP BY d.id
            ORDER BY d.name COLLATE NOCASE
            """
        ).fetchall()
    decks = [
        {"id": str(row["id"]), "name": str(row["name"]), "count": int(row["count"])}
        for row in rows
    ]
    return {"decks": decks}

@mcp.tool()
def create_sr_deck(name: str, ctx: Context = None) -> Dict[str, Any]:
    """Create a new SR deck by name."""
    with _sr_connect() as conn:
        deck_id = _sr_ensure_deck_by_name(conn, name)
        deck = _sr_get_deck(conn, deck_id)
        conn.commit()
    return {"deck": deck}

@mcp.tool()
def link_sr_note_to_deck(note_path: str, deck_id: Optional[str] = None, deck_name: Optional[str] = None,
                         allow_multiple: bool = True, create_if_missing: bool = True, ctx: Context = None) -> Dict[str, Any]:
    allow_multiple = bool(allow_multiple)
    create_if_missing = bool(create_if_missing)
    if ctx:
        ctx.info("Linking note to spaced repetition deck")
    note_path_norm = _normalize_note_path(note_path)
    if not note_path_norm:
        return {"error": "invalid_note_path"}
    with _sr_connect() as conn:
        target_deck: Optional[str] = None
        if deck_id:
            target_deck = _sr_ensure_deck(conn, deck_id)
        elif deck_name:
            existing = _sr_find_deck_by_name(conn, deck_name)
            if existing:
                target_deck = existing
            elif create_if_missing:
                target_deck = _sr_ensure_deck_by_name(conn, deck_name)
            else:
                return {"error": f"deck_not_found:{deck_name}"}
        else:
            target_deck = _sr_ensure_deck(conn, "default", "Default")
        decks_for_note = _sr_link_note_to_deck_sql(conn, note_path_norm, target_deck, allow_multiple=allow_multiple)
        deck_info = _sr_get_deck(conn, target_deck)
        conn.commit()
    return {
        "status": "ok",
        "notePath": note_path_norm,
        "deckId": target_deck,
        "deckName": deck_info.get("name") if deck_info else target_deck,
        "linkedDecks": decks_for_note,
    }

@mcp.tool()
def unlink_sr_note_from_deck(note_path: str, deck_id: Optional[str] = None, ctx: Context = None) -> Dict[str, Any]:
    if ctx:
        ctx.info("Unlinking note from spaced repetition deck")
    note_path_norm = _normalize_note_path(note_path)
    if not note_path_norm:
        return {"error": "invalid_note_path"}
    with _sr_connect() as conn:
        removed_name = None
        if deck_id:
            deck = _sr_get_deck(conn, deck_id)
            if deck:
                removed_name = deck.get("name")
        decks_for_note = _sr_unlink_note_from_deck_sql(conn, note_path_norm, deck_id)
        conn.commit()
    return {
        "status": "ok",
        "notePath": note_path_norm,
        "linkedDecks": decks_for_note,
        "removedDeckId": deck_id,
        "removedDeckName": removed_name,
    }

@mcp.tool()
def delete_sr_deck(deck_id: str, reassign_to: Optional[str] = None, ctx: Context = None) -> Dict[str, Any]:
    with _sr_connect() as conn:
        deck = _sr_get_deck(conn, deck_id)
        if not deck:
            return {"error": f"deck_not_found:{deck_id}"}
        target = _sr_ensure_deck(conn, reassign_to or "default", "Default")
        if deck_id == target:
            return {"status": "ok", "reassignTo": target}
        card_rows = conn.execute(
            "SELECT DISTINCT card_id FROM card_decks WHERE deck_id = ?",
            (deck_id,),
        ).fetchall()
        for row in card_rows:
            card_id = str(row["card_id"])
            decks_for_card = _sr_get_deck_ids_for_card(conn, card_id)
            decks_for_card = [did for did in decks_for_card if did != deck_id]
            if target not in decks_for_card:
                decks_for_card.append(target)
            if not decks_for_card:
                decks_for_card = [target]
            conn.execute("DELETE FROM card_decks WHERE card_id = ?", (card_id,))
            for position, did in enumerate(_sr_sanitize_deck_ids(decks_for_card)):
                conn.execute(
                    "INSERT INTO card_decks (card_id, deck_id, position) VALUES (?, ?, ?)",
                    (card_id, did, position),
                )
        note_rows = conn.execute(
            "SELECT note_path FROM note_deck_links WHERE deck_id = ?",
            (deck_id,),
        ).fetchall()
        for row in note_rows:
            note_path_norm = str(row["note_path"])
            conn.execute(
                "DELETE FROM note_deck_links WHERE note_path = ? AND deck_id = ?",
                (note_path_norm, deck_id),
            )
            conn.execute(
                "INSERT OR IGNORE INTO note_deck_links (note_path, deck_id) VALUES (?, ?)",
                (note_path_norm, target),
            )
        if deck_id != target:
            conn.execute("DELETE FROM decks WHERE id = ?", (deck_id,))
        conn.commit()
    return {"status": "ok", "reassignTo": target}

@mcp.tool()
def select_sr_deck(deck_id: str, ctx: Context = None) -> Dict[str, Any]:
    with _sr_connect() as conn:
        did = _sr_ensure_deck(conn, deck_id)
        conn.commit()
    st = _load_settings()
    st.setdefault("spacedRepetition", {})["selectedDeckId"] = did
    _save_settings(st)
    return {"status": "ok", "selectedDeckId": did}

@mcp.tool()
def delete_sr_cards(card_ids: Optional[List[str]] = None, deck_id: Optional[str] = None, ctx: Context = None) -> Dict[str, Any]:
    if ctx:
        ctx.info("Deleting SR cards")
    removed = 0
    with _sr_connect() as conn:
        target_ids: Set[str] = set()
        if deck_id:
            rows = conn.execute(
                "SELECT card_id FROM card_decks WHERE deck_id = ?",
                (deck_id,),
            ).fetchall()
            for row in rows:
                target_ids.add(str(row["card_id"]))
        if card_ids:
            for cid in card_ids:
                if isinstance(cid, str) and cid.strip():
                    target_ids.add(cid.strip())
        for cid in target_ids:
            cur = conn.execute("DELETE FROM cards WHERE id = ?", (cid,))
            removed += cur.rowcount
        conn.commit()
    return {"removed": removed, "byDeck": bool(deck_id)}

@mcp.tool()
def inspect_sr_cards(card_ids: Optional[List[str]] = None,
                     deck_id: Optional[str] = None,
                     limit: int = 20,
                     include_schema: bool = True,
                     include_reviews: bool = False,
                     ctx: Context = None) -> Dict[str, Any]:
    if ctx:
        ctx.info("Inspecting SR cards and schema")
    with _sr_connect() as conn:
        rows: List[sqlite3.Row] = []
        if card_ids:
            ids = [cid for cid in card_ids if isinstance(cid, str) and cid.strip()]
            if ids:
                placeholders = ",".join(["?"] * len(ids))
                rows = conn.execute(
                    f"SELECT * FROM cards WHERE id IN ({placeholders}) ORDER BY updated_at DESC",
                    ids,
                ).fetchall()
        else:
            if deck_id:
                rows = conn.execute(
                    """
                    SELECT c.* FROM cards c
                    INNER JOIN card_decks cd ON cd.card_id = c.id
                    WHERE cd.deck_id = ?
                    ORDER BY c.updated_at DESC
                    LIMIT ?
                    """,
                    (deck_id, max(1, int(limit))),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM cards ORDER BY updated_at DESC LIMIT ?",
                    (max(1, int(limit)),),
                ).fetchall()
        cards_out: List[Dict[str, Any]] = []
        for row in rows:
            deck_ids_for_card = _sr_get_deck_ids_for_card(conn, str(row["id"]))
            cards_out.append(_sr_map_row_to_card(row, deck_ids_for_card, include_reviews))
        conn.commit()
    schema: Optional[Dict[str, Any]] = None
    if include_schema:
        schema = {
            "Card": {
                "id": "string",
                "deckIds": "string[] (all decks the card belongs to; first entry is the primary deck)",
                "deckId?": "string (primary deck alias)",
                "notePath": "string",
                "blockId?": "string",
                "type": "'basic'|'multiple-choice'|'open-ended'",
                "front": "string",
                "back": "string",
                "irreversible?": "boolean",
                "examples?": "string[]",
                "choices?": "{id:string, text:string}[]",
                "correctChoiceId?": "string",
                "correctChoiceIds?": "string[]",
                "multiSelect?": "boolean",
                "shuffleChoices?": "boolean",
                "ease": "number",
                "interval": "number",
                "repetitions": "number",
                "lapses": "number",
                "due": "number",
                "suspended": "boolean",
                "fsrsStability?": "number",
                "fsrsDifficulty?": "number",
                "fsrsCard?": "object",
                "verbPrepositionStats?": "object",
                "reviews?": "ReviewLog[]",
                "createdAt": "number",
                "updatedAt": "number",
            },
            "ReviewLog": {
                "t": "number",
                "rating": "'again'|'hard'|'good'|'easy'",
                "interval": "number",
                "due": "number",
                "deckId": "string",
                "scheduler": "'fsrs'|'sm2'",
                "selectedChoiceIds?": "string[]",
                "correct?": "boolean",
                "durationMs?": "number",
            },
        }
    return {"schema": schema, "cards": cards_out}


# ----------------------------------------------------------------------
# MCP resources
# ----------------------------------------------------------------------

@mcp.resource("thoughts://stats")
def get_thoughts_stats() -> str:
    """
    Get statistics about the thoughts collection.
    """
    logger.info("Getting thoughts statistics")
    
    # Get all markdown files in the thoughts directory
    md_files = list(Path(THOUGHTS_DIR).glob("**/*.md"))
    
    # Get embedding info if available
    title_embedding_count = 0
    thought_embedding_count = 0
    
    if _ensure_embeddings_exist():
        # Load embeddings to get counts
        title_embeddings = load_embeddings(TITLE_EMBEDDINGS_FILE)
        thought_embeddings = load_embeddings(BODY_EMBEDDINGS_FILE)
        
        title_embedding_count = len(title_embeddings)
        thought_embedding_count = len(thought_embeddings)
    
    stats = {
        "total_thoughts": len(md_files),
        "title_embeddings": title_embedding_count,
        "content_embeddings": thought_embedding_count,
        "thoughts_directory": THOUGHTS_DIR,
        "embeddings_ready": _ensure_embeddings_exist()
    }
    
    return json.dumps(stats, indent=2)


@mcp.resource("thoughts://help")
def get_help() -> str:
    """
    Get help information about how to use the thoughts MCP server.
    """
    logger.info("Getting help information")
    
    help_text = """
# Thoughts MCP Server

This MCP server provides access to your thoughts collection through semantic search.

## Available Tools

- **build_thought_embeddings**: Build embeddings for all thoughts (needed before searching)
- **search_by_content**: Search thoughts by content similarity
- **search_by_title**: Search thoughts by title similarity
- **keyword_search**: Search thoughts by exact text matches (only use when explicitly requested)
- **get_thought_content**: Get the full content of a specific thought
- **compare_thoughts**: Compare two thoughts and calculate their similarity
- **list_recent_thoughts**: List the most recently modified thought files
- **write_note**: Write a new note to your Obsidian vault

## Note Writing Guidelines

When writing notes to the vault, follow these important guidelines:

1. **DO NOT** include 'tags' or 'topics' in the frontmatter
2. **Create Good Titles**: Use specific, descriptive titles with capitalized words and spaces
   - Example: "Spaced Repetition", "Decision Making Framework"
   - Avoid vague titles like "Thoughts on X" or "Notes about Y"
3. **Atomic Notes**: One note should contain one main idea or concept
4. **Focus on Ideas**: Write directly about the concepts themselves
   - Never reference "the author" or attribute thoughts to anyone
   - Focus purely on the ideas and information
5. **Use Obsidian Links**: Link to other notes using `[[Note Title]]` syntax rather than duplicating content
6. **Use British English**: All note content should use British English spelling
7. **Repeat Content**: Always repeat the full note content in your chat response after creating it

## Example Usage

To search for thoughts related to "productivity":
```
search_by_content("productivity", max_results=5)
```

To compare two thoughts:
```
compare_thoughts("/path/to/thought1.md", "/path/to/thought2.md")
```

To write a new note:
```
write_note(
    title="Pareto Principle",
    content="[[Pareto Principle]] suggests that roughly 80% of effects come from 20% of causes. This phenomenon appears consistently across many domains.\n\nIn [[Economics]], it manifests when 80% of wealth is owned by 20% of the population. In [[Project Management]], approximately 80% of results come from 20% of efforts.",
    folder_path="Concepts"
)
```

To perform a keyword search (only when explicitly requested):
```
keyword_search("specific phrase", max_results=5, case_sensitive=False)
```
"""
    return help_text


# ----------------------------------------------------------------------
# Main function
# ----------------------------------------------------------------------

def main():
    """Run the MCP server."""
    parser = argparse.ArgumentParser(description="Thoughts MCP Server")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("Starting Thoughts MCP Server...")
    
    # Check if embedding files exist
    if not _ensure_embeddings_exist():
        logger.warning("Embedding files not found. Run build_thought_embeddings tool first.")
    
    try:
        # Run the MCP server
        mcp.run()
    except Exception as e:
        logger.error(f"Error running MCP server: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main() 
