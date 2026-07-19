import Foundation

final class XhsParser {
    func fetch(_ sourceURL: URL, completion: @escaping (NoteData?, Error?) -> Void) {
        let fixed = sourceURL.absoluteString.replacingOccurrences(of: "http://xhslink.com", with: "https://xhslink.com")
        guard let normalized = URL(string: fixed) else {
            completion(nil, AppFailure.invalidURL)
            return
        }
        var request = URLRequest(url: normalized, timeoutInterval: 30)
        request.setValue("Mozilla/5.0 (iPhone; CPU iPhone OS 12_5 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148", forHTTPHeaderField: "User-Agent")
        request.setValue("zh-CN,zh;q=0.9", forHTTPHeaderField: "Accept-Language")
        request.setValue("https://www.xiaohongshu.com/", forHTTPHeaderField: "Referer")
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error { completion(nil, error); return }
            guard let data = data, let html = String(data: data, encoding: .utf8) else {
                completion(nil, AppFailure.pageChanged); return
            }
            do {
                let state = try self.initialState(from: html)
                guard let note = self.findNote(in: state) else { throw AppFailure.noteMissing }
                let finalURL = response?.url ?? normalized
                completion(try self.parse(note: note, sourceURL: finalURL), nil)
            } catch {
                completion(nil, error)
            }
        }.resume()
    }

    private func initialState(from html: String) throws -> [String: Any] {
        let marker = "window.__INITIAL_STATE__="
        guard let markerRange = html.range(of: marker),
              let end = html.range(of: "</script>", range: markerRange.upperBound..<html.endIndex) else {
            throw AppFailure.pageChanged
        }
        var json = String(html[markerRange.upperBound..<end.lowerBound]).trimmingCharacters(in: .whitespacesAndNewlines)
        if json.hasSuffix(";") { json.removeLast() }
        json = json.replacingOccurrences(
            of: #"(?<=[:\[,])\s*undefined(?=\s*[,}\]])"#,
            with: "null",
            options: .regularExpression
        )
        guard let data = json.data(using: .utf8),
              let root = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw AppFailure.pageChanged
        }
        return root
    }

    private func findNote(in root: [String: Any]) -> [String: Any]? {
        if let noteData = root["noteData"] as? [String: Any],
           let data = noteData["data"] as? [String: Any],
           let note = data["noteData"] as? [String: Any] { return note }
        if let noteRoot = root["note"] as? [String: Any],
           let map = noteRoot["noteDetailMap"] as? [String: Any] {
            for value in map.values {
                if let entry = value as? [String: Any], let note = entry["note"] as? [String: Any] { return note }
            }
        }
        return nil
    }

    private func parse(note: [String: Any], sourceURL: URL) throws -> NoteData {
        let user = note["user"] as? [String: Any]
        let interact = note["interactInfo"] as? [String: Any]
        let tags = (note["tagList"] as? [[String: Any]] ?? []).compactMap { $0["name"] as? String }.filter { !$0.isEmpty }
        let kind = string(note["type"], fallback: "normal")
        let media = kind == "video" ? videoItems(note) : imageItems(note["imageList"] as? [[String: Any]] ?? [])
        guard !media.isEmpty else { throw AppFailure.mediaMissing }
        return NoteData(
            sourceURL: sourceURL,
            noteID: string(note["noteId"]),
            title: string(note["title"]),
            body: string(note["desc"]),
            author: string(user?["nickname"] ?? user?["nickName"]),
            comments: string(interact?["commentCount"], fallback: "未知"),
            likes: string(interact?["likedCount"], fallback: "未知"),
            topics: tags,
            media: media
        )
    }

    private func imageItems(_ images: [[String: Any]]) -> [MediaItem] {
        return images.compactMap { image in
            let info = image["infoList"] as? [[String: Any]] ?? image["info_list"] as? [[String: Any]] ?? []
            let detail = info.first { self.string($0["imageScene"] ?? $0["image_scene"]) == "H5_DTL" }
            let raw = string(detail?["url"] ?? info.first?["url"] ?? image["urlDefault"] ?? image["url"])
            let parts = raw.split(separator: "/", omittingEmptySubsequences: false)
            guard parts.count > 5 else { return nil }
            let token = parts.dropFirst(5).joined(separator: "/").split(separator: "!").first.map(String.init) ?? ""
            guard !token.isEmpty, let url = URL(string: "https://ci.xiaohongshu.com/\(token)?imageView2/format/png") else { return nil }
            return MediaItem(url: url, fileExtension: "png")
        }
    }

    private func videoItems(_ note: [String: Any]) -> [MediaItem] {
        guard let video = note["video"] as? [String: Any] else { return [] }
        if let consumer = video["consumer"] as? [String: Any] {
            let key = string(consumer["originVideoKey"])
            if !key.isEmpty, let url = URL(string: "https://sns-video-bd.xhscdn.com/\(key)") {
                return [MediaItem(url: url, fileExtension: "mp4")]
            }
        }
        if let media = video["media"] as? [String: Any],
           let stream = media["stream"] as? [String: Any],
           let h264 = stream["h264"] as? [[String: Any]], let best = h264.last {
            let backups = best["backupUrls"] as? [String]
            let raw = backups?.first ?? string(best["masterUrl"])
            if let url = URL(string: raw), !raw.isEmpty { return [MediaItem(url: url, fileExtension: "mp4")] }
        }
        return []
    }

    private func string(_ value: Any?, fallback: String = "") -> String {
        guard let value = value, !(value is NSNull) else { return fallback }
        return value as? String ?? String(describing: value)
    }
}
