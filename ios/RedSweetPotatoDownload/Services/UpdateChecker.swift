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
        guard let found = findIOSRelease(in: releases) else {
            throw URLError(.cannotParseResponse)
        }
        let current = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0.1.0"
        return UpdateResult(current: current, latest: found.version, available: compare(found.version, current) == .orderedDescending, releaseURL: found.url)
    }

    private func findIOSRelease(in releases: [[String: Any]]) -> (version: String, url: URL)? {
        for release in releases {
            if (release["draft"] as? Bool) == true || (release["prerelease"] as? Bool) == true { continue }
            guard let assets = release["assets"] as? [[String: Any]] else { continue }
            for asset in assets {
                guard let name = asset["name"] as? String,
                      let marker = name.range(of: "ios-v", options: .caseInsensitive),
                      name.lowercased().hasSuffix(".ipa") else { continue }
                let version = String(name[marker.upperBound...].split(separator: "-").first ?? "")
                guard !version.isEmpty,
                      version.split(separator: ".").allSatisfy({ Int($0) != nil }),
                      let value = asset["browser_download_url"] as? String,
                      let url = URL(string: value) else { continue }
                return (version, url)
            }
        }
        return nil
    }

    private func compare(_ left: String, _ right: String) -> ComparisonResult {
        left.compare(right, options: .numeric)
    }
}
