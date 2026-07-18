# OpenClaw shared installation

## Requirements

- OpenClaw 2026.3 or newer
- Node.js 22.19 or newer
- xhs-dl V2 installed and `python scripts/check.py` returns `ready: true`

Do not store tokens, cookies, or account credentials in this skill.

## Install globally

From the cloned xhs-dl repository:

`openclaw skills install D:\AICode\xhs-dl\skills\xhs-download --global`

Then verify:

`openclaw skills info xhs-download --json`

`openclaw skills check --json`

Start a new OpenClaw session and ask: `用 xhs-download 下载这个公开分享链接到 D:\Download\小红书`.

## Rollback

Remove only the installed managed skill through OpenClaw's skill management command or its `~/.openclaw/skills/xhs-download` managed directory. Do not remove the application, engine, or downloaded media. Start a new session after rollback.
