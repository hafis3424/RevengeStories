"""
Configuration settings for Revenge Stories Voice Generator
Edit this file to customize the application behavior.
"""

# =============================================================================
# TEXT INPUT LIMITS
# =============================================================================

# Maximum characters allowed in the story text input
# With auto-chunking, the app can handle very long texts
TEXT_CHAR_LIMIT = 200000  # 200k characters max

# Chunk size for splitting long texts (edge-tts has a ~5000 char limit per request)
# Leave some buffer below the actual limit
CHUNK_SIZE = 4500


# =============================================================================
# SUBTITLE (SRT) SETTINGS
# =============================================================================

# Maximum characters per subtitle entry
# Words are grouped into sentences until they hit this limit
# Keep this reasonable for readability (150-400 chars typical)
MAX_SUBTITLE_CHARS = 350


# =============================================================================
# VOICE SETTINGS
# =============================================================================

# Default voice if none selected
DEFAULT_VOICE = "en-US-GuyNeural"

# Default speech rate (negative = slower, positive = faster)
# Range: -50% to +50%
DEFAULT_RATE = "-5%"

# Default pitch (negative = lower, positive = higher)
# Range: -50Hz to +50Hz
DEFAULT_PITCH = "-5Hz"


# =============================================================================
# OUTPUT DIRECTORIES
# =============================================================================

# Where to save generated audio files
OUTPUT_DIR = "output/audio"

# Where to save/load story text files
STORIES_DIR = "stories"


# =============================================================================
# SERVER SETTINGS
# =============================================================================

# Flask server port
SERVER_PORT = 5000

# Enable Flask debug mode (auto-reload on file changes)
DEBUG_MODE = True
