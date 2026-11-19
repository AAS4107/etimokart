"""Etimokart (Android) - arayüzden bağımsız çekirdek.

Kayıt/giriş, kayıt dosyası, oyun kuralları, mağaza verisi ve site (Supabase) bağlantısı burada.
Kivy'ye bağlı değildir, bu yüzden bilgisayarda test edilebilir.
"""
import hashlib
import hmac
import json
import os
import random
import secrets
import ssl
import urllib.error
import urllib.request

from wordlists import EASY_LIST, MEDIUM_LIST, HARD_LIST

# --- SİTE (LİDER TABLOSU) ---
SB_URL = "https://jssuisvkozinpsjwzjfa.supabase.co"
SB_KEY = "sb_publishable_7S8ulDpKuDmPcFmuBeUORg_HFZq-S_r"  # herkese açık anahtar; secret/service_role ASLA koyma

# --- GİRİŞ / KAYIT KURALLARI ---
NAME_MIN, NAME_MAX, PASS_MIN = 2, 20, 4

# --- OYUN KURALLARI ---
LEVELS = {"kolay": EASY_LIST, "orta": MEDIUM_LIST, "zor": HARD_LIST}
LIVES = {"kolay": 10, "orta": 5, "zor": 3}
WRONG_PENALTY = {"kolay": 0, "orta": 5, "zor": 10}
POINTS_CORRECT, POINTS_HINT, POINTS_REVEAL = 100, 25, 50

RANKS = [
    (0, "Çırak Dilbilimci"), (500, "Kelime Meraklısı"), (1500, "Köken Avcısı"),
    (3000, "Dil Bilgini"), (6000, "Etimolog"), (10000, "Kelime Ustası"), (20000, "Dil Efsanesi"),
]

# --- MAĞAZA (tint: önizleme/arka plan rengi) ---
BACKGROUNDS = [
    {"id": "bg_free", "name": "Klasik Parşömen", "price": 0, "desc": "Ücretsiz sade tema", "tint": None},
    {"id": "bg_fireflies", "name": "Orman Ateş Böcekleri", "price": 40, "desc": "Koyu orman yeşili", "tint": "#10241a"},
    {"id": "bg_snow", "name": "Kar Taneleri", "price": 55, "desc": "Soğuk kış mavisi", "tint": "#16222f"},
    {"id": "bg_golddust", "name": "Altın Parşömen Tozu", "price": 80, "desc": "Sıcak kahverengi", "tint": "#2b2113"},
    {"id": "bg_rain", "name": "Yağmur Damlaları", "price": 95, "desc": "Gri yağmur bulutu", "tint": "#1d2329"},
    {"id": "bg_matrix", "name": "Göktürk Runik Akışı", "price": 120, "desc": "Derin yeşil siyah", "tint": "#07160c"},
    {"id": "bg_embers", "name": "Volkan Közleri", "price": 140, "desc": "Kızıl koyu ton", "tint": "#2a130d"},
    {"id": "bg_sakura", "name": "Japon Kiraz Çiçekleri", "price": 160, "desc": "Koyu pembe", "tint": "#2b1722"},
    {"id": "bg_leaves", "name": "Sonbahar Yaprakları", "price": 185, "desc": "Paslı turuncu", "tint": "#2c1a0e"},
    {"id": "bg_cyberpunk", "name": "Siberpunk Neon", "price": 210, "desc": "Mor neon gece", "tint": "#190d2a"},
    {"id": "bg_confetti", "name": "Konfeti Şenliği", "price": 240, "desc": "Eflatun şenlik", "tint": "#26122f"},
    {"id": "bg_bubbles", "name": "Derin Okyanus", "price": 270, "desc": "Okyanus mavisi", "tint": "#0a1f33"},
    {"id": "bg_aurora", "name": "Kuzey Işıkları", "price": 310, "desc": "Aurora yeşil-mavi", "tint": "#0b2a2a"},
    {"id": "bg_hearts", "name": "Kalp Yağmuru", "price": 330, "desc": "Bordo tutku", "tint": "#2e0f1a"},
    {"id": "bg_starfield", "name": "Kozmik Yıldız Geçidi", "price": 350, "desc": "Uzay laciverti", "tint": "#080b1f"},
]

