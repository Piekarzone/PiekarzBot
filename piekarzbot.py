import os
import socket
import requests
from dotenv import load_dotenv
from obswebsocket import obsws, requests as obs_requests

# 1. Załaduj .env
load_dotenv()
TWITCH_SERVER = "irc.chat.twitch.tv"
TWITCH_PORT = 6667
TWITCH_TOKEN = os.getenv("TWITCH_TOKEN")
TWITCH_NICK = os.getenv("TWITCH_NICK")
TWITCH_CHANNEL = os.getenv("TWITCH_CHANNEL").lower()
CHANNEL = f"#{TWITCH_CHANNEL}"

OBS_HOST = os.getenv("OBS_HOST")
OBS_PORT = int(os.getenv("OBS_PORT"))
OBS_PASS = os.getenv("OBS_PASS")

# 2. Komendy
komendy = {
    "!hello": "Przywitanie",
    "!help": "Lista komend",
    "!zart": "Losowy żart Chucka Norrisa",
    "!kot": "Link do kota",
    "!boo": "Puszcza dźwięk BOO"
}

# 3. Połączenie z OBS (Browser Source)
ws = obsws(OBS_HOST, OBS_PORT, OBS_PASS)
try:
    ws.connect()
    print(f"🔌 Połączono z OBS: {OBS_HOST}:{OBS_PORT}")
except Exception as obs_connection_error:
    print("❌ Nie udało się połączyć z OBS:", obs_connection_error)

def play_remote_audio(sound_id: str):
    """
    Zmienia URL Browser Source w OBS, by odtworzyć dźwięk z chmury.
    """
    base_url = "https://twojanazwa.github.io/player.html"  # <- ZMIEŃ NA WŁASNY URL
    url = f"{base_url}?sound={sound_id}"
    try:
        ws.call(obs_requests.SetBrowserSourceProperties(
            sourceName="remote_audio",
            url=url
        ))
        print(f"🔊 Ustawiono URL dźwięku: {url}")
    except Exception as obs_url_error:
        print("❌ Błąd przy ustawianiu URL:", obs_url_error)

def wyslij_wiadomosc(tresc: str):
    sock.send(f"PRIVMSG {CHANNEL} :{tresc}\r\n".encode("utf-8"))

def czy_admin(tags_str: str) -> bool:
    if not tags_str:
        return False
    parsed = dict(x.split("=", 1) for x in tags_str.split(";") if "=" in x)
    badges = parsed.get("badges", "")
    return "broadcaster" in badges or "moderator" in badges

# 4. Połącz z IRC Twitch
sock = socket.socket()
sock.connect((TWITCH_SERVER, TWITCH_PORT))
sock.send(f"PASS {TWITCH_TOKEN}\r\n".encode())
sock.send(f"NICK {TWITCH_NICK}\r\n".encode())
sock.send(f"JOIN {CHANNEL}\r\n".encode())
sock.send("CAP REQ :twitch.tv/tags\r\n".encode())
sock.send("CAP REQ :twitch.tv/commands\r\n".encode())
sock.send("CAP REQ :twitch.tv/membership\r\n".encode())

print(f"✅ Zalogowano jako {TWITCH_NICK} na {CHANNEL}")
wyslij_wiadomosc("🍞 Piekarzobot wita wszystkich!")

# 5. Pętla główna
while True:
    dane = sock.recv(2048).decode("utf-8", errors="ignore")
    for linia in dane.split("\r\n"):
        if not linia:
            continue
        if linia.startswith("PING"):
            sock.send("PONG :tmi.twitch.tv\r\n".encode())
            continue

        # Rozbij tagi i wiadomość
        if linia.startswith("@"):
            tags_part, content = linia.split(" ", 1)
        else:
            tags_part = ""
            content = linia

        parts = content.split(" ", 3)
        if len(parts) < 4:
            continue

        prefix, _, _, wiadomosc_raw = parts
        wiadomosc = wiadomosc_raw.lstrip(":").strip()
        uzytkownik = prefix.lstrip(":").split("!")[0].lower()

        # Reakcje na komendy
        if wiadomosc == "!hello":
            wyslij_wiadomosc(f"Hej {uzytkownik}, tu Twój piekarniczy bot! 🥖")

        elif wiadomosc == "!help":
            tekst = "Komendy: " + "; ".join(f"{cmd} – {desc}" for cmd, desc in komendy.items())
            wyslij_wiadomosc(tekst)

        elif wiadomosc == "!zart":
            try:
                res = requests.get("https://api.chucknorris.io/jokes/random", timeout=5)
                res.raise_for_status()
                joke = res.json().get("value", "")
                wyslij_wiadomosc(f"🥋 Chuck mówi: {joke}")
            except Exception as zart_error:
                print("❌ Żart error:", zart_error)
                wyslij_wiadomosc("Nie udało się pobrać żartu 😢")

        elif wiadomosc == "!kot":
            try:
                res = requests.get("https://api.thecatapi.com/v1/images/search", timeout=5)
                res.raise_for_status()
                kotek = res.json()[0].get("url", "")
                wyslij_wiadomosc(f"Kotek: {kotek}")
            except Exception as kot_error:
                print("🐱 Błąd kota:", kot_error)
                wyslij_wiadomosc("Nie udało się pobrać kotka 🐾")

        elif wiadomosc == "!boo":
            if czy_admin(tags_part):
                play_remote_audio("boo")
                wyslij_wiadomosc("💥 Puszczam BOO z GitHuba!")
            else:
                wyslij_wiadomosc(f"Sorry {uzytkownik}, to komenda tylko dla admina.")