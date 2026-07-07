"""Offline Transcriber — modern GUI.

Drag audio/video files in, pick options in the sidebar, hit Transcribe.
Everything runs locally: Whisper for speech-to-text, SpeechBrain for
speaker labels. No internet needed after the one-time model downloads.
"""

import json
import queue
import threading
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD

from transcribe import AUDIO_EXTS, fmt_ts, get_vocabulary

APP_NAME = "Offline Transcriber"
LANGUAGES = {
    "Auto-detect": None, "Hindi": "hi", "English": "en", "Bengali": "bn",
    "Tamil": "ta", "Telugu": "te", "Marathi": "mr", "Gujarati": "gu",
    "Kannada": "kn", "Malayalam": "ml", "Punjabi": "pa", "Urdu": "ur",
    "Odia": "or", "Assamese": "as", "Nepali": "ne", "Sanskrit": "sa",
}
MODELS = {"Fast (small)": "small", "Balanced (medium)": "medium",
          "Best (large-v3)": "large-v3"}
SETTINGS_FILE = Path(__file__).parent / ".settings.json"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class JobCancelled(Exception):
    pass


class App(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

        self.title(APP_NAME)
        self.geometry("1020x660")
        self.minsize(860, 560)

        self.files = []            # list[Path]
        self.file_rows = {}        # Path -> (frame, status_label)
        self.model_cache = {}
        self.msg_queue = queue.Queue()
        self.last_out_dir = None
        self.live_stop = None      # threading.Event while live mode runs
        self.speaker_runs = []     # diarized results of the last job, for
                                   # the "Name speakers" dialog
        self.job_cancel = threading.Event()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()
        self._load_settings()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._poll_queue)

    # ---------- settings persistence -----------------------------------------
    def _setting_vars(self):
        return {"model": self.model_var, "language": self.lang_var,
                "speakers": self.speakers_var, "srt": self.srt_var,
                "translate": self.translate_var, "notes": self.notes_var,
                "cloud": self.cloud_var, "docx": self.docx_var,
                "live_source": self.live_source_var,
                "theme": self.theme_var}

    def _load_settings(self):
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        for name, var in self._setting_vars().items():
            if name in data:
                try:
                    var.set(data[name])
                except Exception:
                    pass
        ctk.set_appearance_mode(self.theme_var.get())

    def _on_close(self):
        try:
            SETTINGS_FILE.write_text(json.dumps(
                {name: var.get()
                 for name, var in self._setting_vars().items()}),
                encoding="utf-8")
        except OSError:
            pass
        self.destroy()

    # ---------- layout ----------------------------------------------------
    def _build_sidebar(self):
        side = ctk.CTkFrame(self, width=240, corner_radius=0)
        side.grid(row=0, column=0, sticky="nsw")
        side.grid_propagate(False)

        ctk.CTkLabel(side, text="🎙  Offline\nTranscriber", justify="left",
                     font=ctk.CTkFont(size=24, weight="bold")
                     ).pack(anchor="w", padx=20, pady=(24, 2))
        ctk.CTkLabel(side, text="Indian languages + English\n100% offline",
                     justify="left", text_color="gray60",
                     font=ctk.CTkFont(size=12)
                     ).pack(anchor="w", padx=20, pady=(0, 24))

        ctk.CTkLabel(side, text="MODEL", text_color="gray50",
                     font=ctk.CTkFont(size=11, weight="bold")
                     ).pack(anchor="w", padx=20)
        self.model_var = ctk.StringVar(value="Balanced (medium)")
        ctk.CTkOptionMenu(side, variable=self.model_var,
                          values=list(MODELS), width=200
                          ).pack(anchor="w", padx=20, pady=(4, 16))

        ctk.CTkLabel(side, text="LANGUAGE", text_color="gray50",
                     font=ctk.CTkFont(size=11, weight="bold")
                     ).pack(anchor="w", padx=20)
        self.lang_var = ctk.StringVar(value="Auto-detect")
        ctk.CTkOptionMenu(side, variable=self.lang_var,
                          values=list(LANGUAGES), width=200
                          ).pack(anchor="w", padx=20, pady=(4, 16))

        ctk.CTkLabel(side, text="OPTIONS", text_color="gray50",
                     font=ctk.CTkFont(size=11, weight="bold")
                     ).pack(anchor="w", padx=20)
        self.speakers_var = ctk.BooleanVar()
        self.srt_var = ctk.BooleanVar()
        self.translate_var = ctk.BooleanVar()
        self.cloud_var = ctk.BooleanVar()
        self.notes_var = ctk.BooleanVar()
        self.docx_var = ctk.BooleanVar()
        for text, var in [("Speaker labels", self.speakers_var),
                          ("Subtitles (.srt)", self.srt_var),
                          ("Word (.docx)", self.docx_var),
                          ("Translate to English", self.translate_var),
                          ("📝 Meeting notes", self.notes_var),
                          ("⚡ Cloud boost (free)", self.cloud_var)]:
            ctk.CTkSwitch(side, text=text, variable=var
                          ).pack(anchor="w", padx=20, pady=(6, 0))
        ctk.CTkLabel(side, text="Cloud: ~100x faster via Groq's free\n"
                                "tier (needs internet + free key);\n"
                                "falls back to offline automatically.",
                     justify="left", text_color="gray60",
                     font=ctk.CTkFont(size=11)
                     ).pack(anchor="w", padx=20, pady=(4, 0))

        ctk.CTkLabel(side, text="LIVE", text_color="gray50",
                     font=ctk.CTkFont(size=11, weight="bold")
                     ).pack(anchor="w", padx=20, pady=(16, 0))
        self.live_source_var = ctk.StringVar(value="Microphone")
        ctk.CTkOptionMenu(side, variable=self.live_source_var,
                          values=["Microphone", "Call audio (Teams/Zoom)",
                                  "Mic + call"], width=200
                          ).pack(anchor="w", padx=20, pady=(4, 6))
        self.live_btn = ctk.CTkButton(side, text="🎤  Start live mic",
                                      height=36, corner_radius=10,
                                      fg_color="#B3402A",
                                      hover_color="#93331F",
                                      command=self._toggle_live)
        self.live_btn.pack(anchor="w", padx=20, pady=(6, 0), fill="x")
        ctk.CTkLabel(side, text="Speak, pause — text appears.\n"
                                "Stop to save the session.",
                     justify="left", text_color="gray60",
                     font=ctk.CTkFont(size=11)
                     ).pack(anchor="w", padx=20, pady=(4, 0))

        spacer = ctk.CTkFrame(side, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        self.theme_var = ctk.StringVar(value="dark")
        ctk.CTkSegmentedButton(side, values=["dark", "light"],
                               variable=self.theme_var,
                               command=ctk.set_appearance_mode
                               ).pack(padx=20, pady=(0, 20), fill="x")

    def _build_main(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=16, pady=16)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(3, weight=1)

        # drop zone
        self.drop = ctk.CTkFrame(main, height=92, corner_radius=14,
                                 border_width=2, border_color="gray40")
        self.drop.grid(row=0, column=0, sticky="ew")
        self.drop.grid_propagate(False)
        self.drop_label = ctk.CTkLabel(
            self.drop, text="⬇  Drop audio or video files here — or click to browse",
            font=ctk.CTkFont(size=15), text_color="gray70")
        self.drop_label.place(relx=0.5, rely=0.5, anchor="center")
        for w in (self.drop, self.drop_label):
            w.drop_target_register(DND_FILES)
            w.dnd_bind("<<Drop>>", self._on_drop)
        self.drop_label.bind("<Button-1>", lambda e: self._browse())
        self.drop.bind("<Button-1>", lambda e: self._browse())

        # file queue
        self.queue_frame = ctk.CTkScrollableFrame(main, height=120,
                                                  label_text="Queue",
                                                  corner_radius=14)
        self.queue_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))

        # controls row
        controls = ctk.CTkFrame(main, fg_color="transparent")
        controls.grid(row=2, column=0, sticky="ew", pady=12)
        controls.grid_columnconfigure(2, weight=1)
        self.go_btn = ctk.CTkButton(controls, text="▶   Transcribe",
                                    height=40, corner_radius=10,
                                    font=ctk.CTkFont(size=15, weight="bold"),
                                    command=self._start)
        self.go_btn.grid(row=0, column=0)
        self.cancel_btn = ctk.CTkButton(controls, text="Cancel", height=40,
                                        width=80, corner_radius=10,
                                        fg_color="gray30",
                                        hover_color="gray25",
                                        state="disabled",
                                        command=self.job_cancel.set)
        self.cancel_btn.grid(row=0, column=1, padx=(8, 0))
        ctk.CTkButton(controls, text="Clear", height=40, width=80,
                      corner_radius=10, fg_color="gray30",
                      hover_color="gray25", command=self._clear
                      ).grid(row=0, column=4, padx=(8, 0))
        self.name_btn = ctk.CTkButton(controls, text="Name speakers",
                                      height=40, width=130, corner_radius=10,
                                      fg_color="gray30", hover_color="gray25",
                                      state="disabled",
                                      command=self._open_name_dialog)
        self.name_btn.grid(row=0, column=2, padx=(8, 0), sticky="w")
        self.open_btn = ctk.CTkButton(controls, text="Open output folder",
                                      height=40, width=160, corner_radius=10,
                                      fg_color="gray30", hover_color="gray25",
                                      state="disabled", command=self._open_out)
        self.open_btn.grid(row=0, column=3, sticky="e")

        self.progress = ctk.CTkProgressBar(main, height=8)
        self.progress.set(0)
        self.progress.grid(row=2, column=0, sticky="sew", pady=(0, 0))
        self.progress.grid_remove()

        # transcript panel
        self.log_box = ctk.CTkTextbox(main, corner_radius=14, wrap="word",
                                      font=ctk.CTkFont(size=13))
        self.log_box.grid(row=3, column=0, sticky="nsew")
        self.log_box.configure(state="disabled")

        self.status_var = ctk.StringVar(value="Ready — add some files.")
        ctk.CTkLabel(main, textvariable=self.status_var, anchor="w",
                     text_color="gray60").grid(row=4, column=0, sticky="ew",
                                               pady=(6, 0))

    # ---------- file queue -------------------------------------------------
    def _on_drop(self, event):
        for p in self.tk.splitlist(event.data):
            self._add_path(Path(p))

    def _browse(self):
        from tkinter import filedialog
        for p in filedialog.askopenfilenames(
                title="Choose audio/video files",
                filetypes=[("Audio/Video", " ".join("*" + e for e in AUDIO_EXTS)),
                           ("All files", "*.*")]):
            self._add_path(Path(p))

    def _add_path(self, path: Path):
        if path.is_dir():
            for f in sorted(path.iterdir()):
                if f.suffix.lower() in AUDIO_EXTS:
                    self._add_path(f)
            return
        if path in self.files or not path.is_file():
            return
        self.files.append(path)
        row = ctk.CTkFrame(self.queue_frame, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=path.name, anchor="w").pack(side="left",
                                                           padx=(4, 8))
        status = ctk.CTkLabel(row, text="queued", text_color="gray55",
                              anchor="e")
        status.pack(side="right", padx=4)
        self.file_rows[path] = (row, status)

    def _clear(self):
        self.files.clear()
        for row, _ in self.file_rows.values():
            row.destroy()
        self.file_rows.clear()

    def _open_out(self):
        if self.last_out_dir:
            import os
            os.startfile(self.last_out_dir)

    # ---------- worker plumbing -------------------------------------------
    def _log(self, text):
        self.msg_queue.put(("log", text))

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.msg_queue.get_nowait()
                if kind == "log":
                    self.log_box.configure(state="normal")
                    self.log_box.insert("end", payload + "\n")
                    self.log_box.see("end")
                    self.log_box.configure(state="disabled")
                elif kind == "status":
                    self.status_var.set(payload)
                elif kind == "progress":
                    self.progress.grid()
                    self.progress.set(payload)
                elif kind == "file_status":
                    path, text, color = payload
                    if path in self.file_rows:
                        self.file_rows[path][1].configure(text=text,
                                                          text_color=color)
                elif kind == "done":
                    self.go_btn.configure(state="normal")
                    self.live_btn.configure(state="normal")
                    self.cancel_btn.configure(state="disabled")
                    self.progress.grid_remove()
                    if self.last_out_dir:
                        self.open_btn.configure(state="normal")
                    if self.speaker_runs:
                        self.name_btn.configure(state="normal")
                elif kind == "live_done":
                    self.live_stop = None
                    self.live_btn.configure(text="🎤  Start live mic",
                                            fg_color="#B3402A",
                                            hover_color="#93331F")
                    self.go_btn.configure(state="normal")
                    if self.last_out_dir:
                        self.open_btn.configure(state="normal")
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    # ---------- speaker naming ----------------------------------------------
    def _open_name_dialog(self):
        run = self.speaker_runs[-1] if self.speaker_runs else None
        if not run:
            return
        from voices import display_name

        dlg = ctk.CTkToplevel(self)
        dlg.title("Name speakers")
        dlg.geometry("560x420")
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text=f"Who is who in {run['path'].name}?",
                     font=ctk.CTkFont(size=16, weight="bold")
                     ).pack(anchor="w", padx=16, pady=(14, 2))
        ctk.CTkLabel(dlg, text="Named voices are remembered — future "
                               "meetings will label these people "
                               "automatically.", text_color="gray60"
                     ).pack(anchor="w", padx=16, pady=(0, 8))

        body = ctk.CTkScrollableFrame(dlg)
        body.pack(fill="both", expand=True, padx=12, pady=4)
        entries = {}
        nums = sorted({spk for spk, *_ in run["turns"]})
        for num in nums:
            quote = next((tx for spk, _, _, tx in run["turns"]
                          if spk == num), "")
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(fill="x", pady=6)
            ctk.CTkLabel(row, text=f"Speaker {num}", width=80, anchor="w",
                         font=ctk.CTkFont(weight="bold")).pack(side="left")
            entry = ctk.CTkEntry(row, width=160,
                                 placeholder_text="name (optional)")
            entry.insert(0, run["names"].get(num, ""))
            entry.pack(side="left", padx=(4, 8))
            ctk.CTkLabel(row, text=f"“{quote[:52]}…”" if len(quote) > 52
                         else f"“{quote}”", text_color="gray60",
                         anchor="w").pack(side="left", fill="x", expand=True)
            entries[num] = entry

        def save():
            from voices import enroll, match_speakers
            names = {num: e.get().strip()
                     for num, e in entries.items() if e.get().strip()}
            profiles = None
            for num, name in names.items():
                if num in run["centroids"]:
                    profiles = enroll(name, run["centroids"][num], profiles)

            # Speaker numbers are per-file, so this dialog's number->name map
            # only applies to the file it was built from. Other files in the
            # batch are re-named by matching their voices against the freshly
            # enrolled profiles — the same mechanism used in future meetings.
            for r in self.speaker_runs:
                r["names"] = (dict(names) if r is run
                              else match_speakers(r["centroids"]))
                lines = [(st, en,
                          f"{display_name(spk, r['names'])}: {tx}")
                         for spk, st, en, tx in r["turns"]]
                txt = r["path"].with_suffix(".txt")
                txt.write_text(
                    "\n".join(tx for _, _, tx in lines) + "\n",
                    encoding="utf-8")
                if r["srt"]:
                    blocks = []
                    for i, (st, en, tx) in enumerate(lines, 1):
                        blocks.append(
                            f"{i}\n{fmt_ts(st, srt=True)} --> "
                            f"{fmt_ts(en, srt=True)}\n{tx}\n")
                    r["path"].with_suffix(".srt").write_text(
                        "\n".join(blocks), encoding="utf-8")
            if names:
                self._log("speakers named & voices remembered: "
                          + ", ".join(names.values())
                          + " — transcripts updated.")
            dlg.destroy()

        btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=10)
        ctk.CTkButton(btn_row, text="Save & remember voices", command=save
                      ).pack(side="right")
        ctk.CTkButton(btn_row, text="Cancel", fg_color="gray30",
                      hover_color="gray25", command=dlg.destroy
                      ).pack(side="right", padx=(0, 8))

    # ---------- live microphone mode ----------------------------------------
    def _toggle_live(self):
        if self.live_stop is not None:          # currently listening -> stop
            self.status_var.set("Stopping live mode...")
            self.live_stop.set()
            return
        self.live_stop = threading.Event()
        self.live_btn.configure(text="⏹  Stop & save",
                                fg_color="gray30", hover_color="gray25")
        self.go_btn.configure(state="disabled")
        source = {"Microphone": "mic", "Call audio (Teams/Zoom)": "call",
                  "Mic + call": "both"}[self.live_source_var.get()]
        threading.Thread(target=self._live_loop, args=(self.live_stop, {
            "model": MODELS[self.model_var.get()],
            "language": LANGUAGES[self.lang_var.get()],
            "translate": self.translate_var.get(),
            "source": source,
        }), daemon=True).start()

    def _live_loop(self, stop, a):
        transcript = []
        streams = []
        try:
            import numpy as np
            import sounddevice as sd

            from live import find_loopback_device

            # short utterances gain nothing from batching: use the raw model
            whisper = self._get_model(a["model"]).model

            rate, block = 16000, 0.25
            silence_rms, end_silence = 0.01, 0.8
            max_utterance, min_speech = 12.0, 0.4

            sources = [("you", None)]
            if a["source"] in ("call", "both"):
                loop_dev = find_loopback_device()
                if loop_dev is None:
                    self.msg_queue.put((
                        "status",
                        "No call-audio device found — enable 'Stereo Mix' in "
                        "Windows sound settings or install VB-Audio Cable."))
                    return
                sources = ([("call", loop_dev)] if a["source"] == "call"
                           else [("you", None), ("call", loop_dev)])
            tagged = len(sources) > 1

            audio_q = queue.Queue()

            def make_callback(tag):
                def callback(indata, frames, t, status):
                    audio_q.put((tag, indata[:, 0].copy()))
                return callback

            def flush(tag, buf):
                segments, info = whisper.transcribe(
                    np.concatenate(buf), language=a["language"],
                    task="translate" if a["translate"] else "transcribe",
                    beam_size=2, vad_filter=True,
                    hotwords=get_vocabulary())
                text = " ".join(s.text.strip() for s in segments).strip()
                if text:
                    stamp = datetime.now().strftime("%H:%M:%S")
                    label = f" {tag}" if tagged else ""
                    line = f"[{stamp} {info.language}{label}] {text}"
                    self._log(line)
                    transcript.append(line)

            bufs = {tag: [] for tag, _ in sources}
            speech = {tag: 0.0 for tag, _ in sources}
            silence = {tag: 0.0 for tag, _ in sources}

            def feed(tag, chunk, drain_all=False):
                loud = float(np.sqrt(np.mean(chunk ** 2))) >= silence_rms
                if loud:
                    bufs[tag].append(chunk)
                    speech[tag] += block
                    silence[tag] = 0.0
                elif bufs[tag]:
                    bufs[tag].append(chunk)  # keep a little trailing silence
                    silence[tag] += block
                if bufs[tag] and (silence[tag] >= end_silence
                                  or len(bufs[tag]) * block >= max_utterance
                                  or drain_all):
                    if speech[tag] >= min_speech:
                        flush(tag, bufs[tag])
                    bufs[tag], speech[tag], silence[tag] = [], 0.0, 0.0

            what = " + ".join(tag for tag, _ in sources)
            self.msg_queue.put(("status",
                                f"🔴 Listening ({what}) — press Stop to "
                                "finish."))
            self._log("\n═══ live session started ═══")
            streams = [sd.InputStream(samplerate=rate, channels=1,
                                      dtype="float32", device=dev,
                                      blocksize=int(rate * block),
                                      callback=make_callback(tag))
                       for tag, dev in sources]
            for s in streams:
                s.start()
            while not stop.is_set():
                try:
                    tag, chunk = audio_q.get(timeout=0.3)
                except queue.Empty:
                    continue
                feed(tag, chunk)
            for s in streams:
                s.stop()
            # drain whatever was captured while the last flush was running,
            # so the tail of the final utterance isn't lost on stop
            while True:
                try:
                    tag, chunk = audio_q.get_nowait()
                except queue.Empty:
                    break
                feed(tag, chunk)
            for tag, _ in sources:
                feed(tag, np.zeros(int(rate * block), dtype=np.float32),
                     drain_all=True)

            if transcript:
                out = Path(__file__).parent / (
                    "live_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    + ".txt")
                out.write_text("\n".join(transcript) + "\n", encoding="utf-8")
                self.last_out_dir = str(out.parent)
                self._log(f"═══ live session saved: {out.name} ═══")
                self.msg_queue.put(("status", f"Live session saved to {out}"))
            else:
                self.msg_queue.put(("status",
                                    "Live session ended — no speech heard."))
        except Exception as e:
            self.msg_queue.put(("status", f"Live mode error: {e}"))
            self._log(f"live mode error: {e}")
        finally:
            for s in streams:
                try:
                    s.stop()
                    s.close()
                except Exception:
                    pass
            self.msg_queue.put(("live_done", None))

    # ---------- transcription ----------------------------------------------
    def _start(self):
        if not self.files:
            self.status_var.set("Add some files first — drop them above.")
            return
        if self.live_stop is not None:
            self.status_var.set("Stop the live mic first.")
            return
        self.go_btn.configure(state="disabled")
        self.live_btn.configure(state="disabled")
        self.job_cancel.clear()
        self.cancel_btn.configure(state="normal")
        a = {
            "model": MODELS[self.model_var.get()],
            "language": LANGUAGES[self.lang_var.get()],
            "srt": self.srt_var.get(),
            "docx": self.docx_var.get(),
            "translate": self.translate_var.get(),
            "speakers": self.speakers_var.get(),
            "cloud": self.cloud_var.get(),
            "notes": self.notes_var.get(),
            "files": list(self.files),
        }
        threading.Thread(target=self._run_job, args=(a,), daemon=True).start()

    def _get_model(self, name):
        model = self.model_cache.get(name)
        if model is None:
            self.msg_queue.put(("status",
                                f"Loading model '{name}' (first use downloads "
                                "it once — offline after that)..."))
            import os

            from faster_whisper import BatchedInferencePipeline, WhisperModel
            base = WhisperModel(name, device="cpu", compute_type="int8",
                                cpu_threads=os.cpu_count() or 4)
            model = BatchedInferencePipeline(model=base)
            self.model_cache[name] = model
        return model

    def _run_job(self, a):
        self.speaker_runs = []
        try:
            model = None if a["cloud"] else self._get_model(a["model"])
            for i, f in enumerate(a["files"], 1):
                if self.job_cancel.is_set():
                    self.msg_queue.put(("file_status",
                                        (f, "cancelled", "gray55")))
                    continue
                self.msg_queue.put(("file_status", (f, "working…", "#3B8ED0")))
                self.msg_queue.put(("progress", 0.0))
                self.msg_queue.put(("status",
                                    f"Transcribing {f.name} ({i}/{len(a['files'])})..."))
                try:
                    self._transcribe_one(model, f, a)
                    self.msg_queue.put(("file_status", (f, "done ✓", "#2CC985")))
                except JobCancelled:
                    self.msg_queue.put(("file_status",
                                        (f, "cancelled", "gray55")))
                    self._log(f"cancelled during {f.name}")
                except Exception as e:
                    self.msg_queue.put(("file_status", (f, "error ✗", "#E5544B")))
                    self._log(f"ERROR on {f.name}: {e}")
            self.msg_queue.put(("status", "Cancelled."
                                if self.job_cancel.is_set() else "Done."))
        except Exception as e:
            self.msg_queue.put(("status", f"Error: {e}"))
        finally:
            self.msg_queue.put(("done", None))

    def _transcribe_one(self, model, path: Path, a):
        self._log(f"\n═══ {path.name} ═══")
        segments = None
        if a["cloud"]:
            import cloud
            try:
                self.msg_queue.put(("status",
                                    f"Uploading {path.name} to Groq "
                                    "(free cloud)..."))
                segments, info = cloud.transcribe(
                    path, language=a["language"], translate=a["translate"],
                    want_words=a["speakers"], prompt=get_vocabulary(),
                    log=self._log)
            except cloud.CloudUnavailable as e:
                self._log(f"cloud unavailable — using the local engine.\n"
                          f"({e})")
                self.msg_queue.put(("status",
                                    f"Cloud unavailable — transcribing "
                                    f"{path.name} offline instead..."))
        if segments is None:
            if model is None:
                model = self._get_model(a["model"])
            segments, info = model.transcribe(
                str(path), language=a["language"],
                task="translate" if a["translate"] else "transcribe",
                beam_size=5, batch_size=8,
                word_timestamps=a["speakers"],
                hotwords=get_vocabulary())
        self._log(f"language: {info.language} "
                  f"({info.language_probability:.0%}), "
                  f"duration {fmt_ts(info.duration)}")
        seg_list = []
        for seg in segments:
            if self.job_cancel.is_set():
                raise JobCancelled()
            seg_list.append(seg)
            self._log(f"[{fmt_ts(seg.start)}] {seg.text.strip()}")
            if info.duration:
                self.msg_queue.put(("progress",
                                    min(seg.end / info.duration, 1.0)))

        lines = [(s.start, s.end, s.text.strip()) for s in seg_list]
        if a["speakers"] and seg_list:
            self.msg_queue.put(("status",
                                f"Labelling speakers in {path.name}..."))
            from faster_whisper.audio import decode_audio

            from diarize import diarize_words
            from voices import display_name, match_speakers
            words = [(w.start, w.end, w.word)
                     for s in seg_list for w in (s.words or [])]
            audio = decode_audio(str(path), sampling_rate=16000)
            turns, n, centroids = diarize_words(audio, words)
            if turns:
                self._log(f"speakers found: {n}")
                names = match_speakers(centroids)
                if names:
                    self._log("recognized voices: " + ", ".join(
                        f"Speaker {num} = {name}" for num, name in
                        sorted(names.items())))
                lines = [(st, en, f"{display_name(spk, names)}: {tx}")
                         for spk, st, en, tx in turns]
                for _, _, tx in lines:
                    self._log(tx)
                self.speaker_runs.append({
                    "path": path, "turns": turns, "centroids": centroids,
                    "names": names, "srt": a["srt"]})

        transcript_text = "\n".join(tx for _, _, tx in lines) + "\n"
        txt = path.with_suffix(".txt")
        txt.write_text(transcript_text, encoding="utf-8")
        saved = [txt.name]
        if a["srt"]:
            blocks = []
            for i, (st, en, tx) in enumerate(lines, 1):
                blocks.append(f"{i}\n{fmt_ts(st, srt=True)} --> "
                              f"{fmt_ts(en, srt=True)}\n{tx}\n")
            srt = path.with_suffix(".srt")
            srt.write_text("\n".join(blocks), encoding="utf-8")
            saved.append(srt.name)

        if a["docx"]:
            from docx_export import write_docx
            docx_path = write_docx(path.with_suffix(".docx"),
                                   path.stem, lines)
            saved.append(docx_path.name)

        if a["notes"]:
            self.msg_queue.put(("status",
                                f"Writing meeting notes for {path.name}..."))
            from notes import NotesUnavailable, generate_notes
            try:
                result = generate_notes(transcript_text, log=self._log)
                notes_file = path.with_name(path.stem + "_notes.md")
                notes_file.write_text(result + "\n", encoding="utf-8")
                saved.append(notes_file.name)
                self._log("\n" + result)
            except NotesUnavailable as e:
                self._log(f"meeting notes skipped: {e}")

        self.last_out_dir = str(path.parent)
        self._log("saved: " + ", ".join(saved))


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
