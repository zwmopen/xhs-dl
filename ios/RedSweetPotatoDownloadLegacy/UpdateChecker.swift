import Foundation

final class UpdateChecker {
    func check(completion: @escaping (String?, URL?, Error?) -> Void) {
        let current = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0.1.0"
        guard let url = URL(string: "https://api.github.com/repos/zwmopen/xhs-dl/releases?per_page=20") else {
            completion(nil, nil, AppFailure.invalidURL); return
        }
        var request = URLRequest(url: url, timeoutInterval: 12)
        request.setValue("red-sweet-potato-download-ios", forHTTPHeaderField: "User-Agent")
        URLSession.shared.dataTask(with: request) { data, _, error in
            if let error = error { completion(nil, nil, error); return }
            guard let data = data,
                  let releases = try? JSONSerialization.jsonObject(with: data) as? [[String: Any]],
                  let found = self.findIOSRelease(in: releases) else {
                completion(nil, nil, URLError(.cannotParseResponse)); return
            }
            let available = found.version.compare(current, options: .numeric) == .orderedDescending
            completion(available ? found.version : current, available ? found.url : nil, nil)
        }.resume()
    }

    private func findIOSRelease(in releases: [[String: Any]]) -> (version: String, url: URL)? {
        for release in releases {
            if (release["draft"] as? Bool) == true || (release["prerelease"] as? Bool) == true { continue }
            guard let assets = release["assets"] as? [[String: Any]] else { continue }
            for asset in assets {
                guard let name = asset["name"] as? String,
                      let marker = name.range(of: "ios-v", options: .caseInsensitive),
                      name.lowercased().hasSuffix(".ipa") else { continue }
                let tail = name[marker.upperBound...]
                let version = String(tail.split(separator: "-").first ?? "")
                guard !version.isEmpty,
                      version.split(separator: ".").allSatisfy({ Int($0) != nil }),
                      let value = asset["browser_download_url"] as? String,
                      let url = URL(string: value) else { continue }
                return (version, url)
            }
        }
        return nil
    }
}
