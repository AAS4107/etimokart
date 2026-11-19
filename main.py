"""Etimokart - Android (Kivy) arayüzü. Oyun/kayıt mantığı core.py'dedir."""
import colorsys
import os
import threading

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import NoTransition, Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.utils import get_color_from_hex as hexc

import core

Window.softinput_mode = "below_target"


# ----------------------------------------------------------------------
#  Küçük arayüz yardımcıları
# ----------------------------------------------------------------------
def app():
    return App.get_running_app()


def mix(hex_a, hex_b, t):
    a, b = hexc(hex_a), hexc(hex_b)
    return tuple(a[i] * (1 - t) + b[i] * t for i in range(3)) + (1,)


def palette(user):
    """Tema renkleri. Mağazadan arkaplan alınmışsa koyu tonlu temaya geçer."""
    tint = None
    if user:
        tint = core.find_item(core.BACKGROUNDS, user.get("active_bg", "bg_free")).get("tint")
    if tint:
        return {"bg": hexc(tint), "card": mix(tint, "#ffffff", 0.10), "fg": hexc("#f1f5f9"),
                "sub": hexc("#b6c2d2"), "field": mix(tint, "#000000", 0.35)}
    if user and not user.get("dark_mode", True):
        return {"bg": hexc("#f1f5f9"), "card": hexc("#ffffff"), "fg": hexc("#0f172a"),
                "sub": hexc("#475569"), "field": hexc("#e2e8f0")}
    return {"bg": hexc("#0f172a"), "card": hexc("#1e293b"), "fg": hexc("#f1f5f9"),
            "sub": hexc("#94a3b8"), "field": hexc("#0b1220")}


def rainbow(hue):
    r, g, b = colorsys.hsv_to_rgb(hue % 1.0, 0.8, 1.0)
    return (r, g, b, 1)


class Txt(Label):
    """Satır kaydıran, yüksekliği içeriğe uyan yazı."""

    def __init__(self, text="", size=16, color=None, bold=False, halign="center", **kw):
        super().__init__(text=text, font_size=sp(size), bold=bold, halign=halign, valign="middle",
                         color=color or app().pal["fg"], size_hint_y=None, **kw)
        self.bind(width=self._wrap, texture_size=self._fit)

    def _wrap(self, *_):
        self.text_size = (self.width, None)

    def _fit(self, *_):
        self.height = self.texture_size[1] + dp(6)


def Btn(text, cb, bg="#2980b9", fg="#ffffff", height=48, size=16, **kw):
    b = Button(text=text, background_normal="", background_down="", background_color=hexc(bg),
               color=hexc(fg), font_size=sp(size), size_hint_y=None, height=dp(height), **kw)
    b.bind(on_release=lambda *_: cb())
    return b


def Field(hint, password=False):
    p = app().pal
    return TextInput(hint_text=hint, multiline=False, password=password, write_tab=False,
                     size_hint_y=None, height=dp(48), font_size=sp(16), padding=[dp(12), dp(13)],
                     background_normal="", background_active="", background_color=p["field"],
                     foreground_color=p["fg"], hint_text_color=p["sub"], cursor_color=p["fg"])


class Card(BoxLayout):
    def __init__(self, color, border=None, **kw):
        super().__init__(orientation="vertical", size_hint_y=None, padding=dp(12), spacing=dp(8), **kw)
        self.bind(minimum_height=self.setter("height"))
        with self.canvas.before:
            Color(*color)
            self._rect = RoundedRectangle(radius=[dp(14)])
            self._bcol = Color(*(border or (0, 0, 0, 0)))
            self._line = Line(width=dp(2.5))
        self.bind(pos=self._upd, size=self._upd)

    def _upd(self, *_):
        self._rect.pos, self._rect.size = self.pos, self.size
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(14))

    def set_border(self, rgba):
        self._bcol.rgba = rgba


