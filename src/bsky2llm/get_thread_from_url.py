#!/usr/bin/env python3
"""
Helper script to convert a Bluesky web URL (bsky.app link) to a post URI
and retrieve the full thread information.

Usage:
    python get_thread_from_url.py https://bsky.app/profile/username/post/postid
"""


import logging
import requests

def setup_logging():
    """Set up logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    return logging.getLogger(__name__)

def convert_url_to_uri(bluesky_url: str):
    """
    Convert a Bluesky web URL to a post URI.
    
    Example:
    https://bsky.app/profile/sharedinventory.bsky.social/post/3lmjaz2x63c2c
    ->
    at://did:plc:xxx/app.bsky.feed.post/3lmjaz2x63c2c
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Validate URL format
        if not bluesky_url.startswith("https://bsky.app/profile/"):
            raise ValueError("Invalid Bluesky URL format. Expected: https://bsky.app/profile/username/post/postid")
        
        # Parse URL components more reliably using string operations
        # Remove query parameters if any
        clean_url = bluesky_url.split('?')[0].rstrip('/')
        
        # Extract the parts after 'profile/'
        profile_part = clean_url.split('profile/')[1]
        
        # Check if we have the expected format with '/post/'
        if '/post/' not in profile_part:
            raise ValueError("Invalid Bluesky URL format. Expected: https://bsky.app/profile/username/post/postid")
        
        # Split into handle and post ID
        handle_part, post_part = profile_part.split('/post/', 1)
        handle = handle_part.strip('/')
        rkey = post_part.strip('/')
        
        logger.info(f"Extracted handle: {handle}, post ID: {rkey}")
        
        # Resolve handle to DID using Bluesky's public API
        logger.info(f"Resolving handle to DID: {handle}")
        response = requests.get(f"https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle", 
                               params={"handle": handle})
        response.raise_for_status()
        
        did = response.json().get("did")
        if not did:
            raise ValueError(f"Failed to resolve handle to DID: {handle}")
            
        logger.info(f"Resolved DID: {did}")
        
        # Construct post URI
        post_uri = f"at://{did}/app.bsky.feed.post/{rkey}"
        logger.info(f"Constructed post URI: {post_uri}")
        
        return post_uri
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        return None
    except ValueError as e:
        logger.error(str(e))
        return None
    except Exception as e:
        logger.error(f"Error converting URL to URI: {str(e)}")
        return None

