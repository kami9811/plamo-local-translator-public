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
        if CommandLine.arguments.count > 3 && CommandLine.arguments[2] == "--backend" {
            try verifyRealBackend(output: URL(fileURLWithPath: CommandLine.arguments[1]), repository: CommandLine.arguments[3]); return
        }
        let output = URL(fileURLWithPath: CommandLine.arguments[1]); try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
        let store = SettingsStore(url: output.appendingPathComponent("test-settings.json"))
        try store.save(ControllerSettings(repository: "/Users/example/plamo-local-translator", theme: "light"))
        let backend = FakeBackend(); let controller = ControllerWindow(backend: backend, store: store, icon: NSImage(contentsOfFile: "desktop/assets/controller-128.png"))
        var checks = 0
        func check(_ condition: Bool, _ message: String) { precondition(condition, message); checks += 1 }
        check(controller.brandIcon.image != nil, "original header icon loads")
        let validProject = output.appendingPathComponent("example-project")
        for name in ["scripts/start.py", "scripts/stop.py", "runtime-manifest.json", "server/plamo_local/service.py"] {
            let file = validProject.appendingPathComponent(name); try FileManager.default.createDirectory(at: file.deletingLastPathComponent(), withIntermediateDirectories: true); try Data().write(to: file)
        }
        try controller.acceptFolder(validProject.path)
        check(controller.pathField.stringValue == validProject.path, "valid project folder accepted")
        var wrongFolderRejected = false; do { try controller.acceptFolder(output.path) } catch { wrongFolderRejected = true }
        check(wrongFolderRejected && controller.pathField.stringValue == validProject.path, "wrong folder rejected without changing selection")
        controller.saveButton.performClick(nil)
        check(backend.actions == ["status"] && controller.configurationBody.isHidden, "confirm/save validates without starting API")
        backend.actions.removeAll()
        check(controller.chromeGuideButton.title.contains("Chrome"), "in-app Chrome guide exists")
        check(backend.actions.isEmpty, "opening app must not call API")
        check(!controller.copyButton.isEnabled && controller.visibleKey == nil, "key hidden")
        controller.startButton.performClick(nil); check(backend.actions == ["start"] && controller.lastState == "running", "start dispatch")
        controller.keyButton.performClick(nil); check(controller.visibleKey?.count == 32 && controller.copyButton.isEnabled, "explicit key")
        controller.copyButton.performClick(nil); check(NSPasteboard.general.string(forType: .string) == String(repeating: "x", count: 32), "explicit copy")
        NSPasteboard.general.clearContents()
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
        controller.configurationBody.isHidden = false; controller.chromeGuideBody.isHidden = false
        controller.settings.theme = "light"; controller.applyTheme(); controller.window?.setContentSize(NSSize(width: 620, height: 1300)); controller.window?.contentView?.layoutSubtreeIfNeeded()
        if let view = controller.window?.contentView, let bitmap = view.bitmapImageRepForCachingDisplay(in: view.bounds) {
            view.cacheDisplay(in: view.bounds, to: bitmap); try bitmap.representation(using: .png, properties: [:])!.write(to: output.appendingPathComponent("controller-settings.png"))
        }
        let saved = try String(contentsOf: store.url)
        check(!saved.contains("key") && !saved.contains(String(repeating: "x", count: 32)), "keys never saved")
        var rejected = false; do { _ = try PythonBackend.normalizedRepository("relative/path") } catch { rejected = true }
        check(rejected, "relative path rejected")
        let result: [String: Any] = ["passed": checks, "native_appkit_render": true, "real_api_started": false, "real_models_started": false, "setup_guide_verified": true, "icon_verified": true]
        try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys]).write(to: output.appendingPathComponent("macos-ui-tests.json"))
        print("macOS controller: \(checks) checks passed. No real API/model was started by UI tests.")
        controller.window?.orderOut(nil)
    }
    static func verifyRealBackend(output: URL, repository: String) throws {
        guard ProcessInfo.processInfo.environment["GITHUB_ACTIONS"] == "true" else { throw ControllerError.message("Isolated CI only") }
        try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
        let bridge = URL(fileURLWithPath: repository).appendingPathComponent("desktop/controller_bridge.py")
        let store = SettingsStore(url: output.appendingPathComponent("backend-settings.json"))
        try store.save(ControllerSettings(repository: repository, theme: "light"))
        let controller = ControllerWindow(backend: PythonBackend(bridge: bridge), store: store)
        func waitForAction(_ action: String) throws {
            controller.perform(action)
            let deadline = Date().addingTimeInterval(95)
            while controller.busy && Date() < deadline { RunLoop.current.run(until: Date().addingTimeInterval(0.02)) }
            if controller.busy || controller.lastState == "unknown" { throw ControllerError.message("Native backend action failed: " + action + ": " + controller.message.stringValue) }
        }
        try waitForAction("start")
        do {
            guard controller.lastState == "running" else { throw ControllerError.message("Native start failed") }
            try waitForAction("key")
            guard let key = controller.visibleKey, key.count >= 32, controller.copyButton.isEnabled else { throw ControllerError.message("Native key display failed") }
            let saved = try String(contentsOf: store.url)
            guard !saved.contains(key) else { throw ControllerError.message("Key was persisted") }
            try waitForAction("stop")
            guard controller.lastState == "stopped", controller.visibleKey == nil else { throw ControllerError.message("Native stop failed") }
        } catch { try? waitForAction("stop"); throw error }
        let report: [String: Any] = ["native_ui_to_python": true, "real_api_started": true, "real_models_started": false,
                                     "start_verified": true, "explicit_key_verified": true, "key_not_saved": true, "stop_verified": true]
        try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]).write(to: output.appendingPathComponent("macos-backend-tests.json"))
        print("Native AppKit → Python → actual API: start / explicit key / stop verified. Keys omitted.")
    }

}
