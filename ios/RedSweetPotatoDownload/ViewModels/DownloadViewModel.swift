import Foundation
#if canImport(UIKit)
import UIKit
#endif

@MainActor
final class DownloadViewModel: ObservableObject {
    @Published var input = ""
    @Published var statusTitle = "等待开始"
    @Published var statusDetail = "粘贴后自动识别条数和安全频率"
    @Published var progress = 0.0
    @Published var results: [String] = []
    @Published var running = false
    @Published var errorMessage: String?

    var urls: [URL] { Self.extractURLs(input) }

    func pasteFromClipboard() {
        #if canImport(UIKit)
        input = UIPasteboard.general.string ?? input
        refreshDetection()
        #endif
    }

    func refreshDetection() {
        let count = urls.count
        if count == 0 {
            statusTitle = "等待开始"
            statusDetail = "还没有识别到小红书链接"
        } else {
            statusTitle = "已识别 \(count) 条"
            statusDetail = "自动使用：\(modeDescription(for: count))"
        }
    }

    func start() {
        let targets = urls
        guard !targets.isEmpty, !running else { return }
        running = true
        progress = 0
        results = []
        statusTitle = "正在准备"
        statusDetail = "共 \(targets.count) 条 · \(modeDescription(for: targets.count))"
        Task { await collect(targets) }
    }

    private func collect(_ targets: [URL]) async {
        var success = 0
        var failed = 0
        let parser = XhsParser()
        for (index, url) in targets.enumerated() {
            do {
                statusTitle = "正在解析第 \(index + 1) 条"
                statusDetail = url.absoluteString
                let note = try await parser.fetch(url)
                try await DownloadStore.shared.save(note) { done, total in
                    await MainActor.run {
                        self.statusTitle = "正在保存 · \(note.title)"
                        self.statusDetail = "媒体 \(done) / \(total)"
                    }
                }
                success += 1
                results.append("\(index + 1)/\(targets.count)  完成  \(note.title)")
            } catch {
                failed += 1
                results.append("\(index + 1)/\(targets.count)  失败  \(error.localizedDescription)")
            }
            progress = Double(index + 1) / Double(targets.count)
            if index < targets.count - 1 {
                let wait = delaySeconds(for: targets.count)
                statusTitle = "安全等待中"
                statusDetail = "下一条将在约 \(wait) 秒后开始"
                try? await Task.sleep(for: .seconds(wait))
            }
        }
        running = false
        statusTitle = failed == 0 ? "全部保存完成" : "任务完成"
        statusDetail = "成功 \(success) 条，失败 \(failed) 条"
    }

    private func modeDescription(for count: Int) -> String {
        if count <= 1 { return "单条直接采集" }
        if count <= 20 { return "稳妥 35–55 秒" }
        if count <= 50 { return "慢速 55–85 秒" }
        return "极慢 110–160 秒"
    }

    private func delaySeconds(for count: Int) -> Int {
        if count <= 20 { return Int.random(in: 35...55) }
        if count <= 50 { return Int.random(in: 55...85) }
        return Int.random(in: 110...160)
    }

    static func extractURLs(_ text: String) -> [URL] {
        guard let detector = try? NSDataDetector(types: NSTextCheckingResult.CheckingType.link.rawValue) else { return [] }
        let range = NSRange(text.startIndex..., in: text)
        var seen = Set<String>()
        return detector.matches(in: text, range: range).compactMap { match in
            guard let url = match.url, ["http", "https"].contains(url.scheme?.lowercased() ?? "") else { return nil }
            return seen.insert(url.absoluteString).inserted ? url : nil
        }
    }
}
