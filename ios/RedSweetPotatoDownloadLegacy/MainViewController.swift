import UIKit
import WebKit

final class MainViewController: UIViewController, WKScriptMessageHandler, WKNavigationDelegate, UIDocumentPickerDelegate {
    private var webView: WKWebView!
    private var running = false
    private var resultLines: [String] = []

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = UIColor(red: 0.88, green: 0.91, blue: 0.93, alpha: 1)

        let controller = WKUserContentController()
        controller.add(self, name: "bridge")
        let configuration = WKWebViewConfiguration()
        configuration.userContentController = controller
        webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = self
        webView.scrollView.bounces = false
        webView.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(webView)
        NSLayoutConstraint.activate([
            webView.topAnchor.constraint(equalTo: view.topAnchor),
            webView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            webView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            webView.bottomAnchor.constraint(equalTo: view.bottomAnchor)
        ])

        guard let file = Bundle.main.url(forResource: "index", withExtension: "html", subdirectory: "Resources")
            ?? Bundle.main.url(forResource: "index", withExtension: "html") else {
            presentAlert(title: "启动失败", message: "找不到本地界面资源。")
            return
        }
        webView.loadFileURL(file, allowingReadAccessTo: file.deletingLastPathComponent())
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        emit("folder", payload: ["name": DownloadStore.shared.currentFolderName])
        emit("version", payload: ["value": versionText])
    }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard let body = message.body as? [String: Any], let action = body["action"] as? String else { return }
        switch action {
        case "paste":
            emit("input", payload: ["text": UIPasteboard.general.string ?? ""])
        case "pasteAndCollect":
            let text = UIPasteboard.general.string ?? ""
            emit("input", payload: ["text": text])
            beginCollection(text)
        case "collect":
            beginCollection(body["text"] as? String ?? "")
        case "chooseFolder":
            chooseFolder()
        case "resetFolder":
            DownloadStore.shared.useDefaultFolder()
            emit("folder", payload: ["name": DownloadStore.shared.currentFolderName])
        case "checkUpdate":
            checkUpdate()
        case "openProject":
            if let url = URL(string: "https://github.com/zwmopen/xhs-dl") { UIApplication.shared.openURL(url) }
        default:
            break
        }
    }

    private func beginCollection(_ text: String) {
        guard !running else { return }
        let targets = extractURLs(text)
        guard !targets.isEmpty else {
            emit("status", payload: ["title": "未识别到链接", "detail": "请粘贴小红书公开笔记链接。", "progress": 0])
            return
        }
        running = true
        resultLines = []
        emit("running", payload: ["value": true])
        emit("status", payload: [
            "title": "准备采集 \(targets.count) 条",
            "detail": modeDescription(count: targets.count),
            "progress": 0
        ])
        collect(targets, index: 0, success: 0, failed: 0)
    }

    private func collect(_ targets: [URL], index: Int, success: Int, failed: Int) {
        guard index < targets.count else {
            running = false
            emit("running", payload: ["value": false])
            emit("status", payload: [
                "title": failed == 0 ? "全部保存完成" : "任务完成",
                "detail": "成功 \(success) 条，失败 \(failed) 条",
                "progress": 1,
                "results": resultLines
            ])
            return
        }

        let url = targets[index]
        emit("status", payload: [
            "title": "正在解析第 \(index + 1) 条",
            "detail": url.absoluteString,
            "progress": Double(index) / Double(targets.count),
            "results": resultLines
        ])
        XhsParser().fetch(url) { note, error in
            DispatchQueue.main.async {
                guard let note = note, error == nil else {
                    self.resultLines.append("\(index + 1)/\(targets.count) 失败：\(error?.localizedDescription ?? "未知错误")")
                    self.finishOne(targets, index: index, success: success, failed: failed + 1)
                    return
                }
                DownloadStore.shared.save(note, progress: { done, total in
                    self.emit("status", payload: [
                        "title": "正在保存 · \(note.title)",
                        "detail": "媒体 \(done) / \(total)",
                        "progress": (Double(index) + Double(done) / Double(max(total, 1))) / Double(targets.count),
                        "results": self.resultLines
                    ])
                }) { saveError in
                    DispatchQueue.main.async {
                        if let saveError = saveError {
                            self.resultLines.append("\(index + 1)/\(targets.count) 失败：\(saveError.localizedDescription)")
                            self.finishOne(targets, index: index, success: success, failed: failed + 1)
                        } else {
                            self.resultLines.append("\(index + 1)/\(targets.count) 完成：\(note.title)")
                            self.finishOne(targets, index: index, success: success + 1, failed: failed)
                        }
                    }
                }
            }
        }
    }

    private func finishOne(_ targets: [URL], index: Int, success: Int, failed: Int) {
        let next = index + 1
        guard next < targets.count else {
            collect(targets, index: next, success: success, failed: failed)
            return
        }
        let delay = delaySeconds(count: targets.count)
        emit("status", payload: [
            "title": "安全等待中",
            "detail": "下一条约 \(delay) 秒后开始",
            "progress": Double(next) / Double(targets.count),
            "results": resultLines
        ])
        DispatchQueue.main.asyncAfter(deadline: .now() + .seconds(delay)) {
            self.collect(targets, index: next, success: success, failed: failed)
        }
    }

    private func chooseFolder() {
        let picker = UIDocumentPickerViewController(documentTypes: ["public.folder"], in: .open)
        picker.delegate = self
        picker.allowsMultipleSelection = false
        present(picker, animated: true)
    }

    func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
        guard let url = urls.first else { return }
        do {
            try DownloadStore.shared.rememberFolder(url)
            emit("folder", payload: ["name": DownloadStore.shared.currentFolderName])
        } catch {
            presentAlert(title: "目录设置失败", message: error.localizedDescription)
        }
    }

    func documentPickerWasCancelled(_ controller: UIDocumentPickerViewController) {
        controller.dismiss(animated: true)
    }

    private func checkUpdate() {
        emit("update", payload: ["message": "正在检测…"])
        UpdateChecker().check { version, page, error in
            DispatchQueue.main.async {
                if error != nil {
                    self.emit("update", payload: ["message": "暂时无法检测，请检查网络后再试。"])
                } else if let page = page, let version = version {
                    self.emit("update", payload: ["message": "发现 iOS V\(version)，即将打开发布页。"])
                    UIApplication.shared.openURL(page)
                } else {
                    self.emit("update", payload: ["message": "当前 \(self.versionText)，已是最新版本。"])
                }
            }
        }
    }

    private func extractURLs(_ text: String) -> [URL] {
        guard let detector = try? NSDataDetector(types: NSTextCheckingResult.CheckingType.link.rawValue) else { return [] }
        let matches = detector.matches(in: text, range: NSRange(location: 0, length: (text as NSString).length))
        var seen = Set<String>()
        return matches.compactMap { match in
            guard let url = match.url, let scheme = url.scheme?.lowercased(), scheme == "http" || scheme == "https" else { return nil }
            guard seen.insert(url.absoluteString).inserted else { return nil }
            return url
        }
    }

    private func modeDescription(count: Int) -> String {
        if count == 1 { return "单条直接采集" }
        if count <= 20 { return "稳妥模式 · 每条随机等待 35–55 秒" }
        if count <= 50 { return "慢速模式 · 每条随机等待 55–85 秒" }
        return "极慢模式 · 每条随机等待 110–160 秒"
    }

    private func delaySeconds(count: Int) -> Int {
        if count <= 20 { return Int.random(in: 35...55) }
        if count <= 50 { return Int.random(in: 55...85) }
        return Int.random(in: 110...160)
    }

    private var versionText: String {
        let value = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0.1.0"
        return "iOS V\(value)"
    }

    private func emit(_ name: String, payload: [String: Any]) {
        guard JSONSerialization.isValidJSONObject(payload),
              let data = try? JSONSerialization.data(withJSONObject: payload),
              let json = String(data: data, encoding: .utf8) else { return }
        let safeName = name.replacingOccurrences(of: "'", with: "")
        webView.evaluateJavaScript("window.nativeEvent('\(safeName)', \(json));", completionHandler: nil)
    }

    private func presentAlert(title: String, message: String) {
        let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "知道了", style: .default))
        present(alert, animated: true)
    }

    deinit {
        webView?.configuration.userContentController.removeScriptMessageHandler(forName: "bridge")
    }
}
