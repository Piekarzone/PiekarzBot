import os
import socket
import json
import base64
import time
import requests
from dotenv import load_dotenv

# 1. Załaduj zmienne środowiskowe
load_dotenv()

TWITCH_SERVER  = "irc.chat.twitch.tv"
TWITCH_PORT    = 6667
TWITCH_TOKEN   = os.getenv("TWITCH_TOKEN")           # oauth:...
TWITCH_NICK    = os.getenv("TWITCH_NICK")            # piekarzonebot
TWITCH_CHANNEL = os.getenv("TWITCH_CHANNEL").lower() # piekarzone_
CHANNEL        = f"#{TWITCH_CHANNEL}"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")             # ghp_...
GITHUB_REPO  = os.getenv("GITHUB_REPO")              # piekarzone/PiekarzBot
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept":        "application/vnd.github.v3+json"
}

# 2. Lista dostępnych komend (tylko do !help)
komendy = {
    "!hello": "Przywitanie",
    "!help":  "Lista komend",
    "!zart":  "Losowy żart Chucka Norrisa",
    "!kot":   "Losowy kotek",
    "!boo":   "Dźwięk BOO",
    "!ding":  "Dźwięk DING"
}

def update_now_playing(sound_id: str):
    """
    Aktualizuje docs/now_playing.json w repozytorium,
    zapisując 'sound' oraz 'ts' (timestamp).
    """
    path    = "docs/now_playing.json"
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"

    # Pobierz bieżące SHA pliku
    r1 = requests.get(api_url, headers=HEADERS)
    r1.raise_for_status()
    sha = r1.json()["sha"]

    # Przygotuj nowy JSON z opcją dźwięku i timestampem
    payload_dict = {
        "sound": sound_id,
        "ts": int(time.time())
    }
    raw = json.dumps(payload_dict, separators=(",",":")).encode("utf-8")
    b64 = base64.b64encode(raw).decode("utf-8")

    body = {
        "message": f"now_playing → {sound_id}",
        "content": b64,
        "sha": sha
    }
    r2 = requests.put(api_url, headers=HEADERS, json=body)
    r2.raise_for_status()

def send_message(text: str):
    """Wyślij wiadomość na czacie Twitch."""
    sock.send(f"PRIVMSG {CHANNEL} :{text}\r\n".encode("utf-8"))

def is_admin(tags_line: str) -> bool:
    """
    Z tagów IRC wybiera pole 'badges' i sprawdza,
    czy jest moderator lub broadcaster.
    """
    if not tags_line:
        return False
    parsed = dict(item.split("=",1) for item in tags_line.split(";") if "=" in item)
    badges = parsed.get("badges", "")
    return "broadcaster" in badges or "moderator" in badges

# 3. Łączenie z IRC Twitch
sock = socket.socket()
sock.connect((TWITCH_SERVER, TWITCH_PORT))
for cmd in (
    f"PASS {TWITCH_TOKEN}",
    f"NICK {TWITCH_NICK}",
    "CAP REQ :twitch.tv/tags",
    "CAP REQ :twitch.tv/commands",
    "CAP REQ :twitch.tv/membership",
    f"JOIN {CHANNEL}"
):
    sock.send((cmd + "\r\n").encode("utf-8"))

# 4. Czekaj na potwierdzenie 001 (Welcome)
while True:
    line = sock.recv(1024).decode("utf-8", errors="ignore")
    if line.startswith("PING"):
        sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
    if " 001 " in line:
        send_message("🍞 Piekarzonebot gotowy!")
        break

# 5. Główna pętla obsługi czatu
while True:
    data = sock.recv(2048).decode("utf-8", errors="ignore")
    for raw in data.split("\r\n"):
        if not raw:
            continue
        if raw.startswith("PING"):
            sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
            continue
        if " PRIVMSG " not in raw:
            continue

        # Rozdziel tagi IRC od reszty
        if raw.startswith("@"):
            tags, rest = raw.split(" ", 1)
        else:
            tags, rest = "", raw

        parts = rest.split(" ", 3)
        if len(parts) < 4:
            continue
        prefix, _, _, trailing = parts
        message = trailing.lstrip(":").strip()
        user    = prefix.lstrip(":").split("!")[0].lower()

        # Obsługa komend
        if message == "!hello":
            send_message(f"Hej {user}, tu Piekarzonebot! 🥖")

        elif message == "!help":
            txt = "; ".join(f"{k} – {v}" for k, v in komendy.items())
            send_message(f"Komendy: {txt}")

        elif message == "!zart":
            try:
                r = requests.get("https://api.chucknorris.io/jokes/random", timeout=5)
                r.raise_for_status()
                joke = r.json().get("value", "")
                send_message(f"🥋 {joke}")
            except:
                send_message("😢 Nie udało się pobrać żartu")

        elif message == "!kot":
            try:
                r = requests.get("https://api.thecatapi.com/v1/images/search", timeout=5)
                r.raise_for_status()
                url = r.json()[0].get("url", "")
                send_message(f"🐱 {url}")
            except:
                send_message("😿 Nie udało się pobrać kotka")

        elif message in ("!boo", "!ding"):
            if is_admin(tags):
                sound = message.lstrip("!")         # np. "boo" lub "ding"
                update_now_playing(sound)           # zapisze sound + ts w JSON
                send_message(f"🎵 Puszczam dźwięk `{sound}`!")
            else:
                send_message(f"Sorry {user}, tylko admin może puszczać dźwięki.")