AVATARS = [
    {"id": "av_free", "name": "Çırak Dilbilimci", "price": 0, "desc": "Ücretsiz başlangıç rozeti", "tint": "#7f8c8d"},
    {"id": "av_pulse", "name": "Altın Tamga", "price": 30, "desc": "Altın enerji halkası", "tint": "#f1c40f"},
    {"id": "av_heart", "name": "Atan Kalp", "price": 45, "desc": "Kırmızı kalp rozeti", "tint": "#e74c3c"},
    {"id": "av_gear", "name": "Zaman Çarkı", "price": 60, "desc": "Kadim bilgelik dişlisi", "tint": "#95a5a6"},
    {"id": "av_moon", "name": "Ay Işığı", "price": 80, "desc": "Gece gökyüzü hilali", "tint": "#a29bfe"},
    {"id": "av_orbit", "name": "Atom Yörüngesi", "price": 100, "desc": "Işık elektronları", "tint": "#00cec9"},
    {"id": "av_wave", "name": "Okyanus Dalgası", "price": 125, "desc": "Masmavi sular", "tint": "#0984e3"},
    {"id": "av_flame", "name": "Kor Alev", "price": 140, "desc": "Titreşen alev", "tint": "#e67e22"},
    {"id": "av_galaxy", "name": "Anka Alevi", "price": 160, "desc": "Gökkuşağı halesi", "tint": "rainbow"},
    {"id": "av_crown", "name": "Altın Taç", "price": 220, "desc": "Kraliyet tacı", "tint": "#fdcb6e"},
]

FRAMES = [
    {"id": "fr_free", "name": "Klasik Oluk", "price": 0, "desc": "Standart kart çerçevesi", "tint": None},
    {"id": "fr_gold", "name": "Altın Çerçeve", "price": 50, "desc": "Parlak altın kenarlık", "tint": "#f1c40f"},
    {"id": "fr_emerald", "name": "Zümrüt Yeşili", "price": 70, "desc": "Ferah yeşil kenarlık", "tint": "#2ecc71"},
    {"id": "fr_ruby", "name": "Yakut Kırmızısı", "price": 90, "desc": "Canlı kırmızı kenarlık", "tint": "#e74c3c"},
    {"id": "fr_sapphire", "name": "Safir Mavisi", "price": 110, "desc": "Derin mavi kenarlık", "tint": "#3498db"},
    {"id": "fr_amethyst", "name": "Ametist Moru", "price": 130, "desc": "Asil mor kenarlık", "tint": "#9b59b6"},
    {"id": "fr_neon", "name": "Neon Camgöbeği", "price": 160, "desc": "Parlak neon kenarlık", "tint": "#00e5ff"},
    {"id": "fr_rainbow", "name": "Gökkuşağı Çerçeve", "price": 230, "desc": "Renk değiştiren kenar", "tint": "rainbow"},
]

WORD_STYLES = [
    {"id": "ws_free", "name": "Klasik", "price": 0, "desc": "Standart kelime yazısı", "tint": None},
    {"id": "ws_serif", "name": "Zarif", "price": 35, "desc": "İtalik kelime yazısı", "tint": None, "italic": True},
    {"id": "ws_mono", "name": "Daktilo", "price": 45, "desc": "Eski daktilo karakterleri", "tint": None, "mono": True},
    {"id": "ws_gold", "name": "Altın Yazı", "price": 60, "desc": "Altın renkli kelime", "tint": "#d4a017"},
    {"id": "ws_cyan", "name": "Buz Mavisi", "price": 75, "desc": "Serin camgöbeği yazı", "tint": "#00acc1"},
    {"id": "ws_pink", "name": "Şeker Pembe", "price": 90, "desc": "Tatlı pembe yazı", "tint": "#e84393"},
    {"id": "ws_royal", "name": "Kraliyet Moru", "price": 110, "desc": "Mor renkli italik", "tint": "#8e44ad", "italic": True},
    {"id": "ws_rainbow", "name": "Gökkuşağı Yazı", "price": 170, "desc": "Renk değiştiren kelime", "tint": "rainbow"},
]

