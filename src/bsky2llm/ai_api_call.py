#!/usr/bin/env python3
"""
AI API call module for bsky2llm.
Simple wrapper for making calls to Azure OpenAI API.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Union
from dotenv import load_dotenv
import openai
from tenacity import retry, stop_after_attempt, wait_random_exponential

def setup_logging(debug=False):
    """Configure logging based on debug mode"""
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level, 
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def _setup_azure_openai():
    """
    Configure Azure OpenAI client using environment variables
    
    Returns:
        bool: True if setup was successful, False otherwise
    """
    # Load environment variables
    load_dotenv()
    
    # Get Azure OpenAI API credentials
    api_key = os.getenv("AZURE_OPENAI_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2023-08-01-preview")
    
    if not api_key or not endpoint:
        logging.error("Azure OpenAI API credentials not found in environment variables")
        return False
    
    # Configure OpenAI client for Azure
    openai.api_type = "azure"
    openai.api_key = api_key
    openai.api_base = endpoint
    openai.api_version = api_version
    
    return True

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def _make_api_call(
    messages: List[Dict[str, Any]],
    deployment_id: str,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    structured_output: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Make an API call to Azure OpenAI with retry logic
    
    Args:
        messages: List of messages to send to the API
        deployment_id: Azure OpenAI deployment ID
        temperature: Temperature for response generation
        max_tokens: Maximum tokens in the response
        structured_output: Schema for structured output (optional)
        
    Returns:
        API response
    """
    kwargs = {
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "deployment_id": deployment_id,
    }
    
    # Add structured output parameters if provided
    if structured_output:
        kwargs["response_format"] = {"type": "json_object"}
        
        # Add system message for structured output if not already present
        if not any(msg.get("role") == "system" for msg in messages):
            messages.insert(0, {
                "role": "system",
                "content": "You provide responses in JSON format."
            })
        # Otherwise, update the existing system message
        else:
            for msg in messages:
                if msg.get("role") == "system":
                    msg["content"] += " You provide responses in JSON format."
                    break
        
        # Add the structure definition to the system message
        for msg in messages:
            if msg.get("role") == "system":
                msg["content"] += f" Please provide a response using this JSON structure: {json.dumps(structured_output)}"
                break
    
    # Make the API call
    response = openai.ChatCompletion.create(**kwargs)
    return response

def ai_api_call(
    messages: List[Dict[str, Any]],
    structured_output: Optional[Dict[str, Any]] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    debug: bool = False
) -> Union[str, Dict[str, Any]]:
    """
    Make an API call to Azure OpenAI with the provided messages
    
    Args:
        messages (List[Dict[str, Any]]): List of messages in OpenAI format
        structured_output (Optional[Dict[str, Any]]): Schema for structured JSON output
        temperature (float): Temperature for response generation (0-1)
        max_tokens (int): Maximum tokens in the response
        debug (bool): Enable verbose debug output
        
    Returns:
        Union[str, Dict[str, Any]]: API response content as string or parsed JSON if structured_output was used
    """
    setup_logging(debug)
    load_dotenv()
    
    logging.debug(f"Making API call with {len(messages)} messages")
    
    # Setup Azure OpenAI client
    if not _setup_azure_openai():
        logging.error("Failed to setup Azure OpenAI client")
        return "Error: Azure OpenAI client setup failed. Check credentials."
    
    try:
        # Get deployment ID from environment or use default
        deployment_id = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        if not deployment_id:
            logging.error("Azure OpenAI deployment ID not found in environment variables")
            return "Error: Azure OpenAI deployment ID not specified"
        
        logging.debug(f"Using deployment ID: {deployment_id}")
        
        # Make the API call
        response = _make_api_call(
            messages=messages,
            deployment_id=deployment_id,
            temperature=temperature,
            max_tokens=max_tokens,
            structured_output=structured_output
        )
        
        # Extract the content from the response
        content = response['choices'][0]['message']['content']
        
        # If structured output was requested, parse the JSON response
        if structured_output and content:
            try:
                # Parse JSON response
                parsed_response = json.loads(content)
                logging.debug("Successfully parsed structured JSON response")
                return parsed_response
            except json.JSONDecodeError:
                logging.error("Failed to parse structured response as JSON")
                return content
        
        return content
        
    except Exception as e:
        logging.error(f"Error making API call: {e}")
        return f"Error: {str(e)}"

def main():
    """Main function with hardcoded example"""
    # Example messages
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that provides concise summaries."
        },
        {
            "role": "user",
            "content": "Summarize the key features of Python in a few points."
        }
    ]
    
    # Example structured output schema
    structured_output = {
        "summary": "A concise summary of the key points",
        "points": ["Array of bullet points"],
        "complexity": "A rating of complexity (1-5)"
    }
    
    # Make API call with debug output
    print("\nMaking standard API call...")
    response = ai_api_call(messages, debug=True)
    
    if response and not response.startswith("Error"):
        print("\nAPI call successful:")
        print(response)
    else:
        print(f"\nAPI call failed: {response}")
    
    # Make API call with structured output
    print("\nMaking structured API call...")
    structured_response = ai_api_call(
        messages, 
        structured_output=structured_output,
        debug=True
    )
    
    if isinstance(structured_response, dict):
        print("\nStructured API call successful:")
        print(json.dumps(structured_response, indent=2))
    else:
        print(f"\nStructured API call failed or returned non-JSON: {structured_response}")

if __name__ == "__main__":
    main()