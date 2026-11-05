using System;
using System.IO;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Automation;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Markup;
using System.Windows.Media;
using Microsoft.Win32;

namespace PlamoLocalController
{
    public sealed class ControllerWindow : Window
    {
        private readonly IBackend backend;
        private readonly ISettingsStore store;
        private Settings saved;
        private string theme;
        private bool busy;
        private string visibleKey;
        private readonly StackPanel content;
        private readonly Border statusPill;
        internal readonly TextBox DistributionBox;
        internal readonly TextBox RepositoryBox;
        internal readonly TextBox KeyBox;
        internal readonly Button StartButton;
        internal readonly Button StopButton;
        internal readonly Button KeyButton;
        internal readonly Button CopyButton;
        internal readonly Button SaveButton;
        internal readonly Button ThemeButton;
        internal readonly Expander Configuration;
        internal readonly TextBlock StatusText;
        internal readonly TextBlock MessageText;
        internal bool IsBusy { get { return busy; } }
        internal string LastState { get; private set; }
        internal string CurrentTheme { get { return theme; } }

        private const string Styles = @"
<ResourceDictionary xmlns='http://schemas.microsoft.com/winfx/2006/xaml/presentation' xmlns:x='http://schemas.microsoft.com/winfx/2006/xaml'>
 <Style x:Key='FocusRing'><Setter Property='Control.Template'><Setter.Value><ControlTemplate><Border BorderBrush='{DynamicResource Primary}' BorderThickness='2' CornerRadius='10' Margin='-3'/></ControlTemplate></Setter.Value></Setter></Style>
 <Style TargetType='Button'>
  <Setter Property='Background' Value='{DynamicResource Surface}'/><Setter Property='Foreground' Value='{DynamicResource Text}'/>
  <Setter Property='BorderBrush' Value='{DynamicResource Line}'/><Setter Property='BorderThickness' Value='1'/>
  <Setter Property='Padding' Value='16,10'/><Setter Property='MinHeight' Value='44'/><Setter Property='FontSize' Value='14'/><Setter Property='FontWeight' Value='Medium'/>
  <Setter Property='Cursor' Value='Hand'/><Setter Property='FocusVisualStyle' Value='{StaticResource FocusRing}'/>
  <Setter Property='Template'><Setter.Value><ControlTemplate TargetType='Button'><Border x:Name='border' Background='{TemplateBinding Background}' BorderBrush='{TemplateBinding BorderBrush}' BorderThickness='{TemplateBinding BorderThickness}' CornerRadius='9' Padding='{TemplateBinding Padding}'><ContentPresenter HorizontalAlignment='Center' VerticalAlignment='Center' RecognizesAccessKey='True'/></Border><ControlTemplate.Triggers><Trigger Property='IsMouseOver' Value='True'><Setter TargetName='border' Property='Opacity' Value='0.88'/></Trigger><Trigger Property='IsPressed' Value='True'><Setter TargetName='border' Property='Opacity' Value='0.75'/></Trigger><Trigger Property='IsEnabled' Value='False'><Setter TargetName='border' Property='Opacity' Value='0.45'/></Trigger></ControlTemplate.Triggers></ControlTemplate></Setter.Value></Setter>
 </Style>
 <Style TargetType='TextBox'>
  <Setter Property='Background' Value='{DynamicResource Surface}'/><Setter Property='Foreground' Value='{DynamicResource Text}'/>
  <Setter Property='CaretBrush' Value='{DynamicResource Text}'/><Setter Property='BorderBrush' Value='{DynamicResource Line}'/><Setter Property='BorderThickness' Value='1'/>
  <Setter Property='Padding' Value='12,10'/><Setter Property='FontSize' Value='14'/><Setter Property='MinHeight' Value='44'/>
  <Setter Property='Template'><Setter.Value><ControlTemplate TargetType='TextBox'><Border x:Name='border' Background='{TemplateBinding Background}' BorderBrush='{TemplateBinding BorderBrush}' BorderThickness='{TemplateBinding BorderThickness}' CornerRadius='8'><ScrollViewer x:Name='PART_ContentHost' Margin='{TemplateBinding Padding}'/></Border><ControlTemplate.Triggers><Trigger Property='IsKeyboardFocused' Value='True'><Setter TargetName='border' Property='BorderBrush' Value='{DynamicResource Primary}'/></Trigger><Trigger Property='IsEnabled' Value='False'><Setter TargetName='border' Property='Opacity' Value='0.55'/></Trigger></ControlTemplate.Triggers></ControlTemplate></Setter.Value></Setter>
 </Style>
</ResourceDictionary>";

