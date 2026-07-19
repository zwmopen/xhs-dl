# 红薯下载

小红书公开笔记原始媒体下载器，提供 Windows、Android、iPhone 三套独立客户端。各端只保存本机数据，不做设备互联或云同步。

## V2 特性

- 默认下载无平台水印的原始媒体，图片保存为 PNG
- 支持 `xhslink.com` 短链接与带 `xsec_token` 的小红书长链接
- 整段粘贴、批量去重、慢速执行、逐条回报
- 每篇笔记生成 `文案.txt`，包含标题、正文和话题
- 成功历史集中写入应用数据目录的一个 `history.json`，下载目录不散落 JSON
- 文件夹按 `评数-赞数-标题-作者` 命名，便于快速筛选
- 拟态悬浮 / 克制玻璃双主题界面，主题、保存位置与下载节奏会在本机记住
- Web 任务改为后台执行，可实时查看逐条进度，界面不会在下载时卡死
- Web 版默认保存到当前 Windows 用户的“下载”文件夹，高级设置默认收起
- V1 仍保留为显式备用，但不会静默降级到水印图

V2 通过独立的 [XHS-Downloader](https://github.com/JoeanAmier/XHS-Downloader) CLI 工作。该引擎使用 GPL-3.0，本仓库只做进程适配，不复制其源码。

## 无水印原理

软件不会把水印区域模糊或涂掉。它解析公开分享链接，读取笔记公开媒体信息，并优先下载平台叠加账号水印之前的原始媒体地址。因此画质不会因为“修图去水印”而损失；如果作者把署名、Logo 或文字直接做进原图，这些内容会原样保留。

## 首次安装

Windows 用户解压发布包后，可以先双击 `一键安装V2.bat`，安装完成后双击 `启动无水印版.bat`。

推荐使用 V2.4.0 便携桌面版：解压 `红薯下载-v2.4.0-portable-windows.zip`，首次使用先运行 `一键安装V2.bat`，之后双击 `红薯下载.exe`。

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

桌面版默认自动判断：1 条直接采集，2–20 条随机等待 35–55 秒，21–50 条 55–85 秒，超过 50 条 110–160 秒；设置中可以手动覆盖。命令行可选 `fast`、`normal`、`cautious`、`slow`、`very-slow`。

## 桌面界面

桌面版提供独立窗口、设置按钮、系统文件夹选择、实时进度和更新检测。默认保存到 `C:\Users\你的用户名\Downloads`，设置会在本机记住。

旧 Web 界面仍可使用：

```powershell
xhs-dl-web
```

浏览器会打开 `http://127.0.0.1:5678`。Web 版同样使用 V2 本地无水印引擎，并提供实时进度、结果清单与持久化视觉主题。默认保存到 `C:\Users\你的用户名\Downloads`。

## Android 应用

安装发布页中的 `红薯下载-android-v1.1.0.apk`。可以手动粘贴分享文字，也可以在其他应用中点“分享”并选择“红薯下载”。新安装默认保存到手机 `Download/红薯下载`；设置中既能修改默认子目录，也能用 Android 系统文件夹选择器授权任意可写目录。升级用户会保留旧目录设置。

安卓端与电脑端使用同名的“拟态悬浮 / 克制玻璃”双主题，并记住主题、下载子目录、自动频率和更新检测设置。Android 10 及以上使用系统 MediaStore 保存，不需要索取全部文件权限。

## iPhone 应用

`ios/` 提供红薯下载 iOS V0.1.0 SwiftUI 客户端。默认保存到“文件”App 可见的 `红薯下载` 目录，也可以通过系统目录选择器改到“我的 iPhone”或 iCloud Drive 中用户授权的文件夹。iOS 设置页包含主题、下载目录、设计说明、使用说明和手动更新检测。

iPhone 版与另外两端相互独立，不上传下载历史。仓库使用 GitHub macOS 构建机做无签名模拟器编译；安装到真机仍需用户自己的 Apple 开发签名，详见 `ios/README.md`。

## 本地输出

```text
xhs_downloads/
└── 评128-赞3560-标题-作者/
    ├── 图片_1.png
    ├── 图片_2.png
    └── 文案.txt
```

所有成功历史集中保存在 `%LOCALAPPDATA%\xhs-dl\history.json`。

模板配置保存在 `templates/local-cli.json`。可用环境变量 `XHS_DOWNLOADER_HOME` 覆盖引擎位置。

## 使用边界

仅下载你有权访问和保存的公开内容；请尊重创作者版权、平台规则与隐私。链接解析受平台接口和风控变化影响，失败时可降低频率或更新本地引擎。

详细说明见 `使用手册.md` 与 `安全与注意事项.md`。共享 AI/OpenClaw 技能位于 `skills/xhs-download`。

## License

本适配项目为 MIT；独立下载引擎为 GPL-3.0，以其仓库许可证为准。
