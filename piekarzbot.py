import os
import socket
import json
import base64
import requests
from dotenv import load_dotenv

# 1. Załaduj konfigurację
load_dotenv()
TWITCH_SERVER = "irc.chat.twitch.tv"
TWITCH_PORT = 6667
TWITCH_TOKEN = os.getenv("TWITCH_TOKEN")
TWITCH_NICK = os.getenv("TWITCH_NICK")
TWITCH_CHANNEL = os.getenv("TWITCH_CHANNEL").lower()
CHANNEL = f"#{TWITCH_CHANNEL}"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")  # format "User/Repo"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

komendy = {
    "!hello": "Przywitanie",
    "!help": "Lista komend",
    "!zart": "Losowy żart Chucka Norrisa",
    "!kot": "Link do kota",
    "!boo": "Dźwięk BOO",
    "!ding": "Dźwięk DING"
}

# 2. Funkcja aktualizująca now_playing.json
def update_now_playing(sound_id: str):
    path = "docs/now_playing.json"
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"

    # Pobierz bieżącą wersję pliku, by zdobyć sha
    resp_get = requests.get(api_url, headers=HEADERS)
    resp_get.raise_for_status()
    sha = resp_get.json()["sha"]

    content_dict = {"sound": sound_id}
    raw = json.dumps(content_dict, separators=(",", ":")).encode("utf-8")
    b64 = base64.b64encode(raw).decode("utf-8")

    payload = {
        "message": f"Update now_playing to {sound_id}",
        "content": b64,
        "sha": sha
    }
    resp_put = requests.put(api_url, headers=HEADERS, json=payload)
    resp_put.raise_for_status()

# 3. IRC: połączenie z Twitch
sock = socket.socket()
sock.connect((TWITCH_SERVER, TWITCH_PORT))
sock.send(f"PASS {TWITCH_TOKEN}\r\n".encode())
sock.send(f"NICK {TWITCH_NICK}\r\n".encode())
sock.send(f"JOIN {CHANNEL}\r\n".encode())
sock.send("CAP REQ :twitch.tv/tags\r\n".encode())
sock.send("CAP REQ :twitch.tv/commands\r\n".encode())
sock.send("CAP REQ :twitch.tv/membership\r\n".encode())

print(f"✅ Zalogowano jako {TWITCH_NICK} w {CHANNEL}")

def send_message(text: str):
    sock.send(f"PRIVMSG {CHANNEL} :{text}\r\n".encode())

def is_admin(tags: str) -> bool:
    if not tags:
        return False
    parsed = dict(item.split("=", 1) for item in tags.split(";") if "=" in item)
    badges = parsed.get("badges", "")
    return "broadcaster" in badges or "moderator" in badges

send_message("🍞 Piekarzobot gotowy do działania!")

# 4. Pętla główna: odbieranie i parsowanie
while True:
    data = sock.recv(2048).decode("utf-8", errors="ignore")
    for line in data.split("\r\n"):
        if not line:
            continue
        if line.startswith("PING"):
            sock.send("PONG :tmi.twitch.tv\r\n".encode())
            continue

        # Rozdziel tagi od reszty
        if line.startswith("@"):
            tags_part, remainder = line.split(" ", 1)
        else:
            tags_part = ""
            remainder = line

        parts = remainder.split(" ", 3)
        if len(parts) < 4:
            continue
        prefix, _, _, raw_msg = parts
        message = raw_msg.lstrip(":").strip()
        sender = prefix.lstrip(":").split("!")[0].lower()

        # Obsługa komend
        if message == "!hello":
            send_message(f"Hej {sender}, tu Twój piekarniczy bot! 🥖")

        elif message == "!help":
            send_message("Komendy: " + "; ".join(f"{cmd} – {desc}"
                                                for cmd, desc in komendy.items()))

        elif message == "!zart":
            try:
                joke_resp = requests.get("https://api.chucknorris.io/jokes/random", timeout=5)
                joke_resp.raise_for_status()
                joke = joke_resp.json().get("value", "")
                send_message(f"🥋 Chuck mówi: {joke}")
            except Exception as joke_error:
                print("❌ Błąd żartu:", joke_error)
                send_message("Nie udało się pobrać żartu 😢")

        elif message == "!kot":
            try:
                cat_resp = requests.get("https://api.thecatapi.com/v1/images/search", timeout=5)
                cat_resp.raise_for_status()
                url = cat_resp.json()[0].get("url", "")
                send_message(f"Kotek: {url}")
            except Exception as cat_error:
                print("🐱 Błąd kota:", cat_error)
                send_message("Nie udało się pobrać kotka 🐾")

        elif message in ("!boo", "!ding"):
            if is_admin(tags_part):
                sound_id = message.lstrip("!")
                update_now_playing(sound_id)
                send_message(f"🎵 Puszczam dźwięk `{sound_id}`!")
            else:
                send_message(f"Sorry {sender}, tylko admin może uruchamiać dźwięki!")