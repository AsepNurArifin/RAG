"""
EnterpriseMind AI — Backend Application Package.
"""
import os

# Disable Hugging Face Hub symlinks globally on Windows systems where developer mode is disabled
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"

__version__ = "1.0.0"
__author__ = "EnterpriseMind Team"
