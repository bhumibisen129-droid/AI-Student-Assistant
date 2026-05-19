"""
dashboard.py
Tkinter GUI — dark theme, tabbed interface
Tabs: Chat | Timetable | Notes | Reminders | PDF
"""
import win32com.client
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import sys
import core.assistant_brain as assistant_brain
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.assistant_brain import process_command, load_pdf_context, on_startup
from core.voice_engine    import VoiceEngine
from core.timetable       import (get_full_timetable, add_class,
                                   get_today_classes, format_classes, DAYS)
from core.notes           import get_all_notes, get_note, format_notes_list
from core.reminder        import get_reminders, format_reminders_text

# ── Color palette (dark theme) ───────────────────────────────────────────────
BG       = "#0f0f18"
BG2      = "#1a1a2e"
BG3      = "#16213e"
ACCENT   = "#4f6ef7"
ACCENT2  = "#7c3aed"
GREEN    = "#22c55e"
RED      = "#ef4444"
YELLOW   = "#f59e0b"
TEXT     = "#e2e8f0"
TEXT_DIM = "#64748b"
FONT_MAIN= ("Segoe UI", 11)
FONT_BIG = ("Segoe UI", 13, "bold")
FONT_SM  = ("Segoe UI", 9)


class StudentAssistantApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.voice = VoiceEngine()
        self.is_listening = False
        self.pdf_loaded   = False

        self._setup_window()
        self._build_header()
        self._build_tabs()
        self._build_status_bar()

        # Restore reminders
        on_startup(self._reminder_alert)
        self._refresh_all()

    # ── Window setup ─────────────────────────────────────────────────────────
    def _setup_window(self):
        self.root.title("AI Student Assistant")
        self.root.geometry("1000x700")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook",       background=BG2, borderwidth=0)
        style.configure("TNotebook.Tab",   background=BG3, foreground=TEXT_DIM,
                         padding=[16, 8],  font=("Segoe UI", 10))
        style.map("TNotebook.Tab",
                   background=[("selected", ACCENT)],
                   foreground=[("selected", "#ffffff")])
        style.configure("TFrame",  background=BG)
        style.configure("TLabel",  background=BG, foreground=TEXT, font=FONT_MAIN)
        style.configure("TEntry",  fieldbackground=BG3, foreground=TEXT, insertcolor=TEXT)
        style.configure("Vertical.TScrollbar", background=BG3, troughcolor=BG)

    # ── Header ───────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self.root, bg=BG2, height=60)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="🎓 AI Student Assistant",
                  bg=BG2, fg=TEXT, font=("Segoe UI", 16, "bold")).pack(side="left", padx=20, pady=10)

        self.time_label = tk.Label(hdr, text="", bg=BG2, fg=TEXT_DIM, font=FONT_SM)
        self.time_label.pack(side="right", padx=20)
        self._update_clock()

    def _update_clock(self):
        now = datetime.now().strftime("%A, %d %b %Y  |  %I:%M:%S %p")
        self.time_label.config(text=now)
        self.root.after(1000, self._update_clock)

    # ── Tabs ─────────────────────────────────────────────────────────────────
    def _build_tabs(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(5, 0))

        self._build_chat_tab()
        self._build_timetable_tab()
        self._build_notes_tab()
        self._build_reminders_tab()
        self._build_pdf_tab()

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 1: CHAT
    # ═══════════════════════════════════════════════════════════════════════════
    def _build_chat_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="💬 Chat")

        # Chat display
        self.chat_display = scrolledtext.ScrolledText(
            frame, bg=BG2, fg=TEXT, font=("Segoe UI", 11),
            wrap="word", state="disabled", relief="flat",
            padx=14, pady=14, insertbackground=TEXT,
        )
        self.chat_display.pack(fill="both", expand=True, padx=10, pady=(10, 5))

        # Tag config for bubbles
        self.chat_display.tag_configure("user",      foreground=ACCENT,   font=("Segoe UI", 11, "bold"))
        self.chat_display.tag_configure("assistant", foreground=GREEN,    font=("Segoe UI", 11, "bold"))
        self.chat_display.tag_configure("system",    foreground=YELLOW,  font=("Segoe UI", 9, "italic"))
        self.chat_display.tag_configure("msg",       foreground=TEXT,    font=("Segoe UI", 11))

        # Input row
        input_frame = tk.Frame(frame, bg=BG)
        input_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.chat_input = tk.Entry(
            input_frame, bg=BG3, fg=TEXT, font=FONT_MAIN,
            insertbackground=TEXT, relief="flat", bd=8,
        )
        self.chat_input.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        # 🆕 सीधे self._send_text को बाइंड करें, बिना lambda के!
        self.chat_input.bind("<Return>", self._send_text)
        self.chat_input.insert(0, "Type or speak your question...")
        self.chat_input.bind("<FocusIn>", lambda e: self.chat_input.delete(0, "end")
                              if self.chat_input.get() == "Type or speak your question..." else None)

        self.mic_btn = tk.Button(
            input_frame, text="🎤", bg=ACCENT, fg="#fff",
            font=("Segoe UI", 14), relief="flat", cursor="hand2",
            width=3, command=self._toggle_listen,
        )
        self.mic_btn.pack(side="left", padx=(0, 4))

        # 🛑 शुरुआत में यह डिसेबल और ग्रे रहेगा
        self.stop_btn = tk.Button(
            input_frame, text="🛑 Stop", bg="#64748b", fg="#fff",
            font=FONT_MAIN, relief="flat", cursor="hand2",
            padx=10, command=self._stop_ai_generation,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=(0, 4))

        tk.Button(
            input_frame, text="Send ➤", bg=ACCENT2, fg="#fff",
            font=FONT_MAIN, relief="flat", cursor="hand2",
            padx=14, command=self._send_text,
        ).pack(side="left")

        # Welcome
        self._append_chat("system", "🎓 AI Student Assistant is ready!")
        self._append_chat("assistant", "Hello! I can answer questions, set reminders, manage your timetable, take notes, and summarize PDFs. How can I help?")

    def _append_chat(self, role: str, message: str):
        self.chat_display.config(state="normal")
        prefix = {"user": "You:  ", "assistant": "AI:   ", "system": ""}[role]
        if role in ("user", "assistant"):
            self.chat_display.insert("end", f"\n{prefix}", role)
            self.chat_display.insert("end", f"{message}\n", "msg")
        else:
            self.chat_display.insert("end", f"{message}\n", "system")
        self.chat_display.config(state="disabled")
        self.chat_display.see("end")

    def _send_text(self, event=None):
        text = self.chat_input.get().strip()
        if not text or text == "Type or speak your question...":
            return
            
        self.chat_input.delete(0, "end")
        
        # 🚨 थ्रेडिंग का सटीक इस्तेमाल ताकि UI हैंग न हो
        threading.Thread(target=self._process_input, args=(text,), daemon=True).start()

    def _process_input(self, text: str):
        # UI अपडेट्स को थ्रेड-सेफ तरीके से शेड्यूल करें
        self.root.after(0, lambda: self._append_chat("user", text))
        self.root.after(0, lambda: self._append_chat("system", "⏳ Thinking..."))
        
        # 🛑 क्वेश्चन एंटर होते ही बटन चमकदार लाल और एक्टिव हो जाएगा
        self.root.after(0, lambda: self.stop_btn.config(state="normal", bg=RED))
        
        self.is_first_chunk = True
        self.final_full_text = ""  # पूरा टेक्स्ट स्टोर करने के लिए

        def stream_chunks_to_ui(chunk):
            """यह फ़ंक्शन हर एक शब्द आने पर 'Thinking...' को हटाकर लाइव टेक्स्ट जोड़ेगा"""
            self.final_full_text += chunk  # शब्द दर शब्द पूरा रिस्पॉन्स जोड़ें
            
            def update_ui():
                if self.is_first_chunk:
                    self.is_first_chunk = False
                    try:
                        self.chat_display.config(state="normal")
                        self.chat_display.delete("end-2c linestart", "end")
                        self.chat_display.config(state="disabled")
                    except:
                        pass
                    self._append_chat("assistant", chunk)
                else:
                    try:
                        self.chat_display.config(state="normal")
                        self.chat_display.insert("end", chunk)
                        self.chat_display.see("end")
                        self.chat_display.config(state="disabled")
                    except:
                        self._append_chat("assistant", chunk)

            self.root.after(0, update_ui)

        try:
            from core.assistant_brain import process_command
            
            result = process_command(
                text, 
                reminder_callback=self._reminder_alert,
                update_ui_callback=stream_chunks_to_ui
            )
            
            # 🆕 बोलने वाला अचूक लॉजिक (Windows SAPI5)
            text_to_speak = ""
            if result and "response" in result and result["response"]:
                text_to_speak = result["response"]
            elif self.final_full_text:
                text_to_speak = self.final_full_text

            if text_to_speak:
                # क्लीन टेक्स्ट करें (इमोजी या स्पेशल कैरेक्टर्स हटा दें ताकि इंजन न अटके)
                clean_text = text_to_speak.replace("⏹", "").replace("⏳", "").strip()
                
                # अलग थ्रेड में बोलेंगे ताकि बोलते समय भी UI न अटके
                def speak_in_background():
                    try:
                        # Windows का डिफ़ॉल्ट वॉइस ऑब्जेक्ट हर बार नया थ्रेड में बनाना पड़ता है
                        speaker = win32com.client.Dispatch("SAPI.SpVoice")
                        speaker.Speak(clean_text)
                    except Exception as speech_err:
                        print(f"Speech Error: {speech_err}")
                
                threading.Thread(target=speak_in_background, daemon=True).start()

            if self.is_first_chunk:
                self.root.after(0, lambda: self._show_response(result))
                
        except Exception as e:
            self.root.after(0, lambda: self._append_chat("system", f"Error: {str(e)}"))
        finally:
            # 💤 जवाब आने के बाद बटन वापस डिसेबल
            self.root.after(0, lambda: self.stop_btn.config(state="disabled", bg="#64748b"))
    
    def _stop_ai_generation(self):
        """जब यूज़र Stop बटन दबाएगा"""
        from core import assistant_brain
        assistant_brain.interrupt_generation()  # बैकएंड को रोकने का इशारा भेजें
        self._set_status("🛑 Generation stopped by user.")
        # बटन को तुरंत डिसेबल और ग्रे कर दें
        self.stop_btn.config(state="disabled", bg="#64748b")

    def _show_response(self, result: dict):
        # Remove "Thinking..." line
        self.chat_display.config(state="normal")
        content = self.chat_display.get("1.0", "end")
        if "⏳ Thinking..." in content:
            idx = content.rfind("⏳ Thinking...")
            line_start = content[:idx].count("\n") + 1
            self.chat_display.delete(f"{line_start}.0", f"{line_start}.end+1c")
        self.chat_display.config(state="disabled")

        self._append_chat("assistant", result["response"])

        # Speak the response
        threading.Thread(
            target=self.voice.speak, args=(result["response"],), daemon=True
        ).start()

        # Refresh relevant tab
        action = result.get("action", "")
        if "reminder" in action:   self._refresh_reminders()
        if "class"    in action:   self._refresh_timetable()
        if "note"     in action:   self._refresh_notes()

        self._set_status(f"Intent: {result['intent']} | Action: {action}")

    def _trigger_speech(self, text_):
        """यह फ़ंक्शन बिना UI को अटकाए आवाज़ को चालू करेगा"""
        try:
            # अगर आपकी फ़ाइल में self._speak फ़ंक्शन है
            if hasattr(self, '_speak'):
                self._speak(text_)
            # अगर आपके पास voice_engine नाम का मॉड्यूल इम्पोर्टेड है
            elif 'voice_engine' in globals():
                globals()['voice_engine'].speak(text_)
        except Exception as msg:
            print(f"Speech Trigger Error: {msg}")
    
    def _toggle_listen(self):
        if self.is_listening:
            self.is_listening = False
            self.mic_btn.config(bg=ACCENT, text="🎤")
            return
        self.is_listening = True
        self.mic_btn.config(bg=RED, text="⏹")
        self._append_chat("system", "🎤 Listening...")

        def _listen():
            text = self.voice.listen(timeout=6)
            self.is_listening = False
            self.root.after(0, lambda: self.mic_btn.config(bg=ACCENT, text="🎤"))
            if text:
                self.root.after(0, lambda: self._process_input(text))
            else:
                self.root.after(0, lambda: self._append_chat("system", "❌ Could not hear. Try again."))

        threading.Thread(target=_listen, daemon=True).start()

    # ── [बाकी का Timetable, Notes, Reminders, PDF और Status Bar का कोड वैसा ही रहेगा] ──
    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 2: TIMETABLE
    # ═══════════════════════════════════════════════════════════════════════════
    def _build_timetable_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📅 Timetable")

        form = tk.Frame(frame, bg=BG2, pady=10)
        form.pack(fill="x", padx=10, pady=(10, 5))

        tk.Label(form, text="Subject:", bg=BG2, fg=TEXT).grid(row=0, column=0, padx=8, pady=4, sticky="w")
        self.tt_subject = tk.Entry(form, bg=BG3, fg=TEXT, width=16, font=FONT_MAIN, insertbackground=TEXT, relief="flat", bd=5)
        self.tt_subject.grid(row=0, column=1, padx=4)

        tk.Label(form, text="Day:", bg=BG2, fg=TEXT).grid(row=0, column=2, padx=8, sticky="w")
        self.tt_day = ttk.Combobox(form, values=[d.capitalize() for d in DAYS], width=12, state="readonly")
        self.tt_day.set("Monday")
        self.tt_day.grid(row=0, column=3, padx=4)

        tk.Label(form, text="Time:", bg=BG2, fg=TEXT).grid(row=0, column=4, padx=8, sticky="w")
        self.tt_time = tk.Entry(form, bg=BG3, fg=TEXT, width=14, font=FONT_MAIN, insertbackground=TEXT, relief="flat", bd=5)
        self.tt_time.insert(0, "9:00 AM")
        self.tt_time.grid(row=0, column=5, padx=4)

        tk.Button(form, text="+ Add Class", bg=GREEN, fg="#000", font=("Segoe UI", 10, "bold"),
                   relief="flat", cursor="hand2", padx=10, command=self._add_class_ui).grid(row=0, column=6, padx=10)

        self.tt_text = scrolledtext.ScrolledText(
            frame, bg=BG2, fg=TEXT, font=("Consolas", 11),
            state="disabled", relief="flat", padx=12, pady=12,
        )
        self.tt_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _add_class_ui(self):
        subject = self.tt_subject.get().strip()
        day     = self.tt_day.get().strip()
        time_s  = self.tt_time.get().strip()
        if not subject:
            messagebox.showwarning("Missing", "Enter subject name!")
            return
        result = add_class(subject, day, time_s)
        if result["success"]:
            self._refresh_timetable()
            self.tt_subject.delete(0, "end")
            self._set_status(f"Class added: {subject} on {day}")
        else:
            messagebox.showerror("Error", result.get("error", "Could not add class"))

    def _refresh_timetable(self):
        tt = get_full_timetable()
        lines = []
        for day in DAYS:
            classes = tt.get(day, [])
            if classes:
                lines.append(f"\n{'━'*40}")
                lines.append(f"  {day.upper()}")
                lines.append(f"{'━'*40}")
                for c in classes:
                    teacher = f"  [{c['teacher']}]" if c.get("teacher") else ""
                    lines.append(f"  {c['time']:20s}  {c['subject']}{teacher}")
        text = "\n".join(lines) if lines else "\n  No classes added yet.\n  Use the form above or say:\n  'Add Physics class on Monday at 10 AM'"
        self.tt_text.config(state="normal")
        self.tt_text.delete("1.0", "end")
        self.tt_text.insert("1.0", text)
        self.tt_text.config(state="disabled")

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 3: NOTES
    # ═══════════════════════════════════════════════════════════════════════════
    def _build_notes_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📝 Notes")

        left = tk.Frame(frame, bg=BG2, width=260)
        left.pack(side="left", fill="y", padx=(10, 0), pady=10)
        left.pack_propagate(False)

        tk.Label(left, text="Your Notes", bg=BG2, fg=TEXT, font=FONT_BIG).pack(pady=8)

        self.notes_listbox = tk.Listbox(
            left, bg=BG3, fg=TEXT, font=FONT_MAIN,
            selectbackground=ACCENT, relief="flat", bd=0,
        )
        self.notes_listbox.pack(fill="both", expand=True, padx=6, pady=4)
        self.notes_listbox.bind("<<ListboxSelect>>", self._on_note_select)

        right = tk.Frame(frame, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.note_detail = scrolledtext.ScrolledText(
            right, bg=BG2, fg=TEXT, font=("Segoe UI", 11),
            wrap="word", relief="flat", padx=12, pady=12,
        )
        self.note_detail.pack(fill="both", expand=True)

        add_frame = tk.Frame(right, bg=BG)
        add_frame.pack(fill="x", pady=(6, 0))

        self.note_input = tk.Entry(add_frame, bg=BG3, fg=TEXT, font=FONT_MAIN,
                                    insertbackground=TEXT, relief="flat", bd=6)
        self.note_input.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.note_input.insert(0, "Quick note (type and press Enter)...")
        self.note_input.bind("<FocusIn>", lambda e: self.note_input.delete(0, "end")
                              if "Quick note" in self.note_input.get() else None)
        self.note_input.bind("<Return>", self._quick_save_note)

        tk.Button(add_frame, text="Save", bg=ACCENT, fg="#fff", font=FONT_MAIN,
                   relief="flat", cursor="hand2", padx=12,
                   command=self._quick_save_note).pack(side="left")

        self._note_ids = []

    def _quick_save_note(self, event=None):
        from core.notes import save_note, enhance_note_with_ai
        text = self.note_input.get().strip()
        if not text or "Quick note" in text:
            return

        def _run():
            enhanced = enhance_note_with_ai(text)
            save_note(enhanced)
            self.root.after(0, self._refresh_notes)
            self.root.after(0, lambda: self.note_input.delete(0, "end"))

        threading.Thread(target=_run, daemon=True).start()
        self._set_status("Saving note with AI formatting...")

    def _refresh_notes(self):
        notes = get_all_notes(limit=30)
        self.notes_listbox.delete(0, "end")
        self._note_ids = []
        for n in notes:
            self.notes_listbox.insert("end", f"[{n['subject']}] {n['title'][:30]}")
            self._note_ids.append(n["id"])

    def _on_note_select(self, event):
        sel = self.notes_listbox.curselection()
        if not sel:
            return
        note_id = self._note_ids[sel[0]]
        note    = get_note(note_id)
        if note:
            self.note_detail.config(state="normal")
            self.note_detail.delete("1.0", "end")
            dt = datetime.fromisoformat(note["created"]).strftime("%d %b %Y, %I:%M %p")
            self.note_detail.insert("end",
                f"📌 {note['title']}\n"
                f"Subject: {note['subject']}  |  {dt}\n"
                f"{'─'*40}\n\n"
                f"{note['content']}"
            )
            self.note_detail.config(state="disabled")

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 4: REMINDERS
    # ═══════════════════════════════════════════════════════════════════════════
    def _build_reminders_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🔔 Reminders")

        form = tk.Frame(frame, bg=BG2, pady=10)
        form.pack(fill="x", padx=10, pady=(10, 5))

        tk.Label(form, text="Task:", bg=BG2, fg=TEXT).grid(row=0, column=0, padx=8, sticky="w")
        self.rem_task = tk.Entry(form, bg=BG3, fg=TEXT, width=30, font=FONT_MAIN,
                                  insertbackground=TEXT, relief="flat", bd=5)
        self.rem_task.grid(row=0, column=1, padx=4)

        tk.Label(form, text="Time:", bg=BG2, fg=TEXT).grid(row=0, column=2, padx=8, sticky="w")
        self.rem_time = tk.Entry(form, bg=BG3, fg=TEXT, width=14, font=FONT_MAIN,
                                  insertbackground=TEXT, relief="flat", bd=5)
        self.rem_time.insert(0, "5:00 PM")
        self.rem_time.grid(row=0, column=3, padx=4)

        tk.Button(form, text="+ Set Reminder", bg=YELLOW, fg="#000",
                   font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
                   padx=10, command=self._set_reminder_ui).grid(row=0, column=4, padx=10)

        self.rem_text = scrolledtext.ScrolledText(
            frame, bg=BG2, fg=TEXT, font=("Segoe UI", 12),
            state="disabled", relief="flat", padx=14, pady=14,
        )
        self.rem_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _set_reminder_ui(self):
        from core.reminder import add_reminder
        task = self.rem_task.get().strip()
        time_s = self.rem_time.get().strip()
        if not task:
            messagebox.showwarning("Missing", "Enter a task!")
            return
        result = add_reminder(task, time_s, callback=self._reminder_alert)
        if result["success"]:
            self._refresh_reminders()
            self.rem_task.delete(0, "end")
            self._set_status(f"Reminder set: {task} at {result['time']}")
        else:
            messagebox.showerror("Error", result.get("error", "Could not set reminder"))

    def _refresh_reminders(self):
        reminders = get_reminders()
        text = format_reminders_text(reminders)
        self.rem_text.config(state="normal")
        self.rem_text.delete("1.0", "end")
        self.rem_text.insert("1.0", text)
        self.rem_text.config(state="disabled")

    def _reminder_alert(self, message: str):
        self.root.after(0, lambda: messagebox.showinfo("🔔 Reminder!", message))
        self.root.after(0, lambda: self._refresh_reminders())
        threading.Thread(
            target=self.voice.speak,
            args=(f"Reminder! {message}",),
            daemon=True,
        ).start()

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 5: PDF
    # ═══════════════════════════════════════════════════════════════════════════
    def _build_pdf_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📄 PDF Summarizer")

        top = tk.Frame(frame, bg=BG2, pady=12)
        top.pack(fill="x", padx=10, pady=(10, 5))

        tk.Button(top, text="📂 Browse PDF", bg=ACCENT, fg="#fff",
                   font=FONT_BIG, relief="flat", cursor="hand2",
                   padx=18, command=self._browse_pdf).pack(side="left", padx=10)

        self.pdf_label = tk.Label(top, text="No PDF loaded", bg=BG2, fg=TEXT_DIM, font=FONT_SM)
        self.pdf_label.pack(side="left", padx=10)

        self.pdf_output = scrolledtext.ScrolledText(
            frame, bg=BG2, fg=TEXT, font=("Segoe UI", 11),
            wrap="word", state="disabled", relief="flat", padx=14, pady=14,
        )
        self.pdf_output.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        qa_frame = tk.Frame(frame, bg=BG)
        qa_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.pdf_q_input = tk.Entry(qa_frame, bg=BG3, fg=TEXT, font=FONT_MAIN,
                                     insertbackground=TEXT, relief="flat", bd=6)
        self.pdf_q_input.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.pdf_q_input.insert(0, "Ask a question about the PDF...")
        self.pdf_q_input.bind("<FocusIn>", lambda e: self.pdf_q_input.delete(0, "end")
                               if "Ask a question" in self.pdf_q_input.get() else None)
        self.pdf_q_input.bind("<Return>", self._ask_pdf_question)

        tk.Button(qa_frame, text="Ask", bg=ACCENT2, fg="#fff", font=FONT_MAIN,
                   relief="flat", cursor="hand2", padx=14,
                   command=self._ask_pdf_question).pack(side="left")

    def _browse_pdf(self):
        path = filedialog.askopenfilename(
            title="Select PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if not path:
            return

        self.pdf_label.config(text="⏳ Loading...", fg=YELLOW)
        self._pdf_output("Loading and summarizing PDF. Please wait...\n")

        def _run():
            result = load_pdf_context(path)
            self.root.after(0, lambda: self._show_pdf_result(result))

        threading.Thread(target=_run, daemon=True).start()

    def _show_pdf_result(self, result: dict):
        if result["success"]:
            self.pdf_label.config(
                text=f"✅ {result['file_name']}  ({result['page_count']} pages, {result['word_count']} words)",
                fg=GREEN
            )
            self._pdf_output(f"📄 {result['file_name']}\n{'─'*50}\n\n{result['summary']}")
            self.pdf_loaded = True
            threading.Thread(
                target=self.voice.speak,
                args=("PDF loaded. Summary is ready. You can now ask questions about it.",),
                daemon=True,
            ).start()
        else:
            self.pdf_label.config(text=f"❌ {result['error']}", fg=RED)

    def _ask_pdf_question(self, event=None):
        q = self.pdf_q_input.get().strip()
        if not q or "Ask a question" in q:
            return
        if not self.pdf_loaded:
            messagebox.showinfo("No PDF", "Please load a PDF first!")
            return
        self.pdf_q_input.delete(0, "end")
        self._pdf_output(f"\n\nYou: {q}\n")

        def _run():
            result = process_command(q)
            self.root.after(0, lambda: self._pdf_output(f"AI: {result['response']}\n"))
            threading.Thread(target=self.voice.speak, args=(result["response"],), daemon=True).start()

        threading.Thread(target=_run, daemon=True).start()

    def _pdf_output(self, text: str):
        self.pdf_output.config(state="normal")
        if text.startswith("Loading"):
            self.pdf_output.delete("1.0", "end")
        self.pdf_output.insert("end", text)
        self.pdf_output.see("end")
        self.pdf_output.config(state="disabled")

    # ── Status bar ───────────────────────────────────────────────────────────
    def _build_status_bar(self):
        self.status_var = tk.StringVar(value="Ready")
        bar = tk.Label(self.root, textvariable=self.status_var,
                        bg=BG3, fg=TEXT_DIM, font=FONT_SM,
                        anchor="w", padx=12, pady=4)
        bar.pack(fill="x", side="bottom")

    def _set_status(self, msg: str):
        self.status_var.set(f"  {msg}")

    def _refresh_all(self):
        self._refresh_timetable()
        self._refresh_notes()
        self._refresh_reminders()


# ── Entry point ──────────────────────────────────────────────────────────────
def main():
    root = tk.Tk()
    app  = StudentAssistantApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()