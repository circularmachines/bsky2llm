#!/usr/bin/env python3
"""
Compose Markdown module for bsky2llm.
Converts Bluesky thread data into markdown format.
"""

import logging
import os
import json

def setup_logging(debug=False):
    """Configure logging based on debug mode"""
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level, 
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def compose_thread_markdown(thread_data: dict, debug: bool = False) -> str:
    """
    Convert a thread data structure to markdown format
    
    Args:
        thread_data: Thread data structure from get_post_thread
        debug: Enable verbose logging
        
    Returns:
        Markdown string representing the thread
    """
    setup_logging(debug)
    logging.debug(f"Composing markdown from thread data")
    
    # Process the thread data
    markdown = []
    
    try:
        # Handle root post
        if thread_data:
            # Get author info
            author = thread_data.get('author', {})
            author_name = author.get('display_name', '') or author.get('handle', 'unknown')
            author_handle = author.get('handle', 'unknown')
            
            # Add the author header
            markdown.append(f"## [{author_name} (@{author_handle})](https://bsky.app/profile/{author_handle})")
            
            # Add the post content
            content = thread_data.get('text', '')
            if content:
                markdown.append(f"\n{content}\n")
            
            # Process replies with numerical indices
            def process_replies(replies, index_prefix=""):
                for i, reply in enumerate(replies, 1):
                    # Construct the current index
                    current_index = f"{index_prefix}{i}" if index_prefix else f"{i}"
                    
                    # Get author information
                    author = reply.get('author', {})
                    author_name = author.get('display_name', '') or author.get('handle', 'unknown')
                    author_handle = author.get('handle', 'unknown')
                    
                    # Add reply with author info and index
                    markdown.append(f"{current_index}. ## [{author_name} (@{author_handle})](https://bsky.app/profile/{author_handle})")
                    
                    # Add the reply content
                    content = reply.get('text', '')
                    if content:
                        markdown.append(f"{content}\n")
                    
                    # Add a separator between posts
                    markdown.append(f"---\n")
                    
                    # Process nested replies with updated index prefix
                    if "replies" in reply:
                        process_replies(reply.get('replies', []), f"{current_index}.")
            
            # Process all replies
            if "replies" in thread_data:
                process_replies(thread_data.get('replies', []))
    
    except Exception as e:
        # Catch-all for any unexpected errors
        logging.error(f"Error generating markdown: {e}")
        markdown = ["# Error Generating Markdown", 
                    f"\nAn error occurred while generating the markdown: {str(e)}", 
                    "\nPlease check the logs for more details."]
    
    # If we still have no content, provide a fallback
    if not markdown:
        markdown = ["# No posts could be processed", 
                    "\nThe thread data did not contain any processable posts."]
    
    return '\n'.join(markdown)

def main():
    """Main function with hardcoded example"""
    # Create a minimal thread data structure for testing

    # Load thread data from a JSON file
    thread_data_path = "examples/thread_data_3lnb5ujk2cs24.json"
    
    try:
        with open(thread_data_path, "r") as f:
            thread_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at {thread_data_path}")
        thread_data = {}
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON from {thread_data_path}: {e}")
        thread_data = {}
    
    # Generate markdown from thread data
    print("\nGenerating markdown...")
    markdown = compose_thread_markdown(thread_data, debug=True)
    
    # Save markdown to file
    os.makedirs("vault", exist_ok=True)
    output_path = os.path.join("vault", "thread_markdown_output.md")
    with open(output_path, "w") as f:
        f.write(markdown)
    
    print(f"\nMarkdown file saved to: {output_path}")
    
    # Print the markdown content
    #print("\nMarkdown content:")
    #print("=================")
    #print(markdown)
    #print("=================")

if __name__ == "__main__":
    main()