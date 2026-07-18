# xhs-dl V2

小红书公开笔记无水印下载器。粘贴短链接、长链接或整段分享文本，逐条提取图片/视频到本地。

## V2 特性

- 默认下载无平台水印的原始媒体，图片保存为 PNG
- 支持 `xhslink.com` 短链接与带 `xsec_token` 的小红书长链接
- 整段粘贴、批量去重、慢速执行、逐条回报
- 每条成功结果写入 `xhs-dl-result.json`，便于断点排查和后续 AI 处理
- 批次进度实时写入 `xhs-dl-batch.json`，中途退出也保留已完成结果
- V1 仍保留为显式备用，但不会静默降级到水印图

V2 通过独立的 [XHS-Downloader](https://github.com/JoeanAmier/XHS-Downloader) CLI 工作。该引擎使用 GPL-3.0，本仓库只做进程适配，不复制其源码。

## 首次安装

Windows 用户解压发布包后，可以先双击 `一键安装V2.bat`，安装完成后双击 `启动无水印版.bat`。

在 PowerShell 中运行：

```powershell
cd D:\AICode\xhs-dl
.\setup-v2.ps1
python -m pip install -e .
```

安装器会把引擎放在 `D:\AICode\XHS_Downloader`，并为它单独准备 Python 3.12 环境，不影响系统 Python。

## 直接使用

双击 `启动无水印版.bat`，也可以从命令行运行：

```powershell
# 单条或整段分享文本
xhs-dl "http://xhslink.com/o/70dt8TsFJon"

# 多条链接或文件，指定保存目录
xhs-dl -f links.txt -o D:\Download\小红书 --mode slow

# 明确指定本地引擎
xhs-dl "链接" --engine-home D:\AICode\XHS_Downloader

# 仅在确实需要旧版网页解析时使用（可能有水印）
xhs-dl "链接" --engine v1
```

默认 `cautious` 模式会在笔记之间等待 25–45 秒。可选 `fast`、`normal`、`cautious`、`slow`、`very-slow`。

## Web 界面

```powershell
xhs-dl-web
```

浏览器会打开 `http://127.0.0.1:5678`。Web 版同样使用 V2 本地无水印引擎。

## 本地输出

```text
xhs_downloads/
└── 日期_作者_标题/
    ├── 图片_1.png
    ├── 图片_2.png
    └── xhs-dl-result.json
```

模板配置保存在 `templates/local-cli.json`。可用环境变量 `XHS_DOWNLOADER_HOME` 覆盖引擎位置。

## 使用边界

仅下载你有权访问和保存的公开内容；请尊重创作者版权、平台规则与隐私。链接解析受平台接口和风控变化影响，失败时可降低频率或更新本地引擎。

详细说明见 `使用手册.md` 与 `安全与注意事项.md`。共享 AI/OpenClaw 技能位于 `skills/xhs-download`。

## License

本适配项目为 MIT；独立下载引擎为 GPL-3.0，以其仓库许可证为准。
