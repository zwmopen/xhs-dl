# 红薯下载 iPhone 客户端

## 当前状态

iOS V0.1.0 源码预览版。已完成 SwiftUI 界面、公开笔记解析、原图/视频保存、文案、集中历史、自选 Files 文件夹、双主题、使用说明和更新检测。代码已在 GitHub 的 macOS 15 / Xcode 16.4 构建机完成无签名 iPhone Simulator 编译。当前 Windows 开发机仍无法签名 IPA 或安装到 iPhone，因此不把模拟器编译冒充为真机通过。

## 在 Mac 上构建

1. 安装 Xcode 16 或更高版本，以及 [XcodeGen](https://github.com/yonaskolb/XcodeGen)。
2. 在本目录执行 `xcodegen generate`。
3. 打开 `RedSweetPotatoDownload.xcodeproj`，选择自己的 Team 和唯一 Bundle Identifier。
4. 连接 iPhone，先运行 Debug，按 `IOS-ACCEPTANCE.md` 完成真机验收。
5. 通过后再 Archive，使用 TestFlight、Ad Hoc 或 App Store 分发。

## 数据位置

- 默认下载：App 的 Documents/红薯下载，可在“文件”App 中看到。
- 自选目录：使用系统文件夹选择器保存持久书签，写入期间启用 security-scoped access，授权可随时在设置中恢复默认。
- 历史：Application Support/history.json，仅在本机保存。

## 安全边界

只处理用户有权保存的公开内容；不使用账号、密码或 Cookie，不绕过访问控制，不移除作者嵌入媒体的署名。
