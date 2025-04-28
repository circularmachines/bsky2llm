from setuptools import setup, find_packages

# Read requirements from requirements.txt
with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="bsky2llm",
    version="0.1.0",
    description="A Python module for analyzing Bluesky posts and threads using AI models",
    author="Johan Lagerlöf",
    author_email="johan.lagerloef@gmail.com",
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
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
)