import os
import socket
import requests
from dotenv import load_dotenv
from obswebsocket import obsws, requests as obs_requests

# 1. Wczytanie zmiennych środowiskowych
load_dotenv()
TWITCH_SERVER = "irc.chat.twitch.tv"
TWITCH_PORT = 6667
TWITCH_TOKEN = os.getenv("TWITCH_TOKEN")
TWITCH_NICK = os.getenv("TWITCH_NICK")
TWITCH_CHANNEL = os.getenv("TWITCH_CHANNEL").lower()
CHANNEL = f"#{TWITCH_CHANNEL}"

OBS_HOST = os.getenv("OBS_HOST")         # np. "0.tcp.eu.ngrok.io"
OBS_PORT = int(os.getenv("OBS_PORT"))    # np. 17000
OBS_PASS = os.getenv("OBS_PASS")         # hasło ustawione w obs-websocket

# 2. Komendy bota
komendy = {
    "!hello": "Bot wita się",
    "!help": "Pokazuje listę komend",
    "!zart": "Losowy żart Chucka Norrisa",
    "!kot": "Link do losowego kota",
    "!dzwiek": "Puszcza dźwięk (tylko admin)"
}

# 3. Połączenie z OBS przez obs-websocket
ws = obsws(OBS_HOST, OBS_PORT, OBS_PASS)
try:
    ws.connect()
    print(f"🔌 Połączono z OBS: {OBS_HOST}:{OBS_PORT}")
except Exception as obs_error:
    print("❌ Błąd połączenia z OBS:", obs_error)

def play_obs_sound(source_name: str):
    """Restartuje wskazany Media Source w OBS, by odtworzyć dźwięk."""
    try:
        ws.call(obs_requests.RestartMedia(sourceName=source_name))
    except Exception as playback_error:
        print("❌ Błąd odtwarzania źródła w OBS:", playback_error)

def wyslij_wiadomosc(tresc: str):
    sock.send(f"PRIVMSG {CHANNEL} :{tresc}\r\n".encode("utf-8"))

def czy_admin(tags_str: str) -> bool:
    if not tags_str:
        return False
    parsed_tags = dict(item.split("=", 1) for item in tags_str.split(";") if "=" in item)
    badge_info = parsed_tags.get("badges", "")
    return "broadcaster" in badge_info or "moderator" in badge_info

# 4. Połączenie IRC Twitch
sock = socket.socket()
sock.connect((TWITCH_SERVER, TWITCH_PORT))
sock.send(f"PASS {TWITCH_TOKEN}\r\n".encode())
sock.send(f"NICK {TWITCH_NICK}\r\n".encode())
sock.send(f"JOIN {CHANNEL}\r\n".encode())

sock.send("CAP REQ :twitch.tv/tags\r\n".encode())
sock.send("CAP REQ :twitch.tv/commands\r\n".encode())
sock.send("CAP REQ :twitch.tv/membership\r\n".encode())

print(f"✅ Bot zalogowany jako {TWITCH_NICK} i dołączył do {CHANNEL}.")
wyslij_wiadomosc("Cześć wszystkim! Piekarzobot 🍞🤖 jest gotowy!")

# 5. Główna pętla
while True:
    data = sock.recv(2048).decode("utf-8", errors="ignore")
    for linia in data.split("\r\n"):
        if not linia:
            continue

        if linia.startswith("PING"):
            sock.send("PONG :tmi.twitch.tv\r\n".encode())
            continue

        # Podział linii IRC: tagi, prefix i wiadomość
        if linia.startswith("@"):
            tags_section, raw_line = linia.split(" ", 1)
        else:
            tags_section = ""
            raw_line = linia

        czesci = raw_line.split(" ", 3)
        if len(czesci) < 4:
            continue

        prefix, komenda_irc, cel, tresc_wiadomosci = czesci
        wiadomosc = tresc_wiadomosci.lstrip(":").strip()
        nadawca = prefix.lstrip(":").split("!")[0].lower()

        # Obsługa komend
        if wiadomosc == "!hello":
            wyslij_wiadomosc(f"Siema {nadawca}, tu Piekarzobot!")

        elif wiadomosc == "!help":
            lista = "; ".join(f"{cmd} - {desc}" for cmd, desc in komendy.items())
            wyslij_wiadomosc("Komendy: " + lista)

        elif wiadomosc == "!zart":
            try:
                api_response = requests.get("https://api.chucknorris.io/jokes/random", timeout=5)
                api_response.raise_for_status()
                zart = api_response.json().get("value", "Chuck Norris milczy...")
                wyslij_wiadomosc(f"Chuck mówi: {zart}")
            except Exception as joke_error:
                print("❌ Żart error:", joke_error)
                wyslij_wiadomosc("Nie udało się pobrać żartu 😢")

        elif wiadomosc == "!kot":
            try:
                cat_response = requests.get("https://api.thecatapi.com/v1/images/search", timeout=5)
                cat_response.raise_for_status()
                cat_url = cat_response.json()[0].get("url", "")
                wyslij_wiadomosc(f"Kotek: {cat_url}")
            except Exception as cat_error:
                print("🐱 Błąd kota:", cat_error)
                wyslij_wiadomosc("Nie udało się pobrać kota 🐾")

        elif wiadomosc == "!dzwiek":
            if czy_admin(tags_section):
                play_obs_sound("dzwiek_bot")
                wyslij_wiadomosc("🎵 Puszczam dźwięk na streamie!")
            else:
                wyslij_wiadomosc(f"Sorry {nadawca}, tylko admin może puszczać dźwięki!")