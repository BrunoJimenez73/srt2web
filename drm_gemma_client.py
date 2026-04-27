#!/usr/bin/env python3
"""
Docker Model Runner client for gemma4:E4B with maximum context support.
Configured to use the full 128K context window available in the model.
"""

import json
import sys
from typing import List, Dict, Any, Optional
from openai import OpenAI


class DMRGemmaClient:
    def __init__(
        self,
        base_url: str = "http://localhost:12434/engines/llama.cpp/v1",
        model: str = "docker.io/ai/gemma4:E4B",
        max_context_tokens: int = 131072,
        max_generation_tokens: int = 32768,
        temperature: float = 0.7,
    ):
        """
        Initialize the DMR client for gemma4:E4B.
        
        Args:
            base_url: DMR API endpoint
            model: Model identifier in DMR
            max_context_tokens: Total context window (set to model max: 128K)
            max_generation_tokens: Max tokens for generation (leave room for prompt)
            temperature: Sampling temperature
        """
        self.client = OpenAI(
            base_url=base_url,
            api_key="ignored",  # DMR doesn't use API key
        )
        self.model = model
        self.max_context_tokens = max_context_tokens
        self.max_generation_tokens = max_generation_tokens
        self.temperature = temperature
        
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Send a chat completion request to DMR.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Override max generation tokens
            temperature: Override temperature
            **kwargs: Additional parameters passed to OpenAI client
            
        Returns:
            Generated text response
        """
        params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens or self.max_generation_tokens,
            "temperature": temperature if temperature is not None else self.temperature,
            **kwargs
        }
        
        response = self.client.chat.completions.create(**params)
        return response.choices[0].message.content
    
    def generate_from_prompt(
        self,
        prompt: str,
        system_message: str = "Eres un asistente útil y preciso. Procesa el contexto proporcionado y responde de manera adecuada.",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Generate a response from a single prompt with system message.
        
        Args:
            prompt: User prompt/content
            system_message: System message to set behavior
            max_tokens: Override max generation tokens
            temperature: Override temperature
            
        Returns:
            Generated text response
        """
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
        return self.chat_completion(messages, max_tokens, temperature)


def main():
    """Command line interface for testing."""
    if len(sys.argv) < 2:
        print("Usage: python drm_gemma_client.py \"<prompt>\"")
        print("       or: python drm_gemma_client.py -f <file>")
        sys.exit(1)
    
    client = DMRGemmaClient()
    
    if sys.argv[1] == "-f" and len(sys.argv) > 2:
        # Read prompt from file
        with open(sys.argv[2], 'r', encoding='utf-8') as f:
            prompt = f.read()
    else:
        # Use command line argument as prompt
        prompt = " ".join(sys.argv[1:])
    
    print("Generating response with maximum context...")
    response = client.generate_from_prompt(prompt)
    print("\n" + "="*50)
    print("RESPONSE:")
    print("="*50)
    print(response)


if __name__ == "__main__":
    main()