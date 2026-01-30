import streamlit as st
import pandas as pd
import random
import re
import os
import json
import html as html_lib
import streamlit.components.v1 as components
import plotly.graph_objects as go
from datetime import datetime
from supabase import create_client, Client
import pathlib

# Pfad zur festen Excel-Datei (ändere hier bei Bedarf)
# Aktuell nutzt die Datei im gleichen Ordner wie dieses Skript: 'sample_memory.xlsx'
DEFAULT_XLSX_PATH = os.path.join(os.getcwd(), "sample_memory.xlsx")

# Pfad zur Fehlerstatistik-Datei
STATS_FILE = os.path.join(os.getcwd(), "memory_stats.json")

# Pfad zur Fortschrittsdatei
PROGRESS_FILE = os.path.join(os.getcwd(), "memory_progress.json")

# Supabase Verbindung
@st.cache_resource
def get_supabase_client() -> Client:
	import pathlib
	
	# Versuche zuerst st.secrets zu lesen
	url = st.secrets.get("SUPABASE_URL")
	key = st.secrets.get("SUPABASE_KEY")
	
	# Falls das nicht funktioniert, lies direkt aus secrets.toml
	if not url or len(key or "") < 100:
		print("⚠️ st.secrets funktioniert nicht, lese direkt aus secrets.toml...")
		try:
			secrets_path = pathlib.Path(__file__).parent / ".streamlit" / "secrets.toml"
			if secrets_path.exists():
				print(f"📁 Lese von: {secrets_path}")
				with open(secrets_path, "r", encoding="utf-8") as f:
					content = f.read()
					print(f"📄 Dateiinhalt:\n{content[:500]}")
					# Parse manuell
					for line in content.split("\n"):
						line = line.strip()
						if line.startswith("SUPABASE_URL"):
							url = line.split("=", 1)[1].strip().strip('"')
						elif line.startswith("SUPABASE_KEY"):
							key = line.split("=", 1)[1].strip().strip('"')
					print(f"✅ Manuell geparst: URL={url}, KEY länge={len(key)}")
		except Exception as e:
			print(f"❌ Fehler beim Lesen der secrets.toml: {e}")
	
	print(f"🔍 DEBUG: URL={url}")
	print(f"🔍 DEBUG: KEY länge={len(key) if key else 0}")
	
	if not url or not key:
		st.error("❌ Supabase-Credentials nicht gefunden! Bitte .streamlit/secrets.toml prüfen.")
		st.stop()
	if not url.startswith("https://"):
		st.error("❌ URL muss mit 'https://' beginnen")
		st.stop()
	try:
		print("🔗 Versuche mit Supabase zu verbinden...")
		client = create_client(url, key)
		print("✅ Supabase Client erstellt!")
		return client
	except Exception as e:
		print(f"❌ Fehler beim create_client: {type(e).__name__}: {e}")
		st.error(f"❌ Fehler beim Verbinden zu Supabase: {e}")
		st.stop()


def normalize(s: str) -> str:
	if s is None:
		return ""
	s = str(s).strip().lower()
	s = re.sub(r"\s+", " ", s)
	s = re.sub(r"[^0-9a-zäöüß ]", "", s)
	return s


def load_stats():
	"""Lädt die Fehlerstatistik aus der JSON-Datei."""
	if os.path.exists(STATS_FILE):
		try:
			with open(STATS_FILE, 'r', encoding='utf-8') as f:
				return json.load(f)
		except:
			return {}
	return {}


def save_stats(stats):
	"""Speichert die Fehlerstatistik in der JSON-Datei."""
	with open(STATS_FILE, 'w', encoding='utf-8') as f:
		json.dump(stats, f, ensure_ascii=False, indent=2)


def update_error_stats(prompt, solution):
	"""Erhöht den Fehlerzähler für eine Frage."""
	stats = load_stats()
	key = f"{prompt} → {solution}"
	stats[key] = stats.get(key, 0) + 1
	save_stats(stats)


