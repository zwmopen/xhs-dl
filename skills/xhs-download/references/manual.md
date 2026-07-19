# Operator manual

## Install

1. Run `一键安装V2.bat` from the xhs-dl release folder.
2. Run `python scripts/check.py` from this skill folder.
3. Keep the default `cautious` mode for normal use.

## Invoke

- Share text: `python scripts/download.py --text "分享文本" --output "D:\Download\小红书"`
- Text file: `python scripts/download.py --file "D:\links.txt" --output "D:\Download\小红书"`
- Visual interface: run `启动Web版.bat` from the application folder.

The command prints JSON for the calling agent. Download folders contain media and `文案.txt`; centralized history is stored at `%LOCALAPPDATA%\xhs-dl\history.json`.

## Failure handling

- `ready: false`: run the one-click installer or provide `--engine-home`.
- No supported URL: ask for a fresh public share link.
- Timeout or access failure: keep completed results, wait, and retry using `slow`.
- Never switch to V1 automatically; it may download platform-watermarked media.
