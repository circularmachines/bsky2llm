#!/usr/bin/env python3
"""
Process video module for bsky2llm.
Downloads, extracts frames, and transcribes video content from a Bluesky post.
"""

import os
import sys
import tempfile
import logging
import requests
import uuid
import subprocess
import json
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from dotenv import load_dotenv
import cv2
import numpy as np
from openai import AzureOpenAI, OpenAI

# Load environment variables from a .env file
load_dotenv()

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

def _detect_video_url(post_data: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Find video URL in a post - checks for both HLS playlist and blob
    
    Args:
        post_data: Post data dictionary
        
    Returns:
        Tuple of (video_url, video_type, blob_cid) where:
        - video_url: Direct URL to video if available
        - video_type: "hls" or "blob" depending on source type
        - blob_cid: Content ID for blob if available
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
    
    # Check for HLS playlist first
    playlist_url = safe_get(post_data, 'embed', 'playlist')
    if playlist_url:
        logger.debug(f"Found HLS playlist URL: {playlist_url}")
        return playlist_url, "hls", None
    
    # Check for blob reference
    blob_cid = safe_get(post_data, 'record', 'embed', 'video', 'ref', '$link') or \
              safe_get(post_data, 'record', 'embed', 'video', 'ref', 'link')
    
    if blob_cid:
        # Will need to get DID to download blob
        did = safe_get(post_data, 'author', 'did')
        if did:
            logger.debug(f"Found blob reference: {blob_cid} for DID: {did}")
            blob_url = f"https://bsky.social/xrpc/com.atproto.sync.getBlob?did={did}&cid={blob_cid}"
            return blob_url, "blob", blob_cid
    
    # Look for direct video URL in various locations
    video_url_paths = [
        ['embed', 'video', 'url'],
        ['record', 'embed', 'video', 'url'],
        ['embedView', 'video', 'url'],
        ['embed', 'media', 'video', 'url'],
        ['record', 'embed', 'media', 'video', 'url']
    ]
    
    for path in video_url_paths:
        url = safe_get(post_data, *path)
        if url and isinstance(url, str):
            logger.debug(f"Found direct video URL at path {'.'.join(path)}: {url}")
            return url, "direct", None
    
    logger.debug("No video URL found in post")
    return None, None, None

def _download_hls_video(hls_url: str, output_path: str, debug: bool = False) -> bool:
    """
    Download a video from an HLS URL
    
    Args:
        hls_url: URL to the HLS playlist
        output_path: Path to save the downloaded video
        debug: Enable verbose logging
        
    Returns:
        True if successful, False otherwise
    """
    logger.debug(f"Downloading HLS video from: {hls_url}")
    
    # Check for various libraries for handling HLS downloads
    try:
        import streamlink
        logger.debug("Using streamlink to download HLS")
        
        streams = streamlink.streams(hls_url)
        best_stream = streams.get('best')
        
        if not best_stream:
            logger.error("No streams found in HLS playlist")
            return False
            
        with open(output_path, 'wb') as f:
            with best_stream.open() as stream:
                for data in iter(lambda: stream.read(4096), b""):
                    f.write(data)
                    
        logger.debug(f"HLS video downloaded to: {output_path}")
        return True
        
    except ImportError:
        logger.debug("Streamlink not available, checking for yt-dlp")
        
        try:
            from yt_dlp import YoutubeDL
            logger.debug("Using yt-dlp to download HLS")
            
            ydl_opts = {
                'format': 'best',
                'outtmpl': output_path,
                'quiet': not debug
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([hls_url])
                
            logger.debug(f"HLS video downloaded to: {output_path}")
            return True
            
        except ImportError:
            logger.debug("yt-dlp not available, falling back to ffmpeg")
            
            try:
                # Try using ffmpeg as a last resort
                cmd = [
                    'ffmpeg',
                    '-i', hls_url,
                    '-c', 'copy',
                    '-bsf:a', 'aac_adtstoasc',
                    '-y',
                    output_path
                ]
                
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE if not debug else None,
                    stderr=subprocess.PIPE if not debug else None,
                    text=True
                )
                
                if process.returncode != 0:
                    logger.error(f"ffmpeg failed: {process.stderr}")
                    return False
                    
                logger.debug(f"HLS video downloaded to: {output_path}")
                return True
                
            except (subprocess.SubprocessError, FileNotFoundError) as e:
                logger.error(f"Failed to use ffmpeg: {e}")
                return False
    
    except Exception as e:
        logger.error(f"Failed to download HLS: {e}")
        return False

def _download_blob_video(blob_url: str, output_path: str) -> bool:
    """
    Download a video blob from the Bluesky API
    
    Args:
        blob_url: URL to the blob video
        output_path: Path to save the downloaded video
        
    Returns:
        True if successful, False otherwise
    """
    logger.debug(f"Downloading blob video from: {blob_url}")
    
    try:
        response = requests.get(blob_url)
        response.raise_for_status()
        
        # Verify we received a video
        content_type = response.headers.get('Content-Type', '')
        if 'video' not in content_type:
            logger.error(f"Response is not a valid video: {content_type}")
            return False
        
        # Save the video
        with open(output_path, 'wb') as f:
            f.write(response.content)
            
        logger.debug(f"Blob video downloaded to: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to download blob video: {e}")
        return False

def _extract_audio(video_path: str, output_dir: str) -> Optional[str]:
    """
    Extract audio from a video file
    
    Args:
        video_path: Path to the video file
        output_dir: Directory to save the extracted audio
        
    Returns:
        Path to the extracted audio file or None if failed
    """
    logger.debug(f"Extracting audio from video: {video_path}")
    
    try:
        # Make sure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate output path
        audio_path = os.path.join(output_dir, f'audio_{uuid.uuid4().hex}.mp3')
        
        # Use ffmpeg to extract audio
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-q:a', '0',
            '-map', 'a',
            '-y',
            audio_path
        ]
        
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if process.returncode != 0:
            # Check if error is due to no audio stream
            if "map audio" in process.stderr and "No such stream" in process.stderr:
                logger.warning("Video has no audio stream")
            else:
                logger.error(f"Failed to extract audio: {process.stderr}")
            return None
            
        logger.debug(f"Audio extracted to: {audio_path}")
        return audio_path
        
    except Exception as e:
        logger.error(f"Error extracting audio: {e}")
        return None

