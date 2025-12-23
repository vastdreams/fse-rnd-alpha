"""Low-level LLM client wrapper (OpenAI) with logging, retries, caching, and cost tracking."""
import time
from typing import Dict, Optional
from openai import OpenAI
from openai import RateLimitError, APIError, APITimeoutError
from src.ai.config import OPENAI_API_KEY, GPT_MODEL, MAX_TOKENS, TEMPERATURE, REQUEST_TIMEOUT
from src.logging.logger import get_logger
from src.utils.retry_handler import retry_on_rate_limit, retry_on_network_error
from src.ai.utils.gpt_cache import get_gpt_cache
from src.ai.utils.gpt_cost_tracker import get_cost_tracker

logger = get_logger(__name__)

client = None


def get_client() -> OpenAI:
    """Get OpenAI client, initializing if needed."""
    global client
    if client is None:
        client = OpenAI(api_key=OPENAI_API_KEY)
    return client


def call_gpt(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    max_retries: int = 3,
) -> Optional[str]:
    """
    Call GPT with enhanced retry logic and automatic fallback to available models.
    
    Features:
    - Automatic model fallback chain
    - Rate limit handling with exponential backoff
    - Timeout handling
    - Comprehensive error recovery
    """
    from src.ai.config import GPT_MODEL, MAX_TOKENS, TEMPERATURE, REQUEST_TIMEOUT
    
    model = model or GPT_MODEL
    client = get_client()
    
    # Model fallback chain (try latest first, fallback to older if not available)
    model_fallback = [
        "gpt-5.1",
        "gpt-5",
        "gpt-4o",
        "gpt-4-turbo-preview",
        "gpt-4-turbo",
    ]
    
    # If specified model is not in fallback, add it first
    if model not in model_fallback:
        model_fallback.insert(0, model)
    else:
        # Move requested model to front if it's in fallback
        if model in model_fallback:
            model_fallback.remove(model)
        model_fallback.insert(0, model)
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    # Check cache first
    cache = get_gpt_cache()
    cached_response = cache.get(prompt, system_prompt, model)
    if cached_response:
        logger.debug(f"Returning cached GPT response for prompt")
        return cached_response
    
    # Get cost tracker
    cost_tracker = get_cost_tracker()
    
    last_error = None
    for model_to_try in model_fallback:
        for attempt in range(max_retries):
            try:
                logger.debug(f"Calling GPT with model: {model_to_try} (attempt {attempt + 1}/{max_retries})")
                
                response = client.chat.completions.create(
                    model=model_to_try,
                    messages=messages,
                    max_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                    timeout=REQUEST_TIMEOUT,
                )
                
                if model_to_try != model:
                    logger.info(f"Successfully used {model_to_try} (requested {model} was not available)")
                
                content = response.choices[0].message.content
                
                # Track cost
                usage = response.usage
                if usage:
                    cost_tracker.record_call(
                        model=model_to_try,
                        input_tokens=usage.prompt_tokens or 0,
                        output_tokens=usage.completion_tokens or 0,
                        cached=False
                    )
                
                # Cache response
                cache.set(prompt, content, system_prompt, model_to_try)
                
                return content
                
            except RateLimitError as e:
                # Rate limit error - use longer backoff
                wait_time = min(60 * (2 ** attempt), 300)  # Max 5 minutes
                logger.warning(f"Rate limit exceeded for {model_to_try}, waiting {wait_time}s before retry...")
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                else:
                    last_error = e
                    break  # Try next model
                    
            except APITimeoutError as e:
                logger.warning(f"Timeout calling {model_to_try} (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    last_error = e
                    
            except APIError as e:
                error_str = str(e).lower()
                # If model not found, try next in fallback chain
                if "model" in error_str and ("not found" in error_str or "invalid" in error_str or "does not exist" in error_str):
                    logger.warning(f"Model {model_to_try} not available, trying fallback...")
                    last_error = e
                    break  # Break to try next model
                else:
                    # Other API error, retry with same model
                    logger.warning(f"API error with {model_to_try} (attempt {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        last_error = e
                        
            except Exception as e:
                error_str = str(e).lower()
                # If model not found, try next in fallback chain
                if "model" in error_str and ("not found" in error_str or "invalid" in error_str or "does not exist" in error_str):
                    logger.warning(f"Model {model_to_try} not available, trying fallback...")
                    last_error = e
                    break  # Break to try next model
                else:
                    # Other error, retry with same model
                    logger.warning(f"GPT call failed with {model_to_try} (attempt {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        last_error = e
    
    logger.error(f"GPT call failed after trying all models and retries. Last error: {last_error}")
    return None
