import requests
import socket
from dotenv import load_dotenv
import os
load_dotenv()

# KONFIGURACJA:
server = 'irc.chat.twitch.tv'
port = 6667
token = os.getenv("TWITCH_TOKEN")
nickname = os.getenv("TWITCH_NICK")
channel = "#" + os.getenv("TWITCH_CHANNEL")

# POŁĄCZENIE Z CZATEM:
sock = socket.socket()
sock.connect((server, port))
sock.send(f"PASS {token}\n".encode('utf-8'))
sock.send(f"NICK {nickname}\n".encode('utf-8'))
sock.send(f"JOIN {channel}\n".encode('utf-8'))

print(f"✅ Bot zalogowany jako {nickname} i dołączył do kanału {channel}.")

# KOMENDY:
komendy = {
    "!hello": "Bot wita się",
    "!help": "Pokazuje listę komend",
    "!zart": "Losowy żart Chucka Norrisa",
    "!kot": "Link do losowego kota"
}

# FUNKCJA ODPOWIEDZI:
def wyslij_wiadomosc(msg):
    sock.send(f"PRIVMSG {channel} :{msg}\n".encode('utf-8'))

# ODBIÓR I REAKCJA NA WIADOMOŚCI:
while True:
    resp = sock.recv(2048).decode('utf-8')

    if resp.startswith("PING"):
        sock.send("PONG :tmi.twitch.tv\n".encode('utf-8'))
    else:
        parts = resp.split(":", 2)
        if len(parts) >= 3:
            username = parts[1].split("!")[0]
            message = parts[2].strip()
            print(f"{username}: {message}")

            # Obsługa komend:
            if message == "!hello":
                wyslij_wiadomosc(f"Siema {username}, tu Twój Piekarzobot!")
            elif message == "!help":
                for komenda, opis in komendy.items():
                    wyslij_wiadomosc(f"{komenda} - {opis}")
            elif message == "!zart":
                try:
                    zarcik = requests.get("https://api.chucknorris.io/jokes/random")
                    data = zarcik.json()
                    wyslij_wiadomosc(f"Chuck Norris mówi: {data['value']}")
                except:
                    wyslij_wiadomosc("Nie udało się pobrać żartu 😢")
            elif message == "!kot":
                try:
                    r = requests.get("https://api.thecatapi.com/v1/images/search")
                    data = r.json()
                    wyslij_wiadomosc(f"Kotek: {data[0]['url']}")
                except:
                    wyslij_wiadomosc("Nie udało się pobrać kota 🐱")