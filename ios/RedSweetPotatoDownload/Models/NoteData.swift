import Foundation

struct MediaItem: Sendable {
    let url: URL
    let fileExtension: String
}

struct NoteData: Sendable {
    let sourceURL: URL
    let noteID: String
    let title: String
    let description: String
    let author: String
    let comments: String
    let likes: String
    let topics: [String]
    let media: [MediaItem]

    var folderName: String {
        "评\(safe(comments, 12))-赞\(safe(likes, 12))-\(safe(title.isEmpty ? "未命名笔记" : title, 52))-\(safe(author.isEmpty ? "未知作者" : author, 28))"
    }

    var copyText: String {
        let topicText = topics.isEmpty ? "（无话题）" : topics.map { "#\($0)" }.joined(separator: " ")
        return "标题：\(title)\n\n正文：\n\(description.isEmpty ? "（正文为空）" : description)\n\n话题：\(topicText)\n"
    }

    private func safe(_ value: String, _ limit: Int) -> String {
        let invalid = CharacterSet(charactersIn: "\\/:*?\"<>|").union(.controlCharacters)
        let cleaned = value.components(separatedBy: invalid).joined(separator: "_").trimmingCharacters(in: .whitespacesAndNewlines)
        let fallback = cleaned.isEmpty ? "未知" : cleaned
        return String(fallback.prefix(limit))
    }
}

struct HistoryItem: Codable, Identifiable, Sendable {
    let downloadURL: String
    let noteID: String
    let title: String

    var id: String { noteID.isEmpty ? downloadURL : noteID }

    enum CodingKeys: String, CodingKey {
        case downloadURL = "下载网址"
        case noteID = "笔记ID"
        case title = "标题"
    }
}
