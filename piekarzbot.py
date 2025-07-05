import os
import socket
import json
import base64
import requests
from dotenv import load_dotenv

# 1. Załaduj zmienne środowiskowe z .env
load_dotenv()

TWITCH_SERVER  = "irc.chat.twitch.tv"
TWITCH_PORT    = 6667
TWITCH_TOKEN   = os.getenv("TWITCH_TOKEN")           # oauth:xxxxxx
TWITCH_NICK    = os.getenv("TWITCH_NICK")            # piekarzonebot
TWITCH_CHANNEL = os.getenv("TWITCH_CHANNEL").lower() # piekarzone_
CHANNEL        = f"#{TWITCH_CHANNEL}"

GITHUB_TOKEN   = os.getenv("GITHUB_TOKEN")
GITHUB_REPO    = os.getenv("GITHUB_REPO")            # piekarzone/PiekarzBot

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# 2. Lista komend czatowych
komendy = {
    "!hello": "Przywitanie",
    "!help": "Lista komend",
    "!zart": "Żart Chucka Norrisa",
    "!kot": "Losowy kotek",
    "!boo": "Dźwięk BOO",
    "!ding": "Dźwięk DING"
}

def update_now_playing(sound_id: str):
    """
    Aktualizuje now_playing.json w repo, by player.html odtworzył dźwięk.
    """
    path = "docs/now_playing.json"
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"

    response = requests.get(api_url, headers=HEADERS)
    response.raise_for_status()
    sha = response.json()["sha"]

    content_json = json.dumps({"sound": sound_id}, separators=(",", ":"))
    content_b64 = base64.b64encode(content_json.encode("utf-8")).decode("utf-8")

    payload = {
        "message": f"now_playing → {sound_id}",
        "content": content_b64,
        "sha": sha
    }

    update = requests.put(api_url, headers=HEADERS, json=payload)
    update.raise_for_status()

def send_message(text: str):
    sock.send(f"PRIVMSG {CHANNEL} :{text}\r\n".encode("utf-8"))

def is_admin(tags_line: str) -> bool:
    if not tags_line:
        return False
    parsed = dict(item.split("=",1) for item in tags_line.split(";") if "=" in item)
    badges = parsed.get("badges", "")
    return "broadcaster" in badges or "moderator" in badges

# 3. Połączenie z IRC
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

# 4. Inicjalne potwierdzenie
while True:
    line = sock.recv(1024).decode("utf-8", errors="ignore")
    if line.startswith("PING"):
        sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
    if " 001 " in line:
        send_message("🍞 Piekarzonebot gotowy!")
        break

# 5. Pętla główna
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
            tags_part, rest = raw.split(" ", 1)
        else:
            tags_part, rest = "", raw

        parts = rest.split(" ", 3)
        if len(parts) < 4:
            continue

        prefix, _, _, trailing = parts
        message = trailing.lstrip(":").strip()
        user = prefix.lstrip(":").split("!")[0].lower()

        # Komendy
        if message == "!hello":
            send_message(f"Hej {user}, tu Piekarzonebot! 🥖")

        elif message == "!help":
            send_message("Komendy: " + "; ".join(f"{k} – {v}" for k, v in komendy.items()))

        elif message == "!zart":
            try:
                r = requests.get("https://api.chucknorris.io/jokes/random", timeout=5)
                r.raise_for_status()
                joke = r.json().get("value", "")
                send_message(f"🥋 Chuck mówi: {joke}")
            except:
                send_message("😢 Nie udało się pobrać żartu")

        elif message == "!kot":
            try:
                r = requests.get("https://api.thecatapi.com/v1/images/search", timeout=5)
                r.raise_for_status()
                url = r.json()[0].get("url", "")
                send_message(f"🐱 Kotek: {url}")
            except:
                send_message("😿 Nie udało się pobrać kotka")

        elif message in ("!boo", "!ding"):
            if is_admin(tags_part):
                update_now_playing(message.lstrip("!"))
                send_message(f"🎵 Puszczam dźwięk `{message[1:]}`!")
            else:
                send_message(f"Sorry {user}, tylko admin może puszczać dźwięki.")
