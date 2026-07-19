---
name: xhs-download
description: Download public Xiaohongshu or RedNote notes from user-provided share text, short links, or long links to local original media without platform watermarks or account login. Use for single or batch downloads, local archiving, media extraction, retrying failed public notes, and checking centralized download history. Never use for private, access-controlled, or unauthorized content.
---

# Xiaohongshu Download

Download only public notes the user explicitly provides or authorizes. Keep all media local by default.

## Workflow

1. Run `python scripts/check.py` and stop if `ready` is false.
2. Choose an output folder inside the user's requested scope. Default to `./xhs_downloads` only when none is given.
3. Run `python scripts/download.py --text "<share text or links>" --output "<folder>" --mode cautious`.
   For a UTF-8 text file, replace `--text` with `--file <path>`.
4. Read the JSON printed by the script. Report success only when `success` is positive and the listed local files exist.
5. Point the user to the downloaded media, `文案.txt`, and centralized `%LOCALAPPDATA%\xhs-dl\history.json` when history is needed.

## Guardrails

- Do not request login credentials or cookies for normal public-note downloads.
- Do not silently use the legacy V1 watermark engine.
- Do not send links to third-party parsing websites unless the user explicitly opts in after a privacy warning.
- Do not bypass private-note, deleted-note, age, regional, or access controls.
- Use `cautious` by default. Use `fast` only for a small user-approved test batch.
- Preserve creator-embedded marks; remove only the platform-delivered watermark by selecting original media.
- Read `references/safety.md` before changing engines, network behavior, or installation scripts.
- Read `references/visual-language.md` before changing the Web interface.

## Interfaces

- Desktop UI: run `xhs-dl-desktop` or the portable `xhs-dl.exe`.
- Legacy visual UI: run `xhs-dl-web` or `python -m xhs_dl.web.app`.
- Human CLI: run `xhs-dl "<share text>"`.
- Agent/OpenClaw: use `scripts/check.py` then `scripts/download.py`.
- Installation and shared OpenClaw setup: read `references/manual.md` and `references/openclaw.md`.
