"""
voice_engine.py
Speech-to-Text (mic se suno) + Text-to-Speech (bol ke batao)
Libraries: SpeechRecognition, pyttsx3
"""

import pyttsx3
import speech_recognition as sr
import threading


class VoiceEngine:
    def __init__(self):
        # TTS setup
        self.engine = pyttsx3.init()
        self._configure_tts()

        # STT setup
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 3000
        self.recognizer.pause_threshold = 0.8
        self.is_listening = False

    # ── TTS Config ──────────────────────────────────────────────────────────
    def _configure_tts(self):
        voices = self.engine.getProperty('voices')
        # Female voice prefer karo agar available ho
        for voice in voices:
            if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break
        self.engine.setProperty('rate', 165)   # speed
        self.engine.setProperty('volume', 0.95)

    def speak(self, text: str):
        """Text ko voice mein convert karo (blocking)"""
        print(f"[Assistant]: {text}")
        self.engine.say(text)
        self.engine.runAndWait()

    def speak_async(self, text: str):
        """Background mein bolo (non-blocking)"""
        t = threading.Thread(target=self.speak, args=(text,), daemon=True)
        t.start()

    # ── STT ─────────────────────────────────────────────────────────────────
    def listen(self, timeout: int = 5, phrase_limit: int = 10) -> str | None:
        """
        Mic se suno aur text return karo.
        Returns None agar kuch samajh na aaye.
        """
        with sr.Microphone() as source:
            print("[Listening...]")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = self.recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_limit
                )
                text = self.recognizer.recognize_google(audio, language='en-IN')
                print(f"[You said]: {text}")
                return text.strip()
            except sr.WaitTimeoutError:
                return None
            except sr.UnknownValueError:
                return None
            except sr.RequestError as e:
                print(f"[STT Error]: {e}")
                return None

    def listen_continuous(self, callback):
        """
        Background mein continuously suno.
        callback(text) ko call karta hai jab bhi kuch suna.
        """
        self.is_listening = True

        def _loop():
            while self.is_listening:
                result = self.listen()
                if result:
                    callback(result)

        t = threading.Thread(target=_loop, daemon=True)
        t.start()

    def stop_listening(self):
        self.is_listening = False


# ── Quick test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ve = VoiceEngine()
    ve.speak("Hello! Main tumhara AI student assistant hoon. Bolo kya madad chahiye?")
    text = ve.listen()
    if text:
        ve.speak(f"Tumne kaha: {text}")
    else:
        ve.speak("Mujhe kuch samajh nahi aaya, phir se bolna.")