def _transcribe_audio(audio_path: str, language: str = "en") -> Optional[Dict[str, Any]]:
    """
    Transcribe audio using Azure OpenAI's Whisper API or OpenAI Whisper API
    
    Args:
        audio_path: Path to the audio file
        language: Language code for transcription (default: "en")
        
    Returns:
        Transcription data including segments with timestamps or None if failed
    """
    logger.debug(f"Transcribing audio: {audio_path}")
    
    try:
        # Load environment variables
        load_dotenv()
        
        # Get OpenAI API key first
        openai_api_key = os.getenv("OPENAI_API_KEY")
        openai_model = os.getenv("OPENAI_WHISPER_MODEL", "whisper-1")
        
        # Get Azure OpenAI credentials as fallback
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_api_key = os.getenv("AZURE_OPENAI_KEY")
        deployment_name = os.getenv("WHISPER_DEPLOYMENT_NAME", "whisper")
        api_version = os.getenv("WHISPER_API_VERSION", "2024-06-01")
        
        # Try OpenAI client first if credentials are available
        if openai_api_key:
            logger.debug("Using OpenAI API for transcription")
            
            # Initialize OpenAI client
            client = OpenAI(api_key=openai_api_key)
            
            # Transcribe audio with OpenAI Whisper
            with open(audio_path, "rb") as audio_file:
                logger.debug(f"Sending audio to OpenAI for transcription using model: {openai_model}")
                response = client.audio.transcriptions.create(
                    file=audio_file,
                    model=openai_model,
                    language=language,
                    response_format="verbose_json",
                    timestamp_granularities=["segment", "word"]
                )
                
        # Fall back to Azure OpenAI if credentials are available
        elif azure_endpoint and azure_api_key:
            logger.debug("Using Azure OpenAI API for transcription")
            
            # Initialize Azure client
            client = AzureOpenAI(
                api_key=azure_api_key,
                azure_endpoint=azure_endpoint,
                api_version=api_version
            )
            
            # Transcribe with Azure OpenAI Whisper
            with open(audio_path, "rb") as audio_file:
                logger.debug(f"Sending audio to Azure OpenAI for transcription using deployment: {deployment_name}")
                response = client.audio.transcriptions.create(
                    file=audio_file,
                    model=deployment_name,
                    language=language,
                    response_format="verbose_json",
                    timestamp_granularities=["segment", "word"]
                )
        else:
            logger.error("No OpenAI or Azure OpenAI credentials found in environment variables")
            return None
        
        # Parse the response
        if not hasattr(response, "text"):
            logger.warning("Transcription response format unexpected")
            return {"text": str(response)}
        
        # Extract words and segments data
        words_data = []
        if hasattr(response, "words"):
            for word in response.words:
                word_data = {
                    "text": word.word,
                    "start": word.start,
                    "end": word.end
                }
                words_data.append(word_data)
        
        segments_data = []
        if hasattr(response, "segments"):
            for segment in response.segments:
                segment_data = {
                    "text": segment.text,
                    "start": segment.start,
                    "end": segment.end,
                    "frames": []  # Will be populated with frame paths
                }
                segments_data.append(segment_data)
        
        # Prepare the final transcription data
        transcript_data = {
            "text": response.text,
            "segments": segments_data,
            "words": words_data,
            "duration": getattr(response, "duration", 0)
        }
        
        logger.debug(f"Transcription successful: {len(segments_data)} segments, {len(words_data)} words")
        return transcript_data
        
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        return None

