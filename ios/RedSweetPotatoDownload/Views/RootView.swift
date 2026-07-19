import SwiftUI

struct RootView: View {
    @StateObject private var model = DownloadViewModel()
    @AppStorage("theme") private var themeValue = AppTheme.neo.rawValue
    @State private var showsSettings = false

    private var theme: AppTheme { AppTheme(rawValue: themeValue) ?? .neo }

    var body: some View {
        ZStack {
            theme.background.ignoresSafeArea()
            ScrollView {
                VStack(spacing: 18) {
                    header
                    inputCard
                    statusCard
                    actionCard
                    Text("原始媒体直存 · 设置和历史只留在本机 · iOS V0.1.0")
                        .font(.footnote)
                        .foregroundStyle(theme.muted)
                        .padding(.top, 4)
                }
                .padding(.horizontal, 20)
                .padding(.vertical, 16)
            }
        }
        .sheet(isPresented: $showsSettings) { SettingsView() }
        .onChange(of: model.input) { _ in model.refreshDetection() }
    }

    private var header: some View {
        HStack(alignment: .center, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Text("红薯下载")
                    .font(.system(size: 34, weight: .regular, design: .serif))
                    .foregroundStyle(theme.text)
                Text("公开笔记 · iPhone 直存 · 无需登录")
                    .font(.subheadline)
                    .foregroundStyle(theme.muted)
            }
            Spacer(minLength: 8)
            HStack(spacing: 8) {
                Button(theme == .neo ? "克制玻璃" : "拟态悬浮") {
                    withAnimation(.easeInOut(duration: 0.22)) {
                        themeValue = (theme == .neo ? AppTheme.glass : AppTheme.neo).rawValue
                    }
                }
                Button { showsSettings = true } label: { Image(systemName: "gearshape.fill") }
            }
            .font(.subheadline.weight(.semibold))
            .buttonStyle(.bordered)
            .background(.regularMaterial, in: Capsule())
        }
    }

    private var inputCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("粘贴分享内容").font(.headline)
                Spacer()
                Button("粘贴") { model.pasteFromClipboard() }
                    .font(.subheadline.weight(.semibold))
            }
            TextEditor(text: $model.input)
                .frame(minHeight: 170)
                .padding(10)
                .scrollContentBackground(.hidden)
                .background(Color.white.opacity(0.38), in: RoundedRectangle(cornerRadius: 16, style: .continuous))
                .overlay(RoundedRectangle(cornerRadius: 16).stroke(theme.accent.opacity(0.22)))
        }
        .padding(18)
        .contentSurface(theme)
    }

    private var statusCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("采集状态").font(.caption.weight(.bold)).foregroundStyle(theme.muted)
            Text(model.statusTitle).font(.title2.weight(.bold)).foregroundStyle(theme.text)
            Text(model.statusDetail).font(.subheadline).foregroundStyle(theme.muted).lineLimit(3)
            ProgressView(value: model.progress).tint(theme.accent)
            ForEach(Array(model.results.enumerated()), id: \.offset) { _, line in
                Text(line).font(.caption).foregroundStyle(theme.text)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(18)
        .contentSurface(theme)
    }

    private var actionCard: some View {
        Button(model.running ? "采集中…" : "开始采集") { model.start() }
            .font(.headline)
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity, minHeight: 54)
            .background(theme.primary, in: RoundedRectangle(cornerRadius: 17, style: .continuous))
            .shadow(color: theme.primary.opacity(0.22), radius: 10, y: 6)
            .disabled(model.running || model.urls.isEmpty)
            .opacity((model.running || model.urls.isEmpty) ? 0.58 : 1)
    }
}