        public ControllerWindow(IBackend backend, ISettingsStore store)
        {
            this.backend = backend; this.store = store; saved = store.Load(); theme = saved.Theme ?? "system";
            Title = "PLaMo Local コントローラー"; Width = 640; Height = 790;
            MinWidth = 560; MinHeight = 660; WindowStartupLocation = WindowStartupLocation.CenterScreen;
            FontFamily = new FontFamily("Yu Gothic UI"); FontSize = 14;
            Resources = (ResourceDictionary)XamlReader.Parse(Styles);
            SetResourceReference(BackgroundProperty, "Background"); SetResourceReference(ForegroundProperty, "Text");
            ApplyPalette();
            ScrollViewer scroll = new ScrollViewer { VerticalScrollBarVisibility = ScrollBarVisibility.Auto, HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled };
            scroll.SetResourceReference(Control.BackgroundProperty, "Background");
            content = new StackPanel { Margin = new Thickness(28) }; scroll.Content = content; Content = scroll;

            DockPanel brand = new DockPanel { Margin = new Thickness(0, 0, 0, 22) };
            ThemeButton = MakeButton("表示：" + ThemeLabel(), "表示テーマを切り替える");
            ThemeButton.Padding = new Thickness(10, 7, 10, 7); ThemeButton.FontSize = 12; ThemeButton.MinHeight = 36;
            ThemeButton.Click += delegate { CycleTheme(); }; DockPanel.SetDock(ThemeButton, Dock.Right); brand.Children.Add(ThemeButton);
            StackPanel identity = new StackPanel(); identity.Children.Add(Text("PLaMo Local", 19, FontWeights.SemiBold));
            identity.Children.Add(Muted("Windows コントローラー", 12)); brand.Children.Add(identity); content.Children.Add(brand);
            content.Children.Add(Text("ローカル翻訳の操作", 25, FontWeights.SemiBold));
            content.Children.Add(Muted("起動・停止と、拡張に登録する接続キーの確認。", 14, new Thickness(0, 6, 0, 22)));

            StackPanel config = new StackPanel();
            DistributionBox = new TextBox { Text = saved.Distribution ?? "", Margin = new Thickness(0, 7, 0, 14) };
            AddLabel(config, "WSL名（空欄なら既定のディストリビューション）", DistributionBox); config.Children.Add(DistributionBox);
            RepositoryBox = new TextBox { Text = saved.Repository ?? "", Margin = new Thickness(0, 7, 0, 7), AllowDrop = true };
            AddLabel(config, "Linux側のプロジェクトフォルダー", RepositoryBox); config.Children.Add(RepositoryBox);
            config.Children.Add(Muted("WSLのフォルダーをドラッグするか、Linuxパス・WSL共有パスを貼り付けます。", 12));
            RepositoryBox.PreviewDragOver += delegate(object sender, DragEventArgs e) { e.Effects = e.Data.GetDataPresent(DataFormats.FileDrop) ? DragDropEffects.Copy : DragDropEffects.None; e.Handled = true; };
            RepositoryBox.PreviewDrop += delegate(object sender, DragEventArgs e) {
                string[] paths = e.Data.GetData(DataFormats.FileDrop) as string[];
                if (paths != null && paths.Length == 1) RepositoryBox.Text = paths[0]; e.Handled = true;
            };
            SaveButton = MakeButton("設定を保存", "実行先の設定を保存"); SaveButton.Margin = new Thickness(0, 14, 0, 0); SaveButton.HorizontalAlignment = HorizontalAlignment.Right;
            SaveButton.Click += delegate { try { SaveConfiguration(); SetMessage("設定を保存しました。", false); } catch (Exception error) { SetMessage(error.Message, true); } };
            config.Children.Add(SaveButton);
            Configuration = new Expander { Header = "実行先の設定", Content = config, IsExpanded = String.IsNullOrWhiteSpace(saved.Repository) };
            Configuration.SetResourceReference(Control.ForegroundProperty, "Text");
            content.Children.Add(Card(Configuration));

            StackPanel actions = new StackPanel();
            DockPanel status = new DockPanel { Margin = new Thickness(0, 0, 0, 16) };
            StatusText = Text("未確認", 12, FontWeights.Medium);
            statusPill = new Border { Child = StatusText, Padding = new Thickness(10, 5, 10, 5), CornerRadius = new CornerRadius(7) };
            statusPill.SetResourceReference(Border.BackgroundProperty, "Surface2"); DockPanel.SetDock(statusPill, Dock.Right); status.Children.Add(statusPill);
            status.Children.Add(Text("起動と停止", 15, FontWeights.SemiBold)); actions.Children.Add(status);
            Grid row = new Grid(); row.ColumnDefinitions.Add(new ColumnDefinition()); row.ColumnDefinitions.Add(new ColumnDefinition());
            StartButton = MakeButton("起動", "ローカルAPIを起動"); StartButton.Margin = new Thickness(0, 0, 6, 0); StartButton.SetResourceReference(Button.BackgroundProperty, "Primary"); StartButton.SetResourceReference(Button.ForegroundProperty, "OnPrimary"); StartButton.SetResourceReference(Button.BorderBrushProperty, "Primary");
            StopButton = MakeButton("停止", "ローカルAPIとモデルを停止"); StopButton.Margin = new Thickness(6, 0, 0, 0); StopButton.ToolTip = "進行中の翻訳を中断し、APIとモデルを停止します。";
            Grid.SetColumn(StopButton, 1); row.Children.Add(StartButton); row.Children.Add(StopButton); actions.Children.Add(row);
            StartButton.Click += async delegate { await RunActionAsync("start"); }; StopButton.Click += async delegate { await RunActionAsync("stop"); };
            MessageText = Muted("実行先を指定して、操作を選んでください。", 13, new Thickness(0, 14, 0, 0));
            AutomationProperties.SetLiveSetting(MessageText, AutomationLiveSetting.Polite); actions.Children.Add(MessageText); content.Children.Add(Card(actions));

            StackPanel keys = new StackPanel();
            KeyButton = MakeButton("接続キーを表示", "起動中APIの接続キーを表示"); KeyButton.HorizontalAlignment = HorizontalAlignment.Left;
            KeyButton.Click += async delegate { await RunActionAsync("key"); }; keys.Children.Add(KeyButton);
            Grid keyRow = new Grid { Margin = new Thickness(0, 12, 0, 0) }; keyRow.ColumnDefinitions.Add(new ColumnDefinition()); keyRow.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            KeyBox = new TextBox { IsReadOnly = true, FontFamily = new FontFamily("Consolas"), Text = "表示していません", IsTabStop = false, TextWrapping = TextWrapping.Wrap };
            AutomationProperties.SetName(KeyBox, "接続キー"); keyRow.Children.Add(KeyBox);
            CopyButton = MakeButton("コピー", "接続キーをクリップボードへコピー"); CopyButton.Margin = new Thickness(10, 0, 0, 0); CopyButton.IsEnabled = false; Grid.SetColumn(CopyButton, 1); keyRow.Children.Add(CopyButton);
            CopyButton.Click += delegate { try { if (!String.IsNullOrEmpty(visibleKey)) { Clipboard.SetText(visibleKey); SetMessage("接続キーをコピーしました。", false); } } catch (Exception) { SetMessage("コピーできませんでした。キーを選択してコピーしてください。", true); } };
            keys.Children.Add(keyRow); keys.Children.Add(Muted("接続キーは、このPCのChrome拡張だけで使います。", 12, new Thickness(0, 10, 0, 0))); content.Children.Add(Card(keys));
            content.Children.Add(Muted("ウィンドウを閉じてもAPIは動作を続けます。終了するときは「停止」を押してください。", 12, new Thickness(0, 0, 0, 12)));
            content.Children.Add(Muted("Built with PLaMo · 非公式ツール", 11));
            DistributionBox.TextChanged += delegate { ClearKey(); }; RepositoryBox.TextChanged += delegate { ClearKey(); };
            Closing += delegate(object sender, System.ComponentModel.CancelEventArgs e) { if (busy) { e.Cancel = true; SetMessage("処理が終わるまでお待ちください。", false); } };
            LastState = "unknown";
        }

