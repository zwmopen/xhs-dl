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
                  let release = releases.first(where: { ($0["tag_name"] as? String)?.hasPrefix("ios-v") == true }),
                  let tag = release["tag_name"] as? String,
                  let page = release["html_url"] as? String,
                  let pageURL = URL(string: page) else {
                completion(nil, nil, URLError(.cannotParseResponse)); return
            }
            let latest = String(tag.dropFirst("ios-v".count))
            let available = latest.compare(current, options: .numeric) == .orderedDescending
            completion(available ? latest : current, available ? pageURL : nil, nil)
        }.resume()
    }
}
