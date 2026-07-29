import Foundation
import WebKit

final class DouyinParser: NSObject, WKNavigationDelegate {
    private static let desktopUserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

    private weak var hostView: UIView?
    private var webView: WKWebView?
    private var sourceURL: URL?
    private var completion: ((NoteData?, Error?) -> Void)?
    private var attempt = 0
    private var finished = false

    func fetch(_ sourceURL: URL, in hostView: UIView, completion: @escaping (NoteData?, Error?) -> Void) {
        self.sourceURL = sourceURL
        self.hostView = hostView
        self.completion = completion

        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        let view = WKWebView(frame: CGRect(x: 0, y: 0, width: 2, height: 2), configuration: configuration)
        view.alpha = 0.01
        view.customUserAgent = Self.desktopUserAgent
        view.navigationDelegate = self
        hostView.addSubview(view)
        webView = view
        view.load(URLRequest(url: sourceURL, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 45))
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        poll()
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        finish(note: nil, error: error)
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        finish(note: nil, error: error)
    }

    private func poll() {
        guard !finished, let webView = webView else { return }
        webView.evaluateJavaScript(Self.extractionScript) { result, _ in
            guard !self.finished else { return }
            if let raw = result as? String,
               let data = raw.data(using: .utf8),
               let value = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let media = value["media"] as? [[String: Any]], !media.isEmpty {
                do {
                    self.finish(note: try self.parse(value), error: nil)
                } catch {
                    self.finish(note: nil, error: error)
                }
                return
            }
            self.attempt += 1
            if self.attempt >= 40 {
                self.finish(note: nil, error: AppFailure.mediaMissing)
            } else {
                DispatchQueue.main.asyncAfter(deadline: .now() + 1) { self.poll() }
            }
        }
    }

    private func parse(_ payload: [String: Any]) throws -> NoteData {
        guard let sourceURL = sourceURL else { throw AppFailure.invalidURL }
        let title = string(payload["title"])
        let finalURL = string(payload["final_url"])
        let noteID = firstMatch(#"/(?:note|video)/(\d+)"#, in: finalURL)
        let mediaValues = payload["media"] as? [[String: Any]] ?? []
        let media: [MediaItem] = mediaValues.compactMap { value in
            let raw = string(value["url"])
            guard let url = URL(string: raw), !raw.isEmpty else { return nil }
            return MediaItem(url: url, fileExtension: string(value["extension"], fallback: "webp"))
        }
        guard !media.isEmpty else { throw AppFailure.mediaMissing }
        return NoteData(
            sourceURL: sourceURL,
            noteID: noteID,
            title: title,
            body: title,
            author: string(payload["author"]),
            comments: string(payload["comments"], fallback: "未知"),
            likes: string(payload["likes"], fallback: "未知"),
            topics: topicNames(in: title),
            media: media
        )
    }

    private func topicNames(in text: String) -> [String] {
        guard let expression = try? NSRegularExpression(pattern: #"#([^\s#]+)"#) else { return [] }
        let range = NSRange(text.startIndex..., in: text)
        var seen = Set<String>()
        return expression.matches(in: text, range: range).compactMap { match in
            guard let valueRange = Range(match.range(at: 1), in: text) else { return nil }
            let value = String(text[valueRange])
            return seen.insert(value).inserted ? value : nil
        }
    }

    private func firstMatch(_ pattern: String, in text: String) -> String {
        guard let expression = try? NSRegularExpression(pattern: pattern),
              let match = expression.firstMatch(in: text, range: NSRange(text.startIndex..., in: text)),
              let range = Range(match.range(at: 1), in: text) else { return "" }
        return String(text[range])
    }

    private func string(_ value: Any?, fallback: String = "") -> String {
        guard let value = value, !(value is NSNull) else { return fallback }
        let output = value as? String ?? String(describing: value)
        return output.isEmpty ? fallback : output
    }

    private func finish(note: NoteData?, error: Error?) {
        guard !finished else { return }
        finished = true
        webView?.stopLoading()
        webView?.removeFromSuperview()
        webView = nil
        let callback = completion
        completion = nil
        callback?(note, error)
    }

    private static let extractionScript = """
    (function(){
      var main=document.querySelector('main')||document.body;
      var current=location.href, isNote=/\\/note\\//.test(current);
      var text=main.innerText||'', meta=(document.querySelector('meta[name="description"]')||{}).content||'';
      var title=(document.title||'').replace(/\\s*-\\s*抖音\\s*$/,'').trim(), author='';
      document.querySelectorAll('script[type="application/ld+json"]').forEach(function(n){
        try {
          var v=JSON.parse(n.textContent||'{}');
          var a=(v.itemListElement||[]).filter(function(x){return Number(x.position)===2})[0];
          if(!author&&a&&a.name) author=String(a.name);
        } catch(e) {}
      });
      if(!author&&meta.indexOf(' - ')>=0){
        var m=meta.split(' - ').slice(1).join(' - ').match(/^(.*?)于\\d{8}发布/);
        author=m?m[1]:'';
      }
      if(author&&meta.indexOf(' - '+author+'于')>=0) title=meta.split(' - '+author+'于',1)[0].trim()||title;
      function read(s){var n=main.querySelector(s);return n?(n.innerText||n.textContent||'').trim():''}
      var media=[], seen={};
      if(isNote){
        main.querySelectorAll('img').forEach(function(n){
          var u=n.currentSrc||n.src||'';
          if(u.indexOf('aweme-images')<0||seen[u]) return;
          seen[u]=1;
          media.push({url:u,extension:u.indexOf('.png')>=0?'png':((u.indexOf('.jpeg')>=0||u.indexOf('.jpg')>=0)?'jpg':'webp')});
        });
      } else {
        main.querySelectorAll('video,video source').forEach(function(n){
          var u=n.currentSrc||n.src||'';
          if(!/^https?:/.test(u)||seen[u]) return;
          seen[u]=1; media.push({url:u,extension:'mp4'});
        });
      }
      return JSON.stringify({
        final_url:current,title:title,author:author,
        likes:read('[data-e2e="video-player-digg"]')||'未知',
        comments:read('[data-e2e="feed-comment-icon"]')||(text.match(/评论\\(([^)]+)\\)/)||[])[1]||'未知',
        media:media
      });
    })()
    """
}
