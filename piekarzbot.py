import os
import socket
import ssl
import json
import time
from dotenv import load_dotenv
from flask import Flask, jsonify
import threading

# 🍞 Mini serwer HTTP dla Render (nasłuchuje na PORT z Render)
app = Flask(__name__)

current_sound = {"sound": "", "ts": 0}  # przechowuje aktualny dźwięk

@app.route('/')
def index():
    return "🍞 PiekarzBot działa 24/7 na Render!"

@app.route('/now_playing')
def now_playing():
    return jsonify(current_sound)

def run_web():
    port = int(os.environ.get('PORT', 10000))  # Render przekazuje PORT jako zmienną
    app.run(host='0.0.0.0', port=port)

# Start serwera Flask w osobnym wątku
threading.Thread(target=run_web).start()

# 🔥 PiekarzBot IRC logic
load_dotenv()
TWITCH_SERVER  = "irc.chat.twitch.tv"
TWITCH_PORT    = 6697  # SSL port
TWITCH_TOKEN   = os.getenv("TWITCH_TOKEN")
TWITCH_NICK    = os.getenv("TWITCH_NICK")
TWITCH_CHANNEL = os.getenv("TWITCH_CHANNEL").lower()
CHANNEL        = f"#{TWITCH_CHANNEL}"

komendy = {
    "!hello":       "Przywitanie",
    "!help":        "Lista komend",
    "!zart":        "Losowy żart Chucka Norrisa",
    "!kot":         "Losowy kotek",
    "!wyznanie":    "Dźwięk WYZNANIE",
    "!niestreamer": "Dźwięk NIESTREAMER"
}

def update_now_playing(sound_id: str):
    # Aktualizacja zmiennej globalnej dla playera
    current_sound["sound"] = sound_id
    current_sound["ts"] = int(time.time())

def send_message(text: str):
    sock.send(f"PRIVMSG {CHANNEL} :{text}\r\n".encode("utf-8"))

def is_admin(tags_line: str) -> bool:
    if not tags_line:
        return False
    parsed = dict(item.split("=",1) for item in tags_line.split(";") if "=" in item)
    badges = parsed.get("badges", "")
    return "broadcaster" in badges or "moderator" in badges

# Połączenie z IRC przez SSL
context = ssl.create_default_context()
sock = context.wrap_socket(socket.socket(), server_hostname=TWITCH_SERVER)
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
        user    = prefix.lstrip(":").split("!",1)[0].lower()

        if message == "!hello":
            send_message(f"Hej {user}, tu Piekarzonebot! 🥖")

        elif message == "!help":
            txt = "; ".join(f"{k} – {v}" for k,v in komendy.items())
            send_message(f"Komendy: {txt}")

        elif message == "!zart":
            update_now_playing("api:joke")
            send_message("🥋 Pobieram żart...")

        elif message == "!kot":
            update_now_playing("api:cat")
            send_message("🐱 Pobieram kotka...")

        elif message in ("!wyznanie", "!niestreamer"):
            if is_admin(tags):
                sound = "wyznanie" if message == "!wyznanie" else "niestreamer"
                update_now_playing(sound)
                send_message(f"🎵 Puszczam dźwięk `{sound}`!")
            else:
                send_message(f"⚠️ Sorry {user}, tylko admin może puszczać dźwięki.")