def _extract_frames(video_path: str, output_dir: str, transcript: Optional[Dict[str, Any]] = None, max_frames: int = 5) -> List[str]:
    """
    Extract frames from a video file, using transcript segments if available
    
    Args:
        video_path: Path to the video file
        output_dir: Directory to save the extracted frames
        transcript: Transcription data with segments to determine frame extraction points
        max_frames: Maximum number of frames to extract if no transcript is available
        
    Returns:
        List of paths to extracted frames
    """
    logger.debug(f"Extracting frames from video: {video_path}")
    
    frame_paths = []
    try:
        # Make sure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Open the video file
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Could not open video: {video_path}")
            return frame_paths
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        
        logger.debug(f"Video properties: {frame_count} frames, {fps} fps, {duration:.2f}s duration")
        
        # If we have transcript segments, extract frames from middle of each segment
        if transcript and "segments" in transcript and transcript["segments"]:
            logger.debug(f"Extracting frames based on {len(transcript['segments'])} transcript segments")
            
            for i, segment in enumerate(transcript["segments"]):
                if "start" in segment and "end" in segment:
                    # Calculate middle point of the segment
                    start_time = segment["start"]
                    end_time = segment["end"]
                    middle_time = start_time + (end_time - start_time) / 2
                    
                    logger.debug(f"Segment {i}: {segment['text'][:30]}... middle={middle_time:.2f}s")
                    
                    # Set position in video to middle of segment
                    cap.set(cv2.CAP_PROP_POS_MSEC, middle_time * 1000)
                    
                    # Read the frame
                    success, frame = cap.read()
                    
                    if success:
                        # Save the frame
                        frame_path = os.path.join(output_dir, f"frame_{i:03d}_{middle_time:.2f}s.jpg")
                        cv2.imwrite(frame_path, frame)
                        frame_paths.append(frame_path)
                        
                        # Add frame path to transcript segment
                        transcript["segments"][i]["frames"].append({
                            "path": frame_path,
                            "time": middle_time
                        })
                        
                        logger.debug(f"Saved frame at time {middle_time:.2f}s to {frame_path}")
                    else:
                        logger.warning(f"Failed to read frame at time {middle_time:.2f}s")
        else:
            # No transcript segments, extract frames at regular intervals
            logger.debug("No transcript segments, extracting frames at regular intervals")
            
            # Determine interval to extract the requested number of frames
            interval = max(1, int(duration / (max_frames + 1)))
            
            for i in range(max_frames):
                time_sec = (i + 1) * interval
                
                # Don't extract beyond video duration
                if time_sec >= duration:
                    break
                
                # Set position in video
                cap.set(cv2.CAP_PROP_POS_MSEC, time_sec * 1000)
                
                # Read the frame
                success, frame = cap.read()
                
                if success:
                    # Save the frame
                    frame_path = os.path.join(output_dir, f"frame_{i:03d}_{time_sec:.2f}s.jpg")
                    cv2.imwrite(frame_path, frame)
                    frame_paths.append(frame_path)
                    
                    logger.debug(f"Saved frame at time {time_sec:.2f}s to {frame_path}")
                else:
                    logger.warning(f"Failed to read frame at time {time_sec:.2f}s")
        
        # Release the video capture
        cap.release()
        
        logger.debug(f"Extracted {len(frame_paths)} frames from video")
        return frame_paths
        
    except Exception as e:
        logger.error(f"Error extracting frames: {e}")
        return frame_paths

