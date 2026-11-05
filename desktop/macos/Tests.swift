import AppKit

final class FakeBackend: ControllerBackend {
    var actions: [String] = []
    var fail = false
    func execute(_ action: String, repository: String, completion: @escaping (Result<ControllerResult, Error>) -> Void) {
        actions.append(action)
        completion(.success(ControllerResult(ok: !fail, state: action == "stop" ? "stopped" : "running",
            message: fail ? "別の実行先がポートを使用しています。" : "テスト用の状態表示です。",
            key: action == "key" && !fail ? String(repeating: "x", count: 32) : nil, version: "fixture")))
    }
}

@main struct ControllerTests {
    static func main() throws {
        let app = NSApplication.shared; app.setActivationPolicy(.regular)
        let output = URL(fileURLWithPath: CommandLine.arguments[1]); try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
        let store = SettingsStore(url: output.appendingPathComponent("test-settings.json"))
        try store.save(ControllerSettings(repository: "/Users/example/plamo-local-translator", theme: "light"))
        let backend = FakeBackend(); let controller = ControllerWindow(backend: backend, store: store)
        var checks = 0
        func check(_ condition: Bool, _ message: String) { precondition(condition, message); checks += 1 }
        check(backend.actions.isEmpty, "opening app must not call API")
        check(!controller.copyButton.isEnabled && controller.visibleKey == nil, "key hidden")
        controller.startButton.performClick(nil); check(backend.actions == ["start"] && controller.lastState == "running", "start dispatch")
        controller.keyButton.performClick(nil); check(controller.visibleKey?.count == 32 && controller.copyButton.isEnabled, "explicit key")
        controller.stopButton.performClick(nil); check(controller.visibleKey == nil && controller.lastState == "stopped", "stop clears key")
        backend.fail = true; controller.startButton.performClick(nil); check(controller.status.stringValue == "要確認" && !controller.busy, "errors visible and controls restored")
        backend.fail = false; controller.startButton.performClick(nil)
        controller.showWindow(nil); app.activate(ignoringOtherApps: true)
        for theme in ["light", "dark"] {
            controller.settings.theme = theme; controller.applyTheme()
            controller.window?.contentView?.layoutSubtreeIfNeeded()
            RunLoop.current.run(until: Date().addingTimeInterval(0.2))
            guard let view = controller.window?.contentView, let bitmap = view.bitmapImageRepForCachingDisplay(in: view.bounds) else { fatalError("render failed") }
            view.cacheDisplay(in: view.bounds, to: bitmap)
            try bitmap.representation(using: .png, properties: [:])!.write(to: output.appendingPathComponent("controller-" + theme + ".png"))
            let header = controller.themeButton.convert(controller.themeButton.bounds, to: view)
            check(view.bounds.contains(header), "header and theme visible without clipping")
            let visible = controller.startButton.convert(controller.startButton.bounds, to: view)
            check(visible.width >= 44 && visible.height >= 44 && view.bounds.intersects(visible), "primary action visible")
        }
        let saved = try String(contentsOf: store.url)
        check(!saved.contains("key") && !saved.contains(String(repeating: "x", count: 32)), "keys never saved")
        var rejected = false; do { _ = try PythonBackend.normalizedRepository("relative/path") } catch { rejected = true }
        check(rejected, "relative path rejected")
        let result: [String: Any] = ["passed": checks, "native_appkit_render": true, "real_api_started": false, "real_models_started": false]
        try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys]).write(to: output.appendingPathComponent("macos-ui-tests.json"))
        print("macOS controller: \(checks) checks passed. No real API/model was started by UI tests.")
        controller.window?.orderOut(nil)
    }
}
