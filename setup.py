from setuptools import setup, find_packages
import os

# Define requirements directly instead of reading from file
requirements = [
    "requests==2.32.3",
    "python-dotenv==1.1.0",
    "openai==1.76.0",
    "opencv-python==4.11.0.86",
    "streamlink==7.2.0"
]

# Define long description directly
long_description = """
# bsky2llm

A Python module for analyzing Bluesky posts and threads using AI models.

## Installation

```bash
pip install bsky2llm
```

## Usage

```python
from bsky2llm import process_post

# Process a Bluesky post and get AI analysis
result = process_post("at://did:plc:12345/app.bsky.feed.post/12345")
print(result)
```

See GitHub repository for more details: https://github.com/circularmachines/bsky2llm
"""

setup(
    name="bsky2llm",
    version="0.1.0",
    description="A Python module for analyzing Bluesky posts and threads using AI models",
    author="Johan Lagerlöf",
    author_email="laagrrluv@gmail.com",  # Replace with your actual email
    url="https://github.com/circularmachines/bsky2llm",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=requirements,
    python_requires=">=3.7",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    long_description=long_description,
    long_description_content_type="text/markdown",
)