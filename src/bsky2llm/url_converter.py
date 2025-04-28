#!/usr/bin/env python3
"""
URL converter module for bsky2llm.
Converts between Bluesky URLs and ATProto URIs.
"""

import logging
import re
from typing import Optional
import requests

def setup_logging(debug=False):
    """Configure logging based on debug mode"""
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level, 
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def _resolve_did(handle: str) -> Optional[str]:
    """
    Resolve a Bluesky handle to a DID
    
    Args:
        handle: Bluesky handle to resolve
        
    Returns:
        DID string or None if resolution failed
    """
    try:
        response = requests.get(f'https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle?handle={handle}')
        response.raise_for_status()
        return response.json().get('did')
    except Exception as e:
        logging.error(f"Failed to resolve DID for {handle}: {e}")
        return None

def convert_url_to_uri(url: str, debug: bool = False) -> Optional[str]:
    """
    Convert a Bluesky URL to an ATProto URI
    
    Args:
        url: Bluesky URL (e.g., https://bsky.app/profile/username.bsky.social/post/3abc123)
        debug: Enable verbose debug output
        
    Returns:
        ATProto URI or None if conversion failed
    """
    if debug:
        setup_logging(debug)
    
    logging.debug(f"Converting URL to URI: {url}")
    
    # Check if it's already a URI
    if url.startswith("at://"):
        logging.debug("Input is already a URI")
        return url
    
    # Standard Bluesky URL pattern
    pattern = r'https?://(?:www\.)?bsky\.app/profile/([^/]+)/post/([^/?&#]+)'
    match = re.match(pattern, url)
    
    if not match:
        logging.error(f"Invalid Bluesky URL format: {url}")
        return None
    
    handle = match.group(1)
    post_id = match.group(2)
    
    # Resolve handle to DID
    did = _resolve_did(handle)
    if not did:
        logging.error(f"Could not resolve handle to DID: {handle}")
        return None
    
    # Construct the URI
    uri = f"at://{did}/app.bsky.feed.post/{post_id}"
    logging.debug(f"Converted to URI: {uri}")
    
    return uri

def main():
    """Main function with hardcoded examples"""
    debug = True
    setup_logging(debug)
    
    # Example URL
    url="https://bsky.app/profile/bsky.app/post/3l6oveex3ii2l"
    
    # Convert URL to URI
    print(f"\nConverting URL to URI:")
    print(f"URL: {url}")
    uri = convert_url_to_uri(url, debug=True)
    
    if uri:
        print(f"URI: {uri}")
    else:
        print("Conversion failed")

if __name__ == "__main__":
    main()