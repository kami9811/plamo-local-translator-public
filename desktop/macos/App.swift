import AppKit

final class FlippedStack: NSStackView { override var isFlipped: Bool { true } }

final class ControllerWindow: NSWindowController, NSWindowDelegate, NSTextFieldDelegate {
    let backend: ControllerBackend
    let store: SettingsStore
    var settings: ControllerSettings
    var busy = false
    var visibleKey: String?
    let pathField = NSTextField(string: "")
    let message = NSTextField(wrappingLabelWithString: "実行先を指定して、操作を選んでください。")
    let status = NSTextField(labelWithString: "未確認")
    let keyField = NSTextField(string: "表示していません")
    let startButton = NSButton(title: "起動", target: nil, action: nil)
    let stopButton = NSButton(title: "停止", target: nil, action: nil)
    let keyButton = NSButton(title: "接続キーを表示", target: nil, action: nil)
    let copyButton = NSButton(title: "コピー", target: nil, action: nil)
    let saveButton = NSButton(title: "設定を保存", target: nil, action: nil)
    let browseButton = NSButton(title: "選択…", target: nil, action: nil)
    let themeButton = NSButton(title: "表示：システム", target: nil, action: nil)
    let root = FlippedStack()
    let configurationBody = NSStackView()
    let configurationButton = NSButton(title: "実行先の設定 ▾", target: nil, action: nil)
    var lastState = "unknown"

    init(backend: ControllerBackend, store: SettingsStore) {
        self.backend = backend; self.store = store; self.settings = store.load()
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 620, height: 790),
                              styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
        super.init(window: window)
        window.title = "PLaMo Local コントローラー"; window.minSize = NSSize(width: 560, height: 650)
        window.center(); window.delegate = self; window.isReleasedWhenClosed = false
        root.orientation = .vertical; root.alignment = .leading; root.spacing = 16
        root.edgeInsets = NSEdgeInsets(top: 24, left: 24, bottom: 24, right: 24)
        root.translatesAutoresizingMaskIntoConstraints = false
        let scroll = NSScrollView(); scroll.hasVerticalScroller = true; scroll.autohidesScrollers = true
        scroll.drawsBackground = true; scroll.backgroundColor = .windowBackgroundColor
        window.contentView = scroll; scroll.documentView = root
        NSLayoutConstraint.activate([root.widthAnchor.constraint(equalTo: scroll.contentView.widthAnchor)])
        let brand = NSStackView(views: [label("PLaMo Local", size: 21, weight: .semibold), themeButton]); brand.distribution = .fill
        brand.setHuggingPriority(.defaultLow, for: .horizontal); add(brand)
        add(label("起動・停止と、拡張に登録する接続キーの確認。", size: 14, secondary: true))
        pathField.stringValue = settings.repository; pathField.placeholderString = "プロジェクトのフォルダーを選択してください"
        pathField.font = .systemFont(ofSize: 14); pathField.setAccessibilityLabel("プロジェクトのフォルダー"); pathField.delegate = self
        let config = configurationBody; config.orientation = .vertical; config.alignment = .leading; config.spacing = 12