def get_stats_dataframe():
	"""Erstellt ein DataFrame mit der Fehlerstatistik, sortiert nach Häufigkeit."""
	stats = load_stats()
	if not stats:
		return None
	items = [(k.split(' → ')[0], k.split(' → ')[1] if ' → ' in k else '', v) for k, v in stats.items()]
	df = pd.DataFrame(items, columns=['Frage', 'Antwort', 'Fehler'])
	return df.sort_values('Fehler', ascending=False)


def save_progress(data):
	"""Speichert Fortschrittsdaten in Supabase."""
	try:
		supabase = get_supabase_client()
		for entry in data:
			supabase.table("progress").insert({
				"timestamp": entry.get("timestamp"),
				"correct": int(entry.get("correct", 0)),
				"total": int(entry.get("total", 0)),
				"percentage": float(entry.get("percentage", 0))
			}).execute()
		st.success("✅ Fortschritt in Supabase gespeichert!")
	except Exception as e:
		st.error(f"❌ Fehler beim Speichern: {e}")


def load_progress():
	"""Lädt Fortschrittsdaten aus Supabase."""
	try:
		print("🔍 Versuche Daten zu laden...")
		supabase = get_supabase_client()
		print("✅ Supabase Client erstellt")
		response = supabase.table("progress").select("*").execute()
		print(f"✅ Datenbankabfrage erfolgreich: {len(response.data)} Einträge")
		if response.data:
			return response.data
		return []
	except Exception as e:
		print(f"❌ Fehler in load_progress: {e}")
		st.warning(f"⚠️ Fehler beim Laden: {e}")
		return []


def add_progress_entry(correct, total):
	"""Fügt einen neuen Fortschrittseintrag zu Supabase hinzu."""
	try:
		supabase = get_supabase_client()
		timestamp = datetime.now().isoformat()
		percentage = (correct / total * 100) if total > 0 else 0
		
		supabase.table("progress").insert({
			"timestamp": timestamp,
			"correct": correct,
			"total": total,
			"percentage": percentage
		}).execute()
	except Exception as e:
		st.error(f"❌ Fehler beim Speichern der Runde: {e}")


def plot_progress():
	"""Erstellt ein interaktives Fortschrittsdiagramm mit Plotly."""
	progress = load_progress()
	if not progress:
		return None
	
	# Daten extrahieren
	timestamps = []
	for entry in progress:
		try:
			ts = entry["timestamp"]
			if "T" in ts:  # ISO format
				timestamps.append(datetime.fromisoformat(ts))
			else:  # alte Format
				timestamps.append(datetime.strptime(ts, "%Y-%m-%d %H:%M:%S"))
		except:
			pass
	percentages = [entry["percentage"] for entry in progress]
	correct_counts = [entry["correct"] for entry in progress]
	total_counts = [entry["total"] for entry in progress]
	
	# Hover-Text erstellen: zeigt "X/Y korrekt" und Zeitstempel
	hover_texts = [
		f"<b>{correct}/{total} korrekt</b><br>" +
		f"{ts.strftime('%d.%m.%Y %H:%M')}<br>" +
		f"{percentage:.1f}%"
		for ts, correct, total, percentage in zip(timestamps, correct_counts, total_counts, percentages)
	]
	
	# Plotly Diagramm erstellen
	fig = go.Figure()
	
	# Linie mit Markern hinzufügen
	fig.add_trace(go.Scatter(
		x=timestamps,
		y=percentages,
		mode='lines+markers',
		marker=dict(
			size=10,
			color='#2E86AB',
			line=dict(width=2, color='white')
		),
		line=dict(
			color='#2E86AB',
			width=3
		),
		hovertext=hover_texts,
		hoverinfo='text',
		name='Fortschritt'
	))
	
	# Layout konfigurieren
	fig.update_layout(
		title=dict(
			text='Lernfortschritt über Zeit',
			font=dict(size=18, color='#0f172a', family='Arial Black')
		),
		xaxis=dict(
			title=dict(
				text='Datum und Uhrzeit',
				font=dict(size=14, color='#0f172a', family='Arial')
			),
			showgrid=True,
			gridcolor='rgba(0,0,0,0.1)'
		),
		yaxis=dict(
			title=dict(
				text='Korrekte Antworten (%)',
				font=dict(size=14, color='#0f172a', family='Arial')
			),
			range=[0, 105],
			showgrid=True,
			gridcolor='rgba(0,0,0,0.1)'
		),
		hovermode='closest',
		plot_bgcolor='rgba(255,255,255,0.9)',
		paper_bgcolor='rgba(255,255,255,0.9)',
		height=500,
		showlegend=False
	)
	
	return fig