FX_LIST = [
    {"id": "fx_none", "name": "Efektsiz", "price": 0, "desc": "Doğru cevapta efekt yok", "tint": None},
    {"id": "fx_confetti", "name": "Konfeti", "price": 60, "desc": "Doğru bilince renkli konfeti", "tint": "#e84393"},
    {"id": "fx_stars", "name": "Yıldız Yağmuru", "price": 90, "desc": "Doğru bilince yıldızlar", "tint": "#f1c40f"},
    {"id": "fx_hearts", "name": "Kalp Yağmuru", "price": 120, "desc": "Doğru bilince kalpler", "tint": "#e74c3c"},
    {"id": "fx_coins", "name": "Altın Yağmuru", "price": 150, "desc": "Doğru bilince altın paralar", "tint": "#d4a017"},
    {"id": "fx_fireworks", "name": "Havai Fişek", "price": 200, "desc": "Doğru bilince havai fişek", "tint": "#00e5ff"},
]

# (anahtar, başlık, öğeler, sahip_olunanlar_alanı, aktif_alanı)
SHOP_CATEGORIES = [
    ("avatar", "Profil", AVATARS, "owned_avatars", "active_avatar"),
    ("bg", "Arkaplan", BACKGROUNDS, "owned_bgs", "active_bg"),
    ("frame", "Çerçeve", FRAMES, "owned_frames", "active_frame"),
    ("wstyle", "Yazı", WORD_STYLES, "owned_wstyles", "active_wstyle"),
    ("fx", "Efekt", FX_LIST, "owned_fx", "active_fx"),
]


def find_item(items, item_id):
    for it in items:
        if it["id"] == item_id:
            return it
    return items[0]


def rank_info(score):
    current, nxt = RANKS[0][1], (RANKS[1] if len(RANKS) > 1 else None)
    for i, (need, name) in enumerate(RANKS):
        if score >= need:
            current = name
            nxt = RANKS[i + 1] if i + 1 < len(RANKS) else None
    return current, nxt


def tr_lower(text):
    if not text:
        return ""
    return text.replace("İ", "i").replace("I", "ı").lower().strip()


# ----------------------------------------------------------------------
#  PAROLA
# ----------------------------------------------------------------------
def hash_password(pw, salt=None):
    if salt is None:
        salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), bytes.fromhex(salt), 120000).hex()
    return f"pbkdf2${salt}${digest}"


def verify_password(pw, stored):
    if not isinstance(stored, str) or not stored.startswith("pbkdf2$"):
        return False
    try:
        _, salt, digest = stored.split("$")
        test = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), bytes.fromhex(salt), 120000).hex()
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(test, digest)


# ----------------------------------------------------------------------
#  KULLANICI VERİSİ + KAYIT DOSYASI
# ----------------------------------------------------------------------
def new_user(password_hash, dark_mode=True):
    return {
        "password": password_hash, "gold": 50, "best_score": 0, "total_score": 0,
        "owned_bgs": ["bg_free"], "active_bg": "bg_free",
        "owned_avatars": ["av_free"], "active_avatar": "av_free",
        "owned_frames": ["fr_free"], "active_frame": "fr_free",
        "owned_wstyles": ["ws_free"], "active_wstyle": "ws_free",
        "owned_fx": ["fx_none"], "active_fx": "fx_none",
        "dark_mode": dark_mode, "site_token": "",
    }


def clean_username(raw):
    return " ".join((raw or "").split())


def validate_username(name):
    """Geçerliyse None, değilse hata metni."""
    if len(name) < NAME_MIN:
        return f"Kullanıcı adı en az {NAME_MIN} karakter olmalı."
    if len(name) > NAME_MAX:
        return f"Kullanıcı adı en fazla {NAME_MAX} karakter olabilir."
    if not all(ch.isalnum() or ch in " _-." for ch in name):
        return "Kullanıcı adında sadece harf, rakam, boşluk ve _ - . kullanılabilir."
    return None