        let pathRow = NSStackView(views: [pathField, browseButton]); pathRow.distribution = .fill; config.addArrangedSubview(pathRow)
        pathRow.widthAnchor.constraint(equalTo: config.widthAnchor).isActive = true
        pathField.setContentHuggingPriority(.defaultLow, for: .horizontal)
        config.addArrangedSubview(label("scripts/start.py があるフォルダーを指定します。", size: 12, secondary: true))
        config.addArrangedSubview(saveButton)
        let configuration = NSStackView(views: [configurationButton, config]); configuration.orientation = .vertical; configuration.alignment = .leading; configuration.spacing = 12; configuration.detachesHiddenViews = true
        config.widthAnchor.constraint(equalTo: configuration.widthAnchor).isActive = true
        configurationBody.isHidden = !settings.repository.isEmpty
        configurationButton.title = configurationBody.isHidden ? "実行先の設定 ▸" : "実行先の設定 ▾"
        add(card(configuration))
        configurationButton.target = self; configurationButton.action = #selector(toggleConfiguration)
        configurationButton.bezelStyle = .regularSquare; configurationButton.isBordered = false
        configurationButton.font = .systemFont(ofSize: 14, weight: .semibold); configurationButton.contentTintColor = .labelColor
        configurationButton.alignment = .left; configurationButton.focusRingType = .exterior
        configurationButton.widthAnchor.constraint(equalTo: configuration.widthAnchor).isActive = true
        configurationButton.heightAnchor.constraint(greaterThanOrEqualToConstant: 32).isActive = true
        configurationButton.setAccessibilityLabel("実行先の設定を開く・閉じる")
        let actions = NSStackView(); actions.orientation = .vertical; actions.alignment = .leading; actions.spacing = 14
        let heading = NSStackView(views: [label("起動と停止", size: 15, weight: .semibold), status]); heading.distribution = .equalSpacing
        actions.addArrangedSubview(heading); heading.widthAnchor.constraint(equalTo: actions.widthAnchor).isActive = true
        let actionRow = NSStackView(views: [startButton, stopButton]); actionRow.distribution = .fillEqually
        actions.addArrangedSubview(actionRow); actionRow.widthAnchor.constraint(equalTo: actions.widthAnchor).isActive = true
        message.font = .systemFont(ofSize: 13); message.textColor = .secondaryLabelColor
        actions.addArrangedSubview(message); message.widthAnchor.constraint(equalTo: actions.widthAnchor).isActive = true
        add(card(actions))
        let keys = NSStackView(); keys.orientation = .vertical; keys.alignment = .leading; keys.spacing = 12
        keys.addArrangedSubview(keyButton)
        keyField.isEditable = false; keyField.isSelectable = false; keyField.font = .monospacedSystemFont(ofSize: 13, weight: .regular)
        keyField.setAccessibilityLabel("接続キー")
        let keyRow = NSStackView(views: [keyField, copyButton]); keyRow.distribution = .fill; keyRow.alignment = .centerY; keys.addArrangedSubview(keyRow)
        keyRow.widthAnchor.constraint(equalTo: keys.widthAnchor).isActive = true; keyField.setContentHuggingPriority(.defaultLow, for: .horizontal)
        keys.addArrangedSubview(label("接続キーは、このMacのChrome拡張だけで使います。", size: 12, secondary: true)); add(card(keys))
        add(label("ウィンドウを閉じてもAPIは動作を続けます。終了するときは「停止」を押してください。", size: 12, secondary: true))
        add(label("Built with PLaMo · 非公式ツール", size: 11, secondary: true))
        for button in [startButton, stopButton, keyButton, copyButton, saveButton, browseButton, themeButton] {
            button.bezelStyle = .regularSquare; button.isBordered = false; button.wantsLayer = true; button.layer?.cornerRadius = 8; button.focusRingType = .exterior; button.font = .systemFont(ofSize: 14, weight: .medium)
            button.heightAnchor.constraint(greaterThanOrEqualToConstant: 44).isActive = true; button.target = self
            button.setAccessibilityLabel(button.title)
        }
        startButton.action = #selector(start); stopButton.action = #selector(stop); keyButton.action = #selector(showKey)
        copyButton.action = #selector(copyKey); saveButton.action = #selector(save); browseButton.action = #selector(browse); themeButton.action = #selector(cycleTheme)
        copyButton.isEnabled = false