def load_dataframe(uploaded_file):
    try:
        # Bei Dateiänderungen: explizit neu einlesen ohne Caching
        if isinstance(uploaded_file, str):
            # Pfad zur lokalen Datei
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        else:
            # Hochgeladene Datei
            df = pd.read_excel(uploaded_file, engine='openpyxl')
    except Exception as e:
        st.error(f"Fehler beim Lesen der Datei: {e}")
        return None

    # Debug-Ausgabe der tatsächlichen Spaltennamen
    st.sidebar.write(f"Gefundene Spalten: {list(df.columns)}")
    
    # Normalize column names (accept case-insensitive)
    cols = {c.strip().lower(): c for c in df.columns}
    if "bezeichnung" in cols and "bedeutung" in cols:
        df = df[[cols["bezeichnung"], cols["bedeutung"]]]
        df.columns = ["Bezeichnung", "Bedeutung"]
        return df.dropna(how="all")
    else:
        st.error(f"Die Excel-Datei muss die Spalten 'Bezeichnung' und 'Bedeutung' enthalten. Gefunden: {list(df.columns)}")
        return None


def start_quiz(df, mode, n_questions, shuffle=True, reset_score=True):
	pairs = list(df[["Bezeichnung", "Bedeutung"]].itertuples(index=False, name=None))
	
	if shuffle:
		# Gewichtete Zufallsauswahl basierend auf Fehlerstatistik
		stats = load_stats()
		weighted_pairs = []
		
		for pair in pairs:
			bezeichnung, bedeutung = pair
			# Erstelle Schlüssel für beide Richtungen
			key_forward = f"{bezeichnung} → {bedeutung}"
			key_backward = f"{bedeutung} → {bezeichnung}"
			
			# Prüfe Fehleranzahl für beide Richtungen
			errors_forward = stats.get(key_forward, 0)
			errors_backward = stats.get(key_backward, 0)
			max_errors = max(errors_forward, errors_backward)
			
			# Füge Frage basierend auf Fehlern mehrfach hinzu
			# Mindestens 1x, plus 1x pro Fehler (bis max 5x)
			weight = min(1 + max_errors, 5)
			weighted_pairs.extend([pair] * weight)
		
		# Zufällige Auswahl aus gewichteter Liste
		random.shuffle(weighted_pairs)
		pairs = weighted_pairs[:n_questions]
	else:
		pairs = pairs[:n_questions]
	
	st.session_state.current_round_count = len(pairs)
	st.session_state.questions = pairs
	st.session_state.index = 0
	# Only reset score/answers if requested (keep cumulative across auto-restarts)
	if reset_score:
		st.session_state.score = 0
		st.session_state.answers = []
		st.session_state.round_offset = 0
	else:
		if "score" not in st.session_state:
			st.session_state.score = 0
		if "answers" not in st.session_state:
			st.session_state.answers = []
		# mark where this round's answers will start in the cumulative answers list
		st.session_state.round_offset = len(st.session_state.answers)
	st.session_state.mode = mode
	# hide summary view when starting/restarting
	st.session_state.show_summary = False
	# mark that the round is not yet finished/revealed
	st.session_state.finished_round = False
	# reset progress_saved flag for new round
	st.session_state.progress_saved = False


def check_answer(user_ans: str, correct: str) -> bool:
	return normalize(user_ans) == normalize(correct)

