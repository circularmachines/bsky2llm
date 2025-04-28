#!/usr/bin/env python3
"""
Get raw post thread module for bsky2llm.
Fetches and saves raw thread data from a Bluesky post URI without processing.
"""

import requests
import logging
import json
from typing import Dict, Any, Optional

def setup_logging(debug=False):
    """Configure logging based on debug mode"""
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level, 
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def get_root_uri(post_uri: str, debug: bool = False) -> Optional[str]:
    """
    Find the root post URI of a thread by checking the post's reply parent field.
    
    Args:
        post_uri (str): The Bluesky post URI to check
        debug (bool): Enable verbose debug output
        
    Returns:
        Optional[str]: The root post URI if found, or None
    """
    setup_logging(debug)
    logging.debug(f"Finding root URI for post: {post_uri}")
    
    api_url = "https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread"
    params = {
        "uri": post_uri,
        "depth": 0  # Minimal depth needed just to get post data
    }
    
    try:
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Check if this post is a reply and has a root
        thread = data.get("thread", {})
        if not isinstance(thread, dict):
            logging.warning("Thread field is not a dictionary")
            return None
            
        post = thread.get("post", {})
        if not isinstance(post, dict):
            logging.warning("Post field is not a dictionary")
            return None
            
        record = post.get("record", {})
        if not isinstance(record, dict):
            logging.warning("Record field is not a dictionary")
            return None
        
        # Check for root in reply field
        reply = record.get("reply", {})
        if isinstance(reply, dict) and "root" in reply and isinstance(reply["root"], dict):
            root_uri = reply["root"].get("uri")
            if root_uri:
                logging.debug(f"Found root URI: {root_uri}")
                return root_uri
                
        # If no root was found, this might be the root post already
        logging.debug("No root found, this post might be the root itself")
        return post_uri
        
    except Exception as e:
        logging.error(f"Error finding root URI: {e}")
        return None

def get_raw_thread(post_uri: str, get_root: bool = False, debug: bool = False) -> Optional[Dict[str, Any]]:
    """
    Fetch raw thread data from a Bluesky post URI using the public API.
    
    Args:
        post_uri (str): The Bluesky post URI (at://did:plc:xyz/app.bsky.feed.post/123)
        get_root (bool): If True, get the root post of this thread instead of the current post
        debug (bool): Enable verbose debug output
        
    Returns:
        Optional[Dict[str, Any]]: Raw thread data exactly as returned by the API,
        or None if the fetch failed
    """
    setup_logging(debug)
    logging.debug(f"Fetching raw thread data for URI: {post_uri}")
    
    # If get_root is True, first find the root post URI
    target_uri = post_uri
    if get_root:
        root_uri = get_root_uri(post_uri, debug)
        if root_uri:
            logging.debug(f"Will fetch thread for root URI: {root_uri} instead of original post")
            target_uri = root_uri
        else:
            logging.warning("Could not determine root URI, using original post URI")
    
    # Now fetch the thread for the target URI
    api_url = "https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread"
    params = {
        "uri": target_uri,
        "depth": 100,  # Get a deep thread for complete context
    }
    
    try:
        logging.debug(f"Making API request to: {api_url} with params: {params}")
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        logging.debug(f"Received {len(str(data))} bytes of raw data")
        
        if debug:
            logging.debug(f"Sample of raw data: {json.dumps(data, indent=2)[:500]}...")
        
        return data
        
    except requests.RequestException as e:
        logging.error(f"API request failed: {e}")
        return None
    except ValueError as e:
        logging.error(f"Failed to parse API response: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return None

def main():
    """Main function with hardcoded example"""
    # Example post URI
    post_uri = "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.post/3l6oveex3ii2l"
    
    # Get the root thread data
    get_root = True
    
    raw_thread_data = get_raw_thread(post_uri, get_root=get_root, debug=True)
    
    if raw_thread_data:
        print("\nRaw thread data fetched successfully")
        
        # Save raw thread data to file - use root post ID for filename
        # Try to extract the root post ID from the thread data
        root_post_id = None
        
        try:
            # Get the actual post URI of what we fetched (may be root or original)
            thread_post_uri = raw_thread_data.get("thread", {}).get("post", {}).get("uri", "")
            if thread_post_uri:
                # Extract the post ID from the URI
                root_post_id = thread_post_uri.split('/')[-1]
            
            # If we couldn't get the ID from the URI, default to original post ID
            if not root_post_id:
                root_post_id = post_uri.split('/')[-1]
                
            # Save file with the root post ID (no suffix)
            output_file = f"raw_thread_{root_post_id}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(raw_thread_data, f, indent=2)
            print(f"\nRaw thread data saved to: {output_file}")
            
        except Exception as e:
            print(f"\nFailed to save raw thread data: {e}")
    else:
        print("\nFailed to fetch raw thread data")

if __name__ == "__main__":
    main()