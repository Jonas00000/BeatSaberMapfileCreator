import os
import dotenv
import requests
import base64
import urllib.parse
import tempfile
import shutil
from difflib import SequenceMatcher
from urllib.request import urlretrieve
from mutagen import File as MutagenFile
from mutagen.flac import FLAC
from mutagen.id3 import ID3
from mutagen.mp4 import MP4
from PIL import Image
import customtkinter as ctk

dotenv.load_dotenv()


def get_spotify_access_token():
    auth_str = f'{os.getenv("SPOTIFY_CLIENT_ID")}:{os.getenv("SPOTIFY_CLIENT_SECRET")}'
    auth_b64 = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')

    url = 'https://accounts.spotify.com/api/token'
    headers = {
        'Authorization': f'Basic {auth_b64}'
    }
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': os.getenv("SPOTIFY_REFRESH_TOKEN")
    }
    res = requests.post(url, headers=headers, data=data)
    return res.json()['access_token']


def _crop_center_square(image_path):
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            if width == height:
                return True
            side = min(width, height)
            left = (width - side) // 2
            top = (height - side) // 2
            right = left + side
            bottom = top + side
            cropped = img.crop((left, top, right, bottom))
            cropped.save(image_path, format=img.format)
        return True
    except Exception:
        return False


def _resize_down_if_needed(image_path, max_size = 1000):
    try:
        with Image.open(image_path) as img:
            if img.width <= max_size and img.height <= max_size:
                return True
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            img.save(image_path, format=img.format)
        return True
    except Exception:
        return False


def _match_score(actual_song, actual_artist, found_song, found_artist):
    song_ratio = SequenceMatcher(None, actual_song.lower(), found_song.lower()).ratio()
    artist_ratio = SequenceMatcher(None, actual_artist.lower(), found_artist.lower()).ratio()
    return (song_ratio + artist_ratio) / 2


def _get_spotify_candidate(song, artist):
    if not (os.getenv("SPOTIFY_CLIENT_ID") and os.getenv("SPOTIFY_CLIENT_SECRET") and os.getenv("SPOTIFY_REFRESH_TOKEN")):
        return None
    try:
        access_token = get_spotify_access_token()
        headers = {'Authorization': f'Bearer {access_token}'}
        query = urllib.parse.quote(f'{song} {artist}')
        res = requests.get(f'https://api.spotify.com/v1/search?q={query}&type=track&limit=1', headers=headers).json()
        track = res['tracks']['items'][0]
        return {
            'source': 'Spotify',
            'url': track['album']['images'][0]['url'],
            'found_song': track['name'],
            'found_artist': track['artists'][0]['name'],
        }
    except Exception:
        return None


def _get_itunes_candidate(song, artist):
    try:
        query = urllib.parse.quote(f'{artist} {song}')
        res = requests.get(f'https://itunes.apple.com/search?term={query}&entity=song&limit=1').json()
        result = res['results'][0]
        return {
            'source': 'iTunes',
            'url': result['artworkUrl100'].replace('100x100', '1000x1000'),
            'found_song': result['trackName'],
            'found_artist': result['artistName'],
        }
    except Exception:
        return None


def _get_musicbrainz_candidate(song, artist):
    try:
        query = f'recording:"{song}" AND artist:"{artist}"'
        url = 'https://musicbrainz.org/ws/2/recording/'
        headers = {'User-Agent': 'AlbumCoverFetcher/1.0'}
        params = {'query': query, 'fmt': 'json', 'limit': 1}

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            return None
        data = response.json()

        if not data['recordings']:
            return None
        recording = data['recordings'][0]
        found_song = recording.get('title', '')
        found_artist = ''
        if 'artist-credit' in recording and recording['artist-credit']:
            found_artist = recording['artist-credit'][0].get('name', '')

        if 'releases' not in recording or not recording['releases']:
            return None

        release_id = recording['releases'][0]['id']
        cover_resp = requests.get(f'https://coverartarchive.org/release/{release_id}')
        if cover_resp.status_code != 200:
            return None

        for image in cover_resp.json().get('images', []):
            if image.get('front', False):
                return {
                    'source': 'MusicBrainz',
                    'url': image.get('image'),
                    'found_song': found_song,
                    'found_artist': found_artist,
                }
        return None
    except Exception:
        return None


