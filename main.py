import os
import random
import shutil
import unicodedata
import webbrowser
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex as hexc
from kivy.utils import platform

from words import EASY_LIST, MEDIUM_LIST, HARD_LIST

PDF_FILENAME = "mehmet_olmez_etimoloji_sozlukleri.pdf"

# Klavye açılınca giriş kutusu ekranda kalsın
Window.softinput_mode = "below_target"

# Bilgisayarda test ederken telefon oranında pencere
if platform not in ("android", "ios"):
    Window.size = (400, 720)

LIGHT = {"bg": "#f4f4f9", "card": "#ffffff", "fg": "#000000",
         "btn": "#e0e0e0", "mode_text": "Koyu Mod"}
DARK = {"bg": "#121212", "card": "#1e1e1e", "fg": "#ffffff",
        "btn": "#2d2d2d", "mode_text": "Açık Mod"}


# ---------------------------------------------------------------- Yardımcılar
def tr_lower(text):
    """Türkçe uyumlu küçük harfe çevirme (I -> ı, İ -> i)."""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("İ", "i").replace("I", "ı")
    return text.lower().strip()


def resource_path(name):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)


def shade(hex_color, factor):
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return "#{:02x}{:02x}{:02x}".format(int(r * factor), int(g * factor), int(b * factor))


class FillLabel(Label):
    """Verilen alanı dolduran, yazıyı kaydıran etiket."""

    def __init__(self, **kw):
        kw.setdefault("halign", "center")
        kw.setdefault("valign", "middle")
        super().__init__(**kw)
        self.bind(size=lambda *_: setattr(self, "text_size", self.size))


class WrapLabel(Label):
    """Genişliğe göre satır kaydıran, yüksekliği yazıya göre ayarlanan etiket."""

    def __init__(self, **kw):
        kw.setdefault("halign", "center")
        kw.setdefault("valign", "middle")
        kw["size_hint_y"] = None
        super().__init__(**kw)
        self.bind(width=lambda *_: setattr(self, "text_size", (self.width, None)))
        self.bind(texture_size=lambda *_: setattr(self, "height", self.texture_size[1] + dp(6)))


class Card(BoxLayout):
    """Yuvarlak köşeli, arka plan renkli kart."""

    def __init__(self, bg_hex, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            Color(*hexc(bg_hex))
            self._rect = RoundedRectangle(radius=[dp(12)])
        self.bind(pos=self._update, size=self._update)

    def _update(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size


# ---------------------------------------------------------------------- Uygulama
class EtimokartApp(App):
    title = "ETİMOKART"

    def build(self):
        self.dark_mode = False
        self.apply_colors()

        self.anim_size = 26
        self.anim_growing = True
        self.anim_event = None
        self.title_label = None

        self.game_level = None
        self.lives_enabled = True
        self.lives = 0
        self.current_pool = []
        self.current_item = None
        self.steps = []
        self.target_word = ""
        self.hint_used = False
        self.saved_guess = ""
        self.guess_input = None

        self._popup = None
        self.back_func = None
        self.current_screen_func = None

        self.root_box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        Window.bind(on_keyboard=self.on_keyboard)

        self.show_main_screen()
        return self.root_box

    def on_pause(self):
        return True

    # ----------------------------------------------------------------- Tema
    def apply_colors(self):
        self.c = DARK if self.dark_mode else LIGHT
        self.fg = hexc(self.c["fg"])
        Window.clearcolor = hexc(self.c["bg"])

    def toggle_theme(self):
        self.saved_guess = ""
        if self.guess_input is not None and self.guess_input.parent is not None:
            self.saved_guess = self.guess_input.text
        self.dark_mode = not self.dark_mode
        self.apply_colors()
        if self.current_screen_func:
            self.current_screen_func()

    # ------------------------------------------------------------- Bileşenler
    def make_btn(self, text, bg, command, fg="#ffffff", height=48, font=16, **kw):
        btn = Button(text=text, bold=True, font_size=sp(font),
                     background_normal="", background_down="",
                     background_color=hexc(bg), color=hexc(fg),
                     size_hint_y=None, height=dp(height), **kw)
        normal, pressed = hexc(bg), hexc(shade(bg, 0.8))

        def on_state(widget, state):
            widget.background_color = pressed if state == "down" else normal

        btn.bind(state=on_state)
        btn.bind(on_release=lambda *_: command())
        return btn

    def clear_container(self):
        if self.anim_event is not None:
            self.anim_event.cancel()
            self.anim_event = None
        self.title_label = None
        self.guess_input = None
        self.root_box.clear_widgets()

    def add_top_bar(self, back_text=None, back_func=None):
        bar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        if back_text and back_func:
            bar.add_widget(self.make_btn(back_text, "#e74c3c", back_func, height=44, font=14,
                                         size_hint_x=None, width=dp(130)))
        bar.add_widget(Widget())
        bar.add_widget(self.make_btn(self.c["mode_text"], self.c["btn"], self.toggle_theme,
                                     fg=self.c["fg"], height=44, font=14,
                                     size_hint_x=None, width=dp(120)))
        self.root_box.add_widget(bar)

    def screen(self, func, back=None):
        """Ortak ekran hazırlığı: tema yenilemesi ve geri tuşu için kayıt."""
        self.current_screen_func = func
        self.back_func = back
        self.clear_container()

    # --------------------------------------------------------------- Mesajlar
    def _close_popup(self):
        if self._popup is not None:
            self._popup.dismiss()
            self._popup = None

    def show_message(self, title, text, on_close=None, ok_text="Tamam", ok_color="#2196F3"):
        if self._popup is not None:
            return
        content = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(12))
        content.add_widget(FillLabel(text=text, font_size=sp(17)))

        def close():
            self._close_popup()
            if on_close:
                Clock.schedule_once(lambda dt: on_close(), 0)

        content.add_widget(self.make_btn(ok_text, ok_color, close))
        self._popup = Popup(title=title, content=content, size_hint=(0.88, None),
                            height=dp(250), auto_dismiss=False, title_align="center")
        self._popup.open()

    def ask_yes_no(self, title, text, on_yes):
        if self._popup is not None:
            return
        content = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(12))
        content.add_widget(FillLabel(text=text, font_size=sp(17)))
        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))

        def yes():
            self._close_popup()
            Clock.schedule_once(lambda dt: on_yes(), 0)

        row.add_widget(self.make_btn("Evet", "#4CAF50", yes))
        row.add_widget(self.make_btn("Hayır", "#e74c3c", self._close_popup))
        content.add_widget(row)
        self._popup = Popup(title=title, content=content, size_hint=(0.88, None),
                            height=dp(230), auto_dismiss=False, title_align="center")
        self._popup.open()

    def on_keyboard(self, window, key, *args):
        # 27 = Android geri tuşu / Esc
        if key == 27:
            if self._popup is not None:
                return True
            if self.back_func:
                self.back_func()
                return True
            return False
        return False

    # ----------------------------------------------------------------- Ekranlar
    def show_main_screen(self):
        self.screen(self.show_main_screen)
        self.add_top_bar()
        self.root_box.add_widget(Widget())

        self.title_label = Label(text="ETİMOKART", bold=True, color=self.fg,
                                 font_size=sp(self.anim_size), size_hint_y=None, height=dp(110))
        self.root_box.add_widget(self.title_label)

        self.root_box.add_widget(self.make_btn("Oyna", "#2196F3", self.show_difficulty_selection,
                                               height=54, font=18, size_hint_x=0.8,
                                               pos_hint={"center_x": 0.5}))
        self.root_box.add_widget(self.make_btn("Kaynakça", "#78909C", self.show_references,
                                               height=54, font=18, size_hint_x=0.8,
                                               pos_hint={"center_x": 0.5}))
        self.root_box.add_widget(Widget())
        self.anim_event = Clock.schedule_interval(self.animate_title, 0.2)

    def animate_title(self, dt):
        if self.title_label is None:
            return False
        if self.anim_growing:
            self.anim_size += 1
            if self.anim_size >= 32:
                self.anim_growing = False
        else:
            self.anim_size -= 1
            if self.anim_size <= 24:
                self.anim_growing = True
        self.title_label.font_size = sp(self.anim_size)
        return True

    def show_references(self):
        self.screen(self.show_references, back=self.show_main_screen)
        self.add_top_bar("← Geri", self.show_main_screen)

        self.root_box.add_widget(WrapLabel(text="Kaynakça", bold=True, font_size=sp(22), color=self.fg))

        card = Card(self.c["card"], orientation="vertical", padding=dp(14), spacing=dp(12))
        for url in ("https://www.etimolojiturkce.com/", "https://www.nisanyansozluk.com/"):
            link = WrapLabel(text=f"[ref={url}][u]{url}[/u][/ref]", markup=True,
                             font_size=sp(15), color=self.fg)
            link.bind(on_ref_press=lambda inst, ref: self.open_url(ref))
            card.add_widget(link)

        card.add_widget(WrapLabel(text=PDF_FILENAME, bold=True, font_size=sp(13), color=self.fg))
        card.add_widget(self.make_btn("PDF'i İndir", "#3498db", self.download_pdf, height=46))
        card.add_widget(Widget())
        self.root_box.add_widget(card)

    def open_url(self, url):
        try:
            if platform == "android":
                from jnius import autoclass
                Intent = autoclass("android.content.Intent")
                Uri = autoclass("android.net.Uri")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                PythonActivity.mActivity.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
            else:
                webbrowser.open(url)
        except Exception as e:
            self.show_message("Hata", f"Bağlantı açılamadı:\n{url}\n{e}")

    # --------------------------------------------------------------------- PDF
    def download_pdf(self):
        source = resource_path(PDF_FILENAME)
        if not os.path.isfile(source):
            self.show_message("Hata", f"'{PDF_FILENAME}' dosyası uygulamaya eklenmemiş.")
            return
        try:
            if platform == "android":
                where = self._save_pdf_android(source)
            else:
                where = self._save_pdf_desktop(source)
            self.show_message("Başarılı", f"PDF başarıyla kaydedildi!\n{where}")
        except Exception as e:
            self.show_message("Hata", f"Dosya kaydedilemedi: {e}")

    def _save_pdf_desktop(self, source):
        folder = Path.home() / "Downloads"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / PDF_FILENAME
        shutil.copyfile(source, target)
        return str(target)

    def _save_pdf_android(self, source):
        from jnius import autoclass

        Build = autoclass("android.os.Build$VERSION")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity

        if Build.SDK_INT >= 29:
            # Android 10+: izin gerektirmeden MediaStore ile İndirilenler klasörüne yaz
            ContentValues = autoclass("android.content.ContentValues")
            Downloads = autoclass("android.provider.MediaStore$Downloads")
            resolver = activity.getContentResolver()
            values = ContentValues()
            values.put("_display_name", PDF_FILENAME)
            values.put("mime_type", "application/pdf")
            values.put("relative_path", "Download")
            uri = resolver.insert(Downloads.EXTERNAL_CONTENT_URI, values)
            out = resolver.openOutputStream(uri)
            try:
                with open(source, "rb") as f:
                    while True:
                        chunk = f.read(65536)
                        if not chunk:
                            break
                        out.write(list(memoryview(chunk).cast("b")))
            finally:
                out.close()
            return "İndirilenler (Downloads) klasörü"

        # Android 9 ve altı: uygulamanın kendi klasörüne kaydet
        target = os.path.join(self.user_data_dir, PDF_FILENAME)
        shutil.copyfile(source, target)
        return target

    # ---------------------------------------------------------------- Zorluk / can
    def show_difficulty_selection(self):
        self.screen(self.show_difficulty_selection, back=self.show_main_screen)
        self.add_top_bar("← Ana Ekran", self.show_main_screen)
        self.root_box.add_widget(Widget())
        self.root_box.add_widget(WrapLabel(text="Zorluk Seviyesi Seçin", bold=True,
                                           font_size=sp(22), color=self.fg))
        for text, color, level in (("Kolay", "#4CAF50", "kolay"),
                                   ("Orta", "#FF9800", "orta"),
                                   ("Zor", "#f44336", "zor")):
            self.root_box.add_widget(self.make_btn(text, color, lambda l=level: self.ask_lives_option(l),
                                                   height=54, font=18, size_hint_x=0.8,
                                                   pos_hint={"center_x": 0.5}))
        self.root_box.add_widget(Widget())

    def ask_lives_option(self, level):
        self.game_level = level
        self.screen(lambda: self.ask_lives_option(level), back=self.show_difficulty_selection)
        self.add_top_bar("← Geri", self.show_difficulty_selection)
        self.root_box.add_widget(Widget())

        card = Card(self.c["card"], orientation="vertical", padding=dp(16), spacing=dp(12),
                    size_hint_y=None, height=dp(220))
        card.add_widget(FillLabel(text="Canlar aktif olsun mu?", bold=True,
                                  font_size=sp(20), color=self.fg))
        card.add_widget(FillLabel(text="Kolay: 10 Can | Orta: 5 Can | Zor: 3 Can",
                                  font_size=sp(14), color=self.fg))
        row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(12))
        row.add_widget(self.make_btn("Evet", "#4CAF50", lambda: self.start_game(True), height=50))
        row.add_widget(self.make_btn("Hayır", "#e74c3c", lambda: self.start_game(False), height=50))
        card.add_widget(row)
        self.root_box.add_widget(card)
        self.root_box.add_widget(Widget())

    # ------------------------------------------------------------------- Oyun
    def start_game(self, lives_enabled):
        self.lives_enabled = lives_enabled

        if self.game_level == "kolay":
            self.lives = 10
            raw_pool = EASY_LIST
        elif self.game_level == "orta":
            self.lives = 5
            raw_pool = MEDIUM_LIST
        else:
            self.lives = 3
            raw_pool = HARD_LIST

        # ID'ler karıştırmadan ÖNCE atanır; her kelimenin ID'si sabit kalır
        indexed = list(enumerate(raw_pool))
        random.shuffle(indexed)
        self.current_pool = indexed
        self.saved_guess = ""
        self.next_word()

    @staticmethod
    def parse_item(item_str):
        return [p.strip() for p in item_str.split("->") if p.strip()]

    def next_word(self):
        if not self.current_pool:
            self.show_message("Tebrikler!", "Bu seviyedeki tüm kelimeleri tamamladınız!",
                              on_close=self.show_main_screen)
            return

        self.current_item = self.current_pool.pop(0)
        _, word_str = self.current_item
        self.steps = self.parse_item(word_str)
        self.target_word = tr_lower(self.steps[-1])
        self.hint_used = False
        self.saved_guess = ""
        self.render_game_screen()

    def game_over(self, message):
        self.show_message("Oyun Bitti", message, on_close=self.show_main_screen,
                          ok_color="#e74c3c")

    def lose_life(self):
        """Can düşer. Canlar bittiyse True döner."""
        if not self.lives_enabled:
            return False
        self.lives -= 1
        return self.lives <= 0

    def render_game_screen(self):
        self.screen(self.render_game_screen, back=self.show_difficulty_selection)
        self.add_top_bar("← Çıkış", self.show_difficulty_selection)

        info_row = BoxLayout(size_hint_y=None, height=dp(30))
        info_row.add_widget(FillLabel(
            text=f"Seviye: {self.game_level.upper()} | Kalan: {len(self.current_pool) + 1}",
            halign="left", bold=True, font_size=sp(13), color=self.fg))
        lives_text = f"Can: {self.lives}" if self.lives_enabled else "Can: Sınırsız"
        info_row.add_widget(FillLabel(text=lives_text, halign="right", bold=True,
                                      font_size=sp(14), color=self.fg))
        self.root_box.add_widget(info_row)

        card = Card(self.c["card"], orientation="vertical", padding=dp(14), spacing=dp(10))
        word_id, _ = self.current_item
        card.add_widget(FillLabel(text=f"ID: #{word_id + 1}", halign="right",
                                  size_hint_y=None, height=dp(18), font_size=sp(11), color=self.fg))
        card.add_widget(WrapLabel(text="Kelimenin evrim sürecini incele ve son halini tahmin et:",
                                  bold=True, font_size=sp(14), color=self.fg))

        if not self.hint_used:
            display_str = self.steps[0] + "  →  ?"
        else:
            display_str = "  →  ".join(self.steps[:-1]) + "  →  ?"
        card.add_widget(FillLabel(text=display_str, bold=True, font_size=sp(24), color=self.fg))

        self.guess_input = TextInput(
            multiline=False, font_size=sp(18), halign="center",
            size_hint_y=None, height=dp(50), padding=[dp(10), dp(12)],
            background_normal="", background_active="",
            background_color=hexc(self.c["bg"]), foreground_color=self.fg,
            cursor_color=self.fg, hint_text="Tahminin", write_tab=False)
        self.guess_input.bind(on_text_validate=lambda *_: self.check_guess())
        if self.saved_guess:
            self.guess_input.text = self.saved_guess
            self.saved_guess = ""
        card.add_widget(self.guess_input)

        card.add_widget(self.make_btn("Tahmin Et", "#2980b9", self.check_guess))
        if not self.hint_used and len(self.steps) > 2:
            card.add_widget(self.make_btn("İpucu Al (Tüm Adımları Göster)", "#f39c12",
                                          self.on_hint_click, font=14))
        card.add_widget(self.make_btn("Cevabı Göster", "#e67e22", self.confirm_show_answer, font=14))
        self.root_box.add_widget(card)

        if platform != "android":
            Clock.schedule_once(lambda dt: self.focus_input(), 0.1)

    def focus_input(self):
        if self.guess_input is not None and self.guess_input.parent is not None:
            self.guess_input.focus = True

    def on_hint_click(self):
        if self.hint_used:
            return
        self.saved_guess = self.guess_input.text if self.guess_input is not None else ""
        self.hint_used = True
        if self.lose_life():
            self.game_over("Canlarınız bitti! Ana ekrana dönülüyor.")
            return
        self.render_game_screen()

    def confirm_show_answer(self):
        self.ask_yes_no("Emin misin?", "Cevabı görmek istediğinizden emin misiniz?",
                        self._reveal_answer)

    def _reveal_answer(self):
        if self.lose_life():
            self.game_over(f"Canlarınız bitti! Doğru cevap: {self.steps[-1]}\nAna ekrana dönülüyor.")
            return
        self.show_message("Cevap", f"Doğru Cevap: {self.steps[-1]}", on_close=self.next_word)

    def check_guess(self):
        if self.guess_input is None:
            return
        user_guess = tr_lower(self.guess_input.text)
        if not user_guess:
            return

        if user_guess == self.target_word:
            self.show_message("Tebrikler!", f"Doğru bildin! Kelime: {self.steps[-1]}",
                              on_close=self.next_word, ok_color="#4CAF50")
            return

        if self.lose_life():
            self.game_over(f"Canlarınız bitti! Doğru cevap: {self.steps[-1]}\nAna ekrana dönülüyor.")
            return

        if self.lives_enabled:
            self.show_message("Yanlış", f"Yanlış tahmin! Kalan can: {self.lives}",
                              on_close=self.render_game_screen, ok_color="#e74c3c")
        else:
            def retry():
                if self.guess_input is not None:
                    self.guess_input.text = ""
                if platform != "android":
                    self.focus_input()

            self.show_message("Yanlış", "Yanlış tahmin, tekrar dene!",
                              on_close=retry, ok_color="#e74c3c")


if __name__ == "__main__":
    EtimokartApp().run()
