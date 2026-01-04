"""
Batch Voice Generator for Revenge Stories
Processes all .txt files in the stories folder
"""

import os
import sys
from pathlib import Path

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')

from voice_generator import generate_voice, VoiceGenerator, VOICE_CONFIG

STORIES_DIR = Path("stories")
OUTPUT_DIR = Path("output/audio")


def list_available_voices():
    """Print available voice presets"""
    print("\n[VOICES] Available Voice Presets:")
    print("-" * 40)
    for name, voice_id in VOICE_CONFIG.items():
        print(f"  {name:20} -> {voice_id}")
    print()


def process_all_stories(voice: str = "default", with_subtitles: bool = True):
    """
    Process all story files in the stories directory.
    
    Args:
        voice: Voice preset to use
        with_subtitles: Generate subtitle files alongside audio
    """
    if not STORIES_DIR.exists():
        print(f"[ERROR] Stories directory not found: {STORIES_DIR}")
        print("   Create the 'stories' folder and add .txt files")
        return
    
    # Find all story files
    story_files = list(STORIES_DIR.glob("*.txt"))
    
    if not story_files:
        print(f"[ERROR] No .txt files found in {STORIES_DIR}")
        return
    
    print(f"[INFO] Found {len(story_files)} stories to process")
    print(f"[VOICE] Using: {VOICE_CONFIG.get(voice, voice)}")
    print("=" * 50)
    
    # Character limit for edge-tts (safe limit)
    CHAR_LIMIT = 5000
    
    successful = 0
    failed = 0
    total_chars = 0
    total_words = 0
    
    for story_file in sorted(story_files):
        print(f"\n[PROCESSING] {story_file.name}")
        
        try:
            # Read story content
            with open(story_file, "r", encoding="utf-8") as f:
                story_text = f.read().strip()
            
            if not story_text:
                print(f"   [SKIP] File is empty")
                continue
            
            # Show character and word count
            char_count = len(story_text)
            word_count = len(story_text.split())
            total_chars += char_count
            total_words += word_count
            
            print(f"   [STATS] {char_count:,} chars | {word_count:,} words")
            
            if char_count > CHAR_LIMIT:
                print(f"   [WARNING] Exceeds {CHAR_LIMIT:,} char limit - may need chunking")
            
            # Generate audio
            filename = story_file.stem  # filename without extension
            audio_path = generate_voice(
                text=story_text,
                filename=filename,
                voice=voice,
                with_subtitles=with_subtitles
            )
            
            successful += 1
            
        except Exception as e:
            print(f"   [ERROR] {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"[SUCCESS] Processed: {successful}")
    if failed > 0:
        print(f"[FAILED] {failed}")
    print(f"[TOTAL] {total_chars:,} chars | {total_words:,} words")
    print(f"[OUTPUT] {OUTPUT_DIR.absolute()}")


def process_single_story(filepath: str, voice: str = "default"):
    """Process a single story file"""
    story_path = Path(filepath)
    
    if not story_path.exists():
        print(f"[ERROR] File not found: {filepath}")
        return
    
    with open(story_path, "r", encoding="utf-8") as f:
        story_text = f.read().strip()
    
    filename = story_path.stem
    audio_path = generate_voice(
        text=story_text,
        filename=filename,
        voice=voice,
        with_subtitles=True
    )
    
    print(f"\n[DONE] Audio: {audio_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch generate voice for revenge stories")
    parser.add_argument("--voice", "-v", default="default", 
                        help="Voice preset (default, dramatic, female, british_male, british_female)")
    parser.add_argument("--file", "-f", type=str,
                        help="Process single file instead of batch")
    parser.add_argument("--list-voices", action="store_true",
                        help="List available voice presets")
    parser.add_argument("--no-subtitles", action="store_true",
                        help="Skip subtitle generation")
    
    args = parser.parse_args()
    
    print("=== Revenge Stories - Voice Generator ===")
    print("=" * 50)
    
    if args.list_voices:
        list_available_voices()
    elif args.file:
        process_single_story(args.file, args.voice)
    else:
        process_all_stories(
            voice=args.voice,
            with_subtitles=not args.no_subtitles
        )
