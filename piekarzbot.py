import os
import socket
import json
import base64
import time
import requests
from dotenv import load_dotenv

# 1. Załaduj .env
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
    Aktualizuje now_playing.json z polem sound + ts.
    """
    path    = "docs/now_playing.json"
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"

    # 1) pobierz SHA
    r1 = requests.get(api_url, headers=HEADERS); r1.raise_for_status()
    sha = r1.json()["sha"]

    # 2) przygotuj nowy JSON z timestampem
    payload_dict = {
        "sound": sound_id,
        "ts": int(time.time())
    }
    raw  = json.dumps(payload_dict, separators=(",",":")).encode("utf-8")
    b64  = base64.b64encode(raw).decode("utf-8")

    # 3) wyślij update
    payload = {"message": f"now_playing → {sound_id}", "content": b64, "sha": sha}
    r2 = requests.put(api_url, headers=HEADERS, json=payload)
    r2.raise_for_status()

def send_message(text: str):
    sock.send(f"PRIVMSG {CHANNEL} :{text}\r\n".encode("utf-8"))

def is_admin(tags_line: str) -> bool:
    if not tags_line: return False
    parsed = dict(item.split("=",1) for item in tags_line.split(";") if "=" in item)
    badges = parsed.get("badges","")
    return "broadcaster" in badges or "moderator" in badges

# Połącz do IRC
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

# Poczekaj na powitanie (001)
while True:
    line = sock.recv(1024).decode("utf-8", errors="ignore")
    if line.startswith("PING"):
        sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
    if " 001 " in line:
        send_message("🍞 Piekarzonebot gotowy!")
        break

# Główna pętla
while True:
    data = sock.recv(2048).decode("utf-8", errors="ignore")
    for raw in data.split("\r\n"):
        if not raw: continue
        if raw.startswith("PING"):
            sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
            continue
        if " PRIVMSG " not in raw: continue

        if raw.startswith("@"):
            tags, rest = raw.split(" ",1)
        else:
            tags, rest = "", raw

        parts = rest.split(" ",3)
        if len(parts) < 4: continue
        prefix, _, _, trailing = parts
        message = trailing.lstrip(":").strip()
        user    = prefix.lstrip(":").split("!")[0].lower()

        if message == "!hello":
            send_message(f"Hej {user}, tu Piekarzonebot! 🥖")

        elif message == "!help":
            send_message("Komendy: " + "; ".join(f"{k} – {v}" for k,v in komendy.items()))

        elif message == "!zart":
            try:
                r = requests.get("https://api.chucknorris.io/jokes/random", timeout=5); r.raise_for_status()
                send_message(f"🥋 {r.json().get('value','')}")
            except:
                send_message("😢 Nie udało się pobrać żartu")

        elif message == "!kot":
            try:
                r = requests.get("https://api.thecatapi.com/v1/images/search", timeout=5); r.raise_for_status()
                send_message(f"🐱 {r.json()[0].get('url','')}")
            except:
                send_message("😿 Nie udało się pobrać kotka")

        elif message in ("!boo","!ding"):
            if is_admin(tags):
                update_now_playing(message.lstrip("!"))
                send_message(f"🎵 Puszczam dźwięk `{message[1:]}`!")
            else:
                send_message(f"Sorry {user}, tylko admin może puszczać dźwięki.")