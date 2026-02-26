import json
import subprocess
import sys
import os
import math
import re
import tempfile
import shutil
import numpy as np
import soundfile as sf
from pathlib import Path
from src.load_cover import load_cover, extract_embedded_cover
from src.paths import BIN_DIR, TEMPLATES_DIR

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0


def _create_dir(config):
    dirname = Path(config['wip_location']) / re.sub(r'[^\w\s]', '', config['song']).replace(' ', '_')
    if os.path.isdir(dirname):
        i = 1
        while True:
            if not os.path.isdir(f'{dirname}_{i}'):
                dirname = f'{dirname}_{i}'
                break
            i += 1
    os.mkdir(dirname)
    print(f'Created directory {dirname}!')
    return dirname


def _load_song(config):
    if os.path.isfile(config['link']):
        command = [
            os.path.join(BIN_DIR, "ffmpeg.exe"),
            '-i', config['link'],
            '-vn',
            '-c:a', "libvorbis",
            '-q:a', '8',
            f'{config['dir_name']}/tmp_song.ogg'
        ]
        try:
            subprocess.run(command, check=True, creationflags=_NO_WINDOW)
            print('Loaded song!')
            
            extract_embedded_cover(config)
            
            return True
        except subprocess.CalledProcessError as e:
            print(e)
            return False
    else:
        update_command = [os.path.join(BIN_DIR, "yt-dlp.exe"), '--update']
        subprocess.run(update_command, check=False, creationflags=_NO_WINDOW)

        command = [
            os.path.join(BIN_DIR, "yt-dlp.exe"), 
            '--extract-audio', 
            '--audio-format', 'vorbis',
            '--audio-quality', '4', 
            '-o', f'{config['dir_name']}/tmp_song', 
            config['link']
        ]
        try:
            print(command)
            subprocess.run(command, check=True, creationflags=_NO_WINDOW)
            print('Downloaded song!')
            return True
        except subprocess.CalledProcessError as e:
            print(e)
            return False


def _get_BPM_and_offset(config):
    def get_song_start_end_and_set_duration(song_path):
        song_data, sr = sf.read(song_path)
        config['song_duration'] = len(song_data) / sr
        abs_vals = np.absolute(song_data.ravel())

        song_start = None
        for i, db in enumerate(abs_vals):
            if db > 0.1:
                song_start = i / sr / 2
                break

        song_end = None
        for i in range(len(abs_vals) - 1, -1, -1):
            if abs_vals[i] > 0.1:
                song_end = i / sr / 2
                break

        return song_start, song_end
    
    path = Path(config['dir_name']) / 'tmp_song.ogg'
    if not os.path.isfile(path):
        print('No song file')
        return False
    try:
        # For non ASCII
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_song_path = os.path.join(tmp_dir, "temp_song.ogg")
            shutil.copy2(path, temp_song_path)
            
            res = subprocess.run(
                [os.path.join(BIN_DIR, "BPMCli.exe"), temp_song_path],
                check=True, capture_output=True, text=True, creationflags=_NO_WINDOW
            )
            
            print(f'result: {res.stdout}')

            try:
                data = json.loads(res.stdout.strip())
                if "error" in data:
                    print(f"BPM detection failed: {data['error']}")
                    return False
            
                bpm = float(data["bpm"])
                offset = float(data["offset"])
            except json.JSONDecodeError:
                print('BPM detection failed, output was not valid JSON')
                return False
            
            bpm = round(bpm, 1)
            bpm = int(bpm) if abs(int(bpm) - bpm) <= 0.1 else bpm

            offset = -offset
            song_start, song_end = get_song_start_end_and_set_duration(temp_song_path)
            config['song_end'] = song_end
        
        beat_length = 60 / bpm
        if song_start and 0 <= song_start < 10:
            missing = 1.5 - offset - song_start
            offset += math.ceil(missing / beat_length) * beat_length
        else:
            offset += math.ceil(1.5 / beat_length) * beat_length
        
        while offset < 0:
            offset += beat_length
        offset = round(offset, 3)
        print('Got bpm and offset!')
        
        config['bpm'] = bpm
        config['offset'] = offset
        return True
    except subprocess.CalledProcessError as e:
        print(e)
        return False


