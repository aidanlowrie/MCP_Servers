#!/usr/bin/env python3
"""
Thoughts Embeddings Builder for Auto-Tagger Obsidian Plugin

This script recursively walks through all Markdown files in the '1 - Thoughts' directory,
generates embeddings for both the title and content of each file, and saves them
to CSV files for later use in similarity searches.

Uses batch processing with ThreadPoolExecutor for parallel embedding generation.
"""

import os
import json
import csv
import sys
import time
import concurrent.futures
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import requests
import tqdm

# Default settings - override these with environment variables if needed
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "mxbai-embed-large:latest")

# Concurrency and batching settings
BATCH_SIZE = 100  # Process files in batches of this size
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "100"))  # Maximum number of concurrent workers
BATCH_DELAY_MS = 200  # Delay between batches in milliseconds

# Output files
TITLE_EMBEDDINGS_FILE = "thoughts_embedding/title_embeddings.csv"
BODY_EMBEDDINGS_FILE = "thoughts_embedding/thought_embeddings.csv"

# Thoughts directory to process - path to the vault's '1 - Thoughts' folder
THOUGHTS_DIR = "/Users/aidanlowrie/Library/Mobile Documents/iCloud~md~obsidian/Documents/My Brain/1 - Thoughts"


def get_title_from_markdown(filepath: Path) -> str:
    """Extract the title from a markdown file (first line, without # prefix)"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            # Remove markdown heading markers
            if first_line.startswith("#"):
                return first_line.lstrip("#").strip()
            return first_line
    except Exception as e:
        print(f"Error reading title from {filepath}: {e}")
        return os.path.basename(filepath)


def get_content_from_markdown(filepath: Path) -> str:
    """Read the entire content of a markdown file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading content from {filepath}: {e}")
        return ""


def embed_text(text: str, model: str = EMBEDDING_MODEL) -> Optional[List[float]]:
    """Generate embeddings for text using Ollama API"""
    if not text.strip():
        return None
    
    url = f"{OLLAMA_BASE_URL}/api/embeddings"
    
    payload = {
        "model": model,
        "prompt": text
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        if "embedding" not in data:
            print(f"Error: No embedding in response: {data}")
            return None
            
        return data["embedding"]
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None


def write_embeddings_to_csv(embeddings: Dict[str, List[float]], output_file: str):
    """Write embeddings to a CSV file"""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['file_path', 'embedding'])
        
        for file_path, embedding in embeddings.items():
            # Convert embedding to JSON string
            embedding_json = json.dumps(embedding)
            writer.writerow([file_path, embedding_json])


def process_file(filepath: Path) -> Tuple[str, Optional[List[float]], Optional[List[float]]]:
    """Process a single file to extract title and content embeddings"""
    # Store the absolute path as the identifier
    file_path_str = str(filepath)
    title = get_title_from_markdown(filepath)
    content = get_content_from_markdown(filepath)
    
    # Skip empty files
    if not content.strip():
        print(f"Skipping empty file: {file_path_str}")
        return file_path_str, None, None
    
    # Generate title embedding
    title_embedding = embed_text(title)
    
    # Generate content embedding
    content_embedding = embed_text(content)
    
    return file_path_str, title_embedding, content_embedding


def process_batch(files: List[Path]) -> Dict[str, Dict[str, Any]]:
    """Process a batch of files concurrently using ThreadPoolExecutor"""
    results = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks to the executor
        future_to_file = {
            executor.submit(process_file, filepath): filepath 
            for filepath in files
        }
        
        # Process completed tasks as they finish
        for future in concurrent.futures.as_completed(future_to_file):
            filepath = future_to_file[future]
            try:
                file_path, title_embedding, content_embedding = future.result()
                results[file_path] = {
                    "title": title_embedding,
                    "content": content_embedding
                }
            except Exception as e:
                print(f"Error processing file {filepath}: {e}")
    
    return results


def main():
    """Main function to build thoughts embeddings"""
    start_time = time.time()
    print(f"Starting thoughts embedding process using model: {EMBEDDING_MODEL}")
    print(f"Looking for Markdown files in: {THOUGHTS_DIR}")
    print(f"Using up to {MAX_WORKERS} concurrent workers")
    
    # Check if Ollama API is accessible
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
        response.raise_for_status()
        print("Successfully connected to Ollama API")
    except Exception as e:
        print(f"Error connecting to Ollama API at {OLLAMA_BASE_URL}: {e}")
        print("Please make sure Ollama is running and the API URL is correct")
        sys.exit(1)
    
    # Get all markdown files in the thoughts directory (including subdirectories)
    markdown_files = list(Path(THOUGHTS_DIR).glob("**/*.md"))
    
    if not markdown_files:
        print(f"No Markdown files found in {THOUGHTS_DIR}")
        sys.exit(0)
    
    total_files = len(markdown_files)
    print(f"Found {total_files} Markdown files")
    
    # Containers for embeddings
    title_embeddings = {}
    body_embeddings = {}
    
    # Process files in batches
    for i in range(0, len(markdown_files), BATCH_SIZE):
        batch = markdown_files[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (total_files + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"Processing batch {batch_num}/{total_batches} with {len(batch)} files")
        
        # Process the batch with concurrent execution
        batch_results = process_batch(batch)
        
        # Extract and store results
        for file_path, embeddings in batch_results.items():
            title_emb = embeddings["title"]
            content_emb = embeddings["content"]
            
            if title_emb:
                title_embeddings[file_path] = title_emb
            
            if content_emb:
                body_embeddings[file_path] = content_emb
        
        # Show progress after each batch
        processed = min(i + BATCH_SIZE, total_files)
        print(f"Progress: {processed}/{total_files} files ({processed/total_files*100:.1f}%)")
        
        # Apply batch delay if not the last batch
        if i + BATCH_SIZE < len(markdown_files):
            time.sleep(BATCH_DELAY_MS / 1000)
    
    # Write embeddings to CSV files
    write_embeddings_to_csv(title_embeddings, TITLE_EMBEDDINGS_FILE)
    write_embeddings_to_csv(body_embeddings, BODY_EMBEDDINGS_FILE)
    
    elapsed_time = time.time() - start_time
    print(f"Process complete in {elapsed_time:.2f} seconds!")
    print(f"Generated embeddings for {len(title_embeddings)} titles and {len(body_embeddings)} documents")
    print(f"Title embeddings saved to: {TITLE_EMBEDDINGS_FILE}")
    print(f"Document embeddings saved to: {BODY_EMBEDDINGS_FILE}")


if __name__ == "__main__":
    main() 