using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows;
using System.Windows.Automation;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace PlamoLocalController
{
    internal sealed class MemoryStore : ISettingsStore
    {
        public Settings Value = new Settings { Repository = "/home/example/plamo-local-translator-public", Distribution = "Ubuntu", Theme = "light" };
        public Settings Load() { return Value; }
        public void Save(Settings settings) { Value = settings; }
    }
    internal sealed class FakeBackend : IBackend
    {
        public List<string> Actions = new List<string>();
        public bool Fail;
        public Task<ControlResult> ExecuteAsync(string action, Settings settings)
        {
            Actions.Add(action);
            if (Fail) return Task.FromResult(new ControlResult { ok = false, state = "unknown", message = "別の実行先がポートを使用しています。" });
            return Task.FromResult(new ControlResult { ok = true, state = action == "stop" ? "stopped" : "running", key = action == "key" ? new String('x', 32) : null, version = "test", message = "テスト用の状態表示です。" });
        }
    }
    internal static class ControllerTests
    {
        private static int passed;
        private static void Check(bool value, string description) { if (!value) throw new Exception(description); passed++; }
        private static void Render(ControllerWindow window, string path)
        {
            FrameworkElement root = (FrameworkElement)window.Content;
            root.Measure(new Size(640, 780)); root.Arrange(new Rect(0, 0, 640, 780)); root.UpdateLayout();
            RenderTargetBitmap bitmap = new RenderTargetBitmap(960, 1170, 144, 144, PixelFormats.Pbgra32); bitmap.Render(root);
            PngBitmapEncoder encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(bitmap));
            using (FileStream stream = File.Create(path)) encoder.Save(stream);
        }
        [STAThread]
        public static int Main(string[] args)
        {
            try
            {
                string output = args.Length > 0 ? args[0] : Path.GetTempPath(); Directory.CreateDirectory(output);
                Settings normalized = Settings.Normalize("", @"\\wsl.localhost\Ubuntu\home\example\論文 draft & notes", "dark");
                Check(normalized.Distribution == "Ubuntu" && normalized.Repository == "/home/example/論文 draft & notes", "UNC conversion");
                Check(Settings.Normalize("", @"\\wsl$\Ubuntu\home\example\repo", "light").Repository == "/home/example/repo", "legacy UNC conversion");
                bool rejected = false; try { Settings.Normalize("Ubuntu", "relative/path", "light"); } catch (ArgumentException) { rejected = true; } Check(rejected, "relative paths rejected");
                string config = Path.Combine(output, "test-settings.json"); SettingsStore disk = new SettingsStore(config); disk.Save(normalized); Check(disk.Load().Repository == normalized.Repository, "settings roundtrip");
                Check(!File.ReadAllText(config).Contains("key"), "no key in settings");
                Application app = new Application(); MemoryStore store = new MemoryStore(); FakeBackend backend = new FakeBackend(); ControllerWindow window = new ControllerWindow(backend, store);
                Check(backend.Actions.Count == 0, "opening window performs no backend action");
                Check(!window.CopyButton.IsEnabled && window.KeyBox.Text == "表示していません", "key hidden initially");
                Check(AutomationProperties.GetName(window.StartButton).Length > 0, "accessible start label");
                window.StartButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent)); Check(backend.Actions.SequenceEqual(new string[] { "start" }) && window.LastState == "running", "start button dispatch");
                window.KeyButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent)); Check(window.CopyButton.IsEnabled && window.KeyBox.Text.Length == 32, "explicit key display");
                window.StopButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent)); Check(window.LastState == "stopped" && !window.CopyButton.IsEnabled && window.KeyBox.Text == "表示していません", "stop and key clear");
                backend.Fail = true; window.StartButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent)); Check(window.StatusText.Text == "要確認" && !window.IsBusy, "failures visible and controls recover"); backend.Fail = false;
                window.RunActionAsync("start").GetAwaiter().GetResult(); Render(window, Path.Combine(output, "controller-light.png"));
                window.CycleTheme(); Check(window.CurrentTheme == "dark", "dark theme selection"); Render(window, Path.Combine(output, "controller-dark.png"));
                window.Configuration.IsExpanded = true; Render(window, Path.Combine(output, "controller-settings.png"));
                Check(File.ReadAllText(config).IndexOf(new String('x', 32), StringComparison.Ordinal) < 0, "displayed key never persisted");
                // Exercise the actual Windows->WSL argv/UTF-8 boundary with an echo only.
                Settings echo = Settings.Normalize("", "/tmp", "light");
                string[] values = { "日本語 with spaces", "quote\"and'", "a&b;$(echo NOT_EXECUTED)", "trailing\\", "" };
                string python = "import json,sys;print(json.dumps(sys.argv[1:],ensure_ascii=False))";
                ProcessResult result = WslBackend.RunAsync(WslBackend.Arguments(echo, python, values)).GetAwaiter().GetResult();
                string[] returned = new JavaScriptSerializer().Deserialize<string[]>(result.Output);
                Check(result.ExitCode == 0 && returned.SequenceEqual(values), "real WSL argument and UTF-8 roundtrip without shell");
                Settings production = Settings.Normalize("", args.Length > 1 ? args[1] : "/tmp", "light");
                if (args.Length > 1) {
                    ControlResult status = new WslBackend().ExecuteAsync("status", production).GetAwaiter().GetResult();
                    Check(status != null && status.key == null && !String.IsNullOrEmpty(status.message), "embedded production bridge status without starting API");
                }
                File.WriteAllText(Path.Combine(output, "windows-tests.json"), new JavaScriptSerializer().Serialize(new { passed = passed, real_api_started = false, real_models_started = false, native_wpf_render = true, actual_wsl_argv = true }), new UTF8Encoding(false));
                Console.WriteLine("Windows controller: " + passed + " checks passed. No real API/model was started."); return 0;
            }
            catch (Exception error) { Console.Error.WriteLine("Controller test failed: " + error.GetType().Name + ": " + error.Message); return 1; }
        }
    }
}
