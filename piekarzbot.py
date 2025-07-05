import os
import socket
import requests
from dotenv import load_dotenv

load_dotenv()
TWITCH_SERVER  = "irc.chat.twitch.tv"
TWITCH_PORT    = 6667
TWITCH_TOKEN   = os.getenv("TWITCH_TOKEN")
TWITCH_NICK    = os.getenv("TWITCH_NICK")        # piekarzonebot
TWITCH_CHANNEL = os.getenv("TWITCH_CHANNEL").lower()  # piekarzone_
CHANNEL        = f"#{TWITCH_CHANNEL}"

# Połącz i uwierzytelnij się
sock = socket.socket()
sock.connect((TWITCH_SERVER, TWITCH_PORT))
sock.send(f"PASS {TWITCH_TOKEN}\r\n".encode())
sock.send(f"NICK {TWITCH_NICK}\r\n".encode())

# Zgłaszamy, że chcemy dostać tagi, komendy i membership
sock.send("CAP REQ :twitch.tv/tags\r\n".encode())
sock.send("CAP REQ :twitch.tv/commands\r\n".encode())
sock.send("CAP REQ :twitch.tv/membership\r\n".encode())

# Dołączenie do kanału
sock.send(f"JOIN {CHANNEL}\r\n".encode())
print(f"✅ {TWITCH_NICK} zalogowany w {CHANNEL}")

def send(msg: str):
    sock.send(f"PRIVMSG {CHANNEL} :{msg}\r\n".encode())

send("🍞 Piekarzonebot gotowy!")

while True:
    data = sock.recv(2048).decode("utf-8", errors="ignore")
    for line in data.split("\r\n"):
        if not line:
            continue

        # Debug: pokaż surową linijkę
        print("<<<", line)

        # Odpowiadamy na PING
        if line.startswith("PING"):
            sock.send("PONG :tmi.twitch.tv\r\n".encode())
            print(">>> Wysłałem PONG")
            continue

        # Łapiemy tylko PRIVMSG
        if " PRIVMSG " not in line:
            continue

        # Wyciągnięcie nicku i treści
        # Format: [@tags ]:nick!user@host PRIVMSG #chan :wiadomość
        # Najpierw split na część z tagami i resztę
        if line.startswith("@"):
            tags_part, rest = line.split(" ", 1)
        else:
            tags_part, rest = "", line

        # Teraz res zawiera ":nick!user@host PRIVMSG #chan :wiadomosc"
        try:
            prefix, command, target, msg = rest.split(" ", 3)
        except ValueError:
            print("!!! Nie udało się rozbić:", rest)
            continue

        nick    = prefix.lstrip(":").split("!")[0]
        message = msg.lstrip(":")
        print(f"MSG from {nick}: {message} (tags={tags_part})")

        # Obsługa komend
        if message.strip() == "!kot":
            # Testujemy od razu wykonanie
            try:
                cat = requests.get("https://api.thecatapi.com/v1/images/search", timeout=5)
                cat.raise_for_status()
                url = cat.json()[0].get("url", "")
                print("🐱 Odp: ", url)
                send(f"Kotek: {url}")
            except Exception as err:
                print("❌ Błąd przy pobieraniu kota:", err)
                send("Nie udało się pobrać kotka 🐱")
