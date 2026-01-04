"""
Revenge Stories - Voice Generator Web UI
"""

from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, Response
import os
import sys
from pathlib import Path
import asyncio
import edge_tts
import time
import json

# Import configuration
from config import (
    TEXT_CHAR_LIMIT, CHUNK_SIZE, MAX_SUBTITLE_CHARS,
    DEFAULT_VOICE, DEFAULT_RATE, DEFAULT_PITCH,
    OUTPUT_DIR as OUTPUT_DIR_STR, STORIES_DIR as STORIES_DIR_STR,
    SERVER_PORT, DEBUG_MODE
)

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__)

# Progress tracking for each generation job
generation_progress = {}

# Configuration from config.py
OUTPUT_DIR = Path(OUTPUT_DIR_STR)
STORIES_DIR = Path(STORIES_DIR_STR)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
STORIES_DIR.mkdir(parents=True, exist_ok=True)

CHAR_LIMIT = TEXT_CHAR_LIMIT

# Cache for voices
_voices_cache = None


async def get_all_voices():
    """Fetch all available voices from edge-tts"""
    global _voices_cache
    if _voices_cache is not None:
        return _voices_cache
    
    voices = await edge_tts.list_voices()
    
    # Organize voices by language
    organized = {}
    for voice in voices:
        locale = voice['Locale']
        lang_code = locale.split('-')[0]
        
        # Get language name from locale
        lang_names = {
            'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
            'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian', 'ja': 'Japanese',
            'ko': 'Korean', 'zh': 'Chinese', 'ar': 'Arabic', 'hi': 'Hindi',
            'nl': 'Dutch', 'pl': 'Polish', 'tr': 'Turkish', 'vi': 'Vietnamese',
            'th': 'Thai', 'id': 'Indonesian', 'ms': 'Malay', 'fil': 'Filipino',
            'cs': 'Czech', 'da': 'Danish', 'fi': 'Finnish', 'el': 'Greek',
            'he': 'Hebrew', 'hu': 'Hungarian', 'no': 'Norwegian', 'nb': 'Norwegian',
            'ro': 'Romanian', 'sk': 'Slovak', 'sv': 'Swedish', 'uk': 'Ukrainian',
            'bg': 'Bulgarian', 'hr': 'Croatian', 'lt': 'Lithuanian', 'lv': 'Latvian',
            'sl': 'Slovenian', 'et': 'Estonian', 'ta': 'Tamil', 'te': 'Telugu',
            'bn': 'Bengali', 'gu': 'Gujarati', 'kn': 'Kannada', 'ml': 'Malayalam',
            'mr': 'Marathi', 'pa': 'Punjabi', 'ur': 'Urdu', 'fa': 'Persian',
            'sw': 'Swahili', 'af': 'Afrikaans', 'am': 'Amharic', 'az': 'Azerbaijani',
            'bs': 'Bosnian', 'ca': 'Catalan', 'cy': 'Welsh', 'ga': 'Irish',
            'gl': 'Galician', 'is': 'Icelandic', 'jv': 'Javanese', 'ka': 'Georgian',
            'kk': 'Kazakh', 'km': 'Khmer', 'lo': 'Lao', 'mk': 'Macedonian',
            'mn': 'Mongolian', 'mt': 'Maltese', 'my': 'Myanmar', 'ne': 'Nepali',
            'ps': 'Pashto', 'si': 'Sinhala', 'so': 'Somali', 'sq': 'Albanian',
            'sr': 'Serbian', 'su': 'Sundanese', 'uz': 'Uzbek', 'zu': 'Zulu'
        }
        
        lang_name = lang_names.get(lang_code, locale)
        
        # Create region label
        region = locale.split('-')[1] if '-' in locale else ''
        region_names = {
            'US': 'US', 'GB': 'UK', 'AU': 'Australia', 'CA': 'Canada',
            'IN': 'India', 'IE': 'Ireland', 'NZ': 'New Zealand', 'ZA': 'South Africa',
            'PH': 'Philippines', 'SG': 'Singapore', 'HK': 'Hong Kong', 'TW': 'Taiwan',
            'CN': 'China', 'MX': 'Mexico', 'ES': 'Spain', 'AR': 'Argentina',
            'CO': 'Colombia', 'CL': 'Chile', 'PE': 'Peru', 'VE': 'Venezuela',
            'BR': 'Brazil', 'PT': 'Portugal', 'FR': 'France', 'BE': 'Belgium',
            'CH': 'Switzerland', 'DE': 'Germany', 'AT': 'Austria', 'IT': 'Italy',
            'RU': 'Russia', 'JP': 'Japan', 'KR': 'Korea', 'SA': 'Saudi Arabia',
            'AE': 'UAE', 'EG': 'Egypt', 'IL': 'Israel', 'TR': 'Turkey',
            'PL': 'Poland', 'NL': 'Netherlands', 'SE': 'Sweden', 'NO': 'Norway',
            'DK': 'Denmark', 'FI': 'Finland', 'CZ': 'Czech', 'GR': 'Greece',
            'HU': 'Hungary', 'RO': 'Romania', 'UA': 'Ukraine', 'TH': 'Thailand',
            'VN': 'Vietnam', 'ID': 'Indonesia', 'MY': 'Malaysia', 'KE': 'Kenya',
            'NG': 'Nigeria', 'TZ': 'Tanzania', 'PK': 'Pakistan', 'BD': 'Bangladesh',
            'LK': 'Sri Lanka', 'NP': 'Nepal', 'MM': 'Myanmar', 'KH': 'Cambodia',
            'LA': 'Laos', 'AF': 'Afghanistan'
        }
        
        region_label = region_names.get(region, region)
        
        # Extract name from ShortName (e.g., "en-US-GuyNeural" -> "Guy")
        short_name = voice['ShortName']
        name_part = short_name.split('-')[-1].replace('Neural', '').replace('Multilingual', '')
        
        gender = voice.get('Gender', 'Unknown')
        gender_icon = '♂️' if gender == 'Male' else '♀️' if gender == 'Female' else ''
        
        voice_data = {
            'id': short_name,
            'name': name_part,
            'gender': gender,
            'locale': locale,
            'region': region_label,
            'display': f"{name_part} {gender_icon} ({region_label})"
        }
        
        # Group by language
        if lang_name not in organized:
            organized[lang_name] = []
        organized[lang_name].append(voice_data)
    
    # Sort languages and voices
    for lang in organized:
        organized[lang].sort(key=lambda x: (x['name'], x['region']))
    
    _voices_cache = dict(sorted(organized.items()))
    return _voices_cache


