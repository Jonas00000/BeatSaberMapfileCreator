import json
import os
import threading
import customtkinter as ctk
from tkinter import filedialog
from mutagen import File as MutagenFile
from src.paths import TEMPLATES_DIR, CONFIG_PATH
from src.yt_music import get_ytmusic_link
from src.create_mapfile import create_mapfile


DEFAULT_CONFIG = {
    "wip_path": "",
    "mapper_name": "",
    "environment": "DefaultEnvironment",
    "map_version": "V3"
}

with open(os.path.join(TEMPLATES_DIR, "environments.json"), 'r', encoding='utf-8') as f:
    ENVIRONMENTS = json.load(f)

if not os.path.isfile(CONFIG_PATH):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(DEFAULT_CONFIG, f, indent=4)

with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    CONFIG = json.load(f)


def run_ui():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("BeatSaber Mapfile Creator")
    root.withdraw()
    root.geometry("450x680")
    root.after_idle(lambda: (root.deiconify(), root.tk.call('tk::PlaceWindow', '.', 'center')))

    # rows: 0 search, 1 link, 2 name, 3 sub name, 4 artist, 5 wip, 6 mapper, 7 env, 8 buttons
    for r in range(9):
        root.grid_rowconfigure(r, weight=1)
    root.grid_columnconfigure((0, 1), weight=1)

    ctk.CTkLabel(root, text="Search YouTube Music").grid(row=0, column=0, columnspan=2, pady=(10, 0), sticky="n")
    yt_search = ctk.CTkEntry(root, width=330)
    yt_search.grid(row=0, column=0, pady=(30, 0), padx=(20, 5), sticky="e")

    def show_search_results(results):
        popup = ctk.CTkToplevel(root)
        popup.title("Select a result")
        popup.withdraw()
        popup.geometry("420x240")
        popup.after_idle(lambda w=popup: (w.deiconify(), w.tk.call('tk::PlaceWindow', str(w), 'center')))
        popup.transient(root)
        popup.grab_set()
        popup.focus()

        ctk.CTkLabel(popup, text="Pick a result to autofill", wraplength=380).pack(pady=(15, 5))

        def apply_result(item):
            link_value, artist_value, title_value = item
            song_name.delete(0, "end")
            song_name.insert(0, title_value)
            sub_name.delete(0, "end")
            artist.delete(0, "end")
            artist.insert(0, artist_value)
            link.delete(0, "end")
            link.insert(0, link_value)
            validate_inputs()
            popup.destroy()

        for item in results:
            link_value, artist_value, title_value = item
            label = f"{title_value} — {artist_value}"
            ctk.CTkButton(popup, text=label, command=lambda i=item: apply_result(i)).pack(pady=6, padx=20, fill="x")

        ctk.CTkButton(popup, text="Cancel", command=popup.destroy).pack(pady=(10, 15))

    def search_ytmusic():
        query = yt_search.get().strip()
        if not query:
            return
        results = get_ytmusic_link(query) or []
        if not results:
            popup = ctk.CTkToplevel(root)
            popup.title("No results")
            popup.withdraw()
            popup.geometry("320x160")
            popup.after_idle(lambda w=popup: (w.deiconify(), w.tk.call('tk::PlaceWindow', str(w), 'center')))
            popup.transient(root)
            popup.grab_set()
            popup.focus()
            ctk.CTkLabel(popup, text="No results found.", wraplength=280).pack(pady=25)
            ctk.CTkButton(popup, text="OK", command=popup.destroy).pack(pady=10)
            return
        show_search_results(results[:3])

    yt_search_btn = ctk.CTkButton(root, text="Search", width=60, command=search_ytmusic)
    yt_search_btn.grid(row=0, column=1, pady=(30, 0), padx=(5, 20), sticky="w")

    yt_search.bind("<Return>", lambda e: search_ytmusic())
    yt_search.bind("<KP_Enter>", lambda e: search_ytmusic())

    # --- Link or Local File (row 1) ---
    last_checked_path = [None]

    def _try_extract_metadata(path):
        if not os.path.isfile(path):
            return None, None
        try:
            audio = MutagenFile(path, easy=True)
            if audio is None:
                return None, None
            title = None
            artist_name = None
            if 'title' in audio:
                title = ' '.join(audio['title'])
            if 'artist' in audio:
                artist_name = ', '.join(audio['artist'])
            return title, artist_name
        except Exception:
            return None, None

    def _on_link_changed(*_args):
        path = link.get().strip().replace('"', '')
        if not path or path == last_checked_path[0]:
            return
        if os.path.isfile(path):
            last_checked_path[0] = path
            title, artist_name = _try_extract_metadata(path)
            if title:
                song_name.delete(0, "end")
                song_name.insert(0, title)
            if artist_name:
                artist.delete(0, "end")
                artist.insert(0, artist_name)
        validate_inputs()

    ctk.CTkLabel(root, text="Link or Local File").grid(row=1, column=0, columnspan=2, pady=(10, 0), sticky="n")
    link = ctk.CTkEntry(root, width=330)
    link.grid(row=1, column=0, pady=(30, 0), padx=(20, 5), sticky="e")

    def browse_file():
        file_path = filedialog.askopenfilename(
            title="Select an audio file",
            filetypes=[("Audio files", "*.mp3 *.ogg *.wav *.flac"), ("All files", "*.*")]
        )
        if file_path:
            link.delete(0, "end")
            link.insert(0, file_path)
            _on_link_changed()

    browse_btn = ctk.CTkButton(root, text="Browse", width=60, command=browse_file)
    browse_btn.grid(row=1, column=1, pady=(30, 0), padx=(5, 20), sticky="w")

    link.bind("<KeyRelease>", lambda e: _on_link_changed())
    link.bind("<FocusOut>", lambda e: _on_link_changed())

    # --- Song Name (row 2) ---
    ctk.CTkLabel(root, text="Song Name").grid(row=2, column=0, columnspan=2, pady=(10, 0), sticky="n")
    song_name = ctk.CTkEntry(root, width=400)
    song_name.grid(row=2, column=0, columnspan=2, pady=(30, 0))

    ctk.CTkLabel(root, text="Sub Name").grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky="n")
    sub_name = ctk.CTkEntry(root, width=400)
    sub_name.grid(row=3, column=0, columnspan=2, pady=(30, 0))

    ctk.CTkLabel(root, text="Artist").grid(row=4, column=0, columnspan=2, pady=(10, 0), sticky="n")
    artist = ctk.CTkEntry(root, width=400)
    artist.grid(row=4, column=0, columnspan=2, pady=(30, 0))

    ctk.CTkLabel(root, text="Wip Path").grid(row=5, column=0, columnspan=2, pady=(10, 0), sticky="n")
    wip_path = ctk.CTkEntry(root, width=330)
    wip_path.grid(row=5, column=0, pady=(30, 0), padx=(20, 5), sticky="e")

    def browse_wip():
        directory = filedialog.askdirectory(title="Select WIP directory")
        if directory:
            wip_path.delete(0, "end")
            wip_path.insert(0, directory)
            save_config_fields()
            validate_inputs()

    wip_browse_btn = ctk.CTkButton(root, text="Browse", width=60, command=browse_wip)
    wip_browse_btn.grid(row=5, column=1, pady=(30, 0), padx=(5, 20), sticky="w")

    ctk.CTkLabel(root, text="Mapper Name").grid(row=6, column=0, columnspan=2, pady=(10, 0), sticky="n")
    mapper = ctk.CTkEntry(root, width=400)
    mapper.grid(row=6, column=0, columnspan=2, pady=(30, 0))

    ctk.CTkLabel(root, text="Environment").grid(row=7, column=0, columnspan=2, pady=(10, 0), sticky="n")
    env_dropdown = ctk.CTkComboBox(root, values=ENVIRONMENTS, state="readonly", width=330)
    env_dropdown.grid(row=7, column=0, pady=(30, 0), padx=(20, 5), sticky="e")

    version_dropdown = ctk.CTkComboBox(root, values=["V3", "V4"], state="readonly", width=60)
    version_dropdown.grid(row=7, column=1, pady=(30, 0), padx=(5, 20), sticky="w")

    # Prefill from CONFIG
    try:
        if CONFIG.get("wip_path"):
            wip_path.insert(0, CONFIG.get("wip_path", ""))
        if CONFIG.get("mapper_name"):
            mapper.insert(0, CONFIG.get("mapper_name", ""))
        env_value = CONFIG.get("environment", ENVIRONMENTS[0])
        if env_value not in ENVIRONMENTS:
            env_value = ENVIRONMENTS[0]
        env_dropdown.set(env_value)
        version_value = CONFIG.get("map_version", "V3")
        if version_value not in ["V3", "V4"]:
            version_value = "V3"
        version_dropdown.set(version_value)
    except Exception:
        pass

    # Save config helper
    def save_config_fields():
        CONFIG["wip_path"] = wip_path.get().strip()
        CONFIG["mapper_name"] = mapper.get().strip()
        CONFIG["environment"] = env_dropdown.get().strip()
        CONFIG["map_version"] = version_dropdown.get().strip()
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(CONFIG, f, indent=4)

    # --- rows: 0-7 inputs, 8 buttons, 9 progress ---
    root.grid_rowconfigure(9, weight=0)

    # Buttons frame at row 8
    buttons_frame = ctk.CTkFrame(root, fg_color="transparent", border_width=0, corner_radius=0)
    buttons_frame.grid(row=8, column=0, columnspan=2, sticky="ew", padx=20, pady=(25, 5))

    for i in range(6):
        buttons_frame.grid_columnconfigure(i, weight=1)

    btn_width = 150
    btn_height = 36

    def on_close():
        save_config_fields()
        root.destroy()

    quit_button = ctk.CTkButton(
        buttons_frame, text="Quit", command=on_close,
        width=btn_width, height=btn_height, fg_color="#D32F2F", hover_color="#B71C1C"
    )
    quit_button.grid(row=0, column=1, columnspan=2, padx=10)

    # --- Progress bar + status label (row 9) ---
    progress_frame = ctk.CTkFrame(root, fg_color="transparent", border_width=0, corner_radius=0)
    progress_frame.grid(row=9, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 15))
    progress_frame.grid_columnconfigure(0, weight=1)

    progress_label = ctk.CTkLabel(progress_frame, text="", anchor="w")
    progress_label.grid(row=0, column=0, sticky="w", pady=(0, 2))

    progress_bar = ctk.CTkProgressBar(progress_frame, width=400)
    progress_bar.grid(row=1, column=0, sticky="ew")
    progress_bar.set(0)

    # Hide progress widgets initially
    progress_frame.grid_remove()

    # Validate WIP path and control Create Map button
    def validate_inputs(event=None):
        valid_wip = os.path.isdir(wip_path.get().strip())
        has_link = bool(link.get().strip())
        state = "normal" if (valid_wip and has_link) else "disabled"
        create_button.configure(state=state)

    # Create Map
    def _set_ui_busy(busy):
        """Disable/enable interactive widgets while the pipeline runs."""
        state = "disabled" if busy else "normal"
        for w in (yt_search, yt_search_btn, link, browse_btn, song_name, sub_name,
                  artist, wip_path, wip_browse_btn, mapper, env_dropdown,
                  version_dropdown, quit_button, create_button):
            try:
                w.configure(state=state)
            except Exception:
                pass

    def _update_progress(step, total, message):
        """Called from the worker thread — schedules UI updates on the main thread."""
        root.after(0, lambda: _apply_progress(step, total, message))

    def _apply_progress(step, total, message):
        progress_bar.set(step / total)
        progress_label.configure(text=message)

    def _on_pipeline_done(msg):
        """Called on the main thread when the pipeline finishes."""
        _set_ui_busy(False)
        if msg is None:
            # Success
            progress_label.configure(text="Done!")
            progress_bar.set(1)
            root.after(2000, lambda: progress_frame.grid_remove())
            song_name.delete(0, "end")
            sub_name.delete(0, "end")
            artist.delete(0, "end")
            link.delete(0, "end")
            return

        # Error
        progress_frame.grid_remove()
        popup = ctk.CTkToplevel(root)
        popup.title("Error")
        popup.withdraw()
        popup.geometry("350x180")
        popup.after_idle(lambda w=popup: (w.deiconify(), w.tk.call('tk::PlaceWindow', str(w), 'center')))
        popup.transient(root)
        popup.grab_set()
        popup.focus()

        def close_and_clear():
            song_name.delete(0, "end")
            sub_name.delete(0, "end")
            artist.delete(0, "end")
            link.delete(0, "end")
            popup.destroy()

        ctk.CTkLabel(popup, text=msg, wraplength=300).pack(pady=20)
        ctk.CTkButton(popup, text="OK", command=close_and_clear).pack(pady=10)

    def create_map():
        validate_inputs()
        if not os.path.isdir(wip_path.get().strip()):
            _on_pipeline_done("Wip Path is empty or does not exist.")
            return
        if not link.get().strip():
            _on_pipeline_done("Link or local file is empty.")
            return

        save_config_fields()
        config = {
            "song": song_name.get().strip(),
            "sub_name": sub_name.get().strip(),
            "artist": artist.get().strip(),
            "link": link.get().replace('"', '').strip(),
            "wip_location": wip_path.get().strip(),
            "mapper": mapper.get().strip(),
            "environment": env_dropdown.get().strip(),
            "version": version_dropdown.get().strip()
        }

        # Show progress bar and disable UI
        progress_bar.set(0)
        progress_label.configure(text="Starting…")
        progress_frame.grid()
        _set_ui_busy(True)

        def worker():
            result = create_mapfile(config, progress=_update_progress)
            root.after(0, lambda: _on_pipeline_done(result))

        threading.Thread(target=worker, daemon=True).start()

    create_button = ctk.CTkButton(
        buttons_frame, text="Create Map", command=create_map,
        width=btn_width, height=btn_height
    )
    create_button.grid(row=0, column=3, columnspan=2, padx=10)

    # Bind changes to validate and save
    wip_path.bind("<KeyRelease>", validate_inputs)
    link.bind("<KeyRelease>", validate_inputs)
    mapper.bind("<FocusOut>", lambda e: save_config_fields())
    env_dropdown.bind("<<ComboboxSelected>>", lambda e: save_config_fields())
    version_dropdown.bind("<<ComboboxSelected>>", lambda e: save_config_fields())

    validate_inputs()
    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
