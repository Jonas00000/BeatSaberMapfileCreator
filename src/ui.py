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
    "map_version": "V3",
    "start_offset": 1.5,
    "end_offset": 2.0,
    "song_speed": 1.0,
    "first_launch_done": False,
}

with open(os.path.join(TEMPLATES_DIR, "environments.json"), 'r', encoding='utf-8') as f:
    ENVIRONMENTS = json.load(f)

if not os.path.isfile(CONFIG_PATH):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(DEFAULT_CONFIG, f, indent=4)

with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    CONFIG = json.load(f)

# Backfill new keys into old config files
for _key, _val in DEFAULT_CONFIG.items():
    if _key not in CONFIG:
        CONFIG[_key] = _val


class _Tooltip:
    def __init__(self, widget, text, delay=200):
        self._widget = widget
        self._text = text
        self._delay = delay
        self._tw = None
        self._id = None
        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._hide)
        widget.bind("<ButtonPress>", self._hide)

    def _schedule(self, _evt=None):
        self._unschedule()
        self._id = self._widget.after(self._delay, self._show)

    def _unschedule(self):
        if self._id:
            self._widget.after_cancel(self._id)
            self._id = None

    def _show(self):
        if self._tw or not self._text:
            return
        x = self._widget.winfo_rootx() + 25
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 5
        self._tw = ctk.CTkToplevel(self._widget)
        self._tw.wm_overrideredirect(True)
        self._tw.wm_geometry(f"+{x}+{y}")
        self._tw.attributes("-topmost", True)
        ctk.CTkLabel(
            self._tw, text=self._text, wraplength=260,
            fg_color=("gray85", "gray25"), corner_radius=6,
        ).pack(ipadx=6, ipady=4)

    def _hide(self, _evt=None):
        self._unschedule()
        if self._tw:
            self._tw.destroy()
            self._tw = None

    def update_text(self, new_text):
        self._text = new_text