def get_voices_sync():
    """Synchronous wrapper to get voices"""
    return asyncio.run(get_all_voices())



def split_text_into_chunks(text: str, max_chars: int = CHUNK_SIZE) -> list:
    """Split text into chunks at sentence boundaries"""
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # Split by sentences (periods, exclamation marks, question marks)
    sentences = []
    temp = ""
    for char in text:
        temp += char
        if char in '.!?' and len(temp.strip()) > 0:
            sentences.append(temp.strip())
            temp = ""
    if temp.strip():
        sentences.append(temp.strip())
    
    for sentence in sentences:
        # If single sentence is too long, split by words
        if len(sentence) > max_chars:
            words = sentence.split()
            for word in words:
                if len(current_chunk) + len(word) + 1 > max_chars:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = word + " "
                else:
                    current_chunk += word + " "
        elif len(current_chunk) + len(sentence) + 1 > max_chars:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
        else:
            current_chunk += sentence + " "
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks


import re
from mutagen.mp3 import MP3
import io

def parse_srt_time(time_str: str) -> float:
    """Convert SRT timestamp to seconds"""
    match = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})', time_str)
    if match:
        h, m, s, ms = map(int, match.groups())
        return h * 3600 + m * 60 + s + ms / 1000
    return 0

def format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp format"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def offset_srt_timestamps(srt_content: str, offset_seconds: float, start_index: int = 1) -> tuple:
    """Offset all timestamps in SRT content and renumber entries. Returns (new_srt, last_index)"""
    if not srt_content.strip():
        return "", start_index
    
    lines = srt_content.strip().split('\n')
    new_lines = []
    current_index = start_index
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue
        
        # Check if this is a subtitle index (number)
        if line.isdigit():
            # Next line should be timestamp
            if i + 1 < len(lines):
                timestamp_line = lines[i + 1].strip()
                timestamp_match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', timestamp_line)
                
                if timestamp_match:
                    start_time = parse_srt_time(timestamp_match.group(1)) + offset_seconds
                    end_time = parse_srt_time(timestamp_match.group(2)) + offset_seconds
                    
                    new_lines.append(str(current_index))
                    new_lines.append(f"{format_srt_time(start_time)} --> {format_srt_time(end_time)}")
                    current_index += 1
                    
                    # Get subtitle text (may be multiple lines until empty line or next index)
                    i += 2
                    while i < len(lines) and lines[i].strip() and not lines[i].strip().isdigit():
                        new_lines.append(lines[i])
                        i += 1
                    new_lines.append("")
                    continue
        
        i += 1
    
    return '\n'.join(new_lines), current_index