class Swatch(Label):
    """Yuvarlak renk/avatar önizlemesi."""

    def __init__(self, rgba, letter="", d=44, **kw):
        super().__init__(text=letter, bold=True, font_size=sp(18), size_hint=(None, None),
                         size=(dp(d), dp(d)), color=(1, 1, 1, 1), **kw)
        with self.canvas.before:
            self._col = Color(*rgba)
            self._el = Ellipse()
        self.bind(pos=self._upd, size=self._upd)

    def _upd(self, *_):
        self._el.pos, self._el.size = self.pos, self.size


def page(children):
    sv = ScrollView(do_scroll_x=False, bar_width=dp(3))
    box = BoxLayout(orientation="vertical", size_hint_y=None, padding=[dp(16)] * 4, spacing=dp(10))
    box.bind(minimum_height=box.setter("height"))
    for c in children:
        box.add_widget(c)
    sv.add_widget(box)
    return sv


def tint_rgba(tint, fallback, hue=0.0):
    if tint == "rainbow":
        return rainbow(hue)
    return hexc(tint) if tint else fallback


# ----------------------------------------------------------------------
#  Ekranlar
# ----------------------------------------------------------------------
class Base(Screen):
    def on_pre_enter(self, *_):
        a = app()
        a.rainbow_cb = None
        a.rank_lbl = None
        Window.clearcolor = a.pal["bg"]
        self.clear_widgets()
        self.add_widget(self.build())

    def build(self):
        return BoxLayout()


class LoginScreen(Base):
    def build(self):
        a, p = app(), app().pal
        self.remember = True
        self.u = Field("Kullanıcı adı")
        self.pw = Field("Şifre", password=True)
        self.u.text = a.store.db.get("remember_username", "")
        self.u.bind(on_text_validate=lambda *_: setattr(self.pw, "focus", True))
        self.pw.bind(on_text_validate=lambda *_: self.go())
        self.err = Txt("", 14, hexc("#e74c3c"), bold=True)
        self.rem = Btn("[x] Beni hatırla", self.toggle, "#00000000", hexc_str(p["fg"]), height=40, size=14)
        return page([
            Txt("ETİMOKART", 30, bold=True), Txt("Kelime evrimini keşfet, altınları topla!", 14, p["sub"]),
            self.u, self.pw, self.err, self.rem,
            Btn("Giriş Yap", self.go, "#27ae60"),
            Btn("Hesabın yok mu?  Kayıt Ol", lambda: a.goto("register"), "#00000000", "#5dade2", height=44, size=15),
        ])

    def toggle(self):
        self.remember = not self.remember
        self.rem.text = ("[x]" if self.remember else "[ ]") + " Beni hatırla"

    def go(self):
        a = app()
        ok, res = a.store.login(self.u.text, self.pw.text, self.remember)
        if not ok:
            self.err.text = res
            self.pw.text = ""
            return
        a.enter(res)


class RegisterScreen(Base):
    def build(self):
        a, p = app(), app().pal
        self.remember = True
        self.u = Field("Kullanıcı adı (2-20 karakter)")
        self.pw = Field("Şifre (en az 4 karakter)", password=True)
        self.pw2 = Field("Şifre (tekrar)", password=True)
        self.u.bind(on_text_validate=lambda *_: setattr(self.pw, "focus", True))
        self.pw.bind(on_text_validate=lambda *_: setattr(self.pw2, "focus", True))
        self.pw2.bind(on_text_validate=lambda *_: self.go())
        self.err = Txt("", 14, hexc("#e74c3c"), bold=True)
        self.rem = Btn("[x] Beni hatırla", self.toggle, "#00000000", hexc_str(p["fg"]), height=40, size=14)
        return page([
            Txt("KAYIT OL", 30, bold=True), Txt("Yeni hesap oluştur, 50 Altın hediye kazan!", 14, p["sub"]),
            self.u, self.pw, self.pw2, self.err, self.rem,
            Btn("Kayıt Ol", self.go, "#2980b9"),
            Btn("← Girişe dön", lambda: a.goto("login"), "#00000000", "#5dade2", height=44, size=15),
        ])

    def toggle(self):
        self.remember = not self.remember
        self.rem.text = ("[x]" if self.remember else "[ ]") + " Beni hatırla"

    def go(self):
        a = app()
        ok, res = a.store.register(self.u.text, self.pw.text, self.pw2.text, self.remember,
                                   a.user["dark_mode"] if a.user else True)
        if not ok:
            self.err.text = res
            return
        a.flash = f"Kayıt başarılı, hoş geldin {res}! Hediye 50 Altın hesabına yüklendi."
        a.enter(res)


