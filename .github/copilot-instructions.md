# bsky2llm Coding Guidelines

This document outlines the coding standards and architectural guidelines for the bsky2llm project.

## Project Organization

- All main functionality should be in the `src/bsky2llm/` folder
- Keep files modular with specific responsibilities
- Follow the consistent file structure pattern

## Coding Standards

### File Structure

Each source file in `src/bsky2llm/` should follow this format:

1. **IMPORTS**:
   - Import necessary libraries (os, requests, logging, etc.)

2. **SETUP LOGGING FUNCTION**:
   - Configure logging with different levels for standalone vs imported use

3. **HELPER CLASSES/FUNCTIONS**:
   - Implement necessary helper functionality
   - Handle edge cases and error conditions

4. **PRIMARY INTERFACE FUNCTION**:
   - Define the main function that external code will call
   - Include clear docstring with parameters and return values
   - Return appropriate values or None if failed

5. **MAIN FUNCTION**:
   - Keep minimal with hardcoded examples for testing
   - Include debug=True for verbose output when run directly
   - Print clear output suitable for command-line use
   - Never use args

6. **SCRIPT EXECUTION CHECK**:
   ```python
   if __name__ == "__main__":
       main()
   ```

### General Guidelines

- Never use chmod in scripts - run files with `python xxx.py`
- Use the public Bluesky API endpoint when possible: https://public.api.bsky.app
- Add dependencies to requirements.txt with latest possible versions
- Install dependencies with `pip install -r requirements.txt`
- Debug output should be verbose when run directly, minimal when imported


## Example Module Template

```python
#!/usr/bin/env python3
"""
Module description goes here.
"""

import logging
import requests
# Other necessary imports

def setup_logging(debug=False):
    """Configure logging based on debug mode"""
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level, 
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def helper_function():
    """Helper function description"""
    # Helper function implementation
    pass

def main_interface_function(param, debug=False):
    """
    Main interface function description
    
    Args:
        param: Input parameter description
        debug: Enable verbose logging
        
    Returns:
        Output description or None if failed
    """
    setup_logging(debug)
    logging.debug(f"Processing: {param}")
    
    # Main function logic here
    
    return result

def main():
    """Main function with hardcoded example"""
    example_input = "example"
    output = main_interface_function(example_input, debug=True)
    
    if output:
        print(f"\nProcessed successfully: {output}")
        print(output)  # Clean output for piping
    else:
        print("\nProcessing failed")

if __name__ == "__main__":
    main()
```