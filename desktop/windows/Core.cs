using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;
using System.Web.Script.Serialization;

namespace PlamoLocalController
{
    public sealed class Settings
    {
        public string Distribution { get; set; }
        public string Repository { get; set; }
        public string Theme { get; set; }
        public Settings() { Distribution = ""; Repository = ""; Theme = "system"; }

        public static Settings Normalize(string distribution, string repository, string theme)
        {
            string distro = (distribution ?? "").Trim();
            string repo = (repository ?? "").Trim();
            if (repo.StartsWith("\\\\wsl.localhost\\", StringComparison.OrdinalIgnoreCase) ||
                repo.StartsWith("\\\\wsl$\\", StringComparison.OrdinalIgnoreCase))
            {
                string[] pieces = repo.Split(new char[] { '\\' }, StringSplitOptions.RemoveEmptyEntries);
                if (pieces.Length < 3) throw new ArgumentException("WSLのプロジェクトフォルダーを指定してください。");
                distro = pieces[1];
                repo = "/" + String.Join("/", pieces, 2, pieces.Length - 2);
            }
            if (!repo.StartsWith("/", StringComparison.Ordinal) || repo.IndexOfAny(new char[] { '\0', '\r', '\n' }) >= 0)
                throw new ArgumentException("「フォルダーを選択」でWSL内の翻訳プロジェクトを選んでください。Linuxの絶対パスやWSL共有パスの貼り付けも使えます。");
            if (distro.StartsWith("-", StringComparison.Ordinal) || distro.IndexOfAny(new char[] { '\0', '\r', '\n', '/', '\\' }) >= 0)
                throw new ArgumentException("WSLディストリビューション名を確認してください。");
            return new Settings { Distribution = distro, Repository = repo, Theme = theme == "dark" || theme == "light" ? theme : "system" };
        }
    }

    public interface ISettingsStore
    {
        Settings Load();
        void Save(Settings settings);
    }

