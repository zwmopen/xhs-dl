---
name: xhs-download
description: Compatibility alias for older requests that explicitly invoke xhs-download or call the former 小红书下载器/小红书抖音下载 skill. Route all current public-media download work to universal-downloader and do not maintain a second downloader implementation.
---

# 旧名称兼容入口

Use `$universal-downloader` for the actual task. Preserve the user's original links, output folder, pacing, and safety requirements.

Do not copy scripts or create another engine here. This alias exists only so older prompts, OpenClaw configurations, and automation can migrate without breaking.

Tell the user the current name is “万能下载器” only when the distinction is useful; otherwise complete the download normally.