class MainScreen(Base):
    def build(self):
        a, p, u = app(), app().pal, app().user
        total = u["total_score"]
        rank_name, nxt = core.rank_info(total)
        nxt_txt = f"Sonraki ünvan: {nxt[1]} ({nxt[0] - total} puan kaldı)" if nxt else "En yüksek ünvandasın!"

        av = core.find_item(core.AVATARS, u["active_avatar"])
        head = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        head.add_widget(Swatch(tint_rgba(av["tint"], hexc("#7f8c8d")), a.cur[:1].upper()))
        head.add_widget(Txt(f"{a.cur}   |   Altın: {u['gold']}   |   Rekor: {u['best_score']}", 14,
                            halign="left"))

        stats = Card(p["card"])
        stats.add_widget(Txt(f"Toplam Puan: {total}", 20, hexc("#f39c12"), bold=True))
        stats.add_widget(Txt(f"Ünvan: {rank_name}", 14))
        stats.add_widget(Txt(nxt_txt, 12, p["sub"]))
        a.rank_lbl = Txt(a.rank_text, 14, hexc("#5dade2"), bold=True)
        stats.add_widget(a.rank_lbl)

        items = [head]
        if a.flash:
            items.append(Txt(a.flash, 14, hexc("#27ae60"), bold=True))
            a.flash = ""
        items += [
            stats,
            Btn("Oyuna Başla", lambda: a.goto("difficulty"), "#2196F3"),
            Btn("Mağaza (Kozmetikler)", lambda: a.goto("shop"), "#8e44ad"),
            Btn("Lider Tablosu (İlk 100)", lambda: a.goto("board"), "#16a085"),
            Btn("Koyu / Açık Tema", a.toggle_theme, "#546e7a"),
            Btn("Çıkış Yap", a.logout, "#c0392b"),
            Btn("Hesabı Sil", a.ask_delete, "#7b241c", height=42, size=14),
        ]
        return page(items)


class DifficultyScreen(Base):
    def build(self):
        a, p = app(), app().pal
        rows = [Txt("Zorluk Seviyesi", 26, bold=True), Txt("Kelime havuzunun tarihsel derinliğine göre seç.", 13, p["sub"])]
        for key, label, color in (("kolay", "Kolay", "#27ae60"), ("orta", "Orta", "#e67e22"), ("zor", "Zor", "#c0392b")):
            rows.append(Btn(f"{label}  ({len(core.LEVELS[key])} kelime, {core.LIVES[key]} can)",
                            lambda k=key: a.pick_level(k), color, height=60))
        rows.append(Btn("← Geri", lambda: a.goto("main"), "#546e7a"))
        return page(rows)


class LivesScreen(Base):
    def build(self):
        a, p = app(), app().pal
        return page([
            Txt("Canlar Aktif Olsun mu?", 26, bold=True),
            Txt(f"{a.level.capitalize()} seviye: {core.LIVES[a.level]} can", 14, p["sub"]),
            Btn("Evet (canlı oyna)", lambda: a.start_game(True), "#27ae60", height=56),
            Btn("Hayır (sınırsız deneme)", lambda: a.start_game(False), "#546e7a", height=56),
            Btn("← Geri", lambda: a.goto("difficulty"), "#546e7a"),
        ])


