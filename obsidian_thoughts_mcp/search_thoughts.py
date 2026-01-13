#!/usr/bin/env python3
"""
Thoughts Search Tool for Auto-Tagger Obsidian Plugin

This script takes a search query, generates an embedding for it, and finds the most
semantically similar thought document from the pre-generated embeddings. It returns the
full content of the top matching documents.
"""

import os
import sys
import json
import csv
import argparse
import numpy as np
from pathlib import Path
import requests
import re
from typing import Dict, List, Tuple, Optional

# Default settings - override these with environment variables if needed
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "mxbai-embed-large:latest")

# Input files
BODY_EMBEDDINGS_FILE = "thoughts_embedding/thought_embeddings.csv"
TITLE_EMBEDDINGS_FILE = "thoughts_embedding/title_embeddings.csv"

# Thoughts directory for reference
THOUGHTS_DIR = "/Users/aidanlowrie/Library/Mobile Documents/iCloud~md~obsidian/Documents/My Brain/1 - Thoughts"


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


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors
    """
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    
    # Convert to numpy arrays
    v1_np = np.array(v1)
    v2_np = np.array(v2)
    
    # Calculate dot product and norms
    dot_product = np.dot(v1_np, v2_np)
    norm_v1 = np.linalg.norm(v1_np)
    norm_v2 = np.linalg.norm(v2_np)
    
    # Avoid division by zero
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    
    # Return cosine similarity
    return dot_product / (norm_v1 * norm_v2)


def load_embeddings(csv_path: str) -> Dict[str, List[float]]:
    """Load embeddings from CSV file"""
    embeddings = {}
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # Skip header
            
            for row in reader:
                if len(row) == 2:
                    file_path, embedding_json = row
                    embedding = json.loads(embedding_json)
                    embeddings[file_path] = embedding
        
        print(f"Loaded {len(embeddings)} embeddings from {csv_path}")
        return embeddings
    except Exception as e:
        print(f"Error loading embeddings from {csv_path}: {e}")
        return {}


def get_document_content(file_path: str) -> str:
    """Read the content of a markdown file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return f"Error: Could not read file {file_path}"


def search_thoughts(query: str, max_results: int = 1, use_titles: bool = False) -> List[Tuple[str, float]]:
    """
    Search for thought documents similar to the query
    
    Args:
        query: The search query
        max_results: Maximum number of results to return
        use_titles: Whether to search in title embeddings (vs document embeddings)
        
    Returns:
        List of tuples with (file_path, similarity_score)
    """
    # Generate embedding for the query
    print(f"Generating embedding for query: {query}")
    query_embedding = embed_text(query)
    
    if not query_embedding:
        print("Failed to generate embedding for the query")
        return []
    
    # Load the appropriate embeddings
    embeddings_file = TITLE_EMBEDDINGS_FILE if use_titles else BODY_EMBEDDINGS_FILE
    document_embeddings = load_embeddings(embeddings_file)
    
    if not document_embeddings:
        print(f"No embeddings found in {embeddings_file}")
        return []
    
    # Calculate similarity with all documents
    similarities = []
    
    for file_path, embedding in document_embeddings.items():
        similarity = cosine_similarity(query_embedding, embedding)
        similarities.append((file_path, similarity))
    
    # Sort by similarity (highest first)
    similarities.sort(key=lambda x: x[1], reverse=True)
    
    # Return top results
    return similarities[:max_results]


def print_results(results: List[Tuple[str, float]], show_content: bool = True) -> None:
    """Print search results"""
    if not results:
        print("No matching documents found")
        return
    
    for i, (file_path, similarity) in enumerate(results):
        print(f"\n{i+1}. {file_path} (Similarity: {similarity:.4f})")
        
        if show_content:
            print("\n" + "="*80 + "\n")
            content = get_document_content(file_path)
            print(content)
            print("\n" + "="*80)


def main():
    """Main function to search thoughts"""
    # Simple argument parser for standard options
    parser = argparse.ArgumentParser(
        description="Search thoughts using semantic embeddings",
        epilog="You can also use --N (where N is a number) as a shorthand for --max-results N. Example: --5"
    )
    parser.add_argument("query", nargs="?", help="The search query")
    parser.add_argument("--max-results", type=int, default=1, help="Maximum number of results to return")
    parser.add_argument("--titles-only", action="store_true", help="Search only in document titles")
    parser.add_argument("--no-content", action="store_true", help="Don't display document content")
    
    # Parse the arguments
    args, unknown = parser.parse_known_args()
    
    # Check for --N style arguments
    max_results = args.max_results
    for arg in unknown:
        match = re.match(r'--(\d+)$', arg)
        if match:
            max_results = int(match.group(1))
            break
    
    # If no query was provided as a positional argument, check if it's in the unknown args
    query = args.query
    if query is None and unknown:
        # Use the first unknown argument that doesn't match --N as the query
        for arg in unknown:
            if not re.match(r'--\d+$', arg):
                query = arg
                break
    
    if not query:
        parser.error("the following arguments are required: query")
    
    # Check if Ollama API is accessible
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
        response.raise_for_status()
        print("Successfully connected to Ollama API")
    except Exception as e:
        print(f"Error connecting to Ollama API at {OLLAMA_BASE_URL}: {e}")
        print("Please make sure Ollama is running and the API URL is correct")
        sys.exit(1)
    
    # Verify embeddings files exist
    if not Path(BODY_EMBEDDINGS_FILE).exists() or not Path(TITLE_EMBEDDINGS_FILE).exists():
        print(f"Embeddings files not found. Please run build_embeddings.py first.")
        sys.exit(1)
    
    # Search for documents
    results = search_thoughts(
        query, 
        max_results=max_results, 
        use_titles=args.titles_only
    )
    
    # Print results
    print_results(results, show_content=not args.no_content)


if __name__ == "__main__":
    main() 