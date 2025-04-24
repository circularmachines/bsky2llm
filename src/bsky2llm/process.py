#!/usr/bin/env python3
"""
Process module for bsky2llm.
Orchestrates the execution of multiple scripts to process a Bluesky thread from URI to formatted markdown.
"""

import os
import logging
import json
import argparse
from typing import Dict, Any, Optional

# Import the required modules
try:
    # When used as a package
    from .get_raw_thread import get_raw_thread
    from .markdown_creator import thread_to_markdown
except ImportError:
    # When run directly as a script
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from bsky2llm.get_raw_thread import get_raw_thread
    from bsky2llm.markdown_creator import thread_to_markdown

def setup_logging(debug=False):
    """Configure logging based on debug mode"""
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level, 
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def process_post(
    post_uri: str, 
    get_root: bool = True,
    format_str: str = "**{displayName}** (@{handle}):\n{text}\n\n",
    include_replies: bool = True,
    max_depth: int = -1,
    include_indices: bool = False,
    process_media: bool = True,
    output_dir: str = "output",
    output_filename: Optional[str] = None,
    debug: bool = False
) -> Optional[str]:
    """
    Process a Bluesky post from URI to formatted markdown
    
    Args:
        post_uri: The Bluesky post URI to process
        get_root: If True, get the root post of the thread
        format_str: Format string template for markdown conversion
        include_replies: Whether to include replies in the output
        max_depth: Maximum depth of replies to include (-1 for all)
        include_indices: Whether to include hierarchical indices
        process_media: Whether to process media (videos, images) in posts
        output_dir: Directory to save extracted files and markdown
        output_filename: Custom filename for the output markdown file (without extension)
        debug: Enable verbose debug output
        
    Returns:
        Path to the generated markdown file or None if processing failed
    """
    setup_logging(debug)
    
    # Create output directory if it doesn't exist
    media_dir = os.path.join(output_dir, "media")
    os.makedirs(media_dir, exist_ok=True)
    
    # Step 1: Get the raw thread data
    logging.info(f"Fetching raw thread data for: {post_uri}")
    raw_thread_data = get_raw_thread(post_uri, get_root=get_root, debug=debug)
    
    if not raw_thread_data:
        logging.error("Failed to fetch raw thread data")
        return None
    
    # Extract post ID for default filename
    try:
        thread_post_uri = raw_thread_data.get("thread", {}).get("post", {}).get("uri", "")
        post_id = thread_post_uri.split('/')[-1] if thread_post_uri else post_uri.split('/')[-1]
    except Exception:
        post_id = "thread"
    
    # Create output directory if it doesn't exist
    raw_dir = os.path.join(output_dir, "thread_data")
    os.makedirs(raw_dir, exist_ok=True)

    # Save raw thread data
    raw_data_path = os.path.join(raw_dir, f"raw_thread_{post_id}.json")
    try:
        with open(raw_data_path, 'w', encoding='utf-8') as f:
            json.dump(raw_thread_data, f, indent=2)
        logging.info(f"Raw thread data saved to: {raw_data_path}")
    except Exception as e:
        logging.error(f"Failed to save raw thread data: {e}")
    
    # Step 2: Convert to markdown
    logging.info("Converting thread to markdown")
    markdown = thread_to_markdown(
        raw_thread_data,
        format_str=format_str,
        include_replies=include_replies,
        max_depth=max_depth,
        include_indices=include_indices,
        process_media=process_media,
        output_dir=media_dir,
        debug=debug
    )
    
    if not markdown:
        logging.error("Failed to convert thread to markdown")
        return None
    
    # Determine output filename
    if output_filename:
        md_filename = f"{output_filename}.md"
    else:
        #prefix = "indexed_" if include_indices else ""
        md_filename = f"thread_{post_id}.md"
    
    # Save markdown
    md_path = os.path.join(output_dir, md_filename)
    try:
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        logging.info(f"Markdown saved to: {md_path}")
        return md_path
    except Exception as e:
        logging.error(f"Failed to save markdown: {e}")
        return None

def main():
    """Main function with hardcoded example"""
    debug = True
    setup_logging(debug)
    
    # Example post URI
    post_uri = "at://did:plc:evocjxmi5cps2thb4ya5jcji/app.bsky.feed.post/3lmjg3ridak2g"
    
    # Process with indices
    print(f"\nProcessing post: {post_uri}")
    output_path = process_post(
        post_uri=post_uri,
        get_root=True,
        format_str="[{index}] **{displayName}** (@{handle}):\n{text}\n\n",
        include_replies=True,
        include_indices=True,
        process_media=True,
        output_dir="output",
        debug=True
    )
    
    if output_path:
        print(f"\nProcessing complete! Output saved to: {output_path}")
        
        # Display a preview of the markdown
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
                preview_length = min(300, len(content))
                print(f"\nMarkdown preview:\n{content[:preview_length]}...")
        except Exception as e:
            print(f"\nCould not display preview: {e}")
    else:
        print("\nProcessing failed")

if __name__ == "__main__":
    main()