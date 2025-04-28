# bsky2llm

A Python module for analyzing Bluesky posts and threads using AI models.

## Overview

This module provides a simple interface to fetch Bluesky posts/threads, process their content, and analyze them using AI models. It handles text content, images, and videos, with support for transcription. The module transforms Bluesky data into an intermediate markdown format that is both human-readable and compatible with AI APIs.

Using markdown as an intermediate format allows you to inspect the data with tools like Obsidian, VSCode, or any markdown viewer before it's sent to AI models. This transparency helps verify what content is being analyzed and provides a useful artifact for debugging or record-keeping.


## Installation

```bash
# Install from PyPI
pip install bsky2llm

# Or clone the repository and install locally
git clone https://github.com/yourusername/bsky2llm.git
cd bsky2llm
pip install -r requirements.txt
```

## Usage

```python
from bsky2llm import process_post

url="https://bsky.app/profile/bsky.app/post/3l6oveex3ii2l"

system_message="""You are a helpful assistant that analyzes Bluesky posts.
Write a short 300 character summary of the post and its comments."""

response = process_post(url, system_message=system_message, max_posts=50, max_depth=1)

print(response)
```

```python
Bluesky's update introduces its open social network, emphasizing creator independence, developer freedom, and user choice. Users report issues with feed visibility, server errors, and content moderation. Concerns about hate speech and discrimination are raised, with suggestions for features like audience limits and video sections. Some users express gratitude, while others highlight challenges in engagement and platform functionality.
```

### Prerequisites

- **ffmpeg**: Required for video processing (extracting frames and audio)
- **Python 3.7+**

### Environment Setup

Create a `.env` file in your project directory with your AI API credentials. You can choose which provider to use by setting the appropriate environment variables:

```
# Azure OpenAI credentials
AZURE_OPENAI_KEY=your_azure_openai_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your_deployment_name
AZURE_OPENAI_API_VERSION=2023-08-01-preview

WHISPER_DEPLOYMENT_NAME=your_whisper_deployment_name
WHISPER_API_VERSION=2024-06-01

# Or OpenAI credentials
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4o
OPENAI_WHISPER_MODEL=whisper-1
```

## Individual Components

The module provides several individual functions that you can use separately:

```python
from bsky2llm.url_converter import convert_url_to_uri
from bsky2llm.get_raw_thread import get_raw_thread
from bsky2llm.markdown_creator import thread_to_markdown
from bsky2llm.md_to_openai import parse_markdown
from bsky2llm.ai_api_call import main_interface_function as call_ai_api

# Convert a Bluesky URL to post URI
post_url = "https://bsky.app/profile/atproto.com/post/3jwgckq72jp2d"
post_uri = convert_url_to_uri(post_url)

# Fetch the raw thread data
thread_data = get_raw_thread(post_uri, get_root=True, include_replies=True)

# Convert thread to markdown format
markdown = thread_to_markdown(thread_data, include_indices=True)

# Convert markdown to OpenAI message format
messages = parse_markdown(markdown, system_message="You are a helpful assistant analyzing a Bluesky thread.")

# Make an AI API call
response = call_ai_api(messages, debug=True)
print(response)
```

## License

MIT