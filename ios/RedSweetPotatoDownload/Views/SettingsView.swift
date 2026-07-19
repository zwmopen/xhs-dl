import SwiftUI

struct SettingsView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.openURL) private var openURL
    @AppStorage("theme") private var themeValue = AppTheme.neo.rawValue
    @AppStorage("autoUpdate") private var autoUpdate = true
    @State private var folderName = "文件/红薯下载"
    @State private var showsFolderPicker = false
    @State private var showsGuide = false
    @State private var updateMessage: String?
    @State private var checkingUpdate = false

    private var theme: AppTheme { AppTheme(rawValue: themeValue) ?? .neo }

    var body: some View {
        NavigationStack {
            ZStack {
                theme.background.ignoresSafeArea()
                ScrollView {
                    VStack(spacing: 16) {
                        storageSection
                        appearanceSection
                        aboutSection
                        Text("所有设置和历史只保存在本机 · 不做云同步")
                            .font(.footnote)
                            .foregroundStyle(theme.muted)
                    }
                    .padding(20)
                }
            }
            .navigationTitle("设置与帮助")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("完成") { dismiss() } } }
        }
        .task { folderName = await DownloadStore.shared.currentFolderName() }
        .sheet(isPresented: $showsFolderPicker) {
            DirectoryPicker { url in
                Task {
                    do {
                        try await DownloadStore.shared.rememberFolder(url)
                        folderName = await DownloadStore.shared.currentFolderName()
                    } catch {
                        updateMessage = "无法记住这个文件夹：\(error.localizedDescription)"
                    }
                    showsFolderPicker = false
                }
            }
        }
        .sheet(isPresented: $showsGuide) { GuideView(theme: theme) }
        .alert("版本与提示", isPresented: Binding(get: { updateMessage != nil }, set: { if !$0 { updateMessage = nil } })) {
            Button("关闭", role: .cancel) {}
        } message: { Text(updateMessage ?? "") }
    }

    private var storageSection: some View {
        section(title: "下载目录", detail: "默认进入 iPhone“文件/红薯下载”；也可以授权 iCloud Drive 或“我的 iPhone”中的其他文件夹。") {
            Label(folderName, systemImage: "folder.fill")
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(theme.text)
            Button("选择其他目录") { showsFolderPicker = true }.buttonStyle(.borderedProminent)
            Button("恢复默认目录") {
                Task {
                    await DownloadStore.shared.clearCustomFolder()
                    folderName = await DownloadStore.shared.currentFolderName()
                }
            }
            .buttonStyle(.bordered)
        }
    }

    private var appearanceSection: some View {
        section(title: "外观与更新", detail: "两套主题会自动记住。自动更新只检查官方发布页，不会静默安装。") {
            Picker("视觉主题", selection: $themeValue) {
                ForEach(AppTheme.allCases) { item in Text(item.name).tag(item.rawValue) }
            }
            .pickerStyle(.segmented)
            Toggle("启动时检测新版本", isOn: $autoUpdate)
        }
    }

    private var aboutSection: some View {
        section(title: "关于红薯下载", detail: "本地优先、免账号登录、直接读取公开笔记原图地址。") {
            info("设计思路", "内容层稳定清楚，玻璃只服务导航和短暂操作；中文可读性、进度和失败原因优先。")
            Button("使用说明与安全边界") { showsGuide = true }.buttonStyle(.bordered)
            Button(checkingUpdate ? "正在检测…" : "检测更新") { checkUpdate() }
                .buttonStyle(.bordered)
                .disabled(checkingUpdate)
            Button("打开项目与历史版本") { openURL(URL(string: "https://github.com/zwmopen/xhs-dl")!) }
                .buttonStyle(.bordered)
            Text("iOS V0.1.0 · 源码预览版")
                .font(.caption)
                .foregroundStyle(theme.muted)
        }
    }

    private func section<Content: View>(title: String, detail: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title).font(.title3.weight(.bold)).foregroundStyle(theme.text)
            Text(detail).font(.subheadline).foregroundStyle(theme.muted)
            content()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(18)
        .contentSurface(theme)
    }

    private func info(_ title: String, _ detail: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title).font(.subheadline.weight(.bold))
            Text(detail).font(.footnote).foregroundStyle(theme.muted)
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.white.opacity(0.34), in: RoundedRectangle(cornerRadius: 14))
    }

    private func checkUpdate() {
        checkingUpdate = true
        Task {
            defer { checkingUpdate = false }
            do {
                let result = try await UpdateChecker().check()
                if result.available {
                    updateMessage = "发现 iOS V\(result.latest)。当前版本 V\(result.current)，请前往官方发布页查看安装说明。"
                    openURL(result.releaseURL)
                } else {
                    updateMessage = "当前 iOS V\(result.current)，已经是最新版。"
                }
            } catch {
                updateMessage = "暂时无法检测更新，请检查网络后再试。"
            }
        }
    }
}

struct GuideView: View {
    @Environment(\.dismiss) private var dismiss
    let theme: AppTheme

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    guide("1 · 粘贴", "复制公开小红书笔记链接或整段分享文字，回到首页点“粘贴”。")
                    guide("2 · 采集", "单条直接开始；批量任务会自动使用随机间隔，降低连续访问风险。")
                    guide("3 · 保存", "默认进入“文件/红薯下载”，每条笔记文件夹只包含媒体和文案.txt。")
                    guide("4 · 数据", "历史 JSON 位于 App 内部数据，不会上云，不散落到下载目录。")
                    guide("安全边界", "只处理你有权保存的公开内容；不绕过私密、删除、年龄、地区或其他访问限制；作者做进原图的署名会保留。")
                }
                .padding(20)
            }
            .background(theme.background.ignoresSafeArea())
            .navigationTitle("使用说明")
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("完成") { dismiss() } } }
        }
    }

    private func guide(_ title: String, _ detail: String) -> some View {
        VStack(alignment: .leading, spacing: 7) {
            Text(title).font(.headline).foregroundStyle(theme.text)
            Text(detail).font(.body).foregroundStyle(theme.muted)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(17)
        .contentSurface(theme)
    }
}
