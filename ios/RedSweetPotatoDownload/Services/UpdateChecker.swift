import Foundation

struct UpdateResult: Sendable {
    let current: String
    let latest: String
    let available: Bool
    let releaseURL: URL
}

struct UpdateChecker {
    func check() async throws -> UpdateResult {
        let url = URL(string: "https://api.github.com/repos/zwmopen/xhs-dl/releases?per_page=20")!
        var request = URLRequest(url: url, timeoutInterval: 10)
        request.setValue("red-sweet-potato-download-ios", forHTTPHeaderField: "User-Agent")
        let (data, _) = try await URLSession.shared.data(for: request)
        let releases = try JSONSerialization.jsonObject(with: data) as? [[String: Any]] ?? []
        guard let release = releases.first(where: { ($0["tag_name"] as? String)?.hasPrefix("ios-v") == true }),
              let tag = release["tag_name"] as? String,
              let page = release["html_url"] as? String,
              let releaseURL = URL(string: page) else {
            throw URLError(.cannotParseResponse)
        }
        let latest = String(tag.dropFirst("ios-v".count))
        let current = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0.1.0"
        return UpdateResult(current: current, latest: latest, available: compare(latest, current) == .orderedDescending, releaseURL: releaseURL)
    }

    private func compare(_ left: String, _ right: String) -> ComparisonResult {
        left.compare(right, options: .numeric)
    }
}