def has_video(post_data: Dict[str, Any], debug: bool = False) -> bool:
    """
    Check if a post contains a video
    
    Args:
        post_data: Post data dictionary
        debug: Enable verbose debug output
        
    Returns:
        True if video is detected, False otherwise
    """
    if debug:
        setup_logging(debug)
    video_url, _, _ = _detect_video_url(post_data)
    return video_url is not None

def video_to_markdown(post_data: Dict[str, Any], output_dir: str = "output", max_frames: int = 3, debug: bool = False) -> Optional[str]:
    """
    Generate markdown representation of a video in a post
    
    Args:
        post_data: Post data dictionary
        output_dir: Directory to save extracted files
        max_frames: Maximum number of frames to extract
        debug: Enable verbose debug output
        
    Returns:
        Markdown string or None if no video found
    """
    if debug:
        setup_logging(debug)
    
    if not has_video(post_data, debug=False):
        logger.debug("No video found in post")
        return None
    
    result = process_video(post_data, output_dir, max_frames, debug=False)
    
    if result.get("error"):
        logger.warning(f"Video processing failed: {result['error']}")
        return f"*Video processing failed: {result['error']}*\n\n"
    
    markdown_lines = []
    markdown_lines.append("**Video Content**\n")
    
    # Check if we have transcript data with segments and frames
    if result.get("transcript_data") and result.get("transcript_data").get("segments"):
        segments = result.get("transcript_data").get("segments")
        
        # Group segments with their corresponding frames
        for i, segment in enumerate(segments):
            if segment.get("text"):

                # Add timestamps if available
                if segment.get("start") is not None and segment.get("end") is not None:
                    start_time = segment.get("start")
                    end_time = segment.get("end")
                    timestamp = f"[{start_time:.2f}s - {end_time:.2f}s]"
                    markdown_lines.append(f"*{timestamp}* ")

                # Add segment text
                markdown_lines.append(f"{segment.get('text')}\n")
                
                
                
                # Add frames for this segment if available
                if segment.get("frames"):
                    for frame_info in segment.get("frames"):
                        frame_path = frame_info.get("path")
                        if frame_path:
                            frame_filename = os.path.basename(frame_path)
                            markdown_lines.append(f"![Frame at {frame_info.get('time', 0):.2f}s](media/frames/{frame_filename})\n") #ToDo proper path for frames
                
                markdown_lines.append("\n")
    # If we don't have segment-specific frames, fall back to showing all frames then transcript
    elif result.get("frames") or result.get("transcript"):
        if result.get("frames"):
            frames = result["frames"]
            markdown_lines.append("**Video Frames:**\n")
            frame_filenames = [os.path.basename(frame) for frame in frames]
            for frame in frame_filenames:
                markdown_lines.append(f"![Frame](images/{frame})\n")
            markdown_lines.append("")
        
        if result.get("transcript"):
            markdown_lines.append("**Transcription:**\n")
            markdown_lines.append(f"> {result['transcript']}\n")
            markdown_lines.append("")
    
    #if result.get("video_url"):
     #   markdown_lines.append(f"[View Original Video]({result['video_url']})\n")
    
    return "\n".join(markdown_lines)