class Store:
    """JSON kayıt dosyası: {"auto_login": ad|None, "remember_username": ad, "users": {ad: {...}}}"""

    def __init__(self, path):
        self.path = path
        self.db = {"auto_login": None, "remember_username": "", "users": {}}
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("users"), dict):
                self.db["users"] = {k: v for k, v in data["users"].items() if isinstance(v, dict)}
                self.db["auto_login"] = data.get("auto_login")
                self.db["remember_username"] = data.get("remember_username", "") or ""
        except (OSError, ValueError):
            pass
        for u in self.db["users"].values():          # eksik alanları tamamla
            for k, v in new_user("").items():
                u.setdefault(k, v)
        if self.db["auto_login"] not in self.db["users"]:
            self.db["auto_login"] = None

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.db, f, ensure_ascii=False)
        os.replace(tmp, self.path)

    # --- kayıt / giriş ---
    def find(self, name):
        target = tr_lower(name)
        for key in self.db["users"]:
            if tr_lower(key) == target:
                return key
        return None

    def register(self, name, pw, pw2, remember=True, dark_mode=True):
        """(True, kayıtlı_ad) ya da (False, hata_metni)"""
        name = clean_username(name)
        err = validate_username(name)
        if err:
            return False, err
        if self.find(name) is not None:
            return False, "Bu kullanıcı adı zaten alınmış."
        if len(pw) < PASS_MIN:
            return False, f"Şifre en az {PASS_MIN} karakter olmalı."
        if pw != pw2:
            return False, "Şifreler birbiriyle aynı değil."
        self.db["users"][name] = new_user(hash_password(pw), dark_mode)
        self._remember(name, remember)
        self.save()
        return True, name

    def login(self, name, pw, remember=True):
        """(True, kayıtlı_ad) ya da (False, hata_metni)"""
        name = clean_username(name)
        if not name or not pw:
            return False, "Kullanıcı adı ve şifreyi gir."
        key = self.find(name)
        if key is None or not verify_password(pw, self.db["users"][key].get("password")):
            return False, "Kullanıcı adı veya şifre hatalı."
        self._remember(key, remember)
        self.save()
        return True, key

    def _remember(self, name, remember):
        self.db["auto_login"] = name if remember else None
        self.db["remember_username"] = name if remember else ""

    def logout(self):
        self.db["auto_login"] = None
        self.save()

    def delete_user(self, name):
        self.db["users"].pop(name, None)
        if self.db.get("auto_login") == name:
            self.db["auto_login"] = None
        if self.db.get("remember_username") == name:
            self.db["remember_username"] = ""
        self.save()

    def user(self, name):
        return self.db["users"][name]


# ----------------------------------------------------------------------
#  MAĞAZA
# ----------------------------------------------------------------------
def shop_action(user, cat, item):
    """Satın al ya da kuşan. (başarılı_mı, mesaj)"""
    _, _, _, owned_key, active_key = cat
    owned = user.setdefault(owned_key, [])
    if item["id"] in owned:
        user[active_key] = item["id"]
        return True, f"'{item['name']}' kullanılıyor."
    if user["gold"] < item["price"]:
        return False, f"Yetersiz altın: {item['price']} gerekli, sende {user['gold']} var."
    user["gold"] -= item["price"]
    owned.append(item["id"])
    user[active_key] = item["id"]
    return True, f"'{item['name']}' satın alındı ve kullanılıyor."


