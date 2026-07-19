import SwiftUI

enum AppTheme: String, CaseIterable, Identifiable {
    case neo
    case glass

    var id: String { rawValue }
    var name: String { self == .neo ? "拟态悬浮" : "克制玻璃" }
    var background: LinearGradient {
        self == .neo
        ? LinearGradient(colors: [Color(red: 0.91, green: 0.93, blue: 0.95), Color(red: 0.84, green: 0.89, blue: 0.92)], startPoint: .topLeading, endPoint: .bottomTrailing)
        : LinearGradient(colors: [Color(red: 0.86, green: 0.92, blue: 0.96), Color(red: 0.75, green: 0.85, blue: 0.91)], startPoint: .topLeading, endPoint: .bottomTrailing)
    }
    var primary: Color { self == .neo ? Color(red: 0.13, green: 0.21, blue: 0.26) : Color(red: 0.18, green: 0.44, blue: 0.62) }
    var accent: Color { Color(red: 0.32, green: 0.48, blue: 0.58) }
    var text: Color { Color(red: 0.07, green: 0.16, blue: 0.22) }
    var muted: Color { Color(red: 0.38, green: 0.48, blue: 0.55) }
}

struct ContentSurface: ViewModifier {
    let theme: AppTheme

    func body(content: Content) -> some View {
        content
            .background(theme == .glass ? AnyShapeStyle(.regularMaterial) : AnyShapeStyle(Color.white.opacity(0.70)))
            .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 24, style: .continuous).stroke(Color.white.opacity(0.46), lineWidth: 1))
            .shadow(color: Color(red: 0.12, green: 0.22, blue: 0.29).opacity(0.12), radius: 16, y: 9)
    }
}

extension View {
    func contentSurface(_ theme: AppTheme) -> some View { modifier(ContentSurface(theme: theme)) }
}
