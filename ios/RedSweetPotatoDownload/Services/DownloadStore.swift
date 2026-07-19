import Foundation

actor DownloadStore {
    static let shared = DownloadStore()
    private let bookmarkKey = "downloadFolderBookmark"
    private let folderNameKey = "downloadFolderName"

    func defaultRoot() throws -> URL {
        let documents = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let root = documents.appendingPathComponent("红薯下载", isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        return root
    }

    func currentFolderName() -> String {
        UserDefaults.standard.string(forKey: folderNameKey) ?? "文件/红薯下载"
    }

    func rememberFolder(_ url: URL) throws {
        let didStartAccess = url.startAccessingSecurityScopedResource()
        defer {
            if didStartAccess {
                url.stopAccessingSecurityScopedResource()
            }
        }
        let bookmark = try url.bookmarkData(options: .withSecurityScope, includingResourceValuesForKeys: nil, relativeTo: nil)
        UserDefaults.standard.set(bookmark, forKey: bookmarkKey)
        UserDefaults.standard.set(url.lastPathComponent, forKey: folderNameKey)
    }

    func clearCustomFolder() {
        UserDefaults.standard.removeObject(forKey: bookmarkKey)
        UserDefaults.standard.removeObject(forKey: folderNameKey)
    }

    func save(_ note: NoteData, progress: @Sendable (Int, Int) async -> Void) async throws {
        let access = try resolveRoot()
        let root = access.url
        defer { if access.securityScoped { root.stopAccessingSecurityScopedResource() } }
        let noteFolder = root.appendingPathComponent(note.folderName, isDirectory: true)
        try FileManager.default.createDirectory(at: noteFolder, withIntermediateDirectories: true)
        for (index, media) in note.media.enumerated() {
            let destination = noteFolder.appendingPathComponent(String(format: "%02d.%@", index + 1, media.fileExtension))
            if !FileManager.default.fileExists(atPath: destination.path) {
                var request = URLRequest(url: media.url, timeoutInterval: 75)
                request.setValue("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)", forHTTPHeaderField: "User-Agent")
                request.setValue("https://www.xiaohongshu.com/", forHTTPHeaderField: "Referer")
                let (temporary, response) = try await URLSession.shared.download(for: request)
                if let http = response as? HTTPURLResponse, !(200..<400).contains(http.statusCode) {
                    throw URLError(.badServerResponse)
                }
                try FileManager.default.moveItem(at: temporary, to: destination)
            }
            await progress(index + 1, note.media.count)
        }
        try note.copyText.write(to: noteFolder.appendingPathComponent("文案.txt"), atomically: true, encoding: .utf8)
        try await HistoryStore.shared.add(note)
    }

    private func resolveRoot() throws -> (url: URL, securityScoped: Bool) {
        guard let data = UserDefaults.standard.data(forKey: bookmarkKey) else {
            return (try defaultRoot(), false)
        }
        var stale = false
        let url = try URL(resolvingBookmarkData: data, options: [.withSecurityScope, .withoutUI], relativeTo: nil, bookmarkDataIsStale: &stale)
        if stale { try rememberFolder(url) }
        guard url.startAccessingSecurityScopedResource() else {
            clearCustomFolder()
            return (try defaultRoot(), false)
        }
        return (url, true)
    }
}
