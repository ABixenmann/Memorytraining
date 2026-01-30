import os
import yt_dlp

# YouTube-Link hier einfügen
url = "https://youtu.be/toRmf2tbcrU?list=RDM8Wj6-gPY0g"

# Standard-Download-Ordner des Benutzers ermitteln
downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")

# Optionen für yt-dlp
ydl_opts = {
    'format': 'bestaudio[ext=m4a]',   # beste Audioqualität im M4A-Format
    'outtmpl': os.path.join(downloads_path, '%(title)s.%(ext)s')  # Dateiname = Videotitel
}

# Download starten
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])

print("Download abgeschlossen! Datei liegt im Downloads-Ordner.")