def get_mp3_duration_from_bytes(audio_bytes: bytes) -> float:
    """Get duration of MP3 audio from bytes"""
    try:
        # Use mutagen to get duration
        audio_io = io.BytesIO(audio_bytes)
        audio = MP3(audio_io)
        return audio.info.length
    except:
        # Fallback: estimate based on bitrate (48kbps mono = 6000 bytes per second)
        return len(audio_bytes) / 6000



def merge_srt_to_sentences(srt_content: str) -> str:
    """Merge word-level SRT into sentence groups (max 350 chars per subtitle)"""
    if not srt_content.strip():
        return ""
    
    lines = srt_content.strip().split('\n')
    entries = []
    i = 0
    
    # Parse all SRT entries
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
        
        if line.isdigit():
            if i + 2 < len(lines):
                timestamp_line = lines[i + 1].strip()
                timestamp_match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', timestamp_line)
                
                if timestamp_match:
                    start_time = timestamp_match.group(1)
                    end_time = timestamp_match.group(2)
                    
                    # Get text (may be multiple lines)
                    text_lines = []
                    i += 2
                    while i < len(lines) and lines[i].strip() and not lines[i].strip().isdigit():
                        text_lines.append(lines[i].strip())
                        i += 1
                    
                    text = ' '.join(text_lines)
                    entries.append({
                        'start': start_time,
                        'end': end_time,
                        'text': text
                    })
                    continue
        i += 1
    
    if not entries:
        return srt_content
    
    # Merge entries into sentences (max 350 chars)
    merged = []
    current_group = {
        'start': entries[0]['start'],
        'end': entries[0]['end'],
        'text': entries[0]['text']
    }
    
    for entry in entries[1:]:
        potential_text = current_group['text'] + ' ' + entry['text']
        
        # Check if adding this word would exceed limit or if current ends with sentence punctuation
        ends_sentence = current_group['text'].rstrip().endswith(('.', '!', '?', '...'))
        
        if len(potential_text) > MAX_SUBTITLE_CHARS or ends_sentence:
            # Save current group and start new one
            merged.append(current_group)
            current_group = {
                'start': entry['start'],
                'end': entry['end'],
                'text': entry['text']
            }
        else:
            # Add to current group
            current_group['text'] = potential_text
            current_group['end'] = entry['end']
    
    # Don't forget the last group
    merged.append(current_group)
    
    # Generate new SRT
    srt_lines = []
    for idx, entry in enumerate(merged, 1):
        srt_lines.append(str(idx))
        srt_lines.append(f"{entry['start']} --> {entry['end']}")
        srt_lines.append(entry['text'])
        srt_lines.append("")
    
    return '\n'.join(srt_lines)


async def generate_audio_chunk(text: str, voice_id: str, rate: str, pitch: str):
    """Generate audio for a single chunk, returns audio bytes and subtitle data"""
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice_id,
        rate=rate,
        pitch=pitch,
        boundary="WordBoundary"
    )
    
    submaker = edge_tts.SubMaker()
    audio_data = bytearray()
    
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            submaker.feed(chunk)
    
    return bytes(audio_data), submaker.get_srt()


async def generate_audio_async(text: str, filename: str, voice_id: str, rate: str = "-5%", pitch: str = "-5Hz", job_id: str = None):
    """Generate audio with subtitles, with auto-chunking for long texts"""
    global generation_progress
    
    output_audio = OUTPUT_DIR / f"{filename}.mp3"
    output_srt = OUTPUT_DIR / f"{filename}.srt"
    
    # Split text if too long
    chunks = split_text_into_chunks(text)
    total_chunks = len(chunks)
    
    # Initialize progress tracking
    if job_id:
        generation_progress[job_id] = {
            'status': 'generating',
            'current_chunk': 0,
            'total_chunks': total_chunks,
            'percent': 0,
            'eta_seconds': None,
            'start_time': time.time(),
            'chunk_times': []
        }
    
    if len(chunks) == 1:
        # Single chunk - simple case
        if job_id:
            generation_progress[job_id]['current_chunk'] = 1
            generation_progress[job_id]['percent'] = 50  # Halfway through
            
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice_id,
            rate=rate,
            pitch=pitch,
            boundary="WordBoundary"
        )
        
        submaker = edge_tts.SubMaker()
        
        with open(output_audio, "wb") as audio_file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_file.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    submaker.feed(chunk)
        
        srt_content = submaker.get_srt()
        
        if job_id:
            generation_progress[job_id]['percent'] = 100
            generation_progress[job_id]['status'] = 'complete'
    else:
        # Multiple chunks - generate and combine with proper timestamp offsets
        all_audio = bytearray()
        all_srt_parts = []
        time_offset = 0.0
        subtitle_index = 1
        
        for i, chunk_text in enumerate(chunks):
            chunk_start = time.time()
            
            # Update progress before processing
            if job_id:
                generation_progress[job_id]['current_chunk'] = i + 1
                generation_progress[job_id]['percent'] = int((i / total_chunks) * 100)
                
                # Calculate ETA based on average chunk time
                if generation_progress[job_id]['chunk_times']:
                    avg_time = sum(generation_progress[job_id]['chunk_times']) / len(generation_progress[job_id]['chunk_times'])
                    remaining_chunks = total_chunks - i
                    generation_progress[job_id]['eta_seconds'] = int(avg_time * remaining_chunks)
            
            audio_data, srt_data = await generate_audio_chunk(chunk_text, voice_id, rate, pitch)
            all_audio.extend(audio_data)
            
            # Track chunk processing time
            chunk_time = time.time() - chunk_start
            if job_id:
                generation_progress[job_id]['chunk_times'].append(chunk_time)
            
            # Offset SRT timestamps and renumber
            if srt_data:
                offset_srt, subtitle_index = offset_srt_timestamps(srt_data, time_offset, subtitle_index)
                if offset_srt:
                    all_srt_parts.append(offset_srt)
            
            # Calculate duration of this chunk for next offset
            chunk_duration = get_mp3_duration_from_bytes(audio_data)
            time_offset += chunk_duration
        
        # Write combined audio
        with open(output_audio, "wb") as f:
            f.write(bytes(all_audio))
        
        srt_content = '\n'.join(all_srt_parts)
        
        if job_id:
            generation_progress[job_id]['percent'] = 100
            generation_progress[job_id]['status'] = 'complete'
    
    # Merge word-level SRT into sentences (max 350 chars per subtitle)
    srt_content = merge_srt_to_sentences(srt_content)
    
    # Save SRT
    with open(output_srt, "w", encoding="utf-8") as srt_file:
        srt_file.write(srt_content)
    
    return str(output_audio), str(output_srt)


@app.route('/')
def index():
    voices = get_voices_sync()
    return render_template('index.html', voices=voices, char_limit=CHAR_LIMIT)


@app.route('/api/voices')
def api_voices():
    """API endpoint to get all voices"""
    voices = get_voices_sync()
    return jsonify(voices)


@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        text = data.get('text', '').strip()
        voice_id = data.get('voice', 'en-US-GuyNeural')  # Now using voice ID directly
        filename = data.get('filename', 'story').strip()
        rate = data.get('rate', '-5%')
        pitch = data.get('pitch', '-5Hz')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        if len(text) > CHAR_LIMIT:
            return jsonify({'error': f'Text exceeds {CHAR_LIMIT} character limit'}), 400
        
        # Sanitize filename
        filename = "".join(c for c in filename if c.isalnum() or c in ('-', '_')).strip()
        if not filename:
            filename = 'story'
        
        # Create job ID for progress tracking
        import uuid
        job_id = str(uuid.uuid4())[:8]
        
        # Calculate chunks for initial info
        chunks = split_text_into_chunks(text)
        
        # Generate audio with progress tracking
        audio_path, srt_path = asyncio.run(generate_audio_async(
            text=text,
            filename=filename,
            voice_id=voice_id,
            rate=rate,
            pitch=pitch,
            job_id=job_id
        ))
        
        # Clean up progress tracking
        if job_id in generation_progress:
            del generation_progress[job_id]
        
        # Get file size
        file_size = os.path.getsize(audio_path)
        
        return jsonify({
            'success': True,
            'audio_file': f'/audio/{filename}.mp3',
            'srt_file': f'/audio/{filename}.srt',
            'file_size': file_size,
            'char_count': len(text),
            'word_count': len(text.split()),
            'chunks': len(chunks)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/generate_with_progress', methods=['POST'])
def generate_with_progress():
    """Start generation and return job_id for progress tracking"""
    try:
        data = request.json
        text = data.get('text', '').strip()
        voice_id = data.get('voice', 'en-US-GuyNeural')
        filename = data.get('filename', 'story').strip()
        rate = data.get('rate', '-5%')
        pitch = data.get('pitch', '-5Hz')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        if len(text) > CHAR_LIMIT:
            return jsonify({'error': f'Text exceeds {CHAR_LIMIT} character limit'}), 400
        
        # Sanitize filename
        filename = "".join(c for c in filename if c.isalnum() or c in ('-', '_')).strip()
        if not filename:
            filename = 'story'
        
        # Create job ID
        import uuid
        job_id = str(uuid.uuid4())[:8]
        
        # Calculate chunks for initial progress info
        chunks = split_text_into_chunks(text)
        
        # Initialize progress
        generation_progress[job_id] = {
            'status': 'starting',
            'current_chunk': 0,
            'total_chunks': len(chunks),
            'percent': 0,
            'eta_seconds': None,
            'filename': filename
        }
        
        # Start generation in background
        import threading
        def run_generation():
            try:
                asyncio.run(generate_audio_async(
                    text=text,
                    filename=filename,
                    voice_id=voice_id,
                    rate=rate,
                    pitch=pitch,
                    job_id=job_id
                ))
                # Mark as complete with file info
                generation_progress[job_id]['status'] = 'complete'
                generation_progress[job_id]['audio_file'] = f'/audio/{filename}.mp3'
                generation_progress[job_id]['srt_file'] = f'/audio/{filename}.srt'
                generation_progress[job_id]['file_size'] = os.path.getsize(OUTPUT_DIR / f"{filename}.mp3")
                generation_progress[job_id]['char_count'] = len(text)
                generation_progress[job_id]['word_count'] = len(text.split())
            except Exception as e:
                generation_progress[job_id]['status'] = 'error'
                generation_progress[job_id]['error'] = str(e)
        
        thread = threading.Thread(target=run_generation)
        thread.start()
        
        return jsonify({
            'job_id': job_id,
            'total_chunks': len(chunks)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/progress/<job_id>')
def get_progress(job_id):
    """Get progress of a generation job"""
    if job_id in generation_progress:
        return jsonify(generation_progress[job_id])
    return jsonify({'error': 'Job not found'}), 404


@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_from_directory(OUTPUT_DIR, filename)


@app.route('/stories')
def list_stories():
    """List all saved stories"""
    stories = []
    for story_file in STORIES_DIR.glob("*.txt"):
        with open(story_file, "r", encoding="utf-8") as f:
            content = f.read()
        stories.append({
            'filename': story_file.stem,
            'chars': len(content),
            'words': len(content.split()),
            'preview': content[:100] + '...' if len(content) > 100 else content
        })
    return jsonify(stories)


@app.route('/save_story', methods=['POST'])
def save_story():
    """Save a story to the stories folder"""
    try:
        data = request.json
        text = data.get('text', '').strip()
        filename = data.get('filename', 'story').strip()
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Sanitize filename
        filename = "".join(c for c in filename if c.isalnum() or c in ('-', '_', ' ')).strip()
        if not filename:
            filename = 'story'
        
        story_path = STORIES_DIR / f"{filename}.txt"
        with open(story_path, "w", encoding="utf-8") as f:
            f.write(text)
        
        return jsonify({'success': True, 'path': str(story_path)})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("\n=== Revenge Stories Voice Generator ===")
    print("Loading voices...")
    voices = get_voices_sync()
    total_voices = sum(len(v) for v in voices.values())
    print(f"Loaded {total_voices} voices across {len(voices)} languages")
    print("Starting web server...")
    print("Open: http://localhost:5000")
    print("=" * 40 + "\n")
    app.run(debug=True, port=5000)
