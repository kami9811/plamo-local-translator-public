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
    let browseButton = NSButton(title: "フォルダーを選択…", target: nil, action: nil)
    let themeButton = NSButton(title: "表示：システム", target: nil, action: nil)
    let root = FlippedStack()
    let configurationBody = NSStackView()
    let configurationButton = NSButton(title: "実行先の設定 ▾", target: nil, action: nil)
    let chromeGuideButton = NSButton(title: "3. Chromeで使うまで ▾", target: nil, action: nil)
    let chromeGuideBody = NSStackView()
    let helpButton = NSButton(title: "拡張の追加から手順を見る", target: nil, action: nil)
    let brandIcon = NSImageView()
    var lastState = "unknown"

    init(backend: ControllerBackend, store: SettingsStore, icon: NSImage? = Bundle.main.url(forResource: "controller-128", withExtension: "png").flatMap { NSImage(contentsOf: $0) }) {
        self.backend = backend; self.store = store; self.settings = store.load()
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 620, height: 840),
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
        brandIcon.image = icon; brandIcon.imageScaling = .scaleProportionallyUpOrDown; brandIcon.setAccessibilityElement(false)
        NSLayoutConstraint.activate([brandIcon.widthAnchor.constraint(equalToConstant: 38), brandIcon.heightAnchor.constraint(equalToConstant: 38)])
        let brand = NSStackView(views: [brandIcon, label("PLaMo Local", size: 21, weight: .semibold), themeButton]); brand.distribution = .fill
        brand.setHuggingPriority(.defaultLow, for: .horizontal); add(brand)
        add(label("起動・停止と、拡張に登録する接続キーの確認。", size: 14, secondary: true))
        pathField.stringValue = settings.repository; pathField.placeholderString = "プロジェクトのフォルダーを選択してください"
        pathField.font = .systemFont(ofSize: 14); pathField.setAccessibilityLabel("プロジェクトのフォルダー"); pathField.delegate = self
        let config = configurationBody; config.orientation = .vertical; config.alignment = .leading; config.spacing = 12

        config.addArrangedSubview(label("1. 翻訳プロジェクトのフォルダー", size: 13, weight: .semibold))
        let pathRow = NSStackView(views: [pathField, browseButton]); pathRow.distribution = .fill; config.addArrangedSubview(pathRow)
        pathRow.widthAnchor.constraint(equalTo: config.widthAnchor).isActive = true
        pathField.setContentHuggingPriority(.defaultLow, for: .horizontal)
        config.addArrangedSubview(label("Finderで、初回セットアップしたplamo-local-translator-publicを選びます。scriptsフォルダーとruntime-manifest.jsonが入る場所です。", size: 12, secondary: true))
        config.addArrangedSubview(label("アプリの.app、ダウンロードしたZIP、拡張のdistフォルダーは選びません。保存先が分からない場合は、セットアップしたターミナルでpwdを実行し、表示されたパスを貼り付けます。", size: 12, secondary: true))
        saveButton.title = "確認して保存"
        config.addArrangedSubview(label("保存時は場所とPythonを確認します。翻訳API・モデルは起動しません。", size: 12, secondary: true))
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
        let heading = NSStackView(views: [label("2. 起動と停止", size: 15, weight: .semibold), status]); heading.distribution = .equalSpacing
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
        chromeGuideBody.orientation = .vertical; chromeGuideBody.alignment = .leading; chromeGuideBody.spacing = 10
        for text in ["初回と接続キーが変わったときだけ登録します。", "① このアプリで「起動」→「接続キーを表示」→「コピー」。", "② Chrome右上のパズル → PLaMo Local →「原稿・用語集・接続設定」を開き、左の「接続と設定」を選びます。", "③「接続キー」欄へ貼り付けて「接続する」。上部に「接続済み · PC内で処理」が出れば利用できます。", "通常のWebページで英文を選択 → 右クリック →「PLaMoで選択文を翻訳」。最初の翻訳ではモデルの準備を待ちます。"] {
            let step = label(text, size: 13, secondary: true); chromeGuideBody.addArrangedSubview(step); step.widthAnchor.constraint(equalTo: chromeGuideBody.widthAnchor).isActive = true
        }
        chromeGuideBody.addArrangedSubview(helpButton)
        let guide = NSStackView(views: [chromeGuideButton, chromeGuideBody]); guide.orientation = .vertical; guide.alignment = .leading; guide.spacing = 12; guide.detachesHiddenViews = true
        chromeGuideBody.widthAnchor.constraint(equalTo: guide.widthAnchor).isActive = true; chromeGuideBody.isHidden = !settings.repository.isEmpty
        chromeGuideButton.title = chromeGuideBody.isHidden ? "3. Chromeで使うまで ▸" : "3. Chromeで使うまで ▾"
        chromeGuideButton.target = self; chromeGuideButton.action = #selector(toggleChromeGuide); chromeGuideButton.bezelStyle = .regularSquare; chromeGuideButton.isBordered = false
        chromeGuideButton.font = .systemFont(ofSize: 14, weight: .semibold); chromeGuideButton.contentTintColor = .labelColor; chromeGuideButton.focusRingType = .exterior
        chromeGuideButton.setAccessibilityLabel("Chromeへの登録と利用開始の手順を開く・閉じる"); chromeGuideButton.heightAnchor.constraint(greaterThanOrEqualToConstant: 36).isActive = true
        add(card(guide))
        add(label("ウィンドウを閉じてもAPIは動作を続けます。終了するときは「停止」を押してください。", size: 12, secondary: true))
        add(label("Built with PLaMo · 非公式ツール", size: 11, secondary: true))
        for button in [startButton, stopButton, keyButton, copyButton, saveButton, browseButton, themeButton, helpButton] {
            button.bezelStyle = .regularSquare; button.isBordered = false; button.wantsLayer = true; button.layer?.cornerRadius = 8; button.focusRingType = .exterior; button.font = .systemFont(ofSize: 14, weight: .medium)
            button.heightAnchor.constraint(greaterThanOrEqualToConstant: 44).isActive = true; button.target = self
            button.setAccessibilityLabel(button.title)
        }
        startButton.action = #selector(start); stopButton.action = #selector(stop); keyButton.action = #selector(showKey)
        copyButton.action = #selector(copyKey); saveButton.action = #selector(save); browseButton.action = #selector(browse); themeButton.action = #selector(cycleTheme); helpButton.action = #selector(openHelp)
        copyButton.isEnabled = false

        applyTheme()
        window.initialFirstResponder = settings.repository.isEmpty ? browseButton : startButton
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
    @objc func toggleChromeGuide() {
        chromeGuideBody.isHidden.toggle()
        chromeGuideButton.title = chromeGuideBody.isHidden ? "3. Chromeで使うまで ▸" : "3. Chromeで使うまで ▾"
    }
    @objc func openHelp() {
        NSWorkspace.shared.open(URL(string: "https://github.com/kami9811/plamo-local-translator-public/blob/controller-v0.1.1/docs/DESKTOP.md#chrome-extension")!)
    }
    @objc func save() { perform("status") }
    func acceptFolder(_ path: String) throws {
        let selected = try PythonBackend.projectRepository(path)
        pathField.stringValue = selected; clearKey()
        updateMessage("フォルダーを選択しました。「確認して保存」を押してください。", error: false)
    }
    @objc func browse() {
        let panel = NSOpenPanel(); panel.canChooseFiles = false; panel.canChooseDirectories = true; panel.allowsMultipleSelection = false
        panel.prompt = "このフォルダーを使用"; panel.message = "初回セットアップした翻訳プロジェクトを選んでください。scriptsとruntime-manifest.jsonが入る場所です。appやdistは選びません。"
        if !pathField.stringValue.isEmpty { panel.directoryURL = URL(fileURLWithPath: pathField.stringValue) }
        if panel.runModal() == .OK, let url = panel.url {
            do { try acceptFolder(url.path) } catch { updateMessage(error.localizedDescription, error: true) }
        }
    }
    @objc func start() { perform("start") }
    @objc func stop() { perform("stop") }
    @objc func showKey() { perform("key") }
    @objc func copyKey() {
        guard let value = visibleKey else { return }
        NSPasteboard.general.clearContents(); NSPasteboard.general.setString(value, forType: .string)
        chromeGuideBody.isHidden = false; chromeGuideButton.title = "3. Chromeで使うまで ▾"
        updateMessage("コピーしました。Chrome拡張の「接続と設定」へ貼り付けて「接続する」を押してください。", error: false)
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
            let path = try PythonBackend.normalizedRepository(pathField.stringValue); clearKey(); setBusy(true); updateMessage("処理しています…", error: false)
            backend.execute(action, repository: path) { [weak self] outcome in
                guard let self = self else { return }; defer { self.setBusy(false) }
                switch outcome {
                case .success(let result):
                    self.lastState = result.ok ? result.state : "unknown"
                    self.status.stringValue = result.ok ? (result.state == "running" ? "起動中" : "停止中") : "要確認"
                    if result.ok {
                        var next = self.settings; next.repository = path
                        do { try self.store.save(next); self.settings = next; self.pathField.stringValue = path }
                        catch { self.updateMessage("操作は完了しましたが、設定を保存できませんでした。", error: true); return }
                        if action == "status" { self.configurationBody.isHidden = true; self.configurationButton.title = "実行先の設定 ▸" }
                    } else if action == "status" { self.configurationBody.isHidden = false; self.configurationButton.title = "実行先の設定 ▾" }
                    self.updateMessage(action == "status" && result.ok ? "実行先を確認して保存しました。次は「起動」を押してください。" : result.message, error: !result.ok)
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
        for button in [stopButton, keyButton, copyButton, saveButton, browseButton, themeButton, helpButton] {
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