    public sealed class SettingsStore : ISettingsStore
    {
        public readonly string FilePath;
        public SettingsStore(string path) { FilePath = path; }
        public Settings Load()
        {
            try
            {
                string json = File.ReadAllText(FilePath, Encoding.UTF8);
                if (json.Length > 32768) return new Settings();
                return new JavaScriptSerializer().Deserialize<Settings>(json) ?? new Settings();
            }
            catch (IOException) { return new Settings(); }
            catch (UnauthorizedAccessException) { return new Settings(); }
            catch (ArgumentException) { return new Settings(); }
            catch (InvalidOperationException) { return new Settings(); }
        }
        public void Save(Settings settings)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(FilePath));
            string temp = FilePath + "." + Guid.NewGuid().ToString("N") + ".tmp";
            try
            {
                File.WriteAllText(temp, new JavaScriptSerializer().Serialize(settings), new UTF8Encoding(false));
                if (File.Exists(FilePath)) File.Replace(temp, FilePath, null);
                else File.Move(temp, FilePath);
            }
            finally { if (File.Exists(temp)) File.Delete(temp); }
        }
    }

    public sealed class ControlResult
    {
        public bool ok { get; set; }
        public string state { get; set; }
        public string message { get; set; }
        public string key { get; set; }
        public string version { get; set; }
        public string error { get; set; }
    }

    public interface IBackend
    {
        Task<ControlResult> ExecuteAsync(string action, Settings settings);
    }

    public sealed class ProcessResult
    {
        public int ExitCode;
        public string Output;
    }

    public static class WindowsArguments
    {
        public static string Quote(string value)
        {
            if (value.Length > 0 && value.IndexOfAny(new char[] { ' ', '\t', '\r', '\n', '"' }) < 0) return value;
            StringBuilder result = new StringBuilder("\"");
            int slashes = 0;
            foreach (char character in value)
            {
                if (character == '\\') { slashes++; continue; }
                if (character == '"')
                {
                    result.Append('\\', slashes * 2 + 1); result.Append('"'); slashes = 0;
                }
                else { result.Append('\\', slashes); slashes = 0; result.Append(character); }
            }
            result.Append('\\', slashes * 2); result.Append('"'); return result.ToString();
        }
        public static string Join(IEnumerable<string> values)
        {
            List<string> quoted = new List<string>();
            foreach (string value in values) quoted.Add(Quote(value));
            return String.Join(" ", quoted.ToArray());
        }
    }

    public sealed class WslBackend : IBackend
    {
        public static string WslExecutable
        {
            get { return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System), "wsl.exe"); }
        }
        public static List<string> Arguments(Settings settings, string code, params string[] extra)
        {
            List<string> args = new List<string>();
            if (!String.IsNullOrWhiteSpace(settings.Distribution))
            {
                args.Add("--distribution"); args.Add(settings.Distribution);
            }
            args.Add("--cd"); args.Add(settings.Repository);
            args.Add("--exec"); args.Add("env"); args.Add("PYTHONIOENCODING=utf-8");
            args.Add("python3"); args.Add("-c"); args.Add(code);
            args.AddRange(extra); return args;
        }

        private static async Task<byte[]> DrainAsync(Stream stream)
        {
            using (MemoryStream result = new MemoryStream())
            {
                byte[] buffer = new byte[8192]; int count;
                while ((count = await stream.ReadAsync(buffer, 0, buffer.Length).ConfigureAwait(false)) > 0)
                {
                    // Keep draining to avoid blocking the child, but cap retained output.
                    int keep = (int)Math.Min(count, Math.Max(0, 1048576 - result.Length));
                    if (keep > 0) result.Write(buffer, 0, keep);
                }
                return result.ToArray();
            }
        }

        public static async Task<ProcessResult> RunAsync(IList<string> args, bool detectUnicode = false)
        {
            if (!File.Exists(WslExecutable)) throw new InvalidOperationException("WSLが見つかりません。WSL2とUbuntuを先にセットアップしてください。");
            ProcessStartInfo start = new ProcessStartInfo(WslExecutable, WindowsArguments.Join(args));
            start.UseShellExecute = false; start.CreateNoWindow = true;
            start.RedirectStandardOutput = true; start.RedirectStandardError = true;
            using (Process process = new Process())
            {
                process.StartInfo = start; process.Start();
                Task<byte[]> stdout = DrainAsync(process.StandardOutput.BaseStream);
                Task<byte[]> stderr = DrainAsync(process.StandardError.BaseStream);
                bool exited = await Task.Run(delegate { return process.WaitForExit(90000); }).ConfigureAwait(false);
                if (!exited)
                {
                    try { process.Kill(); } catch (InvalidOperationException) { }
                    throw new InvalidOperationException("WSLからの応答がタイムアウトしました。WSLと実行先を確認し、少し待ってから再操作してください。");
                }
                byte[] output = await stdout.ConfigureAwait(false);
                await stderr.ConfigureAwait(false); // Never display raw stderr; it can contain private data.
                return new ProcessResult { ExitCode = process.ExitCode, Output = DecodeOutput(output, detectUnicode).Trim('\uFEFF', '\0', '\r', '\n', ' ') };
            }
        }

        public static string DecodeOutput(byte[] data, bool detectUnicode)
        {
            // wsl.exe list uses UTF-16LE on supported Windows builds; inference emits UTF-8.
            bool utf16 = detectUnicode && data.Length > 1 && ((data[0] == 0xFF && data[1] == 0xFE) || Array.IndexOf(data, (byte)0, 0, Math.Min(data.Length, 128)) >= 0);
            return (utf16 ? Encoding.Unicode : Encoding.UTF8).GetString(data);
        }

        public async Task<ControlResult> ExecuteAsync(string action, Settings settings)
        {
            if (action != "start" && action != "stop" && action != "key" && action != "status")
                throw new ArgumentException("操作を確認できませんでした。");
            string code;
            using (Stream stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("controller.bridge.py.gz"))
            {
                if (stream == null) throw new InvalidOperationException("実行用のデータが見つかりません。アプリを展開し直してください。");
                using (MemoryStream bytes = new MemoryStream())
                {
                    stream.CopyTo(bytes);
                    code = "import base64,gzip;exec(gzip.decompress(base64.b64decode('" + Convert.ToBase64String(bytes.ToArray()) + "')).decode('utf-8'))";
                }
            }
            ProcessResult process = await RunAsync(Arguments(settings, code, action, settings.Repository));
            ControlResult result;
            try { result = new JavaScriptSerializer().Deserialize<ControlResult>(process.Output); }
            catch (Exception) { throw new InvalidOperationException("WSLからの応答を確認できません。実行先のパスとPython 3を確認してください。"); }
            if (result == null || String.IsNullOrWhiteSpace(result.message) || (process.ExitCode != 0 && result.ok))
                throw new InvalidOperationException("WSLから正常な応答を受け取れませんでした。実行先とWSLを確認してください。");
            if (action != "key") result.key = null;
            return result;
        }
    }
}