# ----------------------------------------------------------------------
#  OYUN
# ----------------------------------------------------------------------
class Game:
    def __init__(self, user, level, lives_enabled, rng=None):
        self.user = user
        self.level = level
        self.lives_enabled = lives_enabled
        self.lives = LIVES[level]
        self.score = 0
        self.gold = 0
        self.correct = 0
        self.wrong = 0
        self.finished = False
        self.record = False
        self.rank_up = None
        rng = rng or random
        pool = []
        for idx, raw in enumerate(LEVELS[level]):
            steps = [p.strip() for p in raw.split("->") if p.strip()]
            if len(steps) >= 2:
                pool.append((idx, steps))
        rng.shuffle(pool)
        self.pool = pool
        self.word_id, self.steps = None, []
        self.hint_used = False

    # --- tur ---
    def next_word(self):
        """Sıradaki kelimeye geçer. Havuz bittiyse False."""
        if not self.pool:
            return False
        self.word_id, self.steps = self.pool.pop(0)
        self.hint_used = False
        return True

    @property
    def remaining(self):
        return len(self.pool) + 1

    @property
    def answer(self):
        return self.steps[-1]

    @property
    def can_hint(self):
        return (not self.hint_used) and len(self.steps) > 2

    def display(self):
        shown = self.steps[:-1] if self.hint_used else self.steps[:1]
        return "  →  ".join(shown) + "  →  ?"

    def _lose_life(self):
        if not self.lives_enabled:
            return False
        self.lives -= 1
        return self.lives <= 0

    # --- hamleler: sonuç sözlüğü döndürür ---
    def guess(self, text):
        g = tr_lower(text)
        if not g:
            return {"result": "empty"}
        if g == tr_lower(self.answer):
            self.correct += 1
            self.score += POINTS_CORRECT
            earned = 0
            if self.level == "kolay":
                earned = 10 if self.correct % 2 == 0 else 0
            elif self.level == "orta":
                earned = 10
            else:
                earned = 20
            if earned:
                self.gold += earned
                self.user["gold"] += earned
            return {"result": "correct", "gold": earned}
        self.wrong += 1
        penalty = WRONG_PENALTY[self.level]
        self.score -= penalty
        if self._lose_life():
            return {"result": "gameover", "penalty": penalty}
        return {"result": "wrong", "penalty": penalty}

    def use_hint(self):
        if not self.can_hint:
            return False
        self.hint_used = True
        self.score -= POINTS_HINT
        return True

    def reveal(self):
        self.score -= POINTS_REVEAL
        if self._lose_life():
            return {"result": "gameover"}
        return {"result": "revealed", "answer": self.answer}

    # --- bitiş: puanı hesaba işler (bir kez) ---
    def finish(self):
        u = self.user
        if not self.finished:
            self.finished = True
            old = rank_info(u["total_score"])[0]
            u["total_score"] += max(0, self.score)
            new = rank_info(u["total_score"])[0]
            self.rank_up = new if new != old else None
            self.record = self.score > u["best_score"]
            if self.record:
                u["best_score"] = self.score
        return {"score": self.score, "gold": self.gold, "correct": self.correct, "wrong": self.wrong,
                "best": u["best_score"], "total": u["total_score"],
                "record": self.record, "rank_up": self.rank_up}


# ----------------------------------------------------------------------
#  SİTE (Supabase)
# ----------------------------------------------------------------------
def _ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def site_rpc(name, payload, timeout=8):
    req = urllib.request.Request(
        SB_URL + "/rest/v1/rpc/" + name, data=json.dumps(payload).encode("utf-8"),
        headers={"apikey": SB_KEY, "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
        return json.loads(resp.read().decode("utf-8") or "null")


def ensure_site_token(user):
    """Hesaba gizli site anahtarı üretir. Yeni üretildiyse True (kaydedilmeli)."""
    if len(user.get("site_token") or "") >= 32:
        return False
    user["site_token"] = secrets.token_hex(32)
    return True


def sync_rank(username, token, total, best):
    """Puanı siteye gönderir, sıralamayı döndürür: (yazı, başarılı_mı)."""
    try:
        site_rpc("submit_score", {"p_username": username, "p_token": token,
                                  "p_total": int(total), "p_best": int(best)})
        rows = site_rpc("get_my_rank", {"p_username": username})
        if rows:
            r = rows[0] if isinstance(rows, list) else rows
            return f"Sıralama: #{r['rank']} / {r['total_players']}", True
        return "Sıralama: listede yok", True
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", "replace")
        except Exception:
            detail = ""
        if "forbidden" in detail:
            return "Bu ad sitede başka hesapta kayıtlı", False
        return f"Sıralama: bağlanamadı (HTTP {e.code})", False
    except Exception as e:
        return f"Sıralama: bağlanamadı ({type(e).__name__})", False


def delete_remote(username, token):
    try:
        site_rpc("delete_player", {"p_username": username, "p_token": token})
        return True
    except Exception:
        return False


def fetch_top(limit=100):
    try:
        rows = site_rpc("get_leaderboard", {"p_limit": limit})
        return rows if isinstance(rows, list) else []
    except Exception:
        return None
