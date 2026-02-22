# BeatSaber Mapfile Creator

A desktop tool that generates BeatSaber WIP map folders from a song link or local audio file. Handles audio conversion, BPM detection, beat synchronization, cover art retrieval, and `Info.dat` generation.

## Download

Grab the latest release from [GitHub Releases](https://github.com/Jonas00000/BeatSaberMapfileCreator/releases).
Unzip the folder and run `BeatSaberMapfileCreator.exe` — no Python or extra installs needed.

## Features

- **YouTube Music search** with auto-fill for song name, artist, and link (even though YT Music is integrated, please prefer higher quality sources)
- **Local file support** (mp3, ogg, wav, flac) with automatic metadata extraction
- **Audio download and conversion** to OGG Vorbis via yt-dlp and ffmpeg
- **BPM and offset detection** with automatic beat synchronization (1.5s hot start and 2s cold end padding)
- **Cover art fetching** from Spotify, iTunes, and MusicBrainz with selection popup or from local file if available
- **Info.dat generation** for both V3 and V4 map formats
- **Persistent settings** for WIP path, mapper name, environment, and map version

## Building from Source

### Requirements

- Python 3.14+

### External Binaries

The following binaries must be placed in `bin/` before running. They are **not** included in the source repository (see [Licensing](#licensing)).

| Binary       | Source                                                                               |
|--------------|--------------------------------------------------------------------------------------|
| `ffmpeg.exe` | [ffmpeg.org](https://ffmpeg.org/download.html)                                       |
| `yt-dlp.exe` | [yt-dlp releases](https://github.com/yt-dlp/yt-dlp/releases)                         |
| `BpmCli.exe` | [ArrowVortex-BPMCli fork](https://github.com/Jonas00000/ArrowVortex-BPMCli/releases) |

### Install & Run

```
pip install -e .
python main.py
```

Or with [uv](https://github.com/astral-sh/uv):

```
uv sync
uv run main.py
```

### Building a Release (PyInstaller)

This creates a standalone `onedir` distribution you can zip and upload to GitHub Releases.

```
python build.py
```

The output is in `dist/BeatSaberMapfileCreator/`.

> **Note:** The `bin/` binaries must be present before building — PyInstaller bundles them into the output.

## Configuration

### config.json

Created automatically on first run. Stores persistent UI settings (WIP path, mapper name, environment, map version).

### .env (optional)

Required only for Spotify cover art. If absent, Spotify is skipped and iTunes/MusicBrainz are still used.

```
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
SPOTIFY_REFRESH_TOKEN=...
```

## Project Structure

```
main.py                  Entry point
build.py                 PyInstaller build script
BeatSaberMapfileCreator.spec  PyInstaller spec file
config.json              Persisted user settings (auto-created)
LICENSE                  GPL-2.0-or-later (this project)
THIRD_PARTY_LICENSES     Licenses for bundled binaries
bin/
    ffmpeg.exe           Audio conversion and synchronization
    yt-dlp.exe           YouTube audio download
    BpmCli.exe           BPM and offset detection
src/
    ui.py                GUI (CustomTkinter)
    create_mapfile.py    Pipeline: download, BPM, sync, cover, Info.dat
    load_cover.py        Cover art fetching, selection, and processing
    yt_music.py          YouTube Music search
    paths.py             Path resolution
templates/
    environments.json    Beat Saber environment list
    V3Info.template      Info.dat template (V3 / version 2.1.0)
    V4Info.template      Info.dat template (V4 / version 4.0.1)
```

## Licensing

This project is licensed under the **GNU General Public License v2.0 or later** (GPL-2.0-or-later) — see [LICENSE](LICENSE).

GPL is required because this project links the [mutagen](https://github.com/quodlibet/mutagen) library, which is GPL-2.0-or-later.

The release builds also bundle the following third-party binaries:

| Binary       | License          | Source                                                                                            |
|--------------|------------------|---------------------------------------------------------------------------------------------------|
| `BpmCli.exe` | GPL-2.0-or-later | [Jonas00000/ArrowVortex-BPMCli](https://github.com/Jonas00000/ArrowVortex-BPMCli) (modified fork) |
| `ffmpeg.exe` | GPL-2.0-or-later | [ffmpeg.org](https://ffmpeg.org/)                                                                 |
| `yt-dlp.exe` | Unlicense        | [yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp)                                                 |

These binaries are distributed only in release builds, not in the source repository.
Full details are in [THIRD_PARTY_LICENSES](THIRD_PARTY_LICENSES).