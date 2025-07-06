# 💡 Propozycja zmian:
# 1️⃣ Dodać printy do konsoli, które pokażą:
#     ✅ kiedy bot łączy się z serwerem Twitch
#     ✅ kiedy bot dołącza do kanału
#     ✅ każdą wiadomość z czatu (kto i co napisał)
# 2️⃣ Nic w logice bota się nie zmienia – to tylko więcej informacji w konsoli dla Ciebie.
# Czy wprowadzić te zmiany?

import os
import socket
import json
import base64
import time
import requests
from dotenv import load_dotenv
from typing import Optional

load_dotenv()
TWITCH_SERVER  = "irc.chat.twitch.tv"
TWITCH_PORT    = 6667
TWITCH_TOKEN: Optional[str] = os.getenv("TWITCH_TOKEN")
TWITCH_NICK: Optional[str] = os.getenv("TWITCH_NICK")

# Ensure TWITCH_CHANNEL is set and lowercase it safely
twitch_channel_env: Optional[str] = os.getenv("TWITCH_CHANNEL")
if twitch_channel_env is None:
    raise ValueError("Environment variable TWITCH_CHANNEL is not set")
TWITCH_CHANNEL: str = twitch_channel_env.lower()
CHANNEL        = f"#{TWITCH_CHANNEL}"

GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN")
GITHUB_REPO: Optional[str] = os.getenv("GITHUB_REPO")
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept":        "application/vnd.github.v3+json"
}

komendy = {
    "!hello":    "Przywitanie",
    "!help":     "Lista komend",
    "!zart":     "Losowy żart Chucka Norrisa",
    "!kot":      "Losowy kotek",
    "!wyznanie": "Dźwięk WYZNANIE",
    "!ding":     "Dźwięk DING"
}

last_played_sound = {"sound": None}

def update_now_playing(sound_id: str):
    path    = "docs/now_playing.json"
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"

    response1 = requests.get(api_url, headers=HEADERS)
    response1.raise_for_status()
    sha = response1.json().get("sha")

    payload = {"sound": sound_id, "ts": int(time.time())}
    encoded_payload = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    b64_content = base64.b64encode(encoded_payload).decode("utf-8")

    body = {
        "message": f"now_playing → {sound_id}",
        "content": b64_content,
        "sha": sha
    }
    response2 = requests.put(api_url, headers=HEADERS, json=body)
    response2.raise_for_status()
    last_played_sound["sound"] = sound_id

def send_message(text: str):
    print(f"[SEND] {text}")
    sock.send(f"PRIVMSG {CHANNEL} :{text}\r\n".encode("utf-8"))

def is_admin(tags_line: str) -> bool:
    if not tags_line:
        return False
    parsed = dict(item.split("=",1) for item in tags_line.split(";") if "=" in item)
    badges = parsed.get("badges", "")
    return "broadcaster" in badges or "moderator" in badges

# Połączenie z IRC
print("[INFO] Łączenie z Twitch IRC...")
sock = socket.socket()
sock.connect((TWITCH_SERVER, TWITCH_PORT))
print("[INFO] Połączono z Twitch IRC.")
for cmd in (
    f"PASS {TWITCH_TOKEN}",
    f"NICK {TWITCH_NICK}",
    "CAP REQ :twitch.tv/tags",
    "CAP REQ :twitch.tv/commands",
    "CAP REQ :twitch.tv/membership",
    f"JOIN {CHANNEL}"
):
    sock.send((cmd + "\r\n").encode("utf-8"))
print(f"[INFO] Dołączono do kanału {CHANNEL}")

# Powitanie (001)
while True:
    line = sock.recv(1024).decode("utf-8", errors="ignore")
    if line.startswith("PING"):
        sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
    if " 001 " in line:
        send_message("🍞 Piekarzonebot gotowy!")
        break

# Obsługa czatu
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

        if raw.startswith("@"):
            tags, rest = raw.split(" ",1)
        else:
            tags, rest = "", raw

        parts = rest.split(" ",3)
        if len(parts) < 4:
            continue
        prefix, _, _, trailing = parts
        message = trailing.lstrip(":").strip()
        user    = prefix.lstrip(":").split("!")[0].lower()

        print(f"[CHAT] <{user}> {message}")

        if message == "!hello":
            send_message(f"Hej {user}, tu Piekarzonebot! 🥖")

        elif message == "!help":
            txt = "; ".join(f"{k} – {v}" for k,v in komendy.items())
            send_message(f"Komendy: {txt}")

        elif message == "!zart":
            try:
                r = requests.get("https://api.chucknorris.io/jokes/random", timeout=5)
                r.raise_for_status()
                send_message(f"🥋 {r.json().get('value','')}")
            except requests.RequestException:
                send_message("😢 Nie udało się pobrać żartu")

        elif message == "!kot":
            try:
                r = requests.get("https://api.thecatapi.com/v1/images/search", timeout=5)
                r.raise_for_status()
                send_message(f"🐱 {r.json()[0].get('url','')}")
            except requests.RequestException:
                send_message("😿 Nie udało się pobrać kotka")

        elif message in ("!wyznanie", "!ding"):
            if is_admin(tags):
                sound = "wyznanie" if message == "!wyznanie" else "ding"
                update_now_playing(sound)
                send_message(f"🎵 Puszczam dźwięk `{sound}`!")
            else:
                send_message(f"⚠️ Sorry {user}, tylko admin może puszczać dźwięki.")