def process_video(post_data: Dict[str, Any], output_dir: str = "output", max_frames: int = 3, debug: bool = False) -> Dict[str, Any]:
    """
    Process a video from a Bluesky post
    
    Args:
        post_data: Bluesky post data dictionary
        output_dir: Directory to save output files
        max_frames: Maximum number of frames to extract
        debug: Enable verbose logging
        
    Returns:
        Dictionary containing:
        - video_url: URL of the video
        - video_type: Type of video (hls, blob, direct)
        - video_path: Path to the downloaded video file
        - frames: List of paths to extracted frames
        - audio_path: Path to extracted audio
        - transcript: Transcription text or None if unavailable
        - transcript_data: Full transcription data with segments and timestamps
        - error: Error message if any step failed
    """
    if debug:
        setup_logging(debug)
    
    result = {
        "video_url": None,
        "video_type": None,
        "video_path": None,
        "frames": [],
        "audio_path": None,
        "transcript": None,
        "transcript_data": None,
        "error": None
    }
    
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        video_url, video_type, blob_cid = _detect_video_url(post_data)
        if not video_url or not video_type:
            result["error"] = "No video found in post"
            return result
            
        result["video_url"] = video_url
        result["video_type"] = video_type
        
        video_path = os.path.join(output_dir, f'video_{uuid.uuid4().hex}.mp4')
        
        success = False
        if video_type == "hls":
            success = _download_hls_video(video_url, video_path, debug)
        elif video_type == "blob" or video_type == "direct":
            success = _download_blob_video(video_url, video_path)
        
        if not success:
            result["error"] = f"Failed to download {video_type} video"
            return result
            
        result["video_path"] = video_path
        
        frames_dir = os.path.join(output_dir, "frames")
        audio_dir = os.path.join(output_dir, "audio")
        os.makedirs(frames_dir, exist_ok=True)
        os.makedirs(audio_dir, exist_ok=True)
        
        audio_path = _extract_audio(video_path, audio_dir)
        if audio_path:
            result["audio_path"] = audio_path
            
            transcript_data = _transcribe_audio(audio_path)
            if transcript_data:
                result["transcript_data"] = transcript_data
                result["transcript"] = transcript_data.get("text", "")
                
                frames = _extract_frames(video_path, frames_dir, transcript_data, max_frames)
                result["frames"] = frames
            else:
                frames = _extract_frames(video_path, frames_dir, None, max_frames)
                result["frames"] = frames
        else:
            frames = _extract_frames(video_path, frames_dir, None, max_frames)
            result["frames"] = frames
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing video: {e}")
        result["error"] = str(e)
        return result

def main():
    """Main function with hardcoded example"""
    debug = True
    setup_logging(debug)
    
    try:
        example_file = "examples/raw_thread_3lnb5ujk2cs24.json"
        
        if not os.path.exists(example_file):
            logger.warning(f"Example file not found: {example_file}")
            logger.info(f"Current directory: {os.getcwd()}")
            logger.info("Fetching example post from API instead...")
            
            post_uri = "at://did:plc:evocjxmi5cps2thb4ya5jcji/app.bsky.feed.post/3ll6wm5krgx2l"
            
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
            
        logger.info("\nChecking if post has video...")
        has_vid = has_video(post_data, debug=False)
        logger.info(f"Post has video: {has_vid}")
        
        if has_vid:
            
            logger.info("\nGenerating markdown...")
            markdown = video_to_markdown(post_data, debug=False)
            
            if markdown:
                logger.info("\nMarkdown representation:")
                logger.info(markdown)
                
                md_file = "video_output.md"
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(markdown)
                logger.info(f"\nMarkdown saved to: {md_file}")
        else:
            logger.info("\nNo video detected in the post")
    
    except Exception as e:
        logger.error(f"\nError in main function: {e}")

if __name__ == "__main__":
    main()