        private TextBlock Text(string text, double size, FontWeight weight)
        {
            TextBlock block = new TextBlock { Text = text, FontSize = size, FontWeight = weight, TextWrapping = TextWrapping.Wrap, VerticalAlignment = VerticalAlignment.Center };
            block.SetResourceReference(TextBlock.ForegroundProperty, "Text"); return block;
        }
        private TextBlock Muted(string text, double size, Thickness? margin = null)
        {
            TextBlock block = Text(text, size, FontWeights.Normal); block.SetResourceReference(TextBlock.ForegroundProperty, "Muted"); if (margin.HasValue) block.Margin = margin.Value; return block;
        }
        private Button MakeButton(string text, string accessibleName)
        {
            Button button = new Button { Content = text }; AutomationProperties.SetName(button, accessibleName); return button;
        }
        private Border Card(UIElement child)
        {
            Border card = new Border { Child = child, Padding = new Thickness(20), BorderThickness = new Thickness(1), CornerRadius = new CornerRadius(14), Margin = new Thickness(0, 0, 0, 16) };
            card.SetResourceReference(Border.BackgroundProperty, "Surface"); card.SetResourceReference(Border.BorderBrushProperty, "Line"); return card;
        }
        private void AddLabel(StackPanel parent, string text, Control control)
        {
            Label label = new Label { Content = text, Target = control, Padding = new Thickness(0), FontSize = 13, FontWeight = FontWeights.Medium, Margin = new Thickness(0, 14, 0, 0) };
            label.SetResourceReference(Label.ForegroundProperty, "Text"); AutomationProperties.SetName(control, text); parent.Children.Add(label);
        }
        private void ClearKey()
        {
            visibleKey = null;
            if (KeyBox != null) { KeyBox.Text = "表示していません"; KeyBox.IsTabStop = false; }
            if (CopyButton != null) CopyButton.IsEnabled = false;
        }
        private Settings SaveConfiguration()
        {
            Settings next = Settings.Normalize(DistributionBox.Text, RepositoryBox.Text, theme);
            store.Save(next); ClearKey(); saved = next; DistributionBox.Text = next.Distribution; RepositoryBox.Text = next.Repository;
            Configuration.IsExpanded = false; Configuration.Header = "実行先：" + (String.IsNullOrEmpty(next.Distribution) ? "既定のWSL" : next.Distribution);
            Configuration.ToolTip = next.Repository; return next;
        }
        private void SetMessage(string message, bool error)
        {
            MessageText.Text = message; MessageText.SetResourceReference(TextBlock.ForegroundProperty, error ? "Error" : "Muted");
        }
        public async Task RunActionAsync(string action)
        {
            if (busy) return;
            try
            {
                Settings settings = SaveConfiguration(); ClearKey(); SetBusy(true); SetMessage("処理しています…", false);
                ControlResult result = await backend.ExecuteAsync(action, settings);
                if (!result.ok) { LastState = "unknown"; StatusText.Text = "要確認"; SetMessage(result.message, true); return; }
                LastState = result.state; StatusText.Text = result.state == "running" ? "起動中" : "停止中";
                SetMessage(result.message, false);
                if (action == "key" && !String.IsNullOrEmpty(result.key)) { visibleKey = result.key; KeyBox.Text = result.key; KeyBox.IsTabStop = true; }
            }
            catch (ArgumentException error) { SetMessage(error.Message, true); }
            catch (InvalidOperationException error) { StatusText.Text = "要確認"; LastState = "unknown"; SetMessage(error.Message, true); }
            catch (Exception) { StatusText.Text = "要確認"; LastState = "unknown"; SetMessage("操作できませんでした。実行先とWSLの設定を確認してください。", true); }
            finally { SetBusy(false); }
        }
        private void SetBusy(bool value)
        {
            busy = value; foreach (Control control in new Control[] { StartButton, StopButton, KeyButton, SaveButton, DistributionBox, RepositoryBox }) control.IsEnabled = !value;
            CopyButton.IsEnabled = !value && !String.IsNullOrEmpty(visibleKey);
        }
        private string ThemeLabel() { return theme == "light" ? "ライト" : theme == "dark" ? "ダーク" : "システム"; }
        internal void CycleTheme()
        {
            theme = theme == "system" ? "light" : theme == "light" ? "dark" : "system"; ApplyPalette(); ThemeButton.Content = "表示：" + ThemeLabel();
            try { saved.Theme = theme; store.Save(saved); } catch (Exception) { SetMessage("表示を変更しました。設定を保存できませんでした。", true); }
        }
        private void ApplyPalette()
        {
            bool dark = theme == "dark";
            if (theme == "system")
            {
                try { using (RegistryKey key = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")) dark = key != null && Convert.ToInt32(key.GetValue("AppsUseLightTheme", 1)) == 0; } catch (Exception) { dark = false; }
            }
            string[] names = { "Background", "Surface", "Surface2", "Text", "Muted", "Primary", "OnPrimary", "Line", "Error" };
            string[] colors = dark ? new string[] { "#151B18", "#1D2521", "#26322B", "#EDF2ED", "#BAC9BF", "#8BDBB3", "#123A27", "#46564B", "#FFB5AD" } : new string[] { "#F5F6F4", "#FFFFFF", "#EDF1ED", "#202C28", "#52625A", "#146B54", "#FFFFFF", "#D5DDD7", "#A52B29" };
            for (int i = 0; i < names.Length; i++) Resources[names[i]] = new SolidColorBrush((Color)ColorConverter.ConvertFromString(colors[i]));
        }
    }
}
