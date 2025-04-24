from setuptools import setup, find_packages

# Read requirements from requirements.txt
with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="bsky2llm",
    version="0.1.0",
    description="A project for integrating Bluesky API with LLMs",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/circularmachines/bsky2llm",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=requirements,
    python_requires=">=3.7",
)