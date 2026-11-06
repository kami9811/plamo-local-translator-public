using System;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows;

[assembly: AssemblyTitle("PLaMo Local Controller")]
[assembly: AssemblyDescription("Local API controls for PLaMo Local Translator")]
[assembly: AssemblyCompany("PLaMo Local Translator contributors")]
[assembly: AssemblyProduct("PLaMo Local Controller")]
[assembly: AssemblyVersion("0.1.1.0")]
[assembly: AssemblyFileVersion("0.1.1.0")]
[assembly: ComVisible(false)]

namespace PlamoLocalController
{
    internal static class Program
    {
        [STAThread]
        private static void Main()
        {
            bool created;
            using (Mutex mutex = new Mutex(true, @"Local\PLaMoLocalController", out created))
            {
                if (!created) { MessageBox.Show("コントローラーは、すでに開いています。タスクバーから開いてください。", "PLaMo Local"); return; }
                Application app = new Application();
                string path = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "PLaMoLocalTranslator", "controller.json");
                app.Run(new ControllerWindow(new WslBackend(), new SettingsStore(path)));
            }
        }
    }
}
