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

def convert_uri_to_url(uri: str, debug: bool = False) -> Optional[str]:
    """
    Convert an ATProto URI to a Bluesky URL
    
    Args:
        uri: ATProto URI (e.g., at://did:plc:xyz/app.bsky.feed.post/3abc123)
        debug: Enable verbose debug output
        
    Returns:
        Bluesky URL or None if conversion failed
    """
    if debug:
        setup_logging(debug)
    
    logging.debug(f"Converting URI to URL: {uri}")
    
    # Check if it's already a URL
    if uri.startswith("http"):
        logging.debug("Input is already a URL")
        return uri
    
    # Standard ATProto URI pattern
    pattern = r'at://([^/]+)/([^/]+)/([^/]+)'
    match = re.match(pattern, uri)
    
    if not match:
        logging.error(f"Invalid ATProto URI format: {uri}")
        return None
    
    did = match.group(1)
    record_type = match.group(2)
    record_id = match.group(3)
    
    # Only handle post URIs for now
    if record_type != "app.bsky.feed.post":
        logging.error(f"Unsupported record type: {record_type}")
        return None
    
    # Get handle from DID (this requires an API call)
    try:
        response = requests.get(f'https://public.api.bsky.app/xrpc/com.atproto.identity.getHandle?did={did}')
        response.raise_for_status()
        handle = response.json().get('handle')
        
        if not handle:
            logging.error(f"Could not resolve DID to handle: {did}")
            return None
            
        # Construct the URL
        url = f"https://bsky.app/profile/{handle}/post/{record_id}"
        logging.debug(f"Converted to URL: {url}")
        
        return url
        
    except Exception as e:
        logging.error(f"Failed to resolve DID to handle: {e}")
        return None

def main():
    """Main function with hardcoded examples"""
    debug = True
    setup_logging(debug)
    
    # Example URL
    url = "https://bsky.app/profile/atproto.com/post/3jwgckq72jp2d"
    
    # Convert URL to URI
    print(f"\nConverting URL to URI:")
    print(f"URL: {url}")
    uri = convert_url_to_uri(url, debug=True)
    
    if uri:
        print(f"URI: {uri}")
        
        # Convert back to URL
        print(f"\nConverting URI back to URL:")
        print(f"URI: {uri}")
        back_url = convert_uri_to_url(uri, debug=True)
        
        if back_url:
            print(f"URL: {back_url}")
        else:
            print("Conversion failed")
    else:
        print("Conversion failed")

if __name__ == "__main__":
    main()