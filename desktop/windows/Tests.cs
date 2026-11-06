using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Runtime.InteropServices;
using System.Threading;
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
    internal sealed class FakeSetupServices : ISetupServices
    {
        public int Lists;
        public Task<string[]> ListDistributionsAsync() { Lists++; return Task.FromResult(new string[] { "Ubuntu", "Ubuntu-24.04" }); }
        public string SelectFolder(Window owner, string distribution, string repository) { return @"\\wsl.localhost\Ubuntu-24.04\home\example\plamo-local-translator-public"; }
    }
    internal static class ControllerTests
    {
        private delegate bool EnumWindowProc(IntPtr handle, IntPtr parameter);
        [DllImport("user32.dll")] private static extern bool EnumThreadWindows(uint thread, EnumWindowProc callback, IntPtr value);
        [DllImport("kernel32.dll")] private static extern uint GetCurrentThreadId();
        [DllImport("user32.dll", CharSet = CharSet.Unicode)] private static extern int GetClassName(IntPtr handle, StringBuilder name, int length);
        [DllImport("user32.dll")] private static extern bool PostMessage(IntPtr handle, uint message, IntPtr wparam, IntPtr lparam);
        private static int passed;
        private static void Check(bool value, string description) { if (!value) throw new Exception(description); passed++; }
        private static void Render(ControllerWindow window, string path)
        {
            FrameworkElement root = (FrameworkElement)window.Content;
            int height = window.Configuration.IsExpanded ? 1320 : 840;
            root.Measure(new Size(680, height)); root.Arrange(new Rect(0, 0, 680, height)); root.UpdateLayout();
            RenderTargetBitmap bitmap = new RenderTargetBitmap(1020, height * 3 / 2, 144, 144, PixelFormats.Pbgra32); bitmap.Render(root);
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
                Application app = new Application(); MemoryStore store = new MemoryStore(); FakeBackend backend = new FakeBackend(); FakeSetupServices setup = new FakeSetupServices(); ControllerWindow window = new ControllerWindow(backend, store, setup);
                Check(window.Icon != null && window.Icon.Width >= 128, "original app icon loaded");
                Check(setup.Lists == 0, "opening does not query WSL");
                Check(WslSetupServices.ParseDistributions("\uFEFFUbuntu\r\nUbuntu-24.04\nUbuntu\n").SequenceEqual(new string[] { "Ubuntu", "Ubuntu-24.04" }), "WSL names parsed without duplicates");
                Check(WslBackend.DecodeOutput(Encoding.Unicode.GetBytes("Ubuntu\r\n"), true) == "Ubuntu\r\n", "WSL UTF-16 output decoded");
                Check(WslBackend.DecodeOutput(Encoding.UTF8.GetBytes("Ubuntu\n"), true) == "Ubuntu\n", "WSL UTF-8 output decoded");
                Check(WslSetupServices.InitialFolder("Ubuntu", "/home/example/repo") == @"\\wsl.localhost\Ubuntu\home\example\repo", "native picker starts at WSL location");
                window.LoadDistributionsAsync().GetAwaiter().GetResult();
                Check(setup.Lists == 1 && window.DistributionMenu.Items.Count == 3, "WSL list populated on explicit action");
                ((MenuItem)window.DistributionMenu.Items[2]).RaiseEvent(new RoutedEventArgs(MenuItem.ClickEvent));
                Check(window.DistributionBox.Text == "Ubuntu-24.04", "WSL menu selection fills name");
                window.BrowseButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
                Check(window.RepositoryBox.Text == "/home/example/plamo-local-translator-public" && window.DistributionBox.Text == "Ubuntu-24.04", "folder picker fills Linux path and distribution");
                window.SaveButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
                Check(backend.Actions.SequenceEqual(new string[] { "status" }) && !window.Configuration.IsExpanded, "confirm/save validates without start or key"); backend.Actions.Clear();
                Check(window.ChromeGuide.Header.ToString().Contains("Chrome") && window.HelpButton.Content.ToString().Contains("手順"), "in-app Chrome guide entry visible");
                Check(backend.Actions.Count == 0, "opening window performs no backend action");
                Check(!window.CopyButton.IsEnabled && window.KeyBox.Text == "表示していません", "key hidden initially");
                Check(AutomationProperties.GetName(window.StartButton).Length > 0, "accessible start label");
                window.StartButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent)); Check(backend.Actions.SequenceEqual(new string[] { "start" }) && window.LastState == "running", "start button dispatch");
                window.KeyButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent)); Check(window.CopyButton.IsEnabled && window.KeyBox.Text.Length == 32, "explicit key display");
                window.StopButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent)); Check(window.LastState == "stopped" && !window.CopyButton.IsEnabled && window.KeyBox.Text == "表示していません", "stop and key clear");
                backend.Fail = true; window.StartButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent)); Check(window.StatusText.Text == "要確認" && !window.IsBusy, "failures visible and controls recover"); backend.Fail = false;
                window.RunActionAsync("start").GetAwaiter().GetResult(); Render(window, Path.Combine(output, "controller-light.png"));
                window.CycleTheme(); Check(window.CurrentTheme == "dark", "dark theme selection"); Render(window, Path.Combine(output, "controller-dark.png"));
                window.Configuration.IsExpanded = true; window.ChromeGuide.IsExpanded = true; Render(window, Path.Combine(output, "controller-settings-dark.png"));
                window.CycleTheme(); window.CycleTheme(); Render(window, Path.Combine(output, "controller-settings.png"));
                Check(File.ReadAllText(config).IndexOf(new String('x', 32), StringComparison.Ordinal) < 0, "displayed key never persisted");
                backend.Fail = true; store.Value.Repository = "/home/example/previous"; window.RepositoryBox.Text = "/home/example/incorrect"; window.SaveButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
                Check(store.Value.Repository == "/home/example/previous" && window.Configuration.IsExpanded, "invalid configuration is not saved and stays open"); backend.Fail = false;
                // Open the real OS folder chooser, then cancel only this test thread's dialog.
                uint pickerThread = GetCurrentThreadId(); int pickerSeen = 0;
                Task cancelPicker = Task.Run(delegate {
                    for (int attempt = 0; attempt < 100 && Volatile.Read(ref pickerSeen) == 0; attempt++) {
                        Thread.Sleep(100);
                        EnumThreadWindows(pickerThread, delegate(IntPtr handle, IntPtr unused) {
                            StringBuilder name = new StringBuilder(128); GetClassName(handle, name, name.Capacity);
                            if (name.ToString() == "#32770") { Interlocked.Exchange(ref pickerSeen, 1); PostMessage(handle, 0x0010, IntPtr.Zero, IntPtr.Zero); }
                            return true;
                        }, IntPtr.Zero);
                    }
                });
                string selectedFolder = ProjectFolderPicker.Select(window, Path.GetTempPath()); cancelPicker.GetAwaiter().GetResult();
                Check(pickerSeen == 1 && selectedFolder == null, "real native Windows folder chooser opens and cancels safely");
                // Exercise the actual Windows->WSL argv/UTF-8 boundary with an echo only.
                Settings echo = Settings.Normalize("", "/tmp", "light");
                string[] values = { "日本語 with spaces", "quote\"and'", "a&b;$(echo NOT_EXECUTED)", "trailing\\", "" };
                string python = "import json,sys;print(json.dumps(sys.argv[1:],ensure_ascii=False))";
                ProcessResult result = WslBackend.RunAsync(WslBackend.Arguments(echo, python, values)).GetAwaiter().GetResult();
                string[] returned = new JavaScriptSerializer().Deserialize<string[]>(result.Output);
                Check(result.ExitCode == 0 && returned.SequenceEqual(values), "real WSL argument and UTF-8 roundtrip without shell");
                string[] installed = new WslSetupServices().ListDistributionsAsync().GetAwaiter().GetResult();
                Check(installed.Length > 0 && installed.All(name => name.IndexOf('\0') < 0), "actual installed WSL names decoded");
                Settings production = Settings.Normalize("", args.Length > 1 ? args[1] : "/tmp", "light");
                if (args.Length > 1) {
                    ControlResult status = new WslBackend().ExecuteAsync("status", production).GetAwaiter().GetResult();
                    Check(status != null && status.key == null && !String.IsNullOrEmpty(status.message), "embedded production bridge status without starting API");
                }
                File.WriteAllText(Path.Combine(output, "windows-tests.json"), new JavaScriptSerializer().Serialize(new { passed = passed, real_api_started = false, real_models_started = false, native_wpf_render = true, actual_wsl_argv = true, icon_verified = true, setup_guide_verified = true }), new UTF8Encoding(false));
                Console.WriteLine("Windows controller: " + passed + " checks passed. No real API/model was started."); return 0;
            }
            catch (Exception error) { Console.Error.WriteLine("Controller test failed: " + error.GetType().Name + ": " + error.Message); return 1; }
        }
    }
}
