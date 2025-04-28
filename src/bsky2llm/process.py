#!/usr/bin/env python3
"""
Process module for bsky2llm.
Orchestrates the execution of multiple scripts to process a Bluesky thread from URI to formatted markdown,
and optionally convert to OpenAI messages for AI API calls.
"""

import os
import logging
import json
import argparse
from typing import Dict, Any, Optional, List, Union, Tuple

# Import the required modules
try:
    # When used as a package
    from .get_raw_thread import get_raw_thread
    from .markdown_creator import thread_to_markdown
    from .url_converter import convert_url_to_uri
    from .md_to_openai import parse_markdown
    from .ai_api_call import main_interface_function as call_ai_api
except ImportError:
    # When run directly as a script
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from bsky2llm.get_raw_thread import get_raw_thread
    from bsky2llm.markdown_creator import thread_to_markdown
    from bsky2llm.url_converter import convert_url_to_uri
    from bsky2llm.md_to_openai import parse_markdown
    from bsky2llm.ai_api_call import main_interface_function as call_ai_api

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
    format_str: str = "*[{index}]* **{displayName}** (@{handle}):\n{text}\n\n",
    include_replies: bool = True,
    max_depth: int = -1,
    include_indices: bool = True,
    process_media: bool = True,
    output_dir: str = "output",
    output_filename: Optional[str] = None,
    debug: bool = False,
    max_posts: int = -1,
    # AI parameters
    get_ai_response: bool = True,
    system_message: str = "You are a helpful assistant. Analyze the following Bluesky thread and provide insights.",
    output_messages_file: Optional[str] = None,
    output_response_file: Optional[str] = None
) -> Union[str, Tuple[str, Optional[str]]]:
    """
    Process a Bluesky post from URI or URL to formatted markdown and optionally get AI response
    
    Args:
        post_uri: The Bluesky post URI or URL to process
        get_root: If True, get the root post of the thread
        format_str: Format string template for markdown conversion
        include_replies: Whether to include replies in the output
        max_depth: Maximum depth of replies to include (-1 for all)
        include_indices: Whether to include hierarchical indices
        process_media: Whether to process media (videos, images) in posts
        output_dir: Directory to save extracted files and markdown
        output_filename: Custom filename for the output markdown file (without extension)
        debug: Enable verbose debug output
        max_posts: Maximum number of posts to include (-1 for unlimited)
        get_ai_response: If True, generate AI response from the markdown content
        system_message: System message to use for AI if get_ai_response is True
        output_messages_file: Custom filename for the OpenAI messages JSON file (without extension)
        output_response_file: Custom filename for the AI response text file (without extension)
        
    Returns:
        If get_ai_response is False:
            Path to the generated markdown file or None if processing failed
        If get_ai_response is True:
            Tuple of (markdown_path, ai_response) or (markdown_path, None) if AI processing failed
    """
    setup_logging(debug)
    
    # Convert URL to URI if needed
    if post_uri.startswith('http'):
        logging.info(f"Converting URL to URI: {post_uri}")
        uri = convert_url_to_uri(post_uri, debug=debug)
        if not uri:
            logging.error(f"Failed to convert URL to URI: {post_uri}")
            return None
        post_uri = uri
        logging.info(f"Using URI: {post_uri}")
    
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
        debug=debug,
        max_posts=max_posts
    )
    
    if not markdown:
        logging.error("Failed to convert thread to markdown")
        return None
    
    # Determine output filename
    if output_filename:
        md_filename = f"{output_filename}.md"
    else:
        md_filename = f"thread_{post_id}.md"
    
    # Save markdown
    md_path = os.path.join(output_dir, md_filename)
    try:
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        logging.info(f"Markdown saved to: {md_path}")
    except Exception as e:
        logging.error(f"Failed to save markdown: {e}")
        return None
    
    # If AI response is not requested, return the markdown path
    if not get_ai_response:
        return md_path
    
    # Step 3: Convert markdown to OpenAI messages (if AI response is requested)
    logging.info(f"Converting markdown to OpenAI messages: {md_path}")
    messages = parse_markdown(md_path, system_message)
    
    if not messages:
        logging.error("Failed to convert markdown to OpenAI messages")
        return md_path, None
    
    # Determine output messages filename
    if output_messages_file:
        messages_filename = f"{output_messages_file}.json"
    else:
        messages_filename = f"messages_{post_id}.json"
    
    # Save messages
    messages_path = os.path.join(output_dir, messages_filename)
    try:
        with open(messages_path, 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=4)
        logging.info(f"OpenAI messages saved to: {messages_path}")
    except Exception as e:
        logging.error(f"Failed to save OpenAI messages: {e}")
    
    # Step 4: Call AI API
    logging.info("Calling AI API")
    response = call_ai_api(messages_path, debug=debug)
    
    if not response:
        logging.error("Failed to get AI response")
        return md_path, None
    
    # Determine output response filename
    if output_response_file:
        response_filename = f"{output_response_file}.txt"
    else:
        response_filename = f"response_{post_id}.txt"
    
    # Save response
    response_path = os.path.join(output_dir, response_filename)
    try:
        with open(response_path, 'w', encoding='utf-8') as f:
            f.write(response)
        logging.info(f"AI response saved to: {response_path}")
    except Exception as e:
        logging.error(f"Failed to save AI response: {e}")
    
    # Return both the markdown path and the AI response
    return response

def main():
    """Main function with hardcoded example"""
    debug = True
    setup_logging(debug)
    
    # Example post URL (instead of URI)
    post_url = "https://bsky.app/profile/atproto.com/post/3jwgckq72jp2d"
    
    # Process post with AI response
    print(f"\nProcessing post: {post_url}")
    result = process_post(
        post_uri=post_url,
        get_root=True,
        format_str="[{index}] **{displayName}** (@{handle}):\n{text}\n\n",
        include_replies=True,
        include_indices=True,
        process_media=True,
        output_dir="output",
        debug=True,
        get_ai_response=True,
        system_message="You are a helpful assistant analyzing a Bluesky thread. Provide a concise summary and identify key points."
    )
    
    if result:
        if isinstance(result, tuple):
            md_path, ai_response = result
            print(f"\nProcessing complete! Markdown output saved to: {md_path}")
            
            # Display a preview of the markdown
            try:
                with open(md_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    preview_length = min(300, len(content))
                    print(f"\nMarkdown preview:\n{content[:preview_length]}...")
            except Exception as e:
                print(f"\nCould not display preview: {e}")
            
            if ai_response:
                print("\nAI Response:")
                print(ai_response)
            else:
                print("\nAI processing failed")
        else:
            print(f"\nProcessing to markdown complete! Output saved to: {result}")
            
            # Display a preview of the markdown
            try:
                with open(result, 'r', encoding='utf-8') as f:
                    content = f.read()
                    preview_length = min(300, len(content))
                    print(f"\nMarkdown preview:\n{content[:preview_length]}...")
            except Exception as e:
                print(f"\nCould not display preview: {e}")
    else:
        print("\nProcessing failed")

if __name__ == "__main__":
    main()