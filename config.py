# Plik konfiguracyjny Bota Discord InstaLing

import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Token Twojego bota Discord (z Discord Developer Portal: https://discord.com/developers/applications)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "WSTAW_TUTAJ_TOKEN_BOTA_DISCORD")

# URL bazy Firebase Realtime Database (dokładnie ta sama, z której korzysta userscript)
FIREBASE_DATABASE_URL = os.getenv(
    "FIREBASE_DATABASE_URL",
    "https://instaling-bot-2362a-default-rtdb.europe-west1.firebasedatabase.app"
)

# Czy przeglądarka ma działać w tle (niewidoczna)?
# True = działa cicho w tle (rekomendowane na serwer/VPS)
# False = widać wyskakujące okno przeglądarki Chrome na żywo (super do podglądu)
HEADLESS = os.getenv("HEADLESS", "True").lower() in ("true", "1", "yes")

# Emulacja człowieka (w milisekundach - spokojne, ludzkie tempo w 100% niewykrywalne)
TYPING_SPEED_MIN = int(os.getenv("TYPING_SPEED_MIN", "100"))    # 100ms - 150ms na znak
TYPING_SPEED_MAX = int(os.getenv("TYPING_SPEED_MAX", "150"))
THINKING_DELAY_MIN = int(os.getenv("THINKING_DELAY_MIN", "2000")) # 2.0s - 3.8s na "zastanowienie się" i przeczytanie pytania
THINKING_DELAY_MAX = int(os.getenv("THINKING_DELAY_MAX", "3800"))
ACTION_DELAY_MIN = int(os.getenv("ACTION_DELAY_MIN", "800"))    # 0.8s - 1.6s przed kliknięciem Sprawdź
ACTION_DELAY_MAX = int(os.getenv("ACTION_DELAY_MAX", "1600"))
NEXT_WORD_DELAY_MIN = int(os.getenv("NEXT_WORD_DELAY_MIN", "1400")) # 1.4s - 2.5s na podgląd odpowiedzi
NEXT_WORD_DELAY_MAX = int(os.getenv("NEXT_WORD_DELAY_MAX", "2500"))

# Maksymalna liczba jednocześnie otwartych przeglądarek (ochrona przed Target crashed / OOM w Dockerze/Railway)
MAX_CONCURRENT_SESSIONS = int(os.getenv("MAX_CONCURRENT_SESSIONS", "1"))

# Losowe paczki kont naraz (1 konto naraz dla 100% stabilności RAM w kontenerach chmurowych)
BATCH_SIZE_MIN = int(os.getenv("BATCH_SIZE_MIN", "1"))          # min. kont w paczce
BATCH_SIZE_MAX = int(os.getenv("BATCH_SIZE_MAX", "1"))          # max. kont w paczce
BATCH_PAUSE_MIN = int(os.getenv("BATCH_PAUSE_MIN", "5"))        # min. sekund przerwy między paczkami
BATCH_PAUSE_MAX = int(os.getenv("BATCH_PAUSE_MAX", "12"))       # max. sekund przerwy między paczkami

# Godziny automatycznego wykonywania sesji (w godzinach 16:00 - 23:00 codziennie)
AUTO_WINDOW_START_HOUR = int(os.getenv("AUTO_WINDOW_START_HOUR", "16")) # Od 16:00
AUTO_WINDOW_END_HOUR = int(os.getenv("AUTO_WINDOW_END_HOUR", "23"))     # Do 23:00
AUTO_CRON_HOURS = os.getenv("AUTO_CRON_HOURS", "16,18,20,22")           # Godziny sprawdzania w oknie 16-23
AUTO_CRON_MINUTE = int(os.getenv("AUTO_CRON_MINUTE", "30"))             # Minuta uruchomienia (np. 16:30, 18:30 itd.)
DEFAULT_AUTO_HOUR = int(os.getenv("DEFAULT_AUTO_HOUR", "16"))
DEFAULT_AUTO_MINUTE = int(os.getenv("DEFAULT_AUTO_MINUTE", "30"))

# Ograniczenie uprawnień do 1 rangi
# Możesz wpisać nazwę roli (np. "VIP", "Klient", "InstaLing") LUB jej dokładne ID z Discorda
# Domyślnie: "VIP". Jeśli ustawisz pusty "" i ID 0, bot będzie dostępny dla każdego.
REQUIRED_ROLE_NAME = os.getenv("REQUIRED_ROLE_NAME", "VIP")
REQUIRED_ROLE_ID = int(os.getenv("REQUIRED_ROLE_ID", "0"))
