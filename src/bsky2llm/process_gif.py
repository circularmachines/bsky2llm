#!/usr/bin/env python3
"""
Process GIF module for bsky2llm.
Downloads GIF files and extracts frames for inclusion in markdown or messages.
"""

import os
import logging
import requests
import tempfile
import shutil
from pathlib import Path
import uuid
from PIL import Image
from typing import List, Dict, Any, Optional

def setup_logging(debug=False):
    """Configure logging based on debug mode"""
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level, 
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def _download_gif(url: str, output_dir: str = None) -> Optional[str]:
    """
    Download a GIF file from a URL
    
    Args:
        url: URL of the GIF to download
        output_dir: Directory to save the downloaded GIF
        
    Returns:
        Path to the downloaded GIF or None if failed
    """
    try:
        # Create temporary directory if output_dir not provided
        if not output_dir:
            output_dir = tempfile.mkdtemp()
        else:
            os.makedirs(output_dir, exist_ok=True)
        
        # Generate unique filename for the GIF
        gif_filename = f"gif_{uuid.uuid4().hex}.gif"
        gif_path = os.path.join(output_dir, gif_filename)
        
        # Download the GIF
        logging.debug(f"Downloading GIF from {url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Save the GIF
        with open(gif_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logging.debug(f"GIF downloaded to {gif_path}")
        return gif_path
    
    except Exception as e:
        logging.error(f"Error downloading GIF from {url}: {e}")
        return None

def _extract_gif_frames(gif_path: str, max_frames: int = 5, output_dir: str = None) -> List[str]:
    """
    Extract frames from a GIF file
    
    Args:
        gif_path: Path to the GIF file
        max_frames: Maximum number of frames to extract
        output_dir: Directory to save extracted frames
        
    Returns:
        List of paths to extracted frames
    """
    try:
        # Create temporary directory if output_dir not provided
        if not output_dir:
            output_dir = tempfile.mkdtemp()
        else:
            os.makedirs(output_dir, exist_ok=True)
        
        # Open the GIF
        gif = Image.open(gif_path)
        
        # Get total number of frames
        try:
            frame_count = gif.n_frames
        except AttributeError:
            frame_count = 1  # Not a GIF or only has one frame
        
        logging.debug(f"GIF has {frame_count} frames, extracting up to {max_frames}")
        
        # Calculate which frames to extract (evenly distributed)
        if frame_count <= max_frames:
            frames_to_extract = list(range(frame_count))
        else:
            # Extract frames at regular intervals
            step = frame_count / max_frames
            frames_to_extract = [int(i * step) for i in range(max_frames)]
        
        frame_paths = []
        
        # Extract selected frames
        for i, frame_num in enumerate(frames_to_extract):
            gif.seek(frame_num)
            frame_filename = f"frame_{i+1}_{uuid.uuid4().hex}.jpg"
            frame_path = os.path.join(output_dir, frame_filename)
            
            # Convert to RGB to save as JPEG
            rgb_frame = gif.convert('RGB')
            rgb_frame.save(frame_path, 'JPEG')
            frame_paths.append(frame_path)
            
            logging.debug(f"Extracted frame {frame_num} to {frame_path}")
        
        return frame_paths
    
    except Exception as e:
        logging.error(f"Error extracting frames from GIF {gif_path}: {e}")
        return []

def process_gif(gif_url: str, max_frames: int = 5, output_dir: str = "vault/images", debug: bool = False) -> Dict[str, Any]:
    """
    Process a GIF file: download and extract frames
    
    Args:
        gif_url: URL of the GIF to process
        max_frames: Maximum number of frames to extract
        output_dir: Directory to save the output files (default: vault/images)
        debug: Enable verbose logging
        
    Returns:
        Dictionary containing:
            - frames: List of paths to extracted frames (relative paths for Obsidian: images/xxx.jpg)
            - original_frames: List of full paths to extracted frames
            - error: Error message if processing failed
    """
    setup_logging(debug)
    
    result = {
        "frames": [],
        "original_frames": [],
        "error": None
    }
    
    try:
        # Create output directory if needed
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        else:
            output_dir = os.path.join(tempfile.gettempdir(), f"gif_frames_{uuid.uuid4().hex}")
            os.makedirs(output_dir, exist_ok=True)
        
        logging.debug(f"Processing GIF from {gif_url}")
        
        # Download the GIF
        gif_path = _download_gif(gif_url, output_dir)
        if not gif_path:
            result["error"] = f"Failed to download GIF from {gif_url}"
            return result
        
        # Extract frames
        original_frames = _extract_gif_frames(gif_path, max_frames, output_dir)
        result["original_frames"] = original_frames
        
        # Generate relative paths for Obsidian
        for frame_path in original_frames:
            # Extract just the filename from the full path
            filename = os.path.basename(frame_path)
            # Create relative path for Obsidian: images/xxx.jpg
            relative_path = f"images/{filename}"
            result["frames"].append(relative_path)
        
        # If no frames were extracted, set error
        if not original_frames:
            result["error"] = "Failed to extract frames from GIF"
        
        return result
    
    except Exception as e:
        logging.error(f"Error processing GIF {gif_url}: {e}")
        result["error"] = str(e)
        return result

def main():
    """Main function with hardcoded example"""
    example_gif_url = "https://media.tenor.com/5R3RCJYvddUAAAAC/bend-and-snap-legally-blonde.gif"
    
    print(f"\nProcessing GIF: {example_gif_url}")
    result = process_gif(example_gif_url, max_frames=5, debug=True)
    
    if result.get("error"):
        print(f"\nError processing GIF: {result['error']}")
    else:
        print(f"\nSuccessfully extracted {len(result['frames'])} frames from GIF")
        for i, frame in enumerate(result["frames"]):
            print(f"Frame {i+1}: {frame}")

if __name__ == "__main__":
    main()