def _fetch_cover_candidates(song, artist):
    candidates = []
    fetchers = [
        ('Spotify', _get_spotify_candidate),
        ('iTunes', _get_itunes_candidate),
        ('MusicBrainz', _get_musicbrainz_candidate),
    ]
    for name, fetcher in fetchers:
        print(f'Fetching cover from {name}...')
        candidate = fetcher(song, artist)
        if candidate:
            candidate['score'] = _match_score(song, artist, candidate['found_song'], candidate['found_artist'])
            candidates.append(candidate)
            print(f"  Found: {candidate['found_artist']} - {candidate['found_song']} (match: {candidate['score']:.0%})")
        else:
            print('  No result.')
    candidates.sort(key=lambda c: c['score'], reverse=True)
    return candidates[:3]


def _download_temp_covers(candidates, temp_dir):
    results = []
    for i, candidate in enumerate(candidates):
        path = os.path.join(temp_dir, f'cover_{i}.tmp')
        try:
            urlretrieve(candidate['url'], path)
            if _crop_center_square(path) and _resize_down_if_needed(path, 1000):
                results.append((path, candidate))
            else:
                if os.path.exists(path):
                    os.remove(path)
        except Exception:
            if os.path.exists(path):
                os.remove(path)
    return results


def _show_cover_selection_popup(covers):
    selection = [None]

    popup = ctk.CTkToplevel()
    popup.title("Select Cover Art")
    popup.withdraw()

    n = len(covers)
    width = max(350, n * 210 + 40)
    popup.geometry(f"{width}x380")
    popup.after_idle(lambda w=popup: (w.deiconify(), w.tk.call('tk::PlaceWindow', str(w), 'center')))
    popup.grab_set()
    popup.focus()

    ctk.CTkLabel(popup, text="Map creation successful!", font=("", 16, "bold"), text_color="#4CAF50").pack(pady=(10, 0))
    ctk.CTkLabel(popup, text="Select a cover image", font=("", 14)).pack(pady=(2, 10))

    frame = ctk.CTkFrame(popup, fg_color="transparent")
    frame.pack(expand=True, fill="both", padx=20)

    tk_images = []  # prevent garbage collection
    for col, (path, candidate) in enumerate(covers):
        col_frame = ctk.CTkFrame(frame)
        col_frame.grid(row=0, column=col, padx=10, pady=5, sticky="n")
        frame.grid_columnconfigure(col, weight=1)

        try:
            pil_img = Image.open(path)
            img_w, img_h = pil_img.size
            ctk_img = ctk.CTkImage(light_image=pil_img, size=(150, 150))
            tk_images.append(ctk_img)

            def on_select(p=path, c=candidate):
                selection[0] = (p, c)
                popup.destroy()

            btn = ctk.CTkButton(col_frame, image=ctk_img, text="", command=on_select,
                                width=160, height=160, fg_color="transparent", hover_color="#333333")
            btn.pack(padx=5, pady=5)

            info = (f"{candidate['source']}\n"
                    f"{candidate['found_artist']}\n"
                    f"{candidate['found_song']}\n"
                    f"{img_w}x{img_h}")
            ctk.CTkLabel(col_frame, text=info, font=("", 11), wraplength=170, justify="center").pack(pady=(0, 5))
        except Exception:
            continue

    ctk.CTkButton(popup, text="No Cover", command=popup.destroy,
                  fg_color="#D32F2F", hover_color="#B71C1C", width=120).pack(pady=(5, 15))

    popup.wait_window()
    return selection[0]


