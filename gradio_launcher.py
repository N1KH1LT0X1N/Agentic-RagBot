"""
MediGuard AI — Gradio Launcher wrapper.

Spawns the Gradio frontend UI on the correct designated port (7861), separating
the frontend runner from the production API layer entirely.
"""

import logging
import os
import sys

# Ensure project root is in path
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.gradio_app import launch_gradio

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    port = int(os.environ.get("GRADIO_PORT", 7861))
    logging.info("Starting Gradio Web UI Launcher on port %d...", port)
    launch_gradio(share=False, server_port=port)
