#!/usr/bin/env python3
"""
Module to process markdown files, extract text and images, and convert them into OpenAI messages.
It encodes images and includes them in a single user message with a list of content items.
"""

import os
import logging
import json
import base64
import mimetypes
from pathlib import Path
from typing import List, Dict, Any, Optional

def setup_logging(debug=False):
    """Configure logging based on debug mode"""
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level, 
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def encode_image(image_path: str) -> Optional[str]:
    """
    Encode an image file to base64
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Base64 encoded string of the image or None if failed
    """
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    except Exception as e:
        logging.error(f"Error encoding image {image_path}: {str(e)}")
        return None

def get_mime_type(file_path: str) -> str:
    """
    Get the MIME type for a file
    
    Args:
        file_path: Path to the file
        
    Returns:
        MIME type string
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or "application/octet-stream"

def parse_markdown(file_path: str, system_message: str) -> List[Dict[str, Any]]:
    """
    Parse a markdown file to extract text and images as OpenAI messages.
    Images are encoded and included in the content list.
    Text lines are joined until an image is encountered.

    Args:
        file_path: Path to the markdown file.
        system_message: Initial system message for the conversation.

    Returns:
        List of messages formatted for OpenAI API.
    """
    messages = [{"role": "system", "content": system_message}]
    content_items = []
    
    md_dir = Path(file_path).parent
    buffer = []
    
    with open(file_path, 'r') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith("![") and "](" in line:
            # First, add any buffered text
            if buffer:
                content_items.append({
                    "type": "text",
                    "text": "\n".join(buffer)
                })
                buffer = []
            
            # Extract image description and URL
            description = line[line.find("![") + 2:line.find("]")]
            url = line[line.find("(") + 1:line.find(")")]
            
            # Handle relative path - make it relative to the markdown file location
            if not url.startswith(("http://", "https://")):
                img_path = md_dir / url
                
                if img_path.exists():
                    logging.debug(f"Processing image: {img_path}")
                    encoded_image = encode_image(str(img_path))
                    
                    if encoded_image:
                        mime_type = get_mime_type(str(img_path))
                        content_items.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{encoded_image}"
                            }
                        })
                    
                    # Add description as text
                    buffer.append(f"Image description: {description}")
                else:
                    logging.warning(f"Image not found: {img_path}")
                    buffer.append(f"[Missing Image: {description}] ({url})")
            else:
                # External URL, just add as text
                buffer.append(f"Image: {description} ({url})")
        else:
            # Accumulate text lines in buffer
            buffer.append(line)
    
    # Add any remaining buffered text
    if buffer:
        content_items.append({
            "type": "text",
            "text": "\n".join(buffer)
        })

    # Add all content items as a single user message
    if content_items:
        messages.append({
            "role": "user",
            "content": content_items
        })
        
    return messages

def main_interface_function(md_file: str, system_message: str, output_file: str, debug=False):
    """
    Main interface function to process markdown and save messages as JSON.

    Args:
        md_file: Path to the markdown file.
        system_message: Initial system message for the conversation.
        output_file: Path to save the JSON file.
        debug: Enable verbose logging.

    Returns:
        True if successful, False otherwise.
    """
    setup_logging(debug)
    logging.debug(f"Processing markdown file: {md_file}")

    if not Path(md_file).is_file():
        logging.error(f"File not found: {md_file}")
        return False

    # Parse markdown file
    messages = parse_markdown(md_file, system_message)
    logging.debug(f"Parsed {len(messages)} messages with content")

    # Save messages to JSON
    try:
        with open(output_file, 'w') as f:
            json.dump(messages, f, indent=4)
        logging.info(f"Messages saved to {output_file}")
        return True
    except Exception as e:
        logging.error(f"Failed to save messages: {e}")
        return False

def main():
    """Main function with hardcoded example"""
    example_md_file = "tests/markdown_example.md"
    example_output_file = "tests/messages_example.json"
    system_message = "You are a helpful assistant. Analyze the following Bluesky thread and provide insights."

    success = main_interface_function(
        md_file=example_md_file, 
        system_message=system_message, 
        output_file=example_output_file, 
        debug=True
    )

    if success:
        print(f"\nMessages successfully saved to {example_output_file}")
        print(example_output_file)  # Clean output for piping
    else:
        print("\nFailed to process markdown file")

if __name__ == "__main__":
    main()