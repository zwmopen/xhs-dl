import Foundation

actor HistoryStore {
    static let shared = HistoryStore()

    private var fileURL: URL {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        try? FileManager.default.createDirectory(at: base, withIntermediateDirectories: true)
        return base.appendingPathComponent("history.json")
    }

    func read() -> [HistoryItem] {
        guard let data = try? Data(contentsOf: fileURL) else { return [] }
        return (try? JSONDecoder().decode([HistoryItem].self, from: data)) ?? []
    }

    func add(_ note: NoteData) throws {
        let item = HistoryItem(downloadURL: note.sourceURL.absoluteString, noteID: note.noteID, title: note.title)
        var items = read().filter { $0.id != item.id }
        items.append(item)
        let data = try JSONEncoder.pretty.encode(items)
        try data.write(to: fileURL, options: .atomic)
    }
}

private extension JSONEncoder {
    static var pretty: JSONEncoder {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        return encoder
    }
}