def _sync_song(config):
    offset = int(config['offset'] * 1000)

    # Calculate trailing silence needed: at least 2s after song end
    tail_pad_ms = 0
    song_end = config.get('song_end')
    song_duration = config.get('song_duration')
    if song_end is not None and song_duration is not None:
        silence_after_end = song_duration - song_end
        total_silence = silence_after_end  # silence already present at end of file
        if total_silence < 2.0:
            tail_pad_ms = int((2.0 - total_silence) * 1000)

    af_filters = [f'adelay={offset}|{offset}']
    if tail_pad_ms > 0:
        af_filters.append(f'apad=pad_dur={tail_pad_ms}ms')
        print(f'Adding {tail_pad_ms}ms trailing silence.')

    output_path = Path(config['dir_name']) / 'song.ogg'
    max_size_bytes = 13 * 1024 * 1024
    quality_levels = [8, 7, 6, 4, 2, 0]

    for quality in quality_levels:
        command = [
            os.path.join(BIN_DIR, "ffmpeg.exe"),
            '-y',
            '-i', Path(config['dir_name']) / 'tmp_song.ogg',
            '-af', ','.join(af_filters),
            '-c:a', 'libvorbis',
            '-q:a', str(quality),
            output_path
        ]
        try:
            subprocess.run(command, check=True, creationflags=_NO_WINDOW)
            size_bytes = output_path.stat().st_size if output_path.exists() else 0
            if size_bytes <= max_size_bytes:
                print(f'Synced song at quality {quality}.')
                return True
        except subprocess.CalledProcessError as e:
            print(e)
            return False

    print('Failed to shrink song below 13 MB.')
    return False


def _create_info(config):
    if config['version'] == 'V3':
        with open(Path(TEMPLATES_DIR) / 'V3Info.template', "r", encoding="utf-8") as f:
            info = json.load(f)
        info['_songName'] = config['song']
        info['_songSubName'] = config['sub_name']
        info['_songAuthorName'] = config['artist']
        info['_levelAuthorName'] = config['mapper']
        info['_beatsPerMinute'] = config['bpm']
        info['_environmentName'] = config['environment']
        info['_coverImageFilename'] = config.get('cover', '')
        with open(Path(config['dir_name']) / 'Info.dat', 'w', encoding='utf-8') as f:
            json.dump(info, f, indent=4, ensure_ascii=False)
        print('Created Info.dat!')
    else:
        with open(Path(TEMPLATES_DIR) / 'V4Info.template', "r", encoding="utf-8") as f:
            info = json.load(f)
        info['song']['title'] = config['song']
        info['song']['subTitle'] = config['sub_name']
        info['song']['author'] = config['artist']
        info['audio']['songFilename'] = 'song.ogg'
        info['audio']['songDuration'] = config['song_duration']
        info['audio']['bpm'] = config['bpm']
        info['environmentNames'] = [config['environment']]
        info['coverImageFilename'] = config.get('cover', '')
        with open(Path(config['dir_name']) / 'Info.dat', 'w', encoding='utf-8') as f:
            json.dump(info, f, indent=4, ensure_ascii=False)
        print('Created Info.dat!')


def create_mapfile(config, progress=None):
    STEPS = 6
    def _progress(step, msg):
        if progress:
            progress(step, STEPS, msg)

    _progress(0, "Creating directory…")
    config['dir_name'] = _create_dir(config)

    def clean_up():
        dir_name = config['dir_name']
        if os.path.isdir(dir_name):
            for fl in os.listdir(dir_name):
                os.remove(os.path.join(dir_name, fl))
            os.rmdir(dir_name)
        print('Cleaned up!')

    _progress(1, "Downloading / loading song…")
    if not _load_song(config):
        clean_up()
        return 'Failed to load song.'

    _progress(2, "Detecting BPM and offset…")
    if not _get_BPM_and_offset(config):
        clean_up()
        return 'Failed to detect BPM and offset.'

    _progress(3, "Synchronizing audio…")
    if not _sync_song(config):
        clean_up()
        return 'Failed to sync song.'

    os.remove(Path(config['dir_name']) / 'tmp_song.ogg')

    _progress(4, "Loading cover art…")
    load_cover(config)

    _progress(5, "Writing Info.dat…")
    _create_info(config)

    _progress(6, "Done!")
    return None
