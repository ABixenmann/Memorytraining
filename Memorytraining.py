import streamlit as st
import pandas as pd
import random
import re
# altair removed — no chart needed
import os
import json
import html as html_lib
import streamlit.components.v1 as components

# Pfad zur festen Excel-Datei (ändere hier bei Bedarf)
# Aktuell nutzt die Datei im gleichen Ordner wie dieses Skript: 'sample_memory.xlsx'
DEFAULT_XLSX_PATH = os.path.join(os.path.dirname(__file__), "sample_memory.xlsx")


def normalize(s: str) -> str:
	if s is None:
		return ""
	s = str(s).strip().lower()
	s = re.sub(r"\s+", " ", s)
	s = re.sub(r"[^0-9a-zäöüß ]", "", s)
	return s


def load_dataframe(uploaded_file):
	try:
		df = pd.read_excel(uploaded_file)
	except Exception as e:
		st.error(f"Fehler beim Lesen der Datei: {e}")
		return None

	# Normalize column names (accept case-insensitive)
	cols = {c.strip().lower(): c for c in df.columns}
	if "bezeichnung" in cols and "bedeutung" in cols:
		df = df[[cols["bezeichnung"], cols["bedeutung"]]]
		df.columns = ["Bezeichnung", "Bedeutung"]
		return df.dropna(how="all")
	else:
		st.error("Die Excel-Datei muss die Spalten 'Bezeichnung' und 'Bedeutung' enthalten.")
		return None


def start_quiz(df, mode, n_questions, shuffle=True, reset_score=True):
	pairs = list(df[["Bezeichnung", "Bedeutung"]].itertuples(index=False, name=None))
	if shuffle:
		random.shuffle(pairs)
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
	max_q = st.sidebar.number_input("Anzahl Fragen (0 = alle)", min_value=0, max_value=len(df), value=min(20, len(df)))

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
		if cols[1].button("Nächste Frage"):
			if st.session_state.index < len(st.session_state.questions) - 1:
				st.session_state.index += 1
		if cols[2].button("Beenden und Ergebnis anzeigen"):
			st.session_state.index = len(st.session_state.questions) - 1
			# force showing summary below
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
			st.write(f"Richtige Antworten (diese Runde): {round_correct} / {round_total}")
			st.write(f"Kumulativ: {st.session_state.score} / {len(st.session_state.answers)}")
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

