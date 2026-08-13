---
name: xhs-download
description: Download public media from Xiaohongshu/RedNote, Douyin, X/Twitter, Bilibili, YouTube, TikTok, Instagram, Facebook, Pinterest, Reddit, Vimeo, and Bluesky to local folders without platform login or browser cookies. Use for single or batch downloads, local archiving, media extraction, retrying failed public works, and checking centralized history. Never use for private, access-controlled, or unauthorized content.
---

# Multi-platform Public Media Download

Download only public works the user explicitly provides or authorizes. Mixed supported links are accepted. Xiaohongshu and Douyin use dedicated engines; other listed platforms use the local yt-dlp adapter. Keep all media local by default.

## Workflow

1. Run `python scripts/check.py` and stop if `ready` is false.
2. Choose an output folder inside the user's requested scope. Default to `./xhs_downloads` only when none is given.
3. Run `python scripts/download.py --text "<share text or links>" --output "<folder>" --mode cautious`.
   For a UTF-8 text file, replace `--text` with `--file <path>`.
4. Read the JSON printed by the script. Report success only when `success` is positive and the listed local files exist. Images default to high-quality JPG and use `封面-标题`, `内页1-标题` naming; videos use `视频-标题`.
5. Point the user to the downloaded media, `文案.txt`, and centralized `%LOCALAPPDATA%\xhs-dl\history.json` when history is needed.

## Guardrails

- Do not request, extract, or reuse login credentials or cookies for normal public downloads.
- Do not silently use the legacy V1 watermark engine.
- Do not send links to third-party parsing websites unless the user explicitly opts in after a privacy warning.
- Do not bypass private-note, deleted-note, age, regional, or access controls.
- Use `cautious` by default. Use `fast` only for a small user-approved test batch.
- Preserve creator-embedded marks; remove only the platform-delivered watermark by selecting original media.
- If a platform demands login or bot confirmation, return the limitation and never import browser cookies automatically.
- Read `references/safety.md` before changing engines, network behavior, or installation scripts.
- Read `references/visual-language.md` before changing any Web, Windows, Android, or iPhone interface.

## Interfaces

- Desktop UI: run `xhs-dl-desktop` or the packaged app. Douyin uses a clean temporary Edge context; generic platforms use packaged yt-dlp and FFmpeg.
- Android UI: install the release APK, paste or share text into “小红书抖音下载”, and use either `Download/小红书抖音下载` or a folder authorized in Settings.
- iPhone UI: build the SwiftUI client under `ios/`; use its local Files default or a user-authorized Files/iCloud Drive directory. It is independent from the other clients.
- Legacy visual UI: run `xhs-dl-web` or `python -m xhs_dl.web.app`.
- Human CLI: run `xhs-dl "<share text>"`.
- Agent/OpenClaw: use `scripts/check.py` then `scripts/download.py`.
- Installation and shared OpenClaw setup: read `references/manual.md` and `references/openclaw.md`.
