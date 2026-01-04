"""
Voice Generator for Revenge Stories
Uses edge-tts to convert story text to speech
"""

import edge_tts
import asyncio
import os
import sys
from pathlib import Path

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')

# Configuration
VOICE_CONFIG = {
    # Popular voices for storytelling - dramatic male voices work great for revenge stories
    "default": "en-US-GuyNeural",           # Deep, engaging male voice
    "dramatic": "en-US-ChristopherNeural",  # More dramatic tone
    "female": "en-US-JennyNeural",          # Clear female voice
    "british_male": "en-GB-RyanNeural",     # British accent
    "british_female": "en-GB-SoniaNeural",  # British female
}

# Speaking rate and pitch adjustments
SPEECH_RATE = "-5%"   # Slightly slower for dramatic effect
SPEECH_PITCH = "-5Hz" # Slightly deeper for dramatic stories


class VoiceGenerator:
    def __init__(self, voice: str = "default", output_dir: str = "output/audio"):
        """
        Initialize the voice generator.
        
        Args:
            voice: Voice preset name or full voice ID
            output_dir: Directory to save generated audio files
        """
        self.voice = VOICE_CONFIG.get(voice, voice)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def generate_audio(self, text: str, filename: str, 
                            rate: str = SPEECH_RATE, 
                            pitch: str = SPEECH_PITCH) -> str:
        """
        Generate audio from text using edge-tts.
        
        Args:
            text: The story text to convert to speech
            filename: Output filename (without extension)
            rate: Speech rate adjustment (e.g., "+10%", "-5%")
            pitch: Pitch adjustment (e.g., "+5Hz", "-10Hz")
            
        Returns:
            Path to the generated audio file
        """
        output_path = self.output_dir / f"{filename}.mp3"
        
        # Create the TTS communicate object with voice settings
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=rate,
            pitch=pitch
        )
        
        # Generate and save the audio
        await communicate.save(str(output_path))
        
        print(f"[OK] Audio generated: {output_path}")
        return str(output_path)
    
    async def generate_with_subtitles(self, text: str, filename: str,
                                      rate: str = SPEECH_RATE,
                                      pitch: str = SPEECH_PITCH) -> tuple:
        """
        Generate audio with subtitle timing data (for later video generation).
        
        Args:
            text: The story text to convert to speech
            filename: Output filename (without extension)
            rate: Speech rate adjustment
            pitch: Pitch adjustment
            
        Returns:
            Tuple of (audio_path, subtitles_list)
        """
        output_audio = self.output_dir / f"{filename}.mp3"
        output_srt = self.output_dir / f"{filename}.srt"
        
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=rate,
            pitch=pitch,
            boundary="WordBoundary"  # Enable word-level timing for subtitles
        )
        
        # Use SubMaker for proper subtitle generation
        submaker = edge_tts.SubMaker()
        
        # Collect audio and feed subtitle data to SubMaker
        with open(output_audio, "wb") as audio_file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_file.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    submaker.feed(chunk)
        
        # Generate SRT content using SubMaker
        srt_content = submaker.get_srt()
        
        # Save SRT file
        with open(output_srt, "w", encoding="utf-8") as srt_file:
            srt_file.write(srt_content)
        
        print(f"[OK] Audio generated: {output_audio}")
        print(f"[OK] Subtitles generated: {output_srt}")
        
        return str(output_audio), []
    
    def _generate_srt(self, word_timings: list, output_path: Path, words_per_subtitle: int = 8):
        """
        Generate SRT subtitle file from word timings.
        Groups words into readable subtitle chunks.
        """
        srt_content = []
        subtitle_num = 1
        
        # Group words into subtitle chunks
        for i in range(0, len(word_timings), words_per_subtitle):
            chunk = word_timings[i:i + words_per_subtitle]
            if not chunk:
                continue
                
            start_time = chunk[0]["start"]
            end_time = chunk[-1]["start"] + chunk[-1]["duration"]
            text = " ".join(w["text"] for w in chunk)
            
            # Format timestamps for SRT
            start_str = self._format_srt_time(start_time)
            end_str = self._format_srt_time(end_time)
            
            srt_content.append(f"{subtitle_num}")
            srt_content.append(f"{start_str} --> {end_str}")
            srt_content.append(text)
            srt_content.append("")
            
            subtitle_num += 1
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_content))
    
    def _format_srt_time(self, seconds: float) -> str:
        """Convert seconds to SRT time format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_voice(text: str, filename: str, voice: str = "default", 
                   with_subtitles: bool = True) -> str:
    """
    Simple function to generate voice from text.
    
    Args:
        text: Story text to convert
        filename: Output filename (without extension)
        voice: Voice preset or full voice ID
        with_subtitles: Whether to generate subtitle timing data
        
    Returns:
        Path to generated audio file
    """
    generator = VoiceGenerator(voice=voice)
    
    if with_subtitles:
        audio_path, _ = asyncio.run(generator.generate_with_subtitles(text, filename))
    else:
        audio_path = asyncio.run(generator.generate_audio(text, filename))
    
    return audio_path


# Example usage
if __name__ == "__main__":
    # Sample revenge story
    sample_story = """
    My neighbor had been stealing packages from my porch for months. 
    I finally had enough. So I ordered a glitter bomb and a GPS tracker.
    
    When they opened it in their living room, they got covered in 
    fine glitter that took weeks to clean up. The best part? 
    I captured everything on my security camera.
    
    They never stole another package again.
    """
    
    print("=== Revenge Stories Voice Generator ===")
    print("=" * 40)
    print(f"Generating audio for sample story...")
    
    # Generate with subtitles (default)
    audio_path = generate_voice(
        text=sample_story.strip(),
        filename="sample_revenge_story",
        voice="default",
        with_subtitles=True
    )
    
    print(f"\n[DONE] Audio saved to: {audio_path}")
