"""
processor/pipeline/__init__.py
===============================
Ana çeviri pipeline'ı için paket giriş noktası.
"""
from processor.pipeline.main import process_and_replace_subtitle

__all__ = ["process_and_replace_subtitle"]