def main():
	st.title("Memorytraining")
	st.subheader("Bezeichnung <-> Bedeutung")

	# Stil: dezenter, inspirierender Hintergrund und leicht transparente Karten
	st.markdown(
		"""
		<style>
		  body {
		    background: linear-gradient(135deg, #f6fbff 0%, #eaf6ff 50%, #fffaf0 100%);
		  }
		  .stApp {
		    color: #0f172a;
		  }
		  .main > div[role="main"] {
		    background: rgba(255,255,255,0.6);
		    border-radius: 12px;
		    padding: 12px;
		  }
		</style>
		""",
		unsafe_allow_html=True,
	)

	# Datei-Uploader in die linke Seitenleiste setzen (vertikal)
	uploaded = st.sidebar.file_uploader("Lade eine .xlsx-Datei hoch (Spalten: Bezeichnung, Bedeutung)", type=["xlsx"])

	df = None
	# Priorität: Upload > feste Standard-Datei
	if uploaded is not None:
		df = load_dataframe(uploaded)
	elif os.path.exists(DEFAULT_XLSX_PATH):
		st.sidebar.info(f"Lade Standarddatei: {DEFAULT_XLSX_PATH}")
		df = load_dataframe(DEFAULT_XLSX_PATH)
	else:
		st.info("Bitte zuerst eine Excel-Datei hochladen oder die Standarddatei anlegen.")
		return

	if df is None:
		return

	st.sidebar.header("Einstellungen")
	mode = st.sidebar.selectbox("Richtung", ["Bezeichnung → Bedeutung", "Bedeutung → Bezeichnung"])
	shuffle = st.sidebar.checkbox("Zufällige Reihenfolge", value=True)
	auto_restart = st.sidebar.checkbox("Automatisch neu starten nach Durchlauf", value=True)
	debug_output = st.sidebar.checkbox("Debug anzeigen (Antworten/Offsets)", value=False)
	max_q = st.sidebar.number_input("Anzahl Fragen (0 = alle)", min_value=0, max_value=len(df), value=0)

	# Fehlerstatistik anzeigen
	st.sidebar.markdown("---")
	st.sidebar.header("📊 Fehlerstatistik")
	stats_df = get_stats_dataframe()
	if stats_df is not None and len(stats_df) > 0:
		st.sidebar.write(f"Gesamt erfasste Fehler: {stats_df['Fehler'].sum()}")
		with st.sidebar.expander("Top 25 häufigste Fehler"):
			# Hinweis: `use_container_width` wurde ersetzt durch `width`.
			# Für volle Breite benutze `width='stretch'`.
			st.dataframe(stats_df.head(25), width='stretch')
		if st.sidebar.button("🗑️ Statistik zurücksetzen"):
			if os.path.exists(STATS_FILE):
				os.remove(STATS_FILE)
				st.sidebar.success("Statistik gelöscht!")
				st.rerun()
	else:
		st.sidebar.info("Noch keine Fehler erfasst.")
	
	# Fortschrittsdaten zurücksetzen
	st.sidebar.markdown("---")
	st.sidebar.header("📈 Lernfortschritt")
	progress_data = load_progress()
	if progress_data:
		st.sidebar.write(f"Anzahl gespeicherter Runden: {len(progress_data)}")
		if st.sidebar.button("🗑️ Fortschritt zurücksetzen"):
			if os.path.exists(PROGRESS_FILE):
				os.remove(PROGRESS_FILE)
				st.sidebar.success("Fortschrittsdaten gelöscht!")
				st.rerun()
	else:
		st.sidebar.info("Noch keine Fortschrittsdaten vorhanden.")

	# Vorschau entfernt auf Benutzerwunsch

	n_questions = len(df) if max_q == 0 else int(max_q)

	if "questions" not in st.session_state:
		st.session_state.questions = []

	if st.button("Quiz starten"):
		start_quiz(df, mode, n_questions, shuffle)

	if st.session_state.questions:
		idx = st.session_state.index
		question = st.session_state.questions[idx]
		if st.session_state.mode == "Bezeichnung → Bedeutung":
			prompt, solution = question
		else:
			solution, prompt = question

		st.markdown(f"### Frage {idx+1} / {len(st.session_state.questions)}")
		st.markdown(f"**{prompt}**")

		# Eingabefeld: sofort sichtbar; nach Absenden automatisch zur nächsten Frage
		input_key = f"input_{idx}"
		with st.form(key=f"form_{idx}"):
			user_input = st.text_area("Deine Antwort", key=input_key)
			submitted = st.form_submit_button("Absenden")
			if submitted:
				correct = check_answer(user_input, solution)
				st.session_state.answers.append((prompt, solution, user_input, correct))
				if correct:
					st.session_state.score += 1
					st.success("Richtig!")
				else:
					# Fehlerstatistik aktualisieren
					update_error_stats(prompt, solution)
					st.error("Nicht korrekt.")
					st.info(f"Richtige Antwort: {solution}")
				# automatisch zur nächsten Frage springen
				if st.session_state.index < len(st.session_state.questions) - 1:
					st.session_state.index += 1
					st.rerun()
				else:
						# letzte Frage beantwortet -> markiere Runde als fertig, aber zeige Ergebnis erst auf Button-Klick
						st.session_state.finished_round = True
						st.rerun()

		cols = st.columns(3)
		if cols[0].button("Zurück"):
			if st.session_state.index > 0:
				st.session_state.index -= 1
				st.rerun()
		if cols[1].button("Nächste Frage"):
			if st.session_state.index < len(st.session_state.questions) - 1:
				st.session_state.index += 1
				st.rerun()
		if cols[2].button("Beenden und Ergebnis anzeigen"):
			st.session_state.index = len(st.session_state.questions) - 1
			st.session_state.show_summary = True
			st.rerun()

		st.markdown("---")
		st.write(f"Punkte: {st.session_state.score} / {len(st.session_state.answers)}")

		# prepare recent-round stats so we can show them in a popup
		recent = st.session_state.answers[st.session_state.round_offset:]
		round_total = len(recent)
		round_correct = sum(1 for (_p, _s, _u, c) in recent if c)
		wrong = [(p, s, u) for (p, s, u, c) in recent if not c]

		# Wenn alle Fragen beantwortet sind: Button anbieten, um das Ergebnis anzuzeigen (keine automatische Anzeige)
		# Falls alle Antworten bereits vorhanden sind (z.B. durch manuelles Setzen), markiere die Runde als fertig
		if (len(st.session_state.answers) - st.session_state.round_offset) == len(st.session_state.questions) and not st.session_state.get("show_summary", False) and not st.session_state.get("finished_round", False):
			st.session_state.finished_round = True
			st.rerun()
		if st.session_state.get("finished_round", False) and not st.session_state.get("show_summary", False):
			st.info("Alle Fragen wurden beantwortet. Klicke auf 'Ergebnis anzeigen', um die Ergebnisse zu sehen.")
			if st.button("Ergebnis anzeigen"):
				# build HTML for popup
				if round_total == 0:
					popup_body = '<p>Keine Ergebnisse vorhanden.</p>'
				else:
					rows = ''
					for p, s, u in wrong:
						rows += f"<tr><td>{html_lib.escape(str(p))}</td><td>{html_lib.escape(str(s))}</td><td>{html_lib.escape(str(u))}</td></tr>"
					if rows:
						wrong_table = f"<h2>Falsche Antworten</h2><table border='1' style='border-collapse:collapse; width:100%'><thead><tr><th>Prompt</th><th>Lösung</th><th>Deine Antwort</th></tr></thead><tbody>{rows}</tbody></table>"
					else:
						wrong_table = '<p>Keine falschen Antworten in dieser Runde.</p>'
					popup_body = f"<p>Richtige Antworten (diese Runde): <strong>{round_correct}</strong> / {round_total}</p>{wrong_table}"
				popup_html = f"<html><head><meta charset='utf-8'><title>Ergebnis</title><style>body{{font-family:Arial,Helvetica,sans-serif;padding:16px}}table th,table td{{padding:8px;text-align:left}}</style></head><body><h1>Ergebnis</h1>{popup_body}</body></html>"
				# open popup via JS and write the HTML
				components.html(f"<script>var w=window.open('','_blank','toolbar=0,location=0,status=0,menubar=0,width=900,height=700'); w.document.write({json.dumps(popup_html)}); w.document.close();</script>", height=1)
				st.session_state.finished_round = False
				st.rerun()
				st.rerun()

		# Only show summary when explicitly requested (show_summary True)
		if st.session_state.get("show_summary", False):
			# anchor for smooth scroll to summary
			st.markdown('<div id="summary_anchor"></div>', unsafe_allow_html=True)
			st.header("Ergebnis")
			# scroll smoothly to the summary anchor so the user sees the results immediately
			# additionally expand the summary container to occupy the viewport for a 'complete view'
			components.html("""
			<script>
			  setTimeout(function(){
			    var el = document.getElementById('summary_anchor');
			    if (el) {
			      el.scrollIntoView({behavior: 'smooth', block: 'start'});
			      try {
			        // try to make the summary container fill the viewport
			        var container = el.closest('main') || el.parentElement;
			        if (container) {
			          container.style.minHeight = '100vh';
			          container.style.paddingTop = '16px';
			        }
			      } catch(e) {
			        // ignore
			      }
			    }
			  }, 50);
			</script>
			""", height=1)
			# compute round results using the stored correctness flag
			recent = st.session_state.answers[st.session_state.round_offset:]
			# recent is list of tuples: (prompt, solution, user_input, is_correct)
			round_total = len(recent)
			round_correct = sum(1 for (_p, _s, _u, c) in recent if c)
			# (Konfetti entfernt) — keine Animation mehr
			# cumulative score uses stored booleans as well
			st.session_state.score = sum(1 for (_p, _s, _u, c) in st.session_state.answers if c)
			
			# Fortschrittsdaten speichern (nur einmal pro Runde)
			if not st.session_state.get("progress_saved", False):
				add_progress_entry(round_correct, round_total)
				st.session_state.progress_saved = True
			
			st.write(f"Richtige Antworten (diese Runde): {round_correct} / {round_total}")
			st.write(f"Kumulativ: {st.session_state.score} / {len(st.session_state.answers)}")
			
			# Lernfortschrittsdiagramm anzeigen
			st.markdown("---")
			st.subheader("📈 Lernfortschritt")
			progress_fig = plot_progress()
			if progress_fig:
				# Hinweis: `use_container_width` deprecated — nutze `width='stretch'`.
				st.plotly_chart(progress_fig, width='stretch')
			else:
				st.info("Noch keine Fortschrittsdaten vorhanden.")
			# Pie chart (single, with explicit color mapping: Grün = Richtig, Rot = Falsch)
			# (Tortendiagramm entfernt — nur Tabelle der falschen Antworten wird angezeigt)
			# show incorrect answers (if any) - only this table
			wrong = [(p, s, u) for (p, s, u, c) in recent if not c]
			# (chart already rendered above)
			if wrong:
				st.subheader("Falsche Antworten")
				# 'wrong' contains tuples (prompt, solution, user_input)
				wrong_df = pd.DataFrame(wrong, columns=["Prompt", "Lösung", "Deine Antwort"]) 
				st.dataframe(wrong_df)
				if debug_output:
					with st.expander("Debug: interne Listen anzeigen"):
						st.write({
							"session_answers_count": len(st.session_state.answers),
							"round_offset": st.session_state.round_offset,
							"recent_count": len(recent),
							"wrong_count": len(wrong),
							"session_answers": st.session_state.answers,
							"recent": recent,
							"wrong": wrong,
						})
			else:
				st.success("Keine falschen Antworten in dieser Runde.")
			# (No overview of correct answers is shown per user preference.)
			# Falls Auto-Restart gewünscht: Button anbieten, damit Zusammenfassung erhalten bleibt
			if auto_restart:
				if st.button("Nächste Runde starten (neu mischen)"):
					start_quiz(df, mode, n_questions, shuffle=shuffle, reset_score=False)
					st.rerun()


if __name__ == "__main__":
	main()

