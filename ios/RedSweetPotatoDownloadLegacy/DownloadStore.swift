import Foundation

final class DownloadStore {
    static let shared = DownloadStore()

    private let bookmarkKey = "downloadFolderBookmark"
    private let folderNameKey = "downloadFolderName"
    private let workQueue = DispatchQueue(label: "com.zwmopen.redsweetpotato.storage")

    var currentFolderName: String {
        return UserDefaults.standard.string(forKey: folderNameKey) ?? "文件/红薯下载"
    }

    func rememberFolder(_ url: URL) throws {
        let started = url.startAccessingSecurityScopedResource()
        defer { if started { url.stopAccessingSecurityScopedResource() } }
        let data = try url.bookmarkData(options: [], includingResourceValuesForKeys: nil, relativeTo: nil)
        UserDefaults.standard.set(data, forKey: bookmarkKey)
        UserDefaults.standard.set(url.lastPathComponent, forKey: folderNameKey)
    }

    func useDefaultFolder() {
        UserDefaults.standard.removeObject(forKey: bookmarkKey)
        UserDefaults.standard.removeObject(forKey: folderNameKey)
    }

    func save(
        _ note: NoteData,
        progress: @escaping (Int, Int) -> Void,
        completion: @escaping (Error?) -> Void
    ) {
        workQueue.async {
            do {
                let access = try self.resolveRoot()
                let folder = access.url.appendingPathComponent(note.folderName, isDirectory: true)
                try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
                self.download(note.media, index: 0, folder: folder, progress: progress) { error in
                    defer { if access.securityScoped { access.url.stopAccessingSecurityScopedResource() } }
                    if let error = error { completion(error); return }
                    do {
                        try note.copyText.write(
                            to: folder.appendingPathComponent("文案.txt"),
                            atomically: true,
                            encoding: .utf8
                        )
                        try self.addHistory(note)
                        completion(nil)
                    } catch {
                        completion(error)
                    }
                }
            } catch {
                completion(error)
            }
        }
    }

    private func download(
        _ media: [MediaItem],
        index: Int,
        folder: URL,
        progress: @escaping (Int, Int) -> Void,
        completion: @escaping (Error?) -> Void
    ) {
        guard index < media.count else { completion(nil); return }
        let item = media[index]
        let destination = folder.appendingPathComponent(String(format: "%02d.%@", index + 1, item.fileExtension))
        if FileManager.default.fileExists(atPath: destination.path) {
            DispatchQueue.main.async { progress(index + 1, media.count) }
            download(media, index: index + 1, folder: folder, progress: progress, completion: completion)
            return
        }
        var request = URLRequest(url: item.url, timeoutInterval: 75)
        request.setValue("Mozilla/5.0 (iPhone; CPU iPhone OS 12_5 like Mac OS X)", forHTTPHeaderField: "User-Agent")
        request.setValue("https://www.xiaohongshu.com/", forHTTPHeaderField: "Referer")
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error { completion(error); return }
            if let http = response as? HTTPURLResponse, !(200..<400).contains(http.statusCode) {
                completion(URLError(.badServerResponse)); return
            }
            guard let data = data else { completion(URLError(.zeroByteResource)); return }
            do {
                try data.write(to: destination, options: .atomic)
                DispatchQueue.main.async { progress(index + 1, media.count) }
                self.download(media, index: index + 1, folder: folder, progress: progress, completion: completion)
            } catch {
                completion(error)
            }
        }.resume()
    }

    private func defaultRoot() throws -> URL {
        let documents = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let root = documents.appendingPathComponent("红薯下载", isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        return root
    }

    private func resolveRoot() throws -> (url: URL, securityScoped: Bool) {
        guard let data = UserDefaults.standard.data(forKey: bookmarkKey) else {
            return (try defaultRoot(), false)
        }
        var stale = false
        let url = try URL(
            resolvingBookmarkData: data,
            options: [.withoutUI],
            relativeTo: nil,
            bookmarkDataIsStale: &stale
        )
        if stale { try rememberFolder(url) }
        guard url.startAccessingSecurityScopedResource() else {
            useDefaultFolder()
            return (try defaultRoot(), false)
        }
        return (url, true)
    }

    private func addHistory(_ note: NoteData) throws {
        let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        try FileManager.default.createDirectory(at: support, withIntermediateDirectories: true)
        let file = support.appendingPathComponent("history.json")
        var items: [HistoryItem] = []
        if let data = try? Data(contentsOf: file) {
            items = (try? JSONDecoder().decode([HistoryItem].self, from: data)) ?? []
        }
        items.removeAll { !$0.noteID.isEmpty ? $0.noteID == note.noteID : $0.downloadURL == note.sourceURL.absoluteString }
        items.append(HistoryItem(downloadURL: note.sourceURL.absoluteString, noteID: note.noteID, title: note.title))
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        try encoder.encode(items).write(to: file, options: .atomic)
    }
}