def _show_success_popup():
    popup = ctk.CTkToplevel()
    popup.title("Success")
    popup.withdraw()
    popup.geometry("300x120")
    popup.after_idle(lambda w=popup: (w.deiconify(), w.tk.call('tk::PlaceWindow', str(w), 'center')))
    popup.grab_set()
    popup.focus()

    ctk.CTkLabel(popup, text="Map creation successful!", font=("", 16, "bold"), text_color="#4CAF50").pack(pady=(20, 10))
    ctk.CTkButton(popup, text="OK", command=popup.destroy, width=100).pack(pady=(0, 15))
    popup.wait_window()


def load_cover(config):
    if 'cover' in config:
        _show_success_popup()
        return True, 'FLAC'

    song = config['song']
    artist = config['artist']
    dir_name = str(config['dir_name'])

    print('Fetching cover candidates...')
    candidates = _fetch_cover_candidates(song, artist)

    if not candidates:
        print('No cover candidates found from any source.')
        _show_success_popup()
        return False, None

    temp_dir = tempfile.mkdtemp(prefix='bs_covers_')
    try:
        covers = _download_temp_covers(candidates, temp_dir)
        if not covers:
            print('All cover downloads failed.')
            _show_success_popup()
            return False, None

        result = _show_cover_selection_popup(covers)
        if result is None:
            print('No cover selected.')
            return False, None

        selected_path, selected_candidate = result
        with Image.open(selected_path) as img:
            ext = '.png' if img.format == 'PNG' else '.jpg'

        cover_filename = f'cover{ext}'
        final_path = os.path.join(dir_name, cover_filename)
        shutil.copy2(selected_path, final_path)
        config['cover'] = cover_filename

        print(f"Cover saved from {selected_candidate['source']}: {cover_filename}")
        return True, selected_candidate['source']
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def extract_embedded_cover(config):
    try:
        filepath = config['link']
        audio = MutagenFile(filepath)
        if audio is None:
            return False

        cover_data = None
        extension = ".jpg"

        # FLAC
        if isinstance(audio, FLAC):
            if not audio.pictures:
                return False
            for pic in audio.pictures:
                if pic.type == 3:  # Front Cover
                    cover_data = pic.data
                    if pic.mime == "image/png":
                        extension = ".png"
                    break
            if not cover_data:
                cover_data = audio.pictures[0].data
                if audio.pictures[0].mime == "image/png":
                    extension = ".png"

        # MP3 / other ID3-tagged formats
        elif hasattr(audio, 'tags') and isinstance(audio.tags, ID3):
            for key, frame in audio.tags.items():
                if key.startswith('APIC'):
                    cover_data = frame.data
                    if frame.mime == "image/png":
                        extension = ".png"
                    if frame.type == 3:  # Front Cover
                        break
            if not cover_data:
                return False

        # MP4 / M4A / AAC
        elif isinstance(audio, MP4):
            covers = audio.tags.get('covr', [])
            if not covers:
                return False
            cover_data = bytes(covers[0])
            from mutagen.mp4 import MP4Cover
            if covers[0].imageformat == MP4Cover.FORMAT_PNG:
                extension = ".png"

        # OGG Vorbis / Opus (may have embedded pictures via metadata_block_picture)
        elif hasattr(audio, 'tags') and audio.tags is not None:
            import base64 as b64
            from mutagen.flac import Picture
            for b64_data in audio.tags.get('metadata_block_picture', []):
                try:
                    pic = Picture(b64.b64decode(b64_data))
                    cover_data = pic.data
                    if pic.mime == "image/png":
                        extension = ".png"
                    if pic.type == 3:
                        break
                except Exception:
                    continue

        if not cover_data:
            return False

        output_path = os.path.join(config['dir_name'], f"cover{extension}")

        with open(output_path, "wb") as img_file:
            img_file.write(cover_data)

        if not _crop_center_square(output_path):
            os.remove(output_path)
            return False
        if not _resize_down_if_needed(output_path, 1000):
            os.remove(output_path)
            return False

        print(f"Cover successfully extracted to: {output_path}")
        config['cover'] = 'cover' + extension
        return True

    except Exception:
        return False
