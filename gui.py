"""Offline Transcriber — modern GUI.

Drag audio/video files in, pick options in the sidebar, hit Transcribe.
Everything runs locally: Whisper for speech-to-text, SpeechBrain for
speaker labels. No internet needed after the one-time model downloads.
"""

import queue
import threading
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD

from transcribe import AUDIO_EXTS, fmt_ts

APP_NAME = "Offline Transcriber"
LANGUAGES = {
    "Auto-detect": None, "Hindi": "hi", "English": "en", "Bengali": "bn",
    "Tamil": "ta", "Telugu": "te", "Marathi": "mr", "Gujarati": "gu",
    "Kannada": "kn", "Malayalam": "ml", "Punjabi": "pa", "Urdu": "ur",
    "Odia": "or", "Assamese": "as", "Nepali": "ne", "Sanskrit": "sa",
}
MODELS = {"Fast (small)": "small", "Balanced (medium)": "medium",
          "Best (large-v3)": "large-v3"}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


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

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()
        self.after(100, self._poll_queue)

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
        for text, var in [("Speaker labels", self.speakers_var),
                          ("Subtitles (.srt)", self.srt_var),
                          ("Translate to English", self.translate_var)]:
            ctk.CTkSwitch(side, text=text, variable=var
                          ).pack(anchor="w", padx=20, pady=(6, 0))

        ctk.CTkLabel(side, text="LIVE", text_color="gray50",
                     font=ctk.CTkFont(size=11, weight="bold")
                     ).pack(anchor="w", padx=20, pady=(16, 0))
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
        ctk.CTkButton(controls, text="Clear", height=40, width=80,
                      corner_radius=10, fg_color="gray30",
                      hover_color="gray25", command=self._clear
                      ).grid(row=0, column=1, padx=(8, 0))
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
                    self.progress.grid_remove()
                    if self.last_out_dir:
                        self.open_btn.configure(state="normal")
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
        threading.Thread(target=self._live_loop, args=(self.live_stop, {
            "model": MODELS[self.model_var.get()],
            "language": LANGUAGES[self.lang_var.get()],
            "translate": self.translate_var.get(),
        }), daemon=True).start()

    def _live_loop(self, stop, a):
        transcript = []
        try:
            import numpy as np
            import sounddevice as sd

            # short utterances gain nothing from batching: use the raw model
            whisper = self._get_model(a["model"]).model

            rate, block = 16000, 0.25
            silence_rms, end_silence = 0.01, 0.8
            max_utterance, min_speech = 12.0, 0.4

            audio_q = queue.Queue()

            def callback(indata, frames, t, status):
                audio_q.put(indata[:, 0].copy())

            def flush(buf):
                segments, info = whisper.transcribe(
                    np.concatenate(buf), language=a["language"],
                    task="translate" if a["translate"] else "transcribe",
                    beam_size=2, vad_filter=True)
                text = " ".join(s.text.strip() for s in segments).strip()
                if text:
                    stamp = datetime.now().strftime("%H:%M:%S")
                    line = f"[{stamp} {info.language}] {text}"
                    self._log(line)
                    transcript.append(line)

            self.msg_queue.put(("status",
                                "🔴 Listening — speak, then pause. "
                                "Press Stop to finish."))
            self._log("\n═══ live session started ═══")
            buf, speech, silence = [], 0.0, 0.0
            with sd.InputStream(samplerate=rate, channels=1, dtype="float32",
                                blocksize=int(rate * block),
                                callback=callback):
                while not stop.is_set():
                    try:
                        chunk = audio_q.get(timeout=0.3)
                    except queue.Empty:
                        continue
                    loud = float(np.sqrt(np.mean(chunk ** 2))) >= silence_rms
                    if loud:
                        buf.append(chunk)
                        speech += block
                        silence = 0.0
                    elif buf:
                        buf.append(chunk)   # keep a little trailing silence
                        silence += block
                    if buf and (silence >= end_silence
                                or len(buf) * block >= max_utterance):
                        if speech >= min_speech:
                            flush(buf)
                        buf, speech, silence = [], 0.0, 0.0
            if buf and speech >= min_speech:
                flush(buf)

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
        a = {
            "model": MODELS[self.model_var.get()],
            "language": LANGUAGES[self.lang_var.get()],
            "srt": self.srt_var.get(),
            "translate": self.translate_var.get(),
            "speakers": self.speakers_var.get(),
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
        try:
            model = self._get_model(a["model"])
            for i, f in enumerate(a["files"], 1):
                self.msg_queue.put(("file_status", (f, "working…", "#3B8ED0")))
                self.msg_queue.put(("status",
                                    f"Transcribing {f.name} ({i}/{len(a['files'])})..."))
                try:
                    self._transcribe_one(model, f, a)
                    self.msg_queue.put(("file_status", (f, "done ✓", "#2CC985")))
                except Exception as e:
                    self.msg_queue.put(("file_status", (f, "error ✗", "#E5544B")))
                    self._log(f"ERROR on {f.name}: {e}")
            self.msg_queue.put(("status", "Done."))
        except Exception as e:
            self.msg_queue.put(("status", f"Error: {e}"))
        finally:
            self.msg_queue.put(("done", None))

    def _transcribe_one(self, model, path: Path, a):
        segments, info = model.transcribe(
            str(path), language=a["language"],
            task="translate" if a["translate"] else "transcribe",
            beam_size=5, batch_size=8,
            word_timestamps=a["speakers"])
        self._log(f"\n═══ {path.name} ═══")
        self._log(f"language: {info.language} "
                  f"({info.language_probability:.0%}), "
                  f"duration {fmt_ts(info.duration)}")
        seg_list = []
        for seg in segments:
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
            words = [(w.start, w.end, w.word)
                     for s in seg_list for w in (s.words or [])]
            audio = decode_audio(str(path), sampling_rate=16000)
            turns, n = diarize_words(audio, words)
            if turns:
                self._log(f"speakers found: {n}")
                lines = [(st, en, f"Speaker {spk}: {tx}")
                         for spk, st, en, tx in turns]
                for _, _, tx in lines:
                    self._log(tx)

        txt = path.with_suffix(".txt")
        txt.write_text("\n".join(tx for _, _, tx in lines) + "\n",
                       encoding="utf-8")
        saved = [txt.name]
        if a["srt"]:
            blocks = []
            for i, (st, en, tx) in enumerate(lines, 1):
                blocks.append(f"{i}\n{fmt_ts(st, srt=True)} --> "
                              f"{fmt_ts(en, srt=True)}\n{tx}\n")
            srt = path.with_suffix(".srt")
            srt.write_text("\n".join(blocks), encoding="utf-8")
            saved.append(srt.name)
        self.last_out_dir = str(path.parent)
        self._log("saved: " + ", ".join(saved))


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
