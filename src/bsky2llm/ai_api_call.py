#!/usr/bin/env python3
"""
AI API Call module for making simple calls to Azure OpenAI or OpenAI models.

This script takes a list of messages in OpenAI format and returns the chat response as text.
It supports both Azure OpenAI and standard OpenAI, removing all JSON structure requirements for simplicity.
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
from openai import AzureOpenAI, OpenAI

def setup_logging(debug=False):
    """Configure logging based on debug mode"""
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level, 
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

class AIApiCaller:
    """Class to handle AI API calls with simple text responses"""
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 azure_endpoint: Optional[str] = None,
                 api_version: Optional[str] = None,
                 deployment_name: Optional[str] = None,
                 openai_api_key: Optional[str] = None,
                 openai_model: Optional[str] = None):
        """Initialize the AI API caller with credentials"""
        self.logger = logging.getLogger(__name__ + ".AIApiCaller")
        
        # Use provided credentials or try to load from environment variables
        # Check multiple possible environment variable names for API keys
        self.api_key = api_key or os.getenv("AZURE_OPENAI_KEY")
        self.azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_version = api_version or os.getenv("GPT_API_VERSION") or os.getenv("WHISPER_API_VERSION", "2023-05-15")
        self.deployment_name = deployment_name or os.getenv("GPT_DEPLOYMENT_NAME", "gpt-4o") or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        
        # OpenAI specific credentials
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.openai_model = openai_model or os.getenv("OPENAI_MODEL", "gpt-4o")
        
        # Initialize clients based on available credentials
        self.azure_client = None
        self.openai_client = None
        
        # Debug information
        if self.azure_endpoint and self.api_key:
            self.logger.debug(f"Azure Endpoint: {self.azure_endpoint}")
            self.logger.debug(f"API Version: {self.api_version}")
            self.logger.debug(f"Model Deployment: {self.deployment_name}")
        
        if self.openai_api_key:
            self.logger.debug(f"OpenAI Model: {self.openai_model}")
        
        # Initialize Azure client if credentials are available
        if self.api_key and self.azure_endpoint:
            self.logger.info("Initializing Azure OpenAI client")
            try:
                self.azure_client = AzureOpenAI(
                    api_key=self.api_key,
                    azure_endpoint=self.azure_endpoint,
                    api_version=self.api_version
                )
                self.logger.info("Azure OpenAI client initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize Azure OpenAI client: {str(e)}")
                self.logger.error(f"Error details: {e}")
        
        # Initialize OpenAI client if API key is available
        if self.openai_api_key:
            self.logger.info("Initializing OpenAI client")
            try:
                self.openai_client = OpenAI(api_key=self.openai_api_key)
                self.logger.info("OpenAI client initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize OpenAI client: {str(e)}")
                self.logger.error(f"Error details: {e}")
        
        # Log warning if no clients were initialized
        if not self.azure_client and not self.openai_client:
            missing = []
            if not self.api_key and not self.openai_api_key:
                missing.append("API_KEY (checked AZURE_OPENAI_KEY, OPENAI_API_KEY)")
            if not self.azure_endpoint and not self.openai_api_key:
                missing.append("AZURE_OPENAI_ENDPOINT or OPENAI_API_KEY")
            self.logger.warning(f"No OpenAI clients initialized: missing {', '.join(missing)}")
    
    def call_ai_api(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        """
        Call AI API with the provided messages and return simple text response
        
        Args:
            messages: List of message dictionaries with role and content
            
        Returns:
            Text response from the AI or None if failed
        """
        if not self.azure_client and not self.openai_client:
            self.logger.error("Cannot call AI API without an initialized client")
            return None
            
        self.logger.info(f"Calling AI API with {len(messages)} messages")
        
        try:
            # Prioritize OpenAI client if available
            if self.openai_client:
                self.logger.info(f"Using OpenAI with model: {self.openai_model}")
                
                completion = self.openai_client.chat.completions.create(
                    model=self.openai_model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000
                )
                
                self.logger.info("Received response from OpenAI API")
            
            # Fall back to Azure client
            elif self.azure_client:
                self.logger.info(f"Using Azure OpenAI with deployment: {self.deployment_name}")
                
                completion = self.azure_client.chat.completions.create(
                    model=self.deployment_name,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000
                )
                
                self.logger.info("Received response from Azure OpenAI API")
            
            # Get the response content
            response = completion.choices[0].message.content
            self.logger.debug(f"Response content: {response[:100]}...")
            
            return response
                
        except Exception as e:
            self.logger.error(f"Error calling AI API: {str(e)}")
            return None

def load_messages(file_path: str) -> List[Dict[str, Any]]:
    """Load messages from a JSON file"""
    logger = logging.getLogger(__name__)
    try:
        logger.info(f"Loading messages from {file_path}")
        with open(file_path, 'r') as f:
            messages = json.load(f)
        logger.info(f"Loaded {len(messages)} messages")
        return messages
    except Exception as e:
        logger.error(f"Error loading messages: {str(e)}")
        return []

def main_interface_function(
    messages_file: str,
    output_file: Optional[str] = None,
    debug: bool = False
) -> Optional[str]:
    """
    Main interface function to load messages and get AI response.
    
    Args:
        messages_file: Path to the JSON file containing messages
        output_file: Optional path to save the response to a file
        debug: Enable verbose logging
        
    Returns:
        AI response text or None if failed
    """
    setup_logging(debug)
    logger = logging.getLogger(__name__)
    
    # Load environment variables
    load_dotenv()
    
    # Load messages from file
    messages = load_messages(messages_file)
    if not messages:
        logger.error("No messages loaded, exiting")
        return None
        
    # Create API caller
    api_caller = AIApiCaller()
    
    # Make API call
    response = api_caller.call_ai_api(messages)
    
    if response:
        logger.info("AI API call successful")
        
        # Save to file if requested
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    f.write(response)
                logger.info(f"Response saved to {output_file}")
            except Exception as e:
                logger.error(f"Failed to save response to file: {e}")
    else:
        logger.error("Failed to get AI response")
    
    return response

def main():
    """Main function with hardcoded example"""
    # Use hardcoded path to messages.json
    example_input = "tests/messages_example.json"
    
    # Call the API and get response
    response = main_interface_function(
        messages_file=example_input,
        debug=True
    )
    
    if response:
        print("\nAI API call successful:")
        print(response)  # Clean output for piping
    else:
        print("\nFailed to get AI response")

if __name__ == "__main__":
    main()