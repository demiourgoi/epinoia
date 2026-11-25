"""Azathoth: a localhost-only OpenAI-compatible chat completions proxy.

Forwards chat completion requests to an Agent Client Protocol agent with all
tools disabled, and returns the answer in the OpenAI response format.
"""

from importlib.metadata import version

__version__ = version("azathoth")

__all__ = ["__version__"]
