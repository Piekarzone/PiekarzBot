import socket
import os
import random
import time
from dotenv import load_dotenv

load_dotenv()

SERVER = 'irc.chat.twitch.tv'
PORT = 6667
TOKEN = os.getenv('TWITCH_TOKEN')
NICK = os.getenv('TWITCH_NICK')
CHANNEL = '#' + os.getenv('TWITCH_CHANNEL')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO = os.getenv('GITHUB_REPO')

sock = socket.socket()

try:
    sock.connect((SERVER, PORT))
    sock.send(f"PASS {TOKEN}\r\n".encode('utf-8'))
    sock.send(f"NICK {NICK}\r\n".encode('utf-8'))
    sock.send(f"JOIN {CHANNEL}\r\n".encode('utf-8'))
except Exception as err:
    print(f"Błąd podczas łączenia z serwerem: {err}")
    sock.close()
    exit(1)

print(f"Bot zalogowany jako {NICK} i dołączył do kanału {CHANNEL}")

def send_message(msg_text):
    msg = f"PRIVMSG {CHANNEL} :{msg_text}\r\n"
    sock.send(msg.encode('utf-8'))

last_coin_flip = {}
last_scavfight = {}
all_users = set()
greetings = ["siema", "hej", "hejka", "witam", "czesc", "dzień dobry", "dzien dobry"]
sound_commands = ["wyznanie", "niestreamer"]

def update_current_sound(sound_name):
    try:
        with open("public/current_sound.txt", "w") as file:
            file.write(sound_name)
        print(f"Zaktualizowano current_sound.txt na '{sound_name}'")
    except Exception as e:
        print(f"Błąd zapisu current_sound.txt: {e}")

def handle_command(user, user_message):
    cleaned_message = user_message.lower().strip()
    current_time = time.time()
    all_users.add(user)

    # Powitania bez $
    if any(cleaned_message == greet for greet in greetings):
        send_message(f"@{user} Witam na streamku!")
        return

    # Komendy zaczynające się od $
    if cleaned_message.startswith("$"):
        command = cleaned_message[1:]  # usuń $
        if command == "rzutmoneta":
            last_time = last_coin_flip.get(user, 0)
            if current_time - last_time >= 5:
                wynik = random.choice(["orzeł", "reszka"])
                send_message(f"@{user} wynik: {wynik}")
                last_coin_flip[user] = current_time
            else:
                send_message(f"@{user} ⏳ Poczekaj {int(5 - (current_time - last_time))} sekund przed kolejnym rzutem monetą.")
        elif command == "scavfight":
            last_time = last_scavfight.get(user, 0)
            if current_time - last_time >= 10:
                random_scav = random.choice(list(all_users - {user})) if len(all_users) > 1 else "inny gracz"
                wynik = random.choice([
                    f"Scav {random_scav} zniszczył Ci plecak i zabrał połowę loot'u!",
                    f"Udało Ci się pokonać Scava {random_scav} i zebrać jego loot!",
                    f"Scav ({random_scav}) Cię zaskoczył, ale uciekłeś bez strat.",
                    f"Zaatakowałeś Scava ({random_scav}) i zdobyłeś dodatkowe ammo!",
                    f"Scav ({random_scav}) headshotował Cię z Mosina – rip gear.",
                    f"Przebiłeś Scava ({random_scav}) nożem i przejąłeś jego plecak.",
                    f"Scav ({random_scav}) zabił Cię granatem F1... loot stracony.",
                    f"Zaskoczyłeś Scava ({random_scav}) i ukradłeś mu klucz do dormów.",
                    f"Scav ({random_scav}) trafił Cię w nogę – musisz uleczyć się!",
                    f"Udało Ci się znaleźć zasobnik Scava ({random_scav}) z bitcoinem!",
                    f"Scav ({random_scav}) Cię nie zauważył – cichy loot zaliczony.",
                    f"Walka z dwoma Scavami ({random_scav} i {random_scav}) – ledwo uszedłeś z życiem.",
                    f"Scav ({random_scav}) strzelił Ci w plecy – rozbita zbroja.",
                    f"Wpadłeś w zasadzkę Scavów ({random_scav}, {random_scav}, {random_scav}) – oddałeś im cały loot.",
                    f"Udało Ci się zabić Scava ({random_scav}) i zabrać jego AK-74.",
                    f"Scav ({random_scav}) rozbroił Cię i uciekł z Twoim plecakiem."
                ])
                send_message(f"@{user} wynik walki: {wynik}")
                last_scavfight[user] = current_time
            else:
                send_message(f"@{user} ⏳ Poczekaj {int(10 - (current_time - last_time))} sekund przed kolejną walką scavfight.")
        elif command in sound_commands:
            update_current_sound(command)
            send_message(f"@{user} ▶️ Odtwarzam dźwięk: {command}")

try:
    buffer = ""
    while True:
        data = sock.recv(4096).decode('utf-8', errors='ignore')
        buffer += data
        while "\r\n" in buffer:
            line, buffer = buffer.split("\r\n", 1)
            if line.startswith('PING'):
                sock.send("PONG :tmi.twitch.tv\r\n".encode('utf-8'))
            elif "PRIVMSG" in line:
                user = line.split('!', 1)[0][1:]
                user_message = line.split('PRIVMSG', 1)[1].split(':', 1)[1].strip()
                handle_command(user, user_message)
except KeyboardInterrupt:
    sock.close()
except Exception as err:
    print(f"Wystąpił błąd: {err}")
    sock.close()
