import AppKit

@main
struct ControllerMain {
    static func main() {
        let app = NSApplication.shared
        app.setActivationPolicy(.regular)
        let delegate = AppDelegate(); app.delegate = delegate
        let menu = NSMenu(); let item = NSMenuItem(); let applicationMenu = NSMenu()
        applicationMenu.addItem(withTitle: "PLaMo Localを終了", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        item.submenu = applicationMenu; menu.addItem(item); app.mainMenu = menu
        withExtendedLifetime(delegate) { app.run() }
    }
}
