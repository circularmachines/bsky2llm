#!/usr/bin/env python3
"""
Process image module for bsky2llm.
Downloads and processes image content from a Bluesky post.
"""

import os
import sys
import logging
import requests
import uuid
import json
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

# Logger for this module
logger = logging.getLogger(__name__)

def setup_logging(debug=False):
    """Configure logging based on debug mode"""
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level, 
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def _resolve_did(handle: str) -> str:
    """
    Resolve a Bluesky handle to a DID
    
    Args:
        handle: Bluesky handle to resolve
        
    Returns:
        DID string or original handle if it's already a DID
    """
    # If already a DID, return it
    if handle.startswith('did:plc:'):
        return handle 
    
    try:
        response = requests.get(f'https://bsky.social/xrpc/com.atproto.identity.resolveHandle?handle={handle}')
        response.raise_for_status()
        return response.json()['did']
    except Exception as e:
        logger.error(f"Failed to resolve DID for {handle}: {e}")
        return handle

def _detect_images(post_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Find images in a post
    
    Args:
        post_data: Post data dictionary
        
    Returns:
        List of image data dictionaries with URLs and alt text
    """
    # Helper function to safely navigate dictionaries
    def safe_get(data, *keys, default=None):
        if not isinstance(data, dict):
            return default
            
        current = data
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return default
            current = current[key]
        return current
    
    images = []
    
    # Check first in the embed view (processed data)
    embed_view = safe_get(post_data, 'embed')
    if isinstance(embed_view, dict) and embed_view.get('$type', '').endswith('images#view'):
        image_list = embed_view.get('images', [])
        if isinstance(image_list, list):
            for img in image_list:
                if isinstance(img, dict):
                    image_data = {
                        'fullsize': img.get('fullsize', ''),
                        'thumb': img.get('thumb', ''),
                        'alt': img.get('alt', ''),
                        'aspectRatio': img.get('aspectRatio', {})
                    }
                    images.append(image_data)
    
    # If no images found in the view, check in the record
    if not images:
        embed_record = safe_get(post_data, 'record', 'embed')
        if isinstance(embed_record, dict) and embed_record.get('$type', '').endswith('images'):
            image_list = embed_record.get('images', [])
            if isinstance(image_list, list):
                for img in image_list:
                    if isinstance(img, dict):
                        # For blob references, we'd need more complex handling
                        # Here we're just collecting the data we have
                        image_data = {
                            'blob_cid': safe_get(img, 'image', 'ref', '$link'),
                            'alt': img.get('alt', ''),
                            'aspectRatio': img.get('aspectRatio', {}),
                            'mimeType': safe_get(img, 'image', 'mimeType')
                        }
                        
                        # We need to construct full URLs for blobs
                        if image_data['blob_cid'] and safe_get(post_data, 'author', 'did'):
                            did = safe_get(post_data, 'author', 'did')
                            image_data['fullsize'] = f"https://cdn.bsky.app/img/feed_fullsize/plain/{did}/{image_data['blob_cid']}@{image_data['mimeType'].split('/')[1]}"
                            image_data['thumb'] = f"https://cdn.bsky.app/img/feed_thumbnail/plain/{did}/{image_data['blob_cid']}@{image_data['mimeType'].split('/')[1]}"
                        
                        images.append(image_data)
    
    # Log what we found
    logger.debug(f"Found {len(images)} images in post")
    for i, img in enumerate(images):
        logger.debug(f"Image {i+1}: fullsize={img.get('fullsize', 'N/A')}, alt={img.get('alt', 'N/A')}")
    
    return images

def _download_image(image_url: str, output_path: str) -> bool:
    """
    Download an image from a URL
    
    Args:
        image_url: URL to the image
        output_path: Path to save the downloaded image
        
    Returns:
        True if successful, False otherwise
    """
    logger.debug(f"Downloading image from: {image_url}")
    
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        
        # Check if we got an image
        content_type = response.headers.get('Content-Type', '')
        if 'image/' not in content_type:
            logger.error(f"Response is not a valid image: {content_type}")
            return False
        
        # Save the image
        with open(output_path, 'wb') as f:
            f.write(response.content)
            
        logger.debug(f"Image downloaded to: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to download image: {e}")
        return False

def has_images(post_data: Dict[str, Any], debug: bool = False) -> bool:
    """
    Check if a post contains images
    
    Args:
        post_data: Post data dictionary
        debug: Enable verbose debug output
        
    Returns:
        True if images are detected, False otherwise
    """
    if debug:
        setup_logging(debug)
    images = _detect_images(post_data)
    return len(images) > 0

def image_to_markdown(post_data: Dict[str, Any], output_dir: str = "output", debug: bool = False) -> Optional[str]:
    """
    Generate markdown representation of images in a post
    
    Args:
        post_data: Post data dictionary
        output_dir: Directory to save downloaded images
        debug: Enable verbose debug output
        
    Returns:
        Markdown string or None if no images found
    """
    if debug:
        setup_logging(debug)
    
    if not has_images(post_data, debug=False):
        logger.debug("No images found in post")
        return None
    
    result = process_images(post_data, output_dir, debug=False)
    
    if result.get("error"):
        logger.warning(f"Image processing failed: {result['error']}")
        return f"*Image processing failed: {result['error']}*\n\n"
    
    markdown_lines = []
    
    # Include each downloaded image in the markdown
    for i, image_info in enumerate(result.get("images", [])):
        local_path = image_info.get("local_path")
        alt_text = image_info.get("alt_text", "")
        
        if local_path:
            # Get just the filename for the markdown
            filename = os.path.basename(local_path)
            
            # Format the markdown image with alt text
            markdown_lines.append(f"![{alt_text}](media/images/{filename})\n")
            
            # Add the alt text as a caption if it exists
            if alt_text:
                markdown_lines.append(f"*{alt_text}*\n")
            
            markdown_lines.append("\n")
    
    return "".join(markdown_lines)

def process_images(post_data: Dict[str, Any], output_dir: str = "output", debug: bool = False) -> Dict[str, Any]:
    """
    Process images from a Bluesky post
    
    Args:
        post_data: Bluesky post data dictionary
        output_dir: Directory to save output files
        debug: Enable verbose logging
        
    Returns:
        Dictionary containing:
        - images: List of dicts with image info (url, alt_text, local_path)
        - error: Error message if any step failed
    """
    if debug:
        setup_logging(debug)
    
    result = {
        "images": [],
        "error": None
    }
    
    try:
        # Create output directory if it doesn't exist
        images_dir = os.path.join(output_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        # Detect images in the post
        image_data_list = _detect_images(post_data)
        
        if not image_data_list:
            result["error"] = "No images found in post"
            return result
        
        # Download each image
        for i, image_data in enumerate(image_data_list):
            # Get the URL to download (prefer fullsize)
            image_url = image_data.get('fullsize') or image_data.get('thumb')
            
            if not image_url:
                logger.warning(f"No URL available for image {i+1}")
                continue
            
            # Create a unique filename
            image_ext = image_url.split('.')[-1] if '.' in image_url else "jpg"
            if '@' in image_ext:  # Handle Bluesky CDN format like "bafkreifyv...@jpeg"
                image_ext = image_ext.split('@')[-1]
            
            local_path = os.path.join(images_dir, f"image_{i+1}_{uuid.uuid4().hex}.{image_ext}")
            
            # Download the image
            success = _download_image(image_url, local_path)
            
            # Add information to result
            result["images"].append({
                "url": image_url,
                "alt_text": image_data.get('alt', ''),
                "local_path": local_path if success else None,
                "aspectRatio": image_data.get('aspectRatio', {})
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing images: {e}")
        result["error"] = str(e)
        return result

def main():
    """Main function with hardcoded example"""
    debug = True
    setup_logging(debug)
    
    try:
        example_file = "examples/raw_thread_3lnjkwfzvw22q.json"
        
        if not os.path.exists(example_file):
            logger.warning(f"Example file not found: {example_file}")
            logger.info(f"Current directory: {os.getcwd()}")
            logger.info("Fetching example post from API instead...")
            
            post_uri = "at://did:plc:twu4iqyasazfles5q5ci2dz3/app.bsky.feed.post/3lnjkwfzvw22q"
            
            api_url = "https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread"
            params = {"uri": post_uri, "depth": 0}
            
            response = requests.get(api_url, params=params)
            response.raise_for_status()
            
            post_data = response.json()["thread"]["post"]
            logger.info(f"Fetched post data for: {post_uri}")
        else:
            with open(example_file, 'r', encoding='utf-8') as f:
                thread_data = json.load(f)
                
            post_data = thread_data.get("thread", {}).get("post", {})
            logger.info(f"Loaded post data from: {example_file}")
            
        logger.info("\nChecking if post has images...")
        has_imgs = has_images(post_data, debug=debug)
        logger.info(f"Post has images: {has_imgs}")
        
        if has_imgs:
            logger.info("\nGenerating markdown...")
            markdown = image_to_markdown(post_data, debug=debug)
            
            if markdown:
                logger.info("\nMarkdown representation:")
                logger.info(markdown)
                
                md_file = "image_output.md"
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(markdown)
                logger.info(f"\nMarkdown saved to: {md_file}")
        else:
            logger.info("\nNo images detected in the post")
    
    except Exception as e:
        logger.error(f"\nError in main function: {e}")

if __name__ == "__main__":
    main()