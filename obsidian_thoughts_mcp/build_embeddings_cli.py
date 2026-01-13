#!/usr/bin/env python3
"""
Build Embeddings CLI

This script is a command-line tool to build embeddings for the thoughts collection.
It ensures proper paths and permissions are used.
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("build_embeddings_cli")

# Get script directory for proper path resolution
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)  # Make sure we can import from this directory

# Set the output file paths
TITLE_EMBEDDINGS_FILE = os.path.join(SCRIPT_DIR, "title_embeddings.csv")
BODY_EMBEDDINGS_FILE = os.path.join(SCRIPT_DIR, "thought_embeddings.csv")

def main():
    """Run the build_embeddings script with proper paths."""
    logger.info("Starting embeddings build process...")
    
    try:
        # Import the build_embeddings module
        import build_embeddings
        
        # Override the output file paths
        build_embeddings.TITLE_EMBEDDINGS_FILE = TITLE_EMBEDDINGS_FILE
        build_embeddings.BODY_EMBEDDINGS_FILE = BODY_EMBEDDINGS_FILE
        
        logger.info(f"Will save title embeddings to: {TITLE_EMBEDDINGS_FILE}")
        logger.info(f"Will save thought embeddings to: {BODY_EMBEDDINGS_FILE}")
        
        # Run the build_embeddings main function
        build_embeddings.main()
        
        logger.info("Embeddings built successfully!")
        
        # Verify the files were created
        if os.path.exists(TITLE_EMBEDDINGS_FILE) and os.path.exists(BODY_EMBEDDINGS_FILE):
            logger.info("Verified that embedding files were created successfully.")
            print("\n✅ Embeddings built successfully! You can now use the Thoughts Assistant in Claude.")
        else:
            logger.error("Embedding files were not created.")
            print("\n❌ Error: Embedding files were not created properly.")
            
    except Exception as e:
        logger.error(f"Error building embeddings: {e}", exc_info=True)
        print(f"\n❌ Error building embeddings: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 