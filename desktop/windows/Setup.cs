using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Interop;

namespace PlamoLocalController
{
    public interface ISetupServices
    {
        Task<string[]> ListDistributionsAsync();
        string SelectFolder(Window owner, string distribution, string repository);
    }

    public sealed class WslSetupServices : ISetupServices
    {
        public async Task<string[]> ListDistributionsAsync()
        {
            ProcessResult result = await WslBackend.RunAsync(new string[] { "--list", "--quiet" }, true);
            if (result.ExitCode != 0) throw new InvalidOperationException("WSLの一覧を取得できませんでした。WSL2のセットアップを確認してください。");
            return ParseDistributions(result.Output);
        }
        public static string[] ParseDistributions(string output)
        {
            List<string> names = new List<string>();
            foreach (string line in output.Trim('\uFEFF').Split(new char[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries))
            {
                string name = line.Trim();
                if (name.Length == 0 || name.StartsWith("-", StringComparison.Ordinal) || name.IndexOfAny(new char[] { '\0', '/', '\\' }) >= 0) continue;
                if (!names.Contains(name)) names.Add(name);
            }
            return names.ToArray();
        }
        public string SelectFolder(Window owner, string distribution, string repository)
        {
            return ProjectFolderPicker.Select(owner, InitialFolder(distribution, repository));
        }
        public static string InitialFolder(string distribution, string repository)
        {
            if (!String.IsNullOrWhiteSpace(distribution))
            {
                Settings normalized = Settings.Normalize(distribution, String.IsNullOrWhiteSpace(repository) ? "/home" : repository, "system");
                return @"\\wsl.localhost\" + normalized.Distribution + normalized.Repository.Replace('/', '\\');
            }
            return @"\\wsl.localhost\";
        }
    }

    // Native Windows file dialog in folder-selection mode; no shell or extra runtime.
    internal static class ProjectFolderPicker
    {
        [DllImport("shell32.dll", CharSet = CharSet.Unicode, PreserveSig = true)]
        private static extern int SHCreateItemFromParsingName(string path, IntPtr context, ref Guid id, out IShellItem item);
        public static string Select(Window owner, string initialFolder)
        {
            IFileOpenDialog dialog = (IFileOpenDialog)new FileOpenDialog();
            IShellItem initial = null; IShellItem selected = null;
            try
            {
                dialog.SetOptions(0x20 | 0x40 | 0x800 | 0x8 | 0x02000000); // PICKFOLDERS / filesystem / existing / no cwd / no recent
                dialog.SetTitle("WSL内の翻訳プロジェクトを選択（scriptsフォルダーを含む場所）");
                dialog.SetOkButtonLabel("このフォルダーを使用");
                Guid id = typeof(IShellItem).GUID;
                if (SHCreateItemFromParsingName(initialFolder, IntPtr.Zero, ref id, out initial) == 0) dialog.SetFolder(initial);
                int outcome = dialog.Show(new WindowInteropHelper(owner).Handle);
                if (outcome == unchecked((int)0x800704C7)) return null;
                Marshal.ThrowExceptionForHR(outcome);
                dialog.GetResult(out selected); IntPtr pointer;
                selected.GetDisplayName(0x80058000, out pointer); // SIGDN_FILESYSPATH
                try { return Marshal.PtrToStringUni(pointer); } finally { Marshal.FreeCoTaskMem(pointer); }
            }
            finally
            {
                if (selected != null) Marshal.ReleaseComObject(selected);
                if (initial != null) Marshal.ReleaseComObject(initial);
                Marshal.ReleaseComObject(dialog);
            }
        }
        [ComImport, Guid("DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7")] private class FileOpenDialog { }
        [ComImport, Guid("D57C7288-D4AD-4768-BE02-9D969532D960"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
        private interface IFileOpenDialog
        {
            [PreserveSig] int Show(IntPtr owner);
            void SetFileTypes(uint count, IntPtr filters); void SetFileTypeIndex(uint index); void GetFileTypeIndex(out uint index);
            void Advise(IntPtr events, out uint cookie); void Unadvise(uint cookie);
            void SetOptions(uint options); void GetOptions(out uint options);
            void SetDefaultFolder(IShellItem item); void SetFolder(IShellItem item); void GetFolder(out IShellItem item);
            void GetCurrentSelection(out IShellItem item);
            void SetFileName([MarshalAs(UnmanagedType.LPWStr)] string name);
            void GetFileName([MarshalAs(UnmanagedType.LPWStr)] out string name);
            void SetTitle([MarshalAs(UnmanagedType.LPWStr)] string title);
            void SetOkButtonLabel([MarshalAs(UnmanagedType.LPWStr)] string label);
            void SetFileNameLabel([MarshalAs(UnmanagedType.LPWStr)] string label);
            void GetResult(out IShellItem item);
        }
        [ComImport, Guid("43826D1E-E718-42EE-BC55-A1E261C37BFE"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
        private interface IShellItem
        {
            void BindToHandler(IntPtr context, ref Guid handler, ref Guid iid, out IntPtr value);
            void GetParent(out IShellItem parent);
            void GetDisplayName(uint kind, out IntPtr name);
            void GetAttributes(uint mask, out uint attributes);
            void Compare(IShellItem other, uint hint, out int order);
        }
    }
}