def run_ui():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("BeatSaber Mapfile Creator")
    root.withdraw()
    root.geometry("450x620")
    root.after_idle(lambda: (root.deiconify(), root.tk.call('tk::PlaceWindow', '.', 'center')))

    # Top bar
    top_bar = ctk.CTkFrame(root, fg_color="transparent", height=36)
    top_bar.pack(fill="x", padx=10, pady=(5, 0))
    top_bar.pack_propagate(False)

    settings_btn = ctk.CTkButton(top_bar, text="⚙ Settings", width=100, height=28)
    settings_btn.pack(side="left")

    # Page container
    container = ctk.CTkFrame(root, fg_color="transparent")
    container.pack(fill="both", expand=True)

    main_frame = ctk.CTkFrame(container, fg_color="transparent")
    settings_frame = ctk.CTkFrame(container, fg_color="transparent")

    current_page = [""]

    def show_main():
        settings_frame.pack_forget()
        main_frame.pack(fill="both", expand=True)
        settings_btn.configure(text="⚙ Settings", state="normal")
        current_page[0] = "main"

    def show_settings():
        main_frame.pack_forget()
        settings_frame.pack(fill="both", expand=True)
        settings_btn.configure(text="← Back")
        current_page[0] = "settings"
        _refresh_close_btn()

    # Settings page
    s_inner = ctk.CTkFrame(settings_frame, fg_color="transparent")
    s_inner.pack(expand=True, fill="both", padx=30, pady=10)

    ctk.CTkLabel(
        s_inner, text="Settings", font=ctk.CTkFont(size=22, weight="bold")
    ).pack(pady=(15, 25))

    # WIP Path
    wip_lbl = ctk.CTkFrame(s_inner, fg_color="transparent")
    wip_lbl.pack(fill="x")
    ctk.CTkLabel(wip_lbl, text="WIP Path", anchor="w").pack(side="left")
    _wip_help = ctk.CTkLabel(wip_lbl, text="ⓘ", cursor="hand2",
                             text_color=("gray40", "gray70"))
    _wip_help.pack(side="left", padx=(4, 0))
    _Tooltip(_wip_help, "The directory where your 'CustomWIPLevels' are stored.")

    wip_row = ctk.CTkFrame(s_inner, fg_color="transparent")
    wip_row.pack(fill="x", pady=(2, 12))
    wip_path = ctk.CTkEntry(wip_row)
    wip_path.pack(side="left", expand=True, fill="x", padx=(0, 5))

    def browse_wip():
        d = filedialog.askdirectory(title="Select WIP directory")
        if d:
            wip_path.delete(0, "end")
            wip_path.insert(0, d)
            save_config_fields()
            validate_inputs()
            _refresh_close_btn()

    ctk.CTkButton(wip_row, text="Browse", width=70, command=browse_wip).pack(side="right")

    # Mapper Name
    mapper_lbl = ctk.CTkFrame(s_inner, fg_color="transparent")
    mapper_lbl.pack(fill="x")
    ctk.CTkLabel(mapper_lbl, text="Mapper Name", anchor="w").pack(side="left")
    _mapper_help = ctk.CTkLabel(mapper_lbl, text="ⓘ", cursor="hand2",
                                text_color=("gray40", "gray70"))
    _mapper_help.pack(side="left", padx=(4, 0))
    _Tooltip(_mapper_help, "Your name.")

    mapper = ctk.CTkEntry(s_inner)
    mapper.pack(fill="x", pady=(2, 12))

    # Start Offset
    so_lbl = ctk.CTkFrame(s_inner, fg_color="transparent")
    so_lbl.pack(fill="x")
    ctk.CTkLabel(so_lbl, text="Start Offset (seconds)", anchor="w").pack(side="left")
    _so_help = ctk.CTkLabel(so_lbl, text="ⓘ", cursor="hand2",
                             text_color=("gray40", "gray70"))
    _so_help.pack(side="left", padx=(4, 0))
    _Tooltip(_so_help,
             "Extra silence added at the beginning of the map to avoid a "
             "'hot start'.")
    start_offset_entry = ctk.CTkEntry(s_inner, placeholder_text="1.5")
    start_offset_entry.pack(fill="x", pady=(2, 12))

    # End Offset
    eo_lbl = ctk.CTkFrame(s_inner, fg_color="transparent")
    eo_lbl.pack(fill="x")
    ctk.CTkLabel(eo_lbl, text="End Offset (seconds)", anchor="w").pack(side="left")
    _eo_help = ctk.CTkLabel(eo_lbl, text="ⓘ", cursor="hand2",
                             text_color=("gray40", "gray70"))
    _eo_help.pack(side="left", padx=(4, 0))
    _Tooltip(_eo_help,
             "Extra silence added at the end of the map to avoid a "
             "'cold end'.")
    end_offset_entry = ctk.CTkEntry(s_inner, placeholder_text="2.0")
    end_offset_entry.pack(fill="x", pady=(2, 12))

    # Close Settings
    close_settings_btn = ctk.CTkButton(
        s_inner, text="Close Settings", width=160, height=38,
    )
    close_settings_btn.pack(pady=(25, 10))

    settings_tip = _Tooltip(settings_btn, "")
    close_tip = _Tooltip(close_settings_btn, "")

    def _refresh_close_btn():
        valid = os.path.isdir(wip_path.get().strip())
        close_settings_btn.configure(state="normal" if valid else "disabled")
        if current_page[0] == "settings":
            settings_btn.configure(state="normal" if valid else "disabled")
        
        msg = "" if valid else "A valid WIP directory must be selected."
        settings_tip.update_text(msg)
        close_tip.update_text(msg)

    def _toggle_page():
        if current_page[0] == "main":
            show_settings()
        else:
            if not os.path.isdir(wip_path.get().strip()):
                return
            save_config_fields()
            show_main()
            validate_inputs()

    settings_btn.configure(command=_toggle_page)
    close_settings_btn.configure(command=_toggle_page)

    # Main page
    for r in range(9):
        main_frame.grid_rowconfigure(r, weight=1)
    main_frame.grid_columnconfigure((0, 1), weight=1)

    # --- YouTube Music Search (row 0) ---
    yt_lbl = ctk.CTkFrame(main_frame, fg_color="transparent")
    yt_lbl.grid(row=0, column=0, columnspan=2, pady=(10, 0), sticky="n")
    ctk.CTkLabel(yt_lbl, text="Autofill fields from YouTube Music search").pack(side="left")
    _yt_help = ctk.CTkLabel(yt_lbl, text="ⓘ", cursor="hand2",
                             text_color=("gray40", "gray70"))
    _yt_help.pack(side="left", padx=(4, 0))
    _Tooltip(_yt_help,
             "Search for a song on YouTube Music to automatically fill in the "
             "Link, Song Name, and Artist fields.")

    yt_search = ctk.CTkEntry(main_frame, width=330)
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

    yt_search_btn = ctk.CTkButton(main_frame, text="Search", width=60, command=search_ytmusic)
    yt_search_btn.grid(row=0, column=1, pady=(30, 0), padx=(5, 20), sticky="w")

    yt_search.bind("<Return>", lambda e: search_ytmusic())
    yt_search.bind("<KP_Enter>", lambda e: search_ytmusic())

    # --- Separator (row 1) ---
    ctk.CTkFrame(main_frame, height=2, fg_color=("gray80", "gray30")).grid(
        row=1, column=0, columnspan=2, pady=10, padx=20, sticky="ew")

    # --- Link or Local File (row 2) ---
    last_checked_path = [None]

    ll_lbl = ctk.CTkFrame(main_frame, fg_color="transparent")
    ll_lbl.grid(row=2, column=0, columnspan=2, pady=(10, 0), sticky="n")
    ctk.CTkLabel(ll_lbl, text="Link or Local File").pack(side="left")
    _ll_help = ctk.CTkLabel(ll_lbl, text="ⓘ", cursor="hand2",
                             text_color=("gray40", "gray70"))
    _ll_help.pack(side="left", padx=(4, 0))
    _Tooltip(_ll_help,
             "This is where your song is sourced from. It can be either a link which is downloadable by yt-dlp or a local audio file on your computer.\n\n"
             "For links: Song and artist metadata is NOT automatically extracted, and needs to be filled in manually.\n\n"
             "For local files: Metadata is extracted automatically if available. Supported formats are mp3, ogg, wav and flac.")

    link = ctk.CTkEntry(main_frame, width=330)
    link.grid(row=2, column=0, pady=(30, 0), padx=(20, 5), sticky="e")

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

    def browse_file():
        file_path = filedialog.askopenfilename(
            title="Select an audio file",
            filetypes=[("Audio files", "*.mp3 *.ogg *.wav *.flac"), ("All files", "*.*")]
        )
        if file_path:
            link.delete(0, "end")
            link.insert(0, file_path)
            _on_link_changed()

    browse_btn = ctk.CTkButton(main_frame, text="Browse", width=60, command=browse_file)
    browse_btn.grid(row=2, column=1, pady=(30, 0), padx=(5, 20), sticky="w")

    link.bind("<KeyRelease>", lambda e: _on_link_changed())
    link.bind("<FocusOut>", lambda e: _on_link_changed())

    # --- Song Name (row 3) ---
    ctk.CTkLabel(main_frame, text="Song Name").grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky="n")
    song_name = ctk.CTkEntry(main_frame, width=400)
    song_name.grid(row=3, column=0, columnspan=2, pady=(30, 0))

    sub_lbl = ctk.CTkFrame(main_frame, fg_color="transparent")
    sub_lbl.grid(row=4, column=0, columnspan=2, pady=(10, 0), sticky="n")
    ctk.CTkLabel(sub_lbl, text="Sub Name").pack(side="left")
    _sub_help = ctk.CTkLabel(sub_lbl, text="ⓘ", cursor="hand2",
                              text_color=("gray40", "gray70"))
    _sub_help.pack(side="left", padx=(4, 0))
    _Tooltip(_sub_help, "Additional info like (feat. Artist), (Remix), or (Sped Up Ver.).")

    sub_name = ctk.CTkEntry(main_frame, width=400)
    sub_name.grid(row=4, column=0, columnspan=2, pady=(30, 0))

    ctk.CTkLabel(main_frame, text="Artist").grid(row=5, column=0, columnspan=2, pady=(10, 0), sticky="n")
    artist = ctk.CTkEntry(main_frame, width=400)
    artist.grid(row=5, column=0, columnspan=2, pady=(30, 0))

    # Row 6 — Environment, Format, Song Speed
    env_row = ctk.CTkFrame(main_frame, fg_color="transparent")
    env_row.grid(row=6, column=0, columnspan=2, pady=(10, 0), padx=25, sticky="ew")
    env_row.grid_columnconfigure((0, 1, 2), weight=1)

    e_lbl = ctk.CTkFrame(env_row, fg_color="transparent")
    e_lbl.grid(row=0, column=0)
    ctk.CTkLabel(e_lbl, text="Environment").pack(side="left")
    _e_help = ctk.CTkLabel(e_lbl, text="ⓘ", cursor="hand2", text_color=("gray40", "gray70"))
    _e_help.pack(side="left", padx=(4, 0))
    _Tooltip(_e_help, "The environment you want to be set by default.")

    env_dropdown = ctk.CTkComboBox(env_row, values=ENVIRONMENTS, state="readonly", width=220)
    env_dropdown.grid(row=1, column=0, sticky="ew", padx=(0, 5))

    v_lbl = ctk.CTkFrame(env_row, fg_color="transparent")
    v_lbl.grid(row=0, column=1)
    ctk.CTkLabel(v_lbl, text="Format").pack(side="left")
    _v_help = ctk.CTkLabel(v_lbl, text="ⓘ", cursor="hand2", text_color=("gray40", "gray70"))
    _v_help.pack(side="left", padx=(4, 0))
    _Tooltip(_v_help, "V3 (Legacy) or V4 (Newest). V4 added variable note jump speed but the maps are not playable on older versions of the game.")

    version_dropdown = ctk.CTkComboBox(env_row, values=["V3", "V4"], state="readonly", width=75)
    version_dropdown.grid(row=1, column=1, padx=5)

    sp_lbl = ctk.CTkFrame(env_row, fg_color="transparent")
    sp_lbl.grid(row=0, column=2)
    ctk.CTkLabel(sp_lbl, text="Speed").pack(side="left")
    _sp_help = ctk.CTkLabel(sp_lbl, text="ⓘ", cursor="hand2", text_color=("gray40", "gray70"))
    _sp_help.pack(side="left", padx=(4, 0))
    _Tooltip(_sp_help, "Song speed (affects pitch). Change if you want to make a sped up / slowed down version. Default is 1.0 (original speed).")

    speed_entry = ctk.CTkEntry(env_row, width=80)
    speed_entry.grid(row=1, column=2, padx=(5, 0))

    # Prefill from CONFIG
    try:
        if CONFIG.get("wip_path"):
            wip_path.insert(0, CONFIG["wip_path"])
        if CONFIG.get("mapper_name"):
            mapper.insert(0, CONFIG["mapper_name"])
        env_val = CONFIG.get("environment", ENVIRONMENTS[0])
        if env_val not in ENVIRONMENTS:
            env_val = ENVIRONMENTS[0]
        env_dropdown.set(env_val)
        ver_val = CONFIG.get("map_version", "V3")
        if ver_val not in ("V3", "V4"):
            ver_val = "V3"
        version_dropdown.set(ver_val)
        so = CONFIG.get("start_offset", 0.0)
        if so:
            start_offset_entry.insert(0, str(so))
        eo = CONFIG.get("end_offset", 0.0)
        if eo:
            end_offset_entry.insert(0, str(eo))
        speed_entry.insert(0, str(CONFIG.get("song_speed", 1.0)))
    except Exception:
        pass

    # Save config helper
    def _get_positive_float(entry, default):
        try:
            val = float(entry.get().strip() or default)
        except ValueError:
            val = default
        if val < 0:
            val = 0.0
        entry.delete(0, "end")
        entry.insert(0, str(val))
        return val

    def save_config_fields():
        CONFIG["wip_path"] = wip_path.get().strip()
        CONFIG["mapper_name"] = mapper.get().strip()
        CONFIG["environment"] = env_dropdown.get().strip()
        CONFIG["map_version"] = version_dropdown.get().strip()
        CONFIG["start_offset"] = _get_positive_float(start_offset_entry, 0.0)
        CONFIG["end_offset"] = _get_positive_float(end_offset_entry, 0.0)
        try:
            CONFIG["song_speed"] = float(speed_entry.get().strip() or 1.0)
        except ValueError:
            CONFIG["song_speed"] = 1.0
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(CONFIG, f, indent=4, ensure_ascii=False)

    # --- Buttons (row 7) ---
    main_frame.grid_rowconfigure(8, weight=0)
    buttons_frame = ctk.CTkFrame(main_frame, fg_color="transparent", border_width=0, corner_radius=0)
    buttons_frame.grid(row=7, column=0, columnspan=2, sticky="ew", padx=20, pady=(25, 5))
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

    # --- Progress bar + status label (row 8) ---
    progress_frame = ctk.CTkFrame(main_frame, fg_color="transparent", border_width=0, corner_radius=0)
    progress_frame.grid(row=8, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 15))
    progress_frame.grid_columnconfigure(0, weight=1)

    progress_label = ctk.CTkLabel(progress_frame, text="", anchor="w")
    progress_label.grid(row=0, column=0, sticky="w", pady=(0, 2))

    progress_bar = ctk.CTkProgressBar(progress_frame, width=400)
    progress_bar.grid(row=1, column=0, sticky="ew")
    progress_bar.set(0)
    progress_frame.grid_remove()

    # Create Map
    def _set_ui_busy(busy):
        state = "disabled" if busy else "normal"
        for w in (yt_search, yt_search_btn, link, browse_btn, song_name,
                  sub_name, artist, env_dropdown, version_dropdown,
                  speed_entry, quit_button, create_button, settings_btn):
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
            for w in (song_name, sub_name, artist, link):
                w.delete(0, "end")
            return

        progress_frame.grid_remove()
        popup = ctk.CTkToplevel(root)
        popup.title("Error")
        popup.withdraw()
        popup.geometry("350x180")
        popup.after_idle(lambda w=popup: (w.deiconify(), w.tk.call('tk::PlaceWindow', str(w), 'center')))
        popup.transient(root)
        popup.grab_set()
        popup.focus()

        def _close():
            for w in (song_name, sub_name, artist, link):
                w.delete(0, "end")
            popup.destroy()

        ctk.CTkLabel(popup, text=msg, wraplength=300).pack(pady=20)
        ctk.CTkButton(popup, text="OK", command=_close).pack(pady=10)

    def create_map():
        validate_inputs()
        if not os.path.isdir(wip_path.get().strip()):
            _on_pipeline_done("WIP Path is empty or does not exist.")
            return
        if not link.get().strip():
            _on_pipeline_done("Link or local file is empty.")
            return

        save_config_fields()

        try:
            spd = float(speed_entry.get().strip() or 1.0)
            if spd <= 0:
                spd = 1.0
        except ValueError:
            spd = 1.0

        config = {
            "song": song_name.get().strip(),
            "sub_name": sub_name.get().strip(),
            "artist": artist.get().strip(),
            "link": link.get().replace('"', '').strip(),
            "wip_location": wip_path.get().strip(),
            "mapper": mapper.get().strip(),
            "environment": env_dropdown.get().strip(),
            "version": version_dropdown.get().strip(),
            "song_speed": spd,
            "start_offset": CONFIG.get("start_offset", 0.0),
            "end_offset": CONFIG.get("end_offset", 0.0),
        }

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

    # Validate WIP path and control Create Map button
    create_tip = _Tooltip(create_button, "")

    def validate_inputs(_evt=None):
        valid_wip = os.path.isdir(wip_path.get().strip())
        has_link = bool(link.get().strip())
        create_button.configure(state="normal" if (valid_wip and has_link) else "disabled")
        
        if not valid_wip:
            create_tip.update_text("A valid WIP directory must be selected in Settings.")
        elif not has_link:
            create_tip.update_text("The link or local file path must be filled in.")
        else:
            create_tip.update_text("")

    # Bind changes to validate and save
    def _on_wip_key(_evt=None):
        validate_inputs()
        _refresh_close_btn()

    wip_path.bind("<KeyRelease>", _on_wip_key)
    link.bind("<KeyRelease>", validate_inputs)
    mapper.bind("<FocusOut>", lambda e: save_config_fields())
    env_dropdown.bind("<<ComboboxSelected>>", lambda e: save_config_fields())
    version_dropdown.bind("<<ComboboxSelected>>", lambda e: save_config_fields())
    start_offset_entry.bind("<FocusOut>", lambda e: save_config_fields())
    end_offset_entry.bind("<FocusOut>", lambda e: save_config_fields())
    speed_entry.bind("<FocusOut>", lambda e: save_config_fields())

    validate_inputs()

    # First launch popup
    def _show_first_launch_popup():
        popup = ctk.CTkToplevel(root)
        popup.title("Important Notice")
        popup.withdraw()
        popup.geometry("440x170")
        popup.after_idle(
            lambda w=popup: (w.deiconify(), w.tk.call('tk::PlaceWindow', str(w), 'center'))
        )
        popup.transient(root)
        popup.grab_set()
        popup.focus()

        ctk.CTkLabel(
            popup,
            text=(
                "Please note that the detected BPM and offset can be "
                "inaccurate and the map should always be manually checked.\n\n"
                "A high-quality audio file should be preferred "
                "over downloading from YouTube Music."
            ),
            wraplength=400, justify="left",
        ).pack(pady=(25, 15), padx=20)

        def _understood():
            CONFIG["first_launch_done"] = True
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(CONFIG, f, indent=4)
            popup.destroy()

        ctk.CTkButton(popup, text="I Understood", command=_understood, width=140).pack(
            pady=(5, 20)
        )

    # Show main or settings based on whether WIP path is set
    if not CONFIG.get("wip_path"):
        show_settings()
        if not CONFIG.get("first_launch_done"):
            root.after(600, _show_first_launch_popup)
    else:
        show_main()
        if not CONFIG.get("first_launch_done"):
            root.after(600, _show_first_launch_popup)

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
