#!/usr/bin/env python3
"""
Markdown creator module for bsky2llm.
Converts Bluesky thread data to markdown with customizable formatting.
"""

import logging
import json
import os
from typing import Dict, Any, Optional, List, Union, Callable

# Import video and image processing functionality
try:
    # When used as a package
    from .process_video import has_video, video_to_markdown
    from .process_image import has_images, image_to_markdown
except ImportError:
    # When run directly as a script
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from bsky2llm.process_video import has_video, video_to_markdown
    from bsky2llm.process_image import has_images, image_to_markdown

def setup_logging(debug=False):
    """Configure logging based on debug mode"""
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level, 
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def _extract_post_data(post_obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract relevant data from a post object for formatting
    
    Args:
        post_obj: Raw post object from Bluesky API
        
    Returns:
        Dictionary with extracted fields for formatting
    """
    if not isinstance(post_obj, dict):
        return {}
        
    # Get basic post data
    post_data = {}
    
    # Extract post info
    post_data["uri"] = post_obj.get("uri", "")
    post_data["cid"] = post_obj.get("cid", "")
    
    # Extract author info
    author = post_obj.get("author", {})
    if isinstance(author, dict):
        post_data["did"] = author.get("did", "")
        post_data["handle"] = author.get("handle", "")
        post_data["displayName"] = author.get("displayName", author.get("handle", ""))
        post_data["avatar"] = author.get("avatar", "")
    
    # Extract post content
    record = post_obj.get("record", {})
    if isinstance(record, dict):
        post_data["text"] = record.get("text", "")
        post_data["createdAt"] = record.get("createdAt", "")
        
        # Handle facets (mentions, links, etc)
        facets = record.get("facets", [])
        if isinstance(facets, list) and facets:
            post_data["hasFacets"] = True
            post_data["facets"] = facets
        else:
            post_data["hasFacets"] = False
    
    # Extract engagement metrics
    post_data["replyCount"] = post_obj.get("replyCount", 0)
    post_data["repostCount"] = post_obj.get("repostCount", 0) 
    post_data["likeCount"] = post_obj.get("likeCount", 0)
    post_data["indexedAt"] = post_obj.get("indexedAt", "")
    
    # Extract embed data (images, external links)
    embed = post_obj.get("embed", {})
    if isinstance(embed, dict):
        embed_type = embed.get("$type", "")
        post_data["embedType"] = embed_type.split("#")[1] if "#" in embed_type else ""
        
        # Handle images
        if "images" in post_data["embedType"]:
            post_data["hasImage"] = True
            images = embed.get("images", [])
            if isinstance(images, list) and images:
                post_data["imageCount"] = len(images)
                post_data["images"] = images
        
        # Handle quotes
        elif "record" in post_data["embedType"]:
            post_data["hasQuote"] = True
            record = embed.get("record", {})
            if isinstance(record, dict):
                post_data["quoteUri"] = record.get("uri", "")
                post_data["quoteText"] = record.get("value", {}).get("text", "")
        
        # Handle external links
        elif "external" in post_data["embedType"]:
            post_data["hasExternal"] = True
            external = embed.get("external", {})
            if isinstance(external, dict):
                post_data["externalUrl"] = external.get("uri", "")
                post_data["externalTitle"] = external.get("title", "")
                post_data["externalDescription"] = external.get("description", "")
                post_data["externalThumb"] = external.get("thumb", "")
    
    return post_data

def _process_thread_node(
    node: Dict[str, Any], 
    format_str: str,
    depth: int = 0,
    include_replies: bool = True,
    max_depth: int = -1,
    filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
    include_indices: bool = False,
    process_media: bool = False,
    output_dir: str = "vault/media",
    current_index: List[int] = None,
    debug: bool = False,
    post_count: List[int] = None,
    max_posts: int = -1
) -> List[str]:
    """
    Process a thread node recursively and format as markdown
    
    Args:
        node: Thread node to process
        format_str: Format string template
        depth: Current depth in the thread
        include_replies: Whether to include replies
        max_depth: Maximum depth to process (-1 for unlimited)
        filter_fn: Optional function to filter posts
        include_indices: Whether to include hierarchical indices
        process_media: Whether to process media (videos, images) in posts
        output_dir: Directory to save extracted files
        current_index: Current index path (e.g., [1, 2, 3])
        debug: Enable verbose debug output
        post_count: Reference to a list containing the current post count [count]
        max_posts: Maximum number of posts to include (-1 for unlimited)
        
    Returns:
        List of formatted post strings
    """
    results = []
    
    if not isinstance(node, dict):
        return results
        
    # Initialize index if not provided
    if current_index is None:
        current_index = [1]
        
    # Initialize post count if not provided
    if post_count is None:
        post_count = [0]
        
    # Check if we've reached the maximum number of posts
    if max_posts > 0 and post_count[0] >= max_posts:
        logging.debug(f"Reached maximum post count ({max_posts}), stopping thread processing")
        return results
    
    # Get post object
    post_obj = node.get("post", {})
    if not isinstance(post_obj, dict):
        return results
        
    # Extract data for formatting
    post_data = _extract_post_data(post_obj)
    
    # Apply filter if provided
    if filter_fn is not None and not filter_fn(post_data):
        return results
    
    # Increment post count
    post_count[0] += 1
    
    # Add index information if requested
    if include_indices:
        index_str = ".".join(str(i) for i in current_index)
        post_data["index"] = index_str
        post_data["depth"] = depth
        post_data["indent"] = "  " * depth  # Add indentation based on depth
    
    # Format the post using the template
    try:
        post_md = format_str.format(**post_data)
        results.append(post_md)
        
        # Process media if requested
        if process_media:
            # Process video if present
            video_md = video_to_markdown(post_obj, output_dir=output_dir, debug=debug)
            if video_md:
                results.append(video_md)
                results.append("\n")
            
            # Process images if present
            image_md = image_to_markdown(post_obj, output_dir=output_dir, debug=debug)
            if image_md:
                results.append(image_md)
                results.append("\n")
            
    except KeyError as e:
        logging.error(f"Missing key in format string: {e}")
        # Fallback to basic format
        index_prefix = f"[{post_data.get('index', '')}] " if include_indices else ""
        post_md = f"{index_prefix}**{post_data.get('displayName', '')}** (@{post_data.get('handle', '')}):\n{post_data.get('text', '')}\n\n"
        results.append(post_md)
        
        # Add media in fallback mode too
        if process_media:
            video_md = video_to_markdown(post_obj, output_dir=output_dir, debug=debug)
            if video_md:
                results.append(video_md)
                results.append("\n")
                
            image_md = image_to_markdown(post_obj, output_dir=output_dir, debug=debug)
            if image_md:
                results.append(image_md)
                results.append("\n")
            
    except Exception as e:
        logging.error(f"Error formatting post: {e}")
        return results
        
    # Process replies if requested
    if include_replies and (max_depth < 0 or depth < max_depth):
        replies = node.get("replies", [])
        if isinstance(replies, list):
            for i, reply in enumerate(replies):
                # Check if we've reached the maximum number of posts
                if max_posts > 0 and post_count[0] >= max_posts:
                    logging.debug(f"Reached maximum post count ({max_posts}) during reply processing")
                    break
                    
                # Create new index for this reply
                reply_index = current_index.copy()
                if len(reply_index) <= depth + 1:
                    # Extend the index if needed
                    reply_index.extend([1] * (depth + 1 - len(reply_index) + 1))
                    
                # Set the specific sub-index for this reply
                reply_index[depth + 1] = i + 1
                
                # Process the reply with updated index
                reply_results = _process_thread_node(
                    reply, 
                    format_str, 
                    depth + 1,
                    include_replies,
                    max_depth,
                    filter_fn,
                    include_indices,
                    process_media,
                    output_dir,
                    reply_index,
                    debug,
                    post_count,
                    max_posts
                )
                results.extend(reply_results)
                
    return results

def thread_to_markdown(
    thread_data: Dict[str, Any], 
    format_str: str = "**{displayName}** (@{handle}):\n{text}\n\n",
    include_replies: bool = True,
    max_depth: int = -1,
    filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
    include_indices: bool = False,
    process_media: bool = False,
    output_dir: str = "vault/media",
    debug: bool = False,
    max_posts: int = -1
) -> str:
    """
    Convert thread data to a markdown string with customizable formatting.
    
    Args:
        thread_data (Dict[str, Any]): Thread data from Bluesky API
        format_str (str): Format string with placeholders for post attributes
                         Uses Python f-string style (e.g. "{displayName}")
        include_replies (bool): Whether to include replies in the output
        max_depth (int): Maximum depth of replies to include (-1 for all)
        filter_fn (Callable): Optional function to filter posts (return True to include)
        include_indices (bool): Whether to include hierarchical indices (like 1.2.3)
        process_media (bool): Whether to process and include media content (videos, images)
        output_dir (str): Directory to save extracted files from media
        debug (bool): Enable verbose debug output
        max_posts (int): Maximum number of posts to include (-1 for unlimited)
        
    Returns:
        str: Formatted markdown string
    """
    setup_logging(debug)
    logging.debug(f"Converting thread to markdown with format: {format_str}")
    
    # Create output directory if it doesn't exist and we're processing media
    if process_media and output_dir:
        # Create main media directory
        os.makedirs(output_dir, exist_ok=True)
        # Create subdirectories for different media types
        os.makedirs(os.path.join(output_dir, "images"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "frames"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "audio"), exist_ok=True)
    
    # Start processing from thread root
    thread_node = thread_data.get("thread", {})
    post_count = [0]  # Using a list to allow modification by reference
    post_mds = _process_thread_node(
        thread_node,
        format_str,
        0,
        include_replies,
        max_depth,
        filter_fn,
        include_indices,
        process_media,
        output_dir,
        None,
        debug,
        post_count,
        max_posts
    )
    
    # Join all formatted posts into a single markdown string
    markdown = "".join(post_mds)
    
    logging.debug(f"Generated {len(markdown)} characters of markdown with {post_count[0]} posts")
    return markdown

def main():
    """Main function with hardcoded example"""
    # Example thread data file
    input_file = "tests/raw_thread_3l6oveex3ii2l.json"

    
    try:
        # Load thread data from file
        with open(input_file, 'r', encoding='utf-8') as f:
            thread_data = json.load(f)
            
        print(f"\nLoaded thread data from: {input_file}")
        

        
        markdown = thread_to_markdown(
            thread_data,
            format_str="[{index}] **{displayName}** (@{handle}):\n{text}\n\n",
            include_replies=True,
            include_indices=True,
            process_media=True,  # Enable media processing
            debug=True,
            max_posts=50,
            max_depth=1,
            output_dir="tests/media"
        )
        

        # sve the markdown to a file
        output_file = "tests/markdown_example.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown)
        print(f"\nMarkdown saved to: {output_file}")
        
        # Print a sample of the markdown
        print("\nMarkdown sample:")
        print(markdown[:300] + "..." if len(markdown) > 300 else markdown)
            

            
    except FileNotFoundError:
        print(f"\nError: Thread data file '{input_file}' not found.")
        print("Run get_raw_thread.py first to fetch and save thread data.")
    except json.JSONDecodeError:
        print(f"\nError: Invalid JSON in thread data file: {input_file}")
    except Exception as e:
        print(f"\nError processing thread data: {e}")

if __name__ == "__main__":
    main()