        applyTheme()
        window.initialFirstResponder = settings.repository.isEmpty ? pathField : startButton
        // Deliberately no backend call on launch: all operations require a user action.
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) is not used") }

    func label(_ text: String, size: CGFloat, weight: NSFont.Weight = .regular, secondary: Bool = false) -> NSTextField {
        let value = NSTextField(wrappingLabelWithString: text); value.font = .systemFont(ofSize: size, weight: weight)
        value.textColor = secondary ? .secondaryLabelColor : .labelColor; return value
    }
    func add(_ view: NSView) {
        root.addArrangedSubview(view); view.widthAnchor.constraint(equalTo: root.widthAnchor, constant: -48).isActive = true
    }
    func card(_ stack: NSStackView) -> NSView {
        let container = NSView(); container.wantsLayer = true
        container.layer?.cornerRadius = 14; container.layer?.borderWidth = 1
        container.layer?.borderColor = NSColor.separatorColor.cgColor
        stack.translatesAutoresizingMaskIntoConstraints = false; container.addSubview(stack)
        NSLayoutConstraint.activate([stack.topAnchor.constraint(equalTo: container.topAnchor, constant: 18), stack.bottomAnchor.constraint(equalTo: container.bottomAnchor, constant: -18),
                                     stack.leadingAnchor.constraint(equalTo: container.leadingAnchor, constant: 18), stack.trailingAnchor.constraint(equalTo: container.trailingAnchor, constant: -18)])
        return container
    }
    func clearKey() { visibleKey = nil; keyField.stringValue = "表示していません"; keyField.isSelectable = false; copyButton.isEnabled = false }
    func controlTextDidChange(_ notification: Notification) { clearKey() }
    @objc func toggleConfiguration() {
        configurationBody.isHidden.toggle()
        configurationButton.title = configurationBody.isHidden ? "実行先の設定 ▸" : "実行先の設定 ▾"
    }
    @discardableResult func saveSettings() throws -> String {
        let path = try PythonBackend.normalizedRepository(pathField.stringValue)
        settings.repository = path; try store.save(settings); pathField.stringValue = path; clearKey(); return path
    }
    @objc func save() {
        do { try saveSettings(); configurationBody.isHidden = true; configurationButton.title = "実行先の設定 ▸"; updateMessage("設定を保存しました。", error: false) }
        catch { updateMessage(error.localizedDescription, error: true) }
    }
    @objc func browse() {
        let panel = NSOpenPanel(); panel.canChooseFiles = false; panel.canChooseDirectories = true; panel.allowsMultipleSelection = false
        panel.prompt = "このフォルダーを使用"; panel.message = "scripts/start.py があるプロジェクトフォルダーを選んでください。"
        if panel.runModal() == .OK, let url = panel.url { pathField.stringValue = url.path; clearKey() }
    }
    @objc func start() { perform("start") }
    @objc func stop() { perform("stop") }
    @objc func showKey() { perform("key") }
    @objc func copyKey() {
        guard let value = visibleKey else { return }
        NSPasteboard.general.clearContents(); NSPasteboard.general.setString(value, forType: .string)
        updateMessage("接続キーをコピーしました。", error: false)
    }
    func updateMessage(_ text: String, error: Bool) { message.stringValue = text; message.textColor = error ? .systemRed : .secondaryLabelColor }
    func setBusy(_ value: Bool) {
        busy = value
        for control in [startButton, stopButton, keyButton, saveButton, browseButton] { control.isEnabled = !value }
        pathField.isEnabled = !value; copyButton.isEnabled = !value && visibleKey != nil
    }
    func perform(_ action: String) {
        guard !busy else { return }
        do {
            let path = try saveSettings(); setBusy(true); updateMessage("処理しています…", error: false)
            backend.execute(action, repository: path) { [weak self] outcome in
                guard let self = self else { return }; defer { self.setBusy(false) }
                switch outcome {
                case .success(let result):
                    self.lastState = result.ok ? result.state : "unknown"
                    self.status.stringValue = result.ok ? (result.state == "running" ? "起動中" : "停止中") : "要確認"
                    self.updateMessage(result.message, error: !result.ok)
                    if result.ok, action == "key", let key = result.key { self.visibleKey = key; self.keyField.stringValue = key; self.keyField.isSelectable = true }
                case .failure(let error): self.lastState = "unknown"; self.status.stringValue = "要確認"; self.updateMessage(error.localizedDescription, error: true)
                }
            }
        } catch { updateMessage(error.localizedDescription, error: true) }
    }
    @objc func cycleTheme() {
        settings.theme = settings.theme == "system" ? "light" : settings.theme == "light" ? "dark" : "system"
        applyTheme(); try? store.save(settings)
    }
    func applyTheme() {
        window?.appearance = settings.theme == "dark" ? NSAppearance(named: .darkAqua) : settings.theme == "light" ? NSAppearance(named: .aqua) : nil
        let dark = settings.theme == "dark" || (settings.theme == "system" && NSApp.effectiveAppearance.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua)
        for button in [stopButton, keyButton, copyButton, saveButton, browseButton, themeButton] {
            button.layer?.backgroundColor = (dark ? NSColor(srgbRed: 0.16, green: 0.20, blue: 0.18, alpha: 1) : NSColor(srgbRed: 0.90, green: 0.94, blue: 0.91, alpha: 1)).cgColor
            button.contentTintColor = dark ? .white : NSColor(srgbRed: 0.12, green: 0.18, blue: 0.15, alpha: 1)
        }
        startButton.layer?.backgroundColor = (dark ? NSColor(srgbRed: 0.55, green: 0.86, blue: 0.70, alpha: 1) : NSColor(srgbRed: 0.078, green: 0.420, blue: 0.329, alpha: 1)).cgColor
        startButton.contentTintColor = dark ? NSColor(srgbRed: 0.07, green: 0.23, blue: 0.15, alpha: 1) : .white
        themeButton.title = "表示：" + (settings.theme == "dark" ? "ダーク" : settings.theme == "light" ? "ライト" : "システム")
    }
    func windowShouldClose(_ sender: NSWindow) -> Bool {
        if busy { updateMessage("処理が終わるまでお待ちください。", error: false); return false }
        return true
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    var controller: ControllerWindow?
    func applicationDidFinishLaunching(_ notification: Notification) {
        guard let bridge = Bundle.main.url(forResource: "controller_bridge", withExtension: "py") else {
            let alert = NSAlert(); alert.messageText = "実行データが見つかりません。アプリを展開し直してください。"; alert.runModal(); NSApp.terminate(nil); return
        }
        controller = ControllerWindow(backend: PythonBackend(bridge: bridge), store: SettingsStore())
        controller?.showWindow(nil); NSApp.activate(ignoringOtherApps: true)
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        if controller?.busy == true { controller?.updateMessage("処理が終わるまでお待ちください。", error: false); return .terminateCancel }
        return .terminateNow
    }
}
