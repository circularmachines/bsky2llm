#!/usr/bin/env python3
"""
Get post thread module for bsky2llm.
Fetches complete thread data from a Bluesky post URI.
"""

import requests
import logging
import json
from typing import Dict, Any, Optional, List

def setup_logging(debug=False):
    """Configure logging based on debug mode"""
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level, 
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def _extract_media_from_post(post: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract media information from a post with comprehensive checking
    
    Args:
        post: Post data dictionary
        
    Returns:
        List of media items with type and URI
    """
    media = []
    
    if not isinstance(post, dict):
        logging.warning(f"Post is not a dictionary: {type(post)}")
        return []

    # Safely access nested fields
    def safe_get(obj, *keys, default=None):
        if not isinstance(obj, dict):
            return default
        current = obj
        for key in keys:
            if not isinstance(current, dict):
                return default
            if key not in current:
                return default
            current = current[key]
        return current
    
    # Extract embed from different possible locations
    embed = None
    if "embed" in post:
        embed = post["embed"]
    elif safe_get(post, "record", "embed") is not None:
        embed = safe_get(post, "record", "embed")
    
    # No embed found, return empty list
    if not isinstance(embed, dict):
        return []
    
    # Extract images from embed
    images = safe_get(embed, "images")
    if isinstance(images, list):
        for image in images:
            if not isinstance(image, dict):
                continue
            fullsize = safe_get(image, "fullsize")
            if isinstance(fullsize, str) and fullsize:
                media.append({
                    "type": "image",
                    "uri": fullsize,
                    "alt": safe_get(image, "alt", default="")
                })
    
    # Extract external links
    external = safe_get(embed, "external")
    if isinstance(external, dict):
        uri = safe_get(external, "uri", default="")
        if uri:
            media_item = {
                "type": "link",
                "uri": uri,
                "title": safe_get(external, "title", default=""),
                "description": safe_get(external, "description", default="")
            }
            
            # Add thumbnail if available
            thumb = safe_get(external, "thumb")
            if isinstance(thumb, dict):
                thumbnail_url = safe_get(thumb, "url", default="")
                if thumbnail_url:
                    media_item["thumbnail"] = thumbnail_url
            
            media.append(media_item)
    
    # Find video in various possible locations
    
    # 1. Direct video in embed
    video = safe_get(embed, "video")
    if isinstance(video, dict):
        url = safe_get(video, "url") or safe_get(video, "currentSrc", default="")
        if url:
            media.append({
                "type": "video",
                "uri": url,
                "poster": safe_get(video, "poster", default="")
            })
    
    # 2. Video in media structure
    media_obj = safe_get(embed, "media")
    if isinstance(media_obj, dict):
        # Check for direct video in media
        video = safe_get(media_obj, "video")
        if isinstance(video, dict):
            url = safe_get(video, "url") or safe_get(video, "currentSrc", default="")
            if url:
                media.append({
                    "type": "video",
                    "uri": url,
                    "poster": safe_get(video, "poster", default="")
                })
        
        # Check for items array containing videos or images
        items = safe_get(media_obj, "items")
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                
                # Check for video in item
                item_video = safe_get(item, "video")
                if isinstance(item_video, dict):
                    url = safe_get(item_video, "url") or safe_get(item_video, "currentSrc", default="")
                    if url:
                        media.append({
                            "type": "video",
                            "uri": url,
                            "poster": safe_get(item_video, "poster", default="")
                        })
                
                # Check for image in item
                item_image = safe_get(item, "image")
                if isinstance(item_image, dict):
                    url = safe_get(item_image, "url") or safe_get(item_image, "fullsize", default="")
                    if url:
                        media.append({
                            "type": "image",
                            "uri": url,
                            "alt": safe_get(item_image, "alt", default="")
                        })
        
        # Check for ref link that might reference media
        ref = safe_get(media_obj, "ref")
        if isinstance(ref, dict) and "$link" in ref:
            ref_link = ref["$link"]
            if isinstance(ref_link, str):
                # Construct potential CDN URL
                media.append({
                    "type": "media",
                    "uri": f"https://cdn.bsky.app/img/feed_thumbnail/plain/{ref_link}@jpeg",
                    "ref": ref_link
                })
    
    # Check for HLS playlist URL
    playlist = safe_get(embed, "playlist")
    if isinstance(playlist, str) and playlist:
        media.append({
            "type": "video",
            "uri": playlist,
            "format": "hls"
        })
    
    # Check for video in embedView
    embedView_video = safe_get(post, "embedView", "video")
    if isinstance(embedView_video, dict):
        url = safe_get(embedView_video, "url", default="")
        if url:
            media.append({
                "type": "video",
                "uri": url,
                "poster": safe_get(embedView_video, "poster", default="")
            })
    
    logging.debug(f"Found {len(media)} media items in post")
    return media

def _process_thread_node(node: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a thread node into a clean format
    
    Args:
        node: The thread node to process
        
    Returns:
        Processed post data with clean structure
    """
    if not isinstance(node, dict):
        return {}
    
    post_data = node.get("post", {})
    if not isinstance(post_data, dict):
        return {}
    
    # Extract author info safely
    author = post_data.get("author", {})
    if not isinstance(author, dict):
        author = {}
    
    author_clean = {
        "did": author.get("did", ""),
        "handle": author.get("handle", ""),
        "display_name": author.get("displayName", ""),
        "avatar": author.get("avatar", "")
    }
    
    # Extract post content safely
    record = post_data.get("record", {})
    if not isinstance(record, dict):
        record = {}
    
    # Extract media from post
    media = _extract_media_from_post(post_data)
    
    # Build clean post structure safely
    viewer = post_data.get("viewer", {})
    if not isinstance(viewer, dict):
        viewer = {}
    
    clean_post = {
        "uri": post_data.get("uri", ""),
        "cid": post_data.get("cid", ""),
        "author": author_clean,
        "text": record.get("text", ""),
        "created_at": record.get("createdAt", ""),
        "media": media,
        "liked_by_me": viewer.get("like", False),
        "reposted_by_me": viewer.get("repost", False),
        "reply_count": post_data.get("replyCount", 0),
        "repost_count": post_data.get("repostCount", 0),
        "like_count": post_data.get("likeCount", 0)
    }
    
    # Process replies recursively if present
    replies = []
    reply_list = node.get("replies", [])
    if not isinstance(reply_list, list):
        reply_list = []
        
    for reply in reply_list:
        reply_data = _process_thread_node(reply)
        if reply_data:
            replies.append(reply_data)
    
    if replies:
        clean_post["replies"] = replies
    
    return clean_post

def get_post_thread(post_uri: str, debug: bool = False) -> Optional[Dict[str, Any]]:
    """
    Fetch a complete thread from a Bluesky post URI using the public API.
    
    Args:
        post_uri (str): The Bluesky post URI (at://did:plc:xyz/app.bsky.feed.post/123)
        debug (bool): Enable verbose debug output
        
    Returns:
        Optional[Dict[str, Any]]: Thread data in a clean JSON format including:
            - Root post with text and media URIs
            - User information
            - Reply structure
            - Media links (images, videos, external links)
            Or None if the fetch failed
    """
    setup_logging(debug)
    logging.debug(f"Fetching thread for URI: {post_uri}")
    
    api_url = "https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread"
    params = {
        "uri": post_uri,
        "depth": 100,  # Get a deep thread for complete context
    }
    
    try:
        logging.debug(f"Making API request to: {api_url} with params: {params}")
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        logging.debug(f"Received {len(str(data))} bytes of data")
        
        if debug:
            logging.debug(f"Sample of raw data: {json.dumps(data, indent=2)[:500]}...")
        
        # Process thread into clean format
        thread_data = _process_thread_node(data.get("thread", {}))
        
        if thread_data:
            logging.debug(f"Successfully processed thread with root post: {thread_data['uri']}")
            return thread_data
        else:
            logging.error("Failed to process thread data, empty response")
            return None
        
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
    # Uncomment either example as needed
    
    # Example 1: Post with video (HLS playlist)
    # post_uri = "at://did:plc:evocjxmi5cps2thb4ya5jcji/app.bsky.feed.post/3ll6wm5krgx2l"
    
    # Example 2: Another test post
    post_uri = "at://did:plc:3t2w2eeklyserjiqpzsyo7uc/app.bsky.feed.post/3lnb5ujk2cs24"

   
    thread_data = get_post_thread(post_uri, debug=True)
    
    # Print full thread data in JSON format for further processing
    if thread_data:
        print("\nFull thread data (JSON):")
        print(json.dumps(thread_data, indent=2))
        
        # Save thread data to file
        output_file = f"thread_data_{post_uri.split('/')[-1]}.json"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(thread_data, f, indent=2)
            print(f"\nThread data saved to: {output_file}")
        except Exception as e:
            print(f"\nFailed to save thread data: {e}")
    else:
        print("\nFailed to fetch thread")

if __name__ == "__main__":
    main()