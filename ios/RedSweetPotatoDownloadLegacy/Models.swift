import Foundation

struct MediaItem {
    let url: URL
    let fileExtension: String
}

struct NoteData {
    let sourceURL: URL
    let noteID: String
    let title: String
    let body: String
    let author: String
    let comments: String
    let likes: String
    let topics: [String]
    let media: [MediaItem]

    var folderName: String {
        return "评\(safe(comments, limit: 12))-赞\(safe(likes, limit: 12))-\(safe(title.isEmpty ? "未命名笔记" : title, limit: 52))-\(safe(author.isEmpty ? "未知作者" : author, limit: 28))"
    }

    var copyText: String {
        let topicText = topics.isEmpty ? "（无话题）" : topics.map { "#\($0)" }.joined(separator: " ")
        let content = body.isEmpty ? "（正文为空）" : body
        return "标题：\(title)\n\n正文：\n\(content)\n\n话题：\n\(topicText)\n"
    }

    private func safe(_ value: String, limit: Int) -> String {
        let invalid = CharacterSet(charactersIn: "\\/:*?\"<>|").union(.controlCharacters)
        let cleaned = value.components(separatedBy: invalid).joined(separator: "_")
            .trimmingCharacters(in: .whitespacesAndNewlines)
        return String((cleaned.isEmpty ? "未知" : cleaned).prefix(limit))
    }
}

struct HistoryItem: Codable {
    let downloadURL: String
    let noteID: String
    let title: String

    enum CodingKeys: String, CodingKey {
        case downloadURL = "下载网址"
        case noteID = "笔记ID"
        case title = "标题"
    }
}

enum AppFailure: LocalizedError {
    case invalidURL
    case pageChanged
    case noteMissing
    case mediaMissing
    case storage(String)

    var errorDescription: String? {
        switch self {
        case .invalidURL: return "链接格式不正确"
        case .pageChanged: return "公开页面结构发生变化，暂时无法解析"
        case .noteMissing: return "没有取得公开笔记数据，链接可能失效或访问受限"
        case .mediaMissing: return "没有找到可保存的原始媒体"
        case .storage(let detail): return "保存失败：\(detail)"
        }
    }
}
