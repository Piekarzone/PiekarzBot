import os
import socket
import json
import base64
import requests
from dotenv import load_dotenv

# 1. Załaduj zmienne środowiskowe
load_dotenv()

TWITCH_SERVER = "irc.chat.twitch.tv"
TWITCH_PORT   = 6667
TWITCH_TOKEN  = os.getenv("TWITCH_TOKEN")      # oauth:xxxxxx
TWITCH_NICK   = os.getenv("TWITCH_NICK")       # piekarzonebot
TWITCH_CHANNEL= os.getenv("TWITCH_CHANNEL").lower()  # piekarzone_
CHANNEL       = f"#{TWITCH_CHANNEL}"

GITHUB_TOKEN  = os.getenv("GITHUB_TOKEN")      # ghp_xxxxxx
GITHUB_REPO   = os.getenv("GITHUB_REPO")       # piekarzone/PiekarzBot
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept":        "application/vnd.github.v3+json"
}

# 2. Komendy i helpery
komendy = {
    "!hello": "Przywitanie",
    "!help":  "Lista komend",
    "!zart":  "Losowy żart Chucka Norrisa",
    "!kot":   "Link do losowego kota",
    "!boo":   "Dźwięk BOO",
    "!ding":  "Dźwięk DING"
}

def update_now_playing(sound_id: str):
    """
    Nadpisuje docs/now_playing.json w repozytorium,
    aby player.html u streamera odtworzył wskazany sound_id.
    """
    path    = "docs/now_playing.json"
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"

    # Pobierz bieżącą wersję pliku
    resp_get = requests.get(api_url, headers=HEADERS)
    resp_get.raise_for_status()
    sha = resp_get.json()["sha"]

    # Przygotuj nowe dane
    payload_content = json.dumps({"sound": sound_id}, separators=(",",":")).encode("utf-8")
    b64_content     = base64.b64encode(payload_content).decode("utf-8")

    # Wyślij aktualizację
    payload = {
        "message": f"Update now_playing → {sound_id}",
        "content": b64_content,
        "sha":     sha
    }
    resp_put = requests.put(api_url, headers=HEADERS, json=payload)
    resp_put.raise_for_status()

def send_message(text: str):
    sock.send(f"PRIVMSG {CHANNEL} :{text}\r\n".encode("utf-8"))

def is_admin(tags: str) -> bool:
    if not tags:
        return False
    parsed = dict(item.split("=",1) for item in tags.split(";") if "=" in item)
    badges = parsed.get("badges","")
    return "broadcaster" in badges or "moderator" in badges

# 3. Połączenie z Twitch IRC
sock = socket.socket()
sock.connect((TWITCH_SERVER, TWITCH_PORT))
for cmd in (
    f"PASS {TWITCH_TOKEN}",
    f"NICK {TWITCH_NICK}",
    f"JOIN {CHANNEL}",
    "CAP REQ :twitch.tv/tags",
    "CAP REQ :twitch.tv/commands",
    "CAP REQ :twitch.tv/membership"
):
    sock.send((cmd + "\r\n").encode("utf-8"))

print(f"✅ {TWITCH_NICK} zalogowany w {CHANNEL}")
send_message("🍞 Piekarzonebot gotowy do działania!")

# 4. Główna pętla odbioru i obsługi komend
while True:
    data = sock.recv(2048).decode("utf-8", errors="ignore")
    for line in data.split("\r\n"):
        if not line:
            continue

        # PING/pong
        if line.startswith("PING"):
            sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
            continue

        # Rozdziel tagi od reszty wiadomości
        if line.startswith("@"):
            tags_part, rest = line.split(" ", 1)
        else:
            tags_part, rest = "", line

        parts = rest.split(" ", 3)
        if len(parts) < 4:
            continue
        prefix, _, _, raw_message = parts
        message = raw_message.lstrip(":").strip()
        user    = prefix.lstrip(":").split("!")[0].lower()

        # Obsługa komend
        if message == "!hello":
            send_message(f"Hej {user}, tu Piekarzonebot! 🥖")

        elif message == "!help":
            help_text = "; ".join(f"{cmd} – {desc}" for cmd, desc in komendy.items())
            send_message("Komendy: " + help_text)

        elif message == "!zart":
            try:
                r = requests.get("https://api.chucknorris.io/jokes/random", timeout=5)
                r.raise_for_status()
                joke = r.json().get("value", "")
                send_message(f"🥋 Chuck mówi: {joke}")
            except Exception as joke_error:
                print("❌ Błąd żartu:", joke_error)
                send_message("😢 Nie udało się pobrać żartu")

        elif message == "!kot":
            try:
                r = requests.get("https://api.thecatapi.com/v1/images/search", timeout=5)
                r.raise_for_status()
                url = r.json()[0].get("url", "")
                send_message(f"🐱 Kotek: {url}")
            except Exception as cat_error:
                print("❌ Błąd kota:", cat_error)
                send_message("🐾 Nie udało się pobrać kotka")

        elif message in ("!boo", "!ding"):
            if is_admin(tags_part):
                sound_id = message.lstrip("!")
                update_now_playing(sound_id)
                send_message(f"🎵 Puszczam dźwięk `{sound_id}`!")
            else:
                send_message(f"Sorry {user}, tylko admin może puszczać dźwięki!")