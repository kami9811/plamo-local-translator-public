import Foundation

struct ControllerSettings: Codable {
    var repository: String = ""
    var theme: String = "system"
}

struct ControllerResult: Decodable {
    var ok: Bool
    var state: String
    var message: String
    var key: String?
    var version: String?
    var error: String?
}

enum ControllerError: LocalizedError {
    case message(String)
    var errorDescription: String? {
        switch self { case .message(let value): return value }
    }
}

protocol ControllerBackend {
    func execute(_ action: String, repository: String, completion: @escaping (Result<ControllerResult, Error>) -> Void)
}

final class SettingsStore {
    let url: URL
    init(url: URL? = nil) {
        self.url = url ?? FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("PLaMoLocalTranslator/controller.json")
    }
    func load() -> ControllerSettings {
        guard let data = try? Data(contentsOf: url), data.count < 32768,
              let value = try? JSONDecoder().decode(ControllerSettings.self, from: data) else { return ControllerSettings() }
        return value
    }
    func save(_ settings: ControllerSettings) throws {
        try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        try JSONEncoder().encode(settings).write(to: url, options: .atomic)
    }
}

final class PythonBackend: ControllerBackend {
    let bridge: URL
    init(bridge: URL) { self.bridge = bridge }

    static func normalizedRepository(_ input: String) throws -> String {
        var value = input.trimmingCharacters(in: .whitespacesAndNewlines)
        if value.hasPrefix("file://"), let url = URL(string: value), url.isFileURL { value = url.path }
        guard value.hasPrefix("/"), !value.contains("\0"), !value.contains("\n"), !value.contains("\r") else {
            throw ControllerError.message("scripts/start.py があるプロジェクトのフォルダーを選んでください。")
        }
        return value
    }

    static func projectRepository(_ input: String) throws -> String {
        let path = try normalizedRepository(input)
        let root = URL(fileURLWithPath: path)
        let required = ["scripts/start.py", "scripts/stop.py", "runtime-manifest.json", "server/plamo_local/service.py"]
        guard required.allSatisfy({ FileManager.default.fileExists(atPath: root.appendingPathComponent($0).path) }) else {
            throw ControllerError.message("初回セットアップしたプロジェクトを選んでください。scriptsとruntime-manifest.jsonが入る場所です。scripts自体やdist、アプリは選びません。")
        }
        return path
    }

    static func python() throws -> String {
        let candidates = ["/opt/homebrew/bin/python3", "/usr/local/bin/python3",
                          "/Library/Frameworks/Python.framework/Versions/Current/bin/python3"]
        for path in candidates where FileManager.default.isExecutableFile(atPath: path) {
            let task = Process(); task.executableURL = URL(fileURLWithPath: path)
            task.arguments = ["-c", "import sys;sys.exit(0 if sys.version_info >= (3,10) else 1)"]
            task.standardOutput = FileHandle.nullDevice; task.standardError = FileHandle.nullDevice
            try task.run(); task.waitUntilExit()
            if task.terminationStatus == 0 { return path }
        }
        throw ControllerError.message("Python 3.10以降を先にインストールしてください。Homebrewまたはpython.orgのPythonを使用します。")
    }

    func execute(_ action: String, repository: String, completion: @escaping (Result<ControllerResult, Error>) -> Void) {
        DispatchQueue.global(qos: .userInitiated).async {
            let result: Result<ControllerResult, Error>
            do {
                guard ["start", "stop", "key", "status"].contains(action) else { throw ControllerError.message("操作を確認できませんでした。") }
                let root = try Self.normalizedRepository(repository)
                let task = Process(); task.executableURL = URL(fileURLWithPath: try Self.python())
                task.currentDirectoryURL = URL(fileURLWithPath: root)
                task.arguments = [self.bridge.path, action, root] // Separate argv; no shell or string interpolation.
                var environment = ProcessInfo.processInfo.environment
                environment["PYTHONIOENCODING"] = "utf-8"
                environment["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
                task.environment = environment
                let output = Pipe(); task.standardOutput = output
                task.standardError = FileHandle.nullDevice; task.standardInput = FileHandle.nullDevice
                let ended = DispatchSemaphore(value: 0)
                task.terminationHandler = { _ in ended.signal() }
                try task.run()
                if ended.wait(timeout: .now() + 90) == .timedOut {
                    task.terminate()
                    throw ControllerError.message("応答がタイムアウトしました。少し待ってから再操作してください。")
                }
                let data = output.fileHandleForReading.readDataToEndOfFile()
                guard data.count <= 65536, var response = try? JSONDecoder().decode(ControllerResult.self, from: data),
                      !response.message.isEmpty, task.terminationStatus == 0 || !response.ok else {
                    throw ControllerError.message("実行結果を確認できません。実行先とPython環境を確認してください。")
                }
                if action != "key" { response.key = nil }
                result = .success(response)
            } catch { result = .failure(error) }
            DispatchQueue.main.async { completion(result) }
        }
    }
}
