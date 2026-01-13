# Thoughts MCP Server

This MCP server allows Claude to interact with your Obsidian thoughts collection, providing semantic search and analysis capabilities through the Model Context Protocol (MCP).

## Features

- **Semantic Search**: Search your thoughts by content or title similarity
- **Keyword Search**: Perform exact text matching searches (only when explicitly requested)
- **Thought Analysis**: Compare thoughts, analyze similarities, and explore connections
- **Recent Thoughts**: List recently modified thoughts for quick access
- **Statistics**: Get insights about your thoughts collection
- **Note Writing**: Create new notes directly in your vault

## Prerequisites

- Python 3.7+ with pip
- Ollama running locally (for embeddings generation)
- Claude Desktop with MCP support

## Installation

1. Make sure you have the required Python packages installed:

```bash
cd thoughts_embedding
pip install -r requirements.txt
pip install mcp[cli]
```

2. Install the MCP server in Claude Desktop:

```bash
cd thoughts_embedding
mcp install mcp_server.py --name "Thoughts Assistant"
```

Or, if you prefer to install it with environment variables:

```bash
PYTHONPATH=$PYTHONPATH:/path/to/auto-tagger mcp install mcp_server.py --name "Thoughts Assistant"
```

## Using with Claude

Once installed, you can use the Thoughts MCP Server with Claude Desktop. Here are some example prompts:

- "List my 5 most recent thoughts"
- "Search my thoughts for information about productivity"
- "Find thoughts with titles related to meditation"
- "Compare these two thought files: [path1] and [path2]"
- "Show me statistics about my thoughts collection"
- "Write a detailed note about [topic] and save it to my Obsidian vault"
- "Create a reflection on [concept] and save it in the 'Reflections' subfolder"
- "Perform an exact keyword search for 'specific phrase' in my thoughts" (Use only when explicitly requested)

After installation, Claude should show "Thoughts Assistant" in the list of connected servers. You'll see the tools appear when you click on the tools button in the Claude interface.

If Claude doesn't automatically suggest using the tools, you can explicitly tell it to:
"Using the Thoughts Assistant tools, search my thoughts for information about [topic]"

## Available Tools

The server provides the following tools:

- **build_thought_embeddings**: Build embeddings for all thoughts (needed before searching)
- **search_by_content**: Search thoughts by content similarity
- **search_by_title**: Search thoughts by title similarity
- **get_thought_content**: Get the full content of a specific thought
- **compare_thoughts**: Compare two thoughts and calculate their similarity
- **list_recent_thoughts**: List the most recently modified thought files
- **write_note**: Write a new AI-generated note to your Obsidian vault
- **create_sr_cards**: Create spaced-repetition cards (supports specifying the target deck and linked note path)
- **list_sr_decks** / **create_sr_deck**: Inspect or create decks managed by the plugin
- **link_sr_note_to_deck** / **unlink_sr_note_from_deck**: Pair a note with a deck (or remove the association) so the Obsidian UI surfaces the correct review buttons

## Note Writing Guidelines

When using the `write_note` tool to create new notes:

- **DO NOT** include 'tags' or 'topics' frontmatter - these will be handled by other systems
- **Create Good Titles**: You should now specify titles for notes that follow good conventions:
  - Use specific, descriptive titles
  - Capitalize important words
  - Avoid vague titles like "Thoughts on X" or "Notes about Y"
  - Examples: "Spaced Repetition", "Decision Making Framework", "Cognitive Biases"
- All notes will automatically include `ai_generated: true` in their frontmatter
- You can provide additional custom frontmatter properties as needed
- Notes are saved with filenames based on the title provided
- Notes default to the '1 - Thoughts' folder; set `folder_path` relative to the vault root (e.g., `University/ANLP` or `/University/ANLP`) or provide an absolute path within the vault to direct notes elsewhere
- **Always repeat the full note content in your chat response after creating it**

### Writing Style and Structure

- **Focus on Ideas**: Write directly about the concepts themselves without attributing thoughts to anyone. Never reference "the author" or use phrases like "the writer believes". The focus should be purely on the ideas and information.
- **Atomic Notes**: Follow the "Atomic Notes" philosophy - one note should contain one main idea or concept. This makes notes more reusable and interconnectable.
- **Creating Links**: Rather than duplicating content, link to existing notes using Obsidian's markdown link syntax:
  - Internal links: `[[Note Title]]` or `[[Note Title|Display Text]]`
  - Section links: `[[Note Title#Section]]`
  - When referencing concepts that likely exist in other notes, create links to them
- **Language**: Use British English spelling and grammar in all notes.
- **Titles**: Create specific, descriptive titles with capitalized words and spaces between words (e.g., "Spaced Repetition" not "spaced-repetition" or "SpacedRepetition")

### Example

**Claude's tool call:**
```python
write_note(
    title="Cats are Despicable Creatures",
    content="[[Cats are Despicable Creatures]] presents a perspective on feline nature that contrasts sharply with common affection for these animals. While many appreciate their independence, certain behaviors can be interpreted as expressions of contempt rather than self-sufficiency.\n\nThis viewpoint forms an interesting counterpoint to [[Pet Ownership Benefits]], challenging the assumption that all domestic animals contribute equally to human wellbeing.",
    folder_path="Animal Perspectives"
)
```

**Claude should then also include the note content in its response:**
```
I've created a note titled "Cats are Despicable Creatures" in your vault. Here's the content:

[[Cats are Despicable Creatures]] presents a perspective on feline nature that contrasts sharply with common affection for these animals. While many appreciate their independence, certain behaviors can be interpreted as expressions of contempt rather than self-sufficiency.

This viewpoint forms an interesting counterpoint to [[Pet Ownership Benefits]], challenging the assumption that all domestic animals contribute equally to human wellbeing.
```

## Resources

The server provides these resources:

- **thoughts://stats**: Get statistics about your thoughts collection
- **thoughts://help**: Get help information about how to use the server

## Troubleshooting

If Claude reports issues finding or using the tools:

1. Ensure the server is properly installed in Claude Desktop
2. Check that the embeddings files exist (run the `build_thought_embeddings` tool if needed)
3. Verify that Ollama is running for embedding generation
4. Check the paths in the MCP server match your Obsidian vault structure

## Advanced Usage

### Running the Server Manually

You can also run the server manually if you prefer:

```bash
cd thoughts_embedding
python mcp_server.py
```

Or with debug logging:

```bash
python mcp_server.py --debug
```

### Customizing the Server

To customize the server for your specific needs, you can modify the constants at the top of the `mcp_server.py` file:

```python
# Constants
BODY_EMBEDDINGS_FILE = "thoughts_embedding/thought_embeddings.csv"
TITLE_EMBEDDINGS_FILE = "thoughts_embedding/title_embeddings.csv"
THOUGHTS_DIR = "/path/to/your/thoughts/directory"
```

# Building Embeddings

The first time you use the Thoughts Assistant, embeddings need to be built for your thoughts collection. This happens in two ways:

1. **Automatic**: The installation script attempts to build embeddings automatically if Ollama is running.

2. **Manual**: If automatic building fails or you need to rebuild embeddings later, run:
   ```
   cd /path/to/auto-tagger/thoughts_embedding
   ./build_embeddings_cli.py
   ```

**Important**: Embeddings only need to be built once, or when you add new thought documents. They are stored as CSV files (`title_embeddings.csv` and `thought_embeddings.csv`) and persist between Claude sessions.
