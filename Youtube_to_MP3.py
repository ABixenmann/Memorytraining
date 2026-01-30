import os
import yt_dlp

# YouTube-Link hier einfügen
url = "https://youtu.be/9On2qtIuBQc"

# Standard-Download-Ordner des Benutzers ermitteln
downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")

# Optionen für yt-dlp
ydl_opts = {
    'format': 'bestaudio/best',   # beste Audioqualität
    'outtmpl': os.path.join(downloads_path, '%(title)s.%(ext)s'),
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',   # gewünschtes Format
        'preferredquality': '192', # Qualität in kbit/s
    }],
}

# Download starten
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])

print("Download abgeschlossen! MP3 liegt im Downloads-Ordner.")
