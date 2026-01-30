## Purpose

This repository contains small, single-file Python scripts for downloading audio from YouTube. This document gives focused, actionable guidance for an AI coding agent to be immediately productive editing or extending the project.

## Big picture
- Scripts are lightweight utilities (no package structure or tests). Main files: [Youtube_to_MP3.py](Youtube_to_MP3.py), [Youtube_to_m4a.py](Youtube_to_m4a.py), [Youtube_to_MP3_Sicherungskopie.py](Youtube_to_MP3_Sicherungskopie.py), [Test1.py](Test1.py).
- Responsibility: each file is a standalone downloader + small postprocessing (e.g., rename or ffmpeg-based extraction). There is no central CLI or shared library.
- Data flow: URL -> downloader (`yt_dlp` or `pytube`) -> temporary file -> optional postprocessor (FFmpeg) -> final file placed in the user's Downloads folder.

## Key patterns & conventions
- Single-responsibility scripts: prefer small, obvious edits rather than large refactors. When adding features, keep them optional and non-breaking.
- Downloads always resolve the user's home `Downloads` directory using `os.path.expanduser("~")` and `os.path.join(..., "Downloads")` — preserve this behavior unless the user asks for configurable output paths.
- `yt_dlp` usage (see [Youtube_to_MP3.py](Youtube_to_MP3.py) and [Youtube_to_m4a.py](Youtube_to_m4a.py)) sets `ydl_opts` and calls `ydl.download([url])`; output filename is controlled with `outtmpl`.
- MP3 extraction relies on `yt_dlp` postprocessor `FFmpegExtractAudio` — requires `ffmpeg` in PATH. If you change `preferredcodec` or postprocessing, ensure ffmpeg compatibility.
- `Test1.py` uses `pytube` and renames a downloaded `.mp4` audio file to `.m4a`; avoid assuming `pytube` returns `.m4a` directly.

## Dependencies & environment
- Python packages: `yt-dlp` and `pytube` are used in different scripts. There is no `requirements.txt` in the repository.
- System dependency: `ffmpeg` is required for `FFmpegExtractAudio` postprocessing to work.
- Example install commands to run locally:

```bash
pip install yt-dlp pytube
# install ffmpeg separately (OS-specific). On Windows recommend adding ffmpeg to PATH.
```

## How to run (developer flows)
- Run a script directly with Python. Example:

```bash
python Youtube_to_MP3.py
python Youtube_to_m4a.py
python Test1.py
```

- Editing notes: each script contains a `url = "..."` sample string at top. When modifying behavior, update the URL or replace the top-level value with a small CLI or function wrapper, but keep backward compatibility.

## Safe change guidance (what reviewers expect)
- Keep changes minimal and explicit in these utilities: add a clear opt-in config instead of changing defaults silently (e.g., add a `--outdir` or `OUTPUT_DIR` variable rather than switching the default save location).
- If you add logging, use simple `print()` calls consistent with existing scripts (no heavy logging frameworks unless you create a new shared module).

## Examples of common edits you may be asked to implement
- Change output format/quality: update `ydl_opts['postprocessors']` or `format` in [Youtube_to_MP3.py](Youtube_to_MP3.py).
- Make output directory configurable: replace `downloads_path = ...` with reading an env var or simple `argparse` option.
- Migrate from `pytube` to `yt_dlp`: replicate the `outtmpl`/postprocessor behavior shown in [Youtube_to_MP3.py](Youtube_to_MP3.py).

## Files to inspect when diagnosing issues
- [Youtube_to_MP3.py](Youtube_to_MP3.py): primary `yt_dlp` + mp3 postprocessing example.
- [Youtube_to_m4a.py](Youtube_to_m4a.py): shows `bestaudio[ext=m4a]` format selection.
- [Test1.py](Test1.py): `pytube` example that renames `.mp4` to `.m4a`.

## When to ask the user
- If you need to change the default output folder behavior, confirm whether the user wants a CLI option or a config file.
- For any new cross-cutting dependency (e.g., adding `requests`, creating a package structure), ask before creating `requirements.txt` or refactoring into modules.

If any section is unclear or you want additional examples (e.g., converting scripts into a small package or adding a `requirements.txt`), tell me which target behavior you prefer and I will update this file.
