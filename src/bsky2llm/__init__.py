"""
bsky2llm package - Convert Bluesky posts to formats suitable for LLMs.

This package provides tools to fetch, process, and convert Bluesky posts
and threads into formats that are easy to use with Large Language Models.
"""

# Import main functions that should be available when importing the package
from .url_converter import convert_url_to_uri
from .get_raw_thread import get_raw_thread
from .process import process_post
from .markdown_creator import thread_to_markdown
from .process_video import has_video, video_to_markdown
from .process_image import has_images, image_to_markdown
from .md_to_openai import parse_markdown
from .ai_api_call import main_interface_function as call_ai_api

# Set version
__version__ = "0.1.0"