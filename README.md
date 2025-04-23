# bsky2llm

A Python module for converting Bluesky posts and threads into OpenAI-compatible message format.

## Overview

This module provides a simple interface to fetch Bluesky posts/threads and convert them into the standard message format expected by OpenAI's API. It handles text content, images, and videos, with support for transcription.

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/bsky2llm.git
cd bsky2llm

# Install dependencies
pip install -r requirements.txt

# Create and configure .env file with your credentials
cp .env.example .env
```

## Usage

Basic usage example:

```python
import bsky2llm
import openai

# Step 1: Get structured messages from a Bluesky thread
post_uri = "at://did:plc:abc123/post/xyz456"
thread_json = bsky2llm.get_post_thread(post_uri)
messages = bsky2llm.compose_ai_prompt(thread_json)

# Step 2: Use those messages in an OpenAI API call
response = bsky2llm.ai_api_call(
    messages=messages,
    structured_output=True  # Optional, for structured output
)

print(response)
```

## Project Structure

```
bsky2llm/
├── src/
│   ├── __init__.py            # Package exports
│   ├── get_post_thread.py     # Get thread data in JSON format
│   ├── process_video.py       # Process video (download, frames, transcription)
│   ├── compose_ai_prompt.py   # Convert thread JSON to OpenAI messages
│   └── ai_api_call.py         # AzureOpenAI wrapper
├── requirements.txt           # Dependencies
└── README.md                  # This file
```

## Module Descriptions

Each module in the `src/` directory performs a specific function:

### get_post_thread.py
- **Input**: Post URI
- **Output**: Complete thread of post URI with relation structure, including users. JSON format with each post being one item. Includes URIs to videos and images and links. Neat structure for downstream processing.

### compose_ai_prompt.py
- **Input**: Thread JSON
- **Output**: List of messages to be sent to AI

### process_video.py
Will be called from compose_ai_prompt when there's a video. Downloads, extracts audio, transcribes, extract video frames.
- **Input**: Video URI
- **Output**: Input for composing AI messages

### ai_api_call.py
Simple AzureOpenAI wrapper that supports structured output (optional).
- **Input**: List of messages
- **Output**: Structured AI output

## Development

Each source file follows a consistent structure for better maintainability:
1. Imports
2. Logging setup
3. Helper functions
4. Main interface function
5. CLI test function

When run directly, each module will execute with verbose debugging output.
When imported, minimal logging is used.

## Environment Variables

Required environment variables (see .env.example):
- AZURE_OPENAI_KEY
- AZURE_OPENAI_ENDPOINT
- AZURE_OPENAI_DEPLOYMENT

## License

MIT