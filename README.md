# 万能下载器

公开社交平台媒体下载器。Windows V2.8.0 使用“万能下载器”正式品牌，在原有小红书、抖音专用引擎上增加本地 yt-dlp 适配层；Android、iPhone 同步改显示名称，但暂时仍保持小红书与抖音能力。各端只保存本机数据，不做设备互联或云同步。

## V2.8.0 多平台范围

Windows 和 AI Skill 首批识别：小红书、抖音、X/Twitter、B站、YouTube、TikTok、Instagram、Facebook、Pinterest、Reddit、Vimeo、Bluesky。小红书与抖音继续走原专用引擎，其他平台由本地 yt-dlp 和随包 FFmpeg 处理。

“支持”表示可尝试下载公开媒体，不代表每条链接永久可用。平台可能临时限流或强制登录；软件不会读取浏览器 Cookie，也不会绕过私密、年龄、地区或访问控制。本机实测 X 与 B站公开链接成功；YouTube 在当前网络触发匿名机器人确认，因此会原样报告失败。

## V2 特性

- 默认下载无平台覆盖水印的原始媒体，保持原尺寸并转为高质量 JPG；设置中可选 PNG 或平台原格式
- 图片按 `封面-标题`、`内页1-标题` 命名，视频按 `视频-标题` 命名
- 支持抖音公开视频和图文作品；无需登录，也不读取浏览器 Cookie
- 支持 `xhslink.com`、`xhslink.cn` 短链接与带 `xsec_token` 的小红书长链接
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

推荐使用 V2.8.0 便携桌面版：解压 `universal-downloader-v2.8.0-windows-portable.zip`，首次使用先运行 `一键安装V2.bat`，之后双击 `万能下载器.exe`。电脑端采集抖音需要系统已安装 Microsoft Edge，但不会使用 Edge 的个人资料或登录态；通用平台组件已经随包提供。

在 PowerShell 中运行：

```powershell
cd D:\AICode\工具开发\projects\xhs-dl
.\setup-v2.ps1
python -m pip install -e .
```

安装器会把引擎放在 `D:\AICode\工具开发\projects\XHS_Downloader`，并为它单独准备 Python 3.12 环境，不影响系统 Python。

## 直接使用

双击 `启动无水印版.bat`，也可以从命令行运行：

```powershell
# 单条或整段分享文本
xhs-dl "http://xhslink.com/o/70dt8TsFJon"
xhs-dl "https://v.douyin.com/VFppn9c-lds/"

# 多条链接或文件，指定保存目录
xhs-dl -f links.txt -o D:\Download\小红书 --mode slow

# 明确指定本地引擎
xhs-dl "链接" --engine-home D:\AICode\工具开发\projects\XHS_Downloader

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

Android V1.3.2 显示名为“万能下载器”，当前仍只支持小红书和抖音。可以手动粘贴或通过系统分享进入；新安装默认保存到 `Download/万能下载器`，升级用户会保留此前自选目录。

安卓端与电脑端使用同名的“拟态悬浮 / 克制玻璃”双主题，并记住主题、下载子目录、自动频率和更新检测设置。Android 10 及以上使用系统 MediaStore 保存，不需要索取全部文件权限。

## iPhone 应用

`ios/` 提供“万能下载器”iOS V0.3.2 客户端，当前仍只支持小红书和抖音，发布目标兼容 iOS 12 / iPhone 6。默认保存到“文件”App 可见的 `万能下载器` 目录，也可以改到用户授权的“我的 iPhone”或 iCloud Drive 文件夹。

iPhone 版与另外两端相互独立，不上传下载历史。仓库使用 GitHub macOS 构建机做无签名模拟器编译；安装到真机仍需用户自己的 Apple 开发签名，详见 `ios/README.md`。

## 本地输出

```text
xhs_downloads/
└── 评128-赞3560-标题-作者/
    ├── 封面-标题.jpg
    ├── 内页1-标题.jpg
    └── 文案.txt
```

所有成功历史集中保存在 `%LOCALAPPDATA%\xhs-dl\history.json`。源码运行要求 Python 3.9 及以上；Windows 便携版无需自行配置 Python。

模板配置保存在 `templates/local-cli.json`。可用环境变量 `XHS_DOWNLOADER_HOME` 覆盖引擎位置。

## 使用边界

仅下载你有权访问和保存的公开内容；请尊重创作者版权、平台规则与隐私。链接解析受平台接口和风控变化影响，失败时可降低频率或更新本地引擎。

详细说明见 `使用手册.md` 与 `安全与注意事项.md`。正式 AI/OpenClaw Skill 位于 `skills/universal-downloader`；`skills/xhs-download` 仅保留旧调用兼容。

## License

本适配项目为 MIT；独立下载引擎为 GPL-3.0，以其仓库许可证为准。