class GameScreen(Base):
    """Kelime başına bir kez kurulur; geri bildirim yerinde güncellenir (klavye kapanmasın)."""

    def build(self):
        a, p, g, u = app(), app().pal, app().game, app().user
        self.locked = False
        frame = core.find_item(core.FRAMES, u["active_frame"])
        ws = core.find_item(core.WORD_STYLES, u["active_wstyle"])
        fx = core.find_item(core.FX_LIST, u["active_fx"])
        self.fx_color = tint_rgba(fx["tint"], hexc("#27ae60"))

        self.info = Txt("", 13, p["sub"], halign="left")
        self.lives = Txt("", 14, hexc("#e74c3c"), bold=True, halign="right")
        top = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        top.add_widget(Btn("Bitir", a.finish_game, "#e74c3c", height=40, size=14, size_hint_x=None, width=dp(80)))
        top.add_widget(self.info)
        top.add_widget(self.lives)
        self.score = Txt("", 15, hexc("#f39c12"), bold=True)

        self.card = Card(p["card"], border=tint_rgba(frame["tint"], None) if frame["tint"] else None)
        self.card.add_widget(Txt(f"ID: #{g.word_id + 1}", 12, p["sub"]))
        self.card.add_widget(Txt("Kelimenin evrim sürecini incele ve son halini tahmin et:", 14, p["sub"]))
        wcolor = tint_rgba(ws["tint"], p["fg"])
        self.word = Txt("", 24, wcolor, bold=True, italic=bool(ws.get("italic")))
        self.card.add_widget(self.word)
        self.fb = Txt("", 15, hexc("#e74c3c"), bold=True)
        self.card.add_widget(self.fb)

        # gökkuşağı çerçeve / yazı için renk döngüsü
        rb_frame, rb_word = frame["tint"] == "rainbow", ws["tint"] == "rainbow"
        if rb_frame or rb_word:
            def cb(color):
                if rb_frame:
                    self.card.set_border(color)
                if rb_word:
                    self.word.color = color
            a.rainbow_cb = cb

        self.guess = Field("Tahmininizi yazın...")
        self.guess.halign = "center"
        self.guess.bind(on_text_validate=lambda *_: self.submit())
        self.ok_btn = Btn(f"Tahmin Et (+{core.POINTS_CORRECT} Puan)", self.submit, "#2980b9")
        self.hint_btn = Btn(f"İpucu Al (-{core.POINTS_HINT} Puan)", self.hint, "#f39c12", height=44, size=14)
        self.show_btn = Btn(f"Cevabı Göster (-{core.POINTS_REVEAL} Puan)", self.reveal_ask, "#e67e22", height=44, size=14)

        self.refresh()
        items = [top, self.score, self.card, self.guess, self.ok_btn]
        if g.can_hint:
            items.append(self.hint_btn)
        items.append(self.show_btn)
        sv = page(items)
        Clock.schedule_once(lambda dt: setattr(self.guess, "focus", True), 0.2)
        return sv

    def refresh(self):
        g = app().game
        self.info.text = f"Seviye: {g.level.upper()} | Kalan: {g.remaining}"
        self.lives.text = f"Can: {g.lives}" if g.lives_enabled else "Can: Sınırsız"
        self.score.text = f"Puan: {g.score}     Altın: +{g.gold}"
        self.word.text = g.display()

    def say(self, text, color):
        self.fb.text, self.fb.color = text, color

    def lock(self):
        self.locked = True
        self.guess.disabled = True
        self.ok_btn.disabled = True
        self.hint_btn.disabled = True
        self.show_btn.disabled = True

    def submit(self):
        a, g = app(), app().game
        if self.locked:
            return
        r = g.guess(self.guess.text)
        if r["result"] == "empty":
            return
        self.refresh()
        if r["result"] == "correct":
            gold = f", +{r['gold']} Altın" if r["gold"] else ""
            self.say(f"Harika! +{core.POINTS_CORRECT} Puan{gold}", self.fx_color)
            self.lock()
            a.save()
            Clock.schedule_once(lambda dt: a.next_word(), 1.1)
        elif r["result"] == "gameover":
            a.finish_game(f"Canların bitti! Doğru cevap: {g.answer}")
        else:
            pen = f"(-{r['penalty']} Puan)" if r["penalty"] else "(puan kaybı yok)"
            self.say(f"Yanlış tahmin! {pen}", hexc("#e74c3c"))
            self.guess.text = ""
            self.guess.focus = True

    def hint(self):
        g = app().game
        if g.use_hint():
            self.refresh()
            self.say(f"İpucu kullanıldı (-{core.POINTS_HINT} Puan)", hexc("#f39c12"))
            if self.hint_btn.parent:
                self.hint_btn.parent.remove_widget(self.hint_btn)

    def reveal_ask(self):
        if self.locked:
            return
        app().confirm("Cevabı Göster", f"Cevabı görmek {core.POINTS_REVEAL} puan ve 1 can götürür. Emin misin?",
                      "Evet", self.reveal)

    def reveal(self):
        a, g = app(), app().game
        r = g.reveal()
        self.refresh()
        if r["result"] == "gameover":
            a.finish_game(f"Canların bitti! Doğru cevap: {g.answer}")
            return
        self.say(f"Doğru cevap: {r['answer']} (-{core.POINTS_REVEAL} Puan)", hexc("#e67e22"))
        self.lock()
        Clock.schedule_once(lambda dt: a.next_word(), 1.8)


class SummaryScreen(Base):
    def build(self):
        a, p, s = app(), app().pal, app().summary
        items = [Txt("OYUN SONU ÖZETİ", 24, hexc("#f39c12"), bold=True), Txt(s["reason"], 14, p["sub"])]
        card = Card(p["card"])
        for line in (f"Oyun Puanı: {s['score']} Puan", f"Kazanılan Altın: +{s['gold']}",
                     f"Doğru: {s['correct']}   |   Yanlış: {s['wrong']}",
                     f"En Yüksek Rekorun: {s['best']} Puan", f"Toplam Puan: {s['total']}"):
            card.add_widget(Txt(line, 16, bold=True))
        items.append(card)
        if s["record"] and s["score"] > 0:
            items.append(Txt("YENİ KİŞİSEL REKOR!", 16, hexc("#27ae60"), bold=True))
        if s["rank_up"]:
            items.append(Txt(f"Yeni ünvan: {s['rank_up']}!", 16, hexc("#8e44ad"), bold=True))
        items += [Btn("Tekrar Oyna", lambda: a.goto("difficulty"), "#2196F3"),
                  Btn("Ana Menü", lambda: a.goto("main"), "#546e7a")]
        return page(items)


class ShopScreen(Base):
    def build(self):
        a, p, u = app(), app().pal, app().user
        cat = core.SHOP_CATEGORIES[a.shop_cat]
        tabs = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(4))
        for i, c in enumerate(core.SHOP_CATEGORIES):
            tabs.add_widget(Btn(c[1], lambda i=i: a.set_shop_cat(i), "#8e44ad" if i == a.shop_cat else "#546e7a",
                                height=40, size=12))
        items = [Txt("Mağaza", 26, bold=True), Txt(f"Altının: {u['gold']}", 16, hexc("#f39c12"), bold=True), tabs]
        if a.shop_msg:
            items.append(Txt(a.shop_msg, 13, hexc("#27ae60"), bold=True))
        for it in cat[2]:
            owned, active = it["id"] in u.get(cat[3], []), u.get(cat[4]) == it["id"]
            if active:
                label, color = "Kullanılıyor", "#27ae60"
            elif owned:
                label, color = "Kullan", "#2980b9"
            else:
                label, color = f"Satın Al ({it['price']})", "#e67e22"
            row = Card(p["card"])
            top = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
            top.add_widget(Swatch(tint_rgba(it["tint"], hexc("#7f8c8d")), "", 40))
            col = BoxLayout(orientation="vertical")
            col.add_widget(Label(text=it["name"], bold=True, font_size=sp(15), color=p["fg"], halign="left",
                                 text_size=(dp(200), None)))
            col.add_widget(Label(text=it["desc"], font_size=sp(12), color=p["sub"], halign="left",
                                 text_size=(dp(200), None)))
            top.add_widget(col)
            row.add_widget(top)
            row.add_widget(Btn(label, lambda it=it: a.shop_buy(cat, it), color, height=40, size=14))
            items.append(row)
        items.append(Btn("← Geri", lambda: a.goto("main"), "#546e7a"))
        return page(items)


class BoardScreen(Base):
    def build(self):
        a, p = app(), app().pal
        self.status = Txt("Yükleniyor...", 14, p["sub"])
        self.box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        self.box.bind(minimum_height=self.box.setter("height"))
        threading.Thread(target=self._load, daemon=True).start()
        return page([Txt("Lider Tablosu", 26, bold=True), self.status, self.box,
                     Btn("← Geri", lambda: a.goto("main"), "#546e7a")])

    def _load(self):
        self._show(core.fetch_top(100))

    @mainthread
    def _show(self, rows):
        p = app().pal
        if rows is None:
            self.status.text = "Tablo yüklenemedi. İnternetini kontrol et."
            return
        self.status.text = f"En iyi {len(rows)} oyuncu" if rows else "Henüz tabloda kimse yok."
        for i, r in enumerate(rows):
            line = Card(p["card"])
            line.add_widget(Txt(f"{i + 1}.  {r.get('username', '')}  -  {r.get('total_score', 0)} puan",
                                15, halign="left", bold=i < 3))
            self.box.add_widget(line)


# ----------------------------------------------------------------------
#  Uygulama
# ----------------------------------------------------------------------
def hexc_str(rgba):
    return "#%02x%02x%02x" % tuple(int(c * 255) for c in rgba[:3])


class EtimokartApp(App):
    title = "Etimokart"

    def build(self):
        self.store = core.Store(os.path.join(self.user_data_dir, "etimokart_kayit.json"))
        self.cur, self.user = None, None
        self.pal = palette(None)
        self.level, self.game, self.summary = "kolay", None, {}
        self.flash, self.shop_msg, self.shop_cat = "", "", 0
        self.rank_text, self.rank_lbl = "Sıralama: ...", None
        self._rank_busy = False
        self.rainbow_cb, self._hue = None, 0.0

        self.sm = ScreenManager(transition=NoTransition())
        for name, cls in (("login", LoginScreen), ("register", RegisterScreen), ("main", MainScreen),
                          ("difficulty", DifficultyScreen), ("lives", LivesScreen), ("game", GameScreen),
                          ("summary", SummaryScreen), ("shop", ShopScreen), ("board", BoardScreen)):
            self.sm.add_widget(cls(name=name))

        Window.bind(on_keyboard=self.on_key)
        Clock.schedule_interval(self._tick, 0.08)

        auto = self.store.db.get("auto_login")
        if auto and auto in self.store.db["users"]:
            self.enter(auto)
        else:
            self.sm.current = "login"
        return self.sm

    # --- genel ---
    def goto(self, name):
        if self.sm.current == name:       # aynı ekrana geçişte yenile
            self.sm.get_screen(name).on_pre_enter()
        self.sm.current = name

    def save(self):
        try:
            self.store.save()
        except OSError:
            pass

    def theme(self):
        self.pal = palette(self.user)
        Window.clearcolor = self.pal["bg"]

    def toggle_theme(self):
        self.user["dark_mode"] = not self.user.get("dark_mode", True)
        self.save()
        self.theme()
        self.goto("main")

    def _tick(self, dt):
        self._hue = (self._hue + 0.01) % 1.0
        if self.rainbow_cb:
            self.rainbow_cb(rainbow(self._hue))

    def on_key(self, window, key, *args):
        if key != 27:                      # Android geri tuşu
            return False
        cur = self.sm.current
        if cur == "game":
            self.finish_game("Oyun sonlandırıldı.")
        elif cur in ("difficulty", "lives", "shop", "board", "summary"):
            self.goto("main")
        elif cur == "register":
            self.goto("login")
        else:
            return False
        return True

    # --- hesap ---
    def enter(self, name):
        self.cur, self.user = name, self.store.user(name)
        self.rank_text = "Sıralama: ..."
        self.theme()
        if core.ensure_site_token(self.user):
            self.save()
        self.sm.current = "main"
        self.refresh_rank()

    def logout(self):
        self.store.logout()
        self.cur = self.user = None
        self.pal = palette(None)
        Window.clearcolor = self.pal["bg"]
        self.goto("login")

    def ask_delete(self):
        p = self.pal
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        box.add_widget(Txt(f"'{self.cur}' hesabı KALICI olarak silinecek. Onaylamak için şifreni gir:", 14))
        pw = Field("Şifre", password=True)
        err = Txt("", 13, hexc("#e74c3c"), bold=True)
        box.add_widget(pw)
        box.add_widget(err)
        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        pop = Popup(title="Hesabı Sil", content=box, size_hint=(0.9, None), height=dp(330))

        def do():
            if not core.verify_password(pw.text, self.user.get("password")):
                err.text, pw.text = "Hatalı şifre.", ""
                return
            pop.dismiss()
            self.delete_account()

        row.add_widget(Btn("Vazgeç", pop.dismiss, "#78909c"))
        row.add_widget(Btn("Sil", do, "#c0392b"))
        box.add_widget(row)
        pop.open()

    def delete_account(self):
        name, token = self.cur, self.user.get("site_token", "")
        threading.Thread(target=core.delete_remote, args=(name, token), daemon=True).start()
        self.store.delete_user(name)
        self.cur = self.user = None
        self.pal = palette(None)
        Window.clearcolor = self.pal["bg"]
        self.goto("login")

    def confirm(self, title, text, yes_text, on_yes):
        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(12))
        box.add_widget(Txt(text, 15))
        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        pop = Popup(title=title, content=box, size_hint=(0.88, None), height=dp(240))
        row.add_widget(Btn("Vazgeç", pop.dismiss, "#78909c"))
        row.add_widget(Btn(yes_text, lambda: (pop.dismiss(), on_yes()), "#c0392b"))
        box.add_widget(row)
        pop.open()

    # --- site sıralaması ---
    def refresh_rank(self):
        if not self.cur or self._rank_busy:
            return
        self._rank_busy = True
        name, u = self.cur, self.user
        args = (name, u.get("site_token", ""), u["total_score"], u["best_score"])

        def work():
            text, _ = core.sync_rank(*args)
            self._set_rank(text)

        threading.Thread(target=work, daemon=True).start()

    @mainthread
    def _set_rank(self, text):
        self._rank_busy = False
        self.rank_text = text
        if self.rank_lbl is not None and self.sm.current == "main":
            self.rank_lbl.text = text

    # --- oyun ---
    def pick_level(self, level):
        self.level = level
        self.goto("lives")

    def start_game(self, lives_enabled):
        self.game = core.Game(self.user, self.level, lives_enabled)
        self.next_word()

    def next_word(self):
        if self.sm.current != "game" and self.sm.current not in ("lives",):
            return                        # bu arada ekrandan çıkıldıysa
        if not self.game or self.game.finished:
            return
        if not self.game.next_word():
            self.finish_game("Tebrikler! Bu seviyedeki tüm kelimeleri tamamladın!")
            return
        self.goto("game")

    def finish_game(self, reason="Oyun sonlandırıldı."):
        if not self.game:
            return
        s = self.game.finish()
        s["reason"] = reason if isinstance(reason, str) else "Oyun sonlandırıldı."
        self.summary = s
        self.save()
        self.refresh_rank()
        self.goto("summary")

    # --- mağaza ---
    def set_shop_cat(self, i):
        self.shop_cat, self.shop_msg = i, ""
        self.goto("shop")

    def shop_buy(self, cat, item):
        ok, msg = core.shop_action(self.user, cat, item)
        self.shop_msg = msg
        if ok:
            self.save()
            self.theme()
        self.goto("shop")


if __name__ == "__main__":
    EtimokartApp().run()
