import Foundation

enum SupportedPlatform {
    case xiaohongshu
    case douyin
}

enum PlatformRouter {
    static func platform(for url: URL) -> SupportedPlatform? {
        let host = url.host?.lowercased() ?? ""
        if host == "douyin.com" || host.hasSuffix(".douyin.com") {
            return .douyin
        }
        if host == "xiaohongshu.com" || host.hasSuffix(".xiaohongshu.com")
            || host == "xhslink.com" || host.hasSuffix(".xhslink.com") {
            return .xiaohongshu
        }
        return nil
    }
}
