__version__ = "1.0.0"

import json
import os
import threading
import urllib.request
import urllib.error

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.utils import get_color_from_hex

BG = "#101116"
PANEL = "#1B1D25"
GOLD = "#E7BD67"
WHITE = "#F5F5F7"
MUTED = "#A7A9B4"

def color(hex_color):
    return get_color_from_hex(hex_color)

class OmnixApp(App):
    def build(self):
        self.title = "GAMMA OMNIX AI"
        Window.clearcolor = color(BG)
        self.store = os.path.join(self.user_data_dir, "omnix_data.json")
        self.data = self.load_data()
        self.busy = False
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        header = BoxLayout(size_hint_y=None, height=dp(62), spacing=dp(8))
        brand = BoxLayout(orientation="vertical")
        brand.add_widget(Label(text="[b]GAMMA OMNIX[/b]", markup=True, color=color(GOLD), font_size="21sp", halign="left"))
        brand.add_widget(Label(text="YOUR IDEAS. YOUR INTELLIGENCE.", color=color(MUTED), font_size="10sp", halign="left"))
        settings_btn = Button(text="SETTINGS", size_hint_x=None, width=dp(95), background_normal="", background_color=color(PANEL), color=color(GOLD))
        settings_btn.bind(on_release=self.show_settings)
        header.add_widget(brand); header.add_widget(settings_btn); root.add_widget(header)
        self.status = Label(text="● OFFLINE MODE", size_hint_y=None, height=dp(24), color=color(MUTED), font_size="11sp", halign="left")
        root.add_widget(self.status)
        self.scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        self.chat = GridLayout(cols=1, spacing=dp(10), padding=dp(3), size_hint_y=None)
        self.chat.bind(minimum_height=self.chat.setter("height"))
        self.scroll.add_widget(self.chat); root.add_widget(self.scroll)
        composer = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(7))
        self.message = TextInput(hint_text="Ask OMNIX anything...", multiline=False, background_normal="", background_active="", background_color=color(PANEL), foreground_color=color(WHITE), hint_text_color=color(MUTED), cursor_color=color(GOLD), padding=[dp(12), dp(15), dp(8), dp(8)], font_size="15sp")
        self.message.bind(on_text_validate=self.send_message)
        send_btn = Button(text="SEND", size_hint_x=None, width=dp(75), background_normal="", background_color=color(GOLD), color=color(BG), bold=True)
        send_btn.bind(on_release=self.send_message)
        composer.add_widget(self.message); composer.add_widget(send_btn); root.add_widget(composer)
        bottom = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
        clear_btn = Button(text="CLEAR CHAT", background_normal="", background_color=color(PANEL), color=color(MUTED))
        clear_btn.bind(on_release=self.confirm_clear); bottom.add_widget(clear_btn); root.add_widget(bottom)
        self.refresh_chat(); self.update_status()
        return root

    def load_data(self):
        try:
            with open(self.store, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict): raise ValueError("Invalid data")
            data.setdefault("history", []); data.setdefault("api_key", ""); data.setdefault("model", "gemini-2.5-flash")
            return data
        except (OSError, ValueError, AttributeError):
            return {"history": [], "api_key": "", "model": "gemini-2.5-flash"}

    def save_data(self):
        try:
            os.makedirs(self.user_data_dir, exist_ok=True)
            with open(self.store, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except OSError:
            self.status.text = "Could not save local data"

    def update_status(self):
        if self.data.get("api_key", "").strip():
            self.status.text = "● GEMINI CONFIGURED — CHECK INTERNET"; self.status.color = color(GOLD)
        else:
            self.status.text = "● OFFLINE MODE — ADD API KEY IN SETTINGS"; self.status.color = color(MUTED)

    def refresh_chat(self):
        self.chat.clear_widgets()
        history = self.data.get("history", [])
        if not history:
            self.add_bubble("OMNIX", "Welcome to GAMMA OMNIX AI.\n\nYour personal AI workspace starts here. Add a Gemini API key in Settings for online answers.", False)
        else:
            for item in history[-60:]:
                self.add_bubble("YOU" if item.get("role") == "user" else "OMNIX", item.get("text", ""), item.get("role") == "user")
        Clock.schedule_once(lambda dt: setattr(self.scroll, "scroll_y", 0), 0.1)

    def add_bubble(self, speaker, text, is_user):
        outer = BoxLayout(orientation="vertical", size_hint_y=None, padding=[dp(10), dp(7)])
        outer.bind(minimum_height=outer.setter("height"))
        title = Label(text=speaker, size_hint_y=None, height=dp(20), color=color(GOLD if not is_user else "#91B9FF"), font_size="11sp", bold=True, halign="left", valign="middle")
        title.bind(size=lambda w, s: setattr(w, "text_size", s))
        body = Label(text=text, size_hint_y=None, color=color(WHITE), font_size="14sp", halign="left", valign="top")
        body.bind(width=lambda w, width: setattr(w, "text_size", (width, None)), texture_size=lambda w, size: setattr(w, "height", size[1] + dp(8)))
        body.height = dp(35)
        outer.add_widget(title); outer.add_widget(body)
        from kivy.graphics import Color, RoundedRectangle
        with outer.canvas.before:
            Color(*color("#252731" if is_user else PANEL))
            rect = RoundedRectangle(pos=outer.pos, size=outer.size, radius=[dp(12)])
        outer.bind(pos=lambda w, p: setattr(rect, "pos", p)); outer.bind(size=lambda w, s: setattr(rect, "size", s))
        self.chat.add_widget(outer)

    def send_message(self, *args):
        message = self.message.text.strip()
        if not message or self.busy: return
        self.message.text = ""
        self.data.setdefault("history", []).append({"role": "user", "text": message})
        self.save_data(); self.refresh_chat()
        self.busy = True; self.status.text = "● OMNIX IS THINKING..."; self.status.color = color(GOLD)
        threading.Thread(target=self.get_answer, args=(message,), daemon=True).start()

    def get_answer(self, message):
        key = self.data.get("api_key", "").strip()
        model = self.data.get("model", "gemini-2.5-flash").strip()
        answer = ""
        if key:
            try:
                history = self.data.get("history", [])[:-1]
                contents = []
                for item in history[-12:]:
                    role = "user" if item.get("role") == "user" else "model"
                    contents.append({"role": role, "parts": [{"text": item.get("text", "")}]})
                contents.append({"role": "user", "parts": [{"text": message}]})
                payload = {"system_instruction": {"parts": [{"text": "You are GAMMA OMNIX AI, a helpful, honest, creative assistant. Give clear answers and explain limitations honestly."}]}, "contents": contents, "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1200}}
                url = "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent"
                request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json", "x-goog-api-key": key}, method="POST")
                with urllib.request.urlopen(request, timeout=45) as response:
                    result = json.loads(response.read().decode("utf-8"))
                candidates = result.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    answer = "\n".join(p.get("text", "") for p in parts if p.get("text"))
                if not answer: answer = "The AI returned no text. Please try again."
            except urllib.error.HTTPError as exc:
                answer = "Gemini request failed (HTTP {}). Check the API key, model and quota in Settings.".format(exc.code)
            except Exception as exc:
                answer = "Connection failed: {}. Check your internet and model settings.".format(exc)
        else:
            answer = self.offline_reply(message)
        Clock.schedule_once(lambda dt: self.finish_answer(answer), 0)

    def offline_reply(self, message):
        text = message.lower()
        if any(w in text for w in ("hello", "hi", "hey")): return "Hello! I am GAMMA OMNIX AI. What shall we create today?"
        if "your name" in text or "who are you" in text: return "I am GAMMA OMNIX AI, your experimental personal assistant."
        if "date" in text:
            from datetime import datetime
            return "Device date: " + datetime.now().strftime("%d %B %Y")
        if "python" in text: return "Python can power AI, automation, software and data processing."
        if "gamma" in text: return "GAMMA is your technology ecosystem for AI, smart systems, robotics and future inventions."
        return "Offline mode is active, so my answers are limited. Open Settings to configure Gemini for online AI responses."

    def finish_answer(self, answer):
        self.data.setdefault("history", []).append({"role": "assistant", "text": answer})
        self.data["history"] = self.data["history"][-200:]
        self.save_data(); self.busy = False; self.refresh_chat(); self.update_status()

    def show_settings(self, *args):
        panel = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(14))
        panel.add_widget(Label(text="OMNIX SETTINGS", color=color(GOLD), font_size="19sp", size_hint_y=None, height=dp(35)))
        panel.add_widget(Label(text="Gemini API key (stored locally on this device)", color=color(WHITE), size_hint_y=None, height=dp(35)))
        key_input = TextInput(text=self.data.get("api_key", ""), hint_text="Paste API key", password=True, multiline=False, size_hint_y=None, height=dp(45))
        panel.add_widget(key_input)
        panel.add_widget(Label(text="Model name", color=color(WHITE), size_hint_y=None, height=dp(25)))
        model_input = TextInput(text=self.data.get("model", "gemini-2.5-flash"), multiline=False, size_hint_y=None, height=dp(42))
        panel.add_widget(model_input)
        buttons = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(8))
        save_btn = Button(text="SAVE", background_normal="", background_color=color(GOLD), color=color(BG))
        cancel_btn = Button(text="CANCEL", background_normal="", background_color=color(PANEL))
        buttons.add_widget(save_btn); buttons.add_widget(cancel_btn); panel.add_widget(buttons)
        popup = Popup(title="", content=panel, size_hint=(0.94, 0.72), auto_dismiss=True)
        def save_settings(*args):
            self.data["api_key"] = key_input.text.strip()
            self.data["model"] = model_input.text.strip() or "gemini-2.5-flash"
            self.save_data(); self.update_status(); popup.dismiss()
        save_btn.bind(on_release=save_settings); cancel_btn.bind(on_release=popup.dismiss); popup.open()

    def confirm_clear(self, *args):
        panel = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(12))
        panel.add_widget(Label(text="Delete the saved conversation?", color=color(WHITE)))
        buttons = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        yes = Button(text="CLEAR", background_color=color(GOLD)); no = Button(text="CANCEL")
        buttons.add_widget(yes); buttons.add_widget(no); panel.add_widget(buttons)
        popup = Popup(title="Clear chat", content=panel, size_hint=(0.86, 0.35))
        def clear(*args):
            self.data["history"] = []; self.save_data(); self.refresh_chat(); popup.dismiss()
        yes.bind(on_release=clear); no.bind(on_release=popup.dismiss); popup.open()

if __name__ == "__main__":
    OmnixApp().run()
