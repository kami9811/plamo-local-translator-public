# Windows / Macの起動・停止用アプリ

起動・停止・Chrome拡張に登録する接続キーの表示とコピーを行う、小さなデスクトップアプリです。モデルとChrome拡張の[初回セットアップ](SETUP.md)が済んだ環境で使います。普段の起動・停止やキーのコピーは、ターミナルを開かずに操作できます。

アプリを開くだけではAPIを起動しません。ウィンドウを閉じてもAPIは動作を続けます。停止するときは「停止」を押します。翻訳モデルは最初の翻訳時に読み込みます。

## ダウンロード

[起動・停止用アプリのリリース](https://github.com/kami9811/plamo-local-translator-public/releases/tag/controller-v0.1.1)から、OSに合うZIPをダウンロードして展開してください。

| OS | ファイル | 実行環境 |
| --- | --- | --- |
| Windows | `plamo-local-controller-windows-0.1.1.zip` | Windows 10/11、.NET Framework 4.7.2以上、WSL2 |
| Mac | `plamo-local-controller-macos-0.1.1.zip` | macOS 12以上、Apple Silicon / Intel、Python 3.10以上 |

Windows版はWPF、Mac版はAppKitを使います。モデル、原稿、接続キー、Python、WSLはZIPに含めません。MacのアプリはUniversalバイナリです。Developer ID署名・Appleの公証は行っていません。MacのMetal推論と、Apple Siliconでの8Bの動作は別途未検証です。実際に確認した範囲は[検証記録](DESKTOP-VALIDATION.md)を参照してください。

## 初回セットアップ済みのWindowsで使う

1. ZIPを右クリック→「すべて展開」します。
2. 中の `PLaMoLocalController.exe` をダブルクリックします。
3. 「実行先の設定」を開きます。WSLはWindows上で使うLinux環境です。「一覧から選ぶ」を押し、**初回セットアップに使ったUbuntu等**を選んでください。通常の既定環境なら空欄でも使えます。分からない場合はPowerShellで `wsl --list --quiet` を実行すると名前だけを確認できます。
4. 「フォルダーを選択…」から、**初回セットアップした翻訳プロジェクト**を選びます。`scripts` フォルダーと `runtime-manifest.json` が直接入っている場所です。起動・停止用アプリのZIP、`.exe`、Chrome拡張の `dist`、`scripts` 自体は選びません。
5. 選択画面で見つからない場合は、エクスプローラーのアドレスバーに `\\wsl.localhost\` と入力します。WSL名 → `home` → 自分のLinuxユーザー → プロジェクトの保存先、と開きます。例えば次の配置では、矢印のプロジェクトを選びます。

   ```text
   Ubuntu/
     home/
       自分のユーザー/
         plamo-local-translator-public/  ← このフォルダー
           scripts/
             start.py
           runtime-manifest.json
           server/
   ```

   別の場所へcloneした場合は、その場所を選びます。共有パスから選択すると、WSL名とLinux側のパスを自動で入力します。パスの貼り付けやフォルダーのドラッグも使えます。
6. 保存場所が分からないときは、セットアップしたUbuntuのターミナルで、使っているプロジェクトへ移動して `pwd` を実行します。表示された `/home/…/plamo-local-translator-public` のようなパスを貼り付けてください。
7. 「確認して保存」を押します。指定した場所・Python・APIの状態を確認し、成功した場合だけ設定を保存します。**この確認で翻訳APIやモデルは起動しません。**
8. 「起動」を押します。その後の登録・翻訳は[Chromeで利用できる状態まで](#chrome-extension)の順に進めます。
9. 終了時は、このアプリの「停止」を押します。

Windows側へプロジェクト全体をコピーする必要はありません。アプリはWSLのPythonを使います。起動済みの別のプロジェクトが8765番ポートを使っている場合は、そのAPIを勝手に停止せず、実行先の確認を促します。

旧版v0.1.1〜v0.1.3のチェックアウトも、セットアップが完了していれば操作できます。起動・停止用アプリ自身に共通ブリッジを同梱しているため、使っているフォルダーへのファイル追加は不要です。ただし、v0.1.4の通信制限を適用するには、翻訳環境と拡張を更新してください。操作アプリ0.1.1はそのまま使えます。[通信と更新方法](NETWORK-SECURITY.md)

<a id="macの初回セットアップ"></a>

## 初回セットアップ済みのMacで使う

先に[Macの翻訳環境を準備する](SETUP.md#mac)と[Chromeへ拡張を追加する](SETUP.md#chrome-extension)を完了してください。以下では、準備したプロジェクトをこのアプリに登録します。

1. Mac版ZIPを展開し、`PLaMo Local Controller.app` を「アプリケーション」へ移動します。
2. アプリを開きます。初回にmacOSがブロックした場合は、配布元とSHA256を確認したうえで「システム設定」→「プライバシーとセキュリティ」→「このまま開く」から許可します。管理されたMacでは管理者の方針に従います。
3. 「フォルダーを選択…」で、初回セットアップした `plamo-local-translator-public` フォルダーを選び、「確認して保存」を押します。`scripts` と `runtime-manifest.json` が入る場所です。`.app`、ZIP、`dist`、`scripts` 自体は選びません。Finderで場所が分からなければ、セットアップしたターミナルで `pwd` を実行し、パスを貼り付けてください。
4. 「起動」を押します。
5. アプリで「接続キーを表示」→「コピー」を押し、[次の手順](#chrome-extension)でChrome拡張へ登録します。
6. 終了時は「停止」を押します。

CLIの `python3 scripts/start.py` / `python3 scripts/stop.py` も同じ起動・停止処理を使います。MacのChromeショートカットは `chrome://extensions/shortcuts` で確認・変更できます。

<a id="chrome-extension"></a>

## Chromeで利用できる状態まで

**起動 → 接続キーを表示・コピー → 拡張の設定へ貼り付け → 接続済みを確認 → 翻訳**の順です。

1. 起動・停止用アプリで「起動」を押します。「接続キーを表示」→「コピー」を押してください。
2. Chrome右上のパズルアイコンから「PLaMo Local」を開きます。見当たらない場合は、先に[Chromeへ拡張を追加する手順](SETUP.md#chrome-extension)を完了してください。
3. 小さなメニューの「原稿・用語集・接続設定」をクリックします。新しく開いたタブの左メニューから「接続と設定」を選びます。
4. 「ローカルエンジンとの接続」の「接続キー」欄へ貼り付け、「接続する」を押します。
5. 上部に **「接続済み · PC内で処理」**と表示されれば準備完了です。登録後にキー欄が空になるのは正常です。
6. 通常のWebページで英文を選択 → 右クリック →「PLaMoで選択文を翻訳」を選びます。最初の翻訳ではモデルの読み込みを待ちます。

キーを貼り付けるのは、アドレスが **`chrome-extension://`** で始まる拡張の画面です。`http://127.0.0.1:8765/app.html` のブラウザー版への接続だけでは、拡張への登録は完了しません。同じキーを使う間は毎回の貼り直しは不要です。

起動・停止用アプリ単体では拡張側の登録完了を取得しません。アプリの「起動中」と拡張の「接続済み」は別の状態です。接続完了は必ずChrome側で確認してください。

## 停止してもWSLのメモリが残る場合

「停止」は、このプロジェクトのAPI・モデルのプロセスを終了します。WSL全体や、他の開発アプリは停止しません。Linuxが読み込んだモデルや他のファイルをキャッシュとして保持すると、CPU/GPUが動いていなくてもWindowsのvmmemWSLのメモリが残る場合があります。停止直後のWindowsの使用量だけでは、翻訳プロセスが残っているかは判断できません。

WSLの自動回収は[MicrosoftのautoMemoryReclaimの説明](https://learn.microsoft.com/en-us/windows/wsl/wsl-config#experimental-settings)を参照してください。起動・停止用アプリはシステム全体のキャッシュ消去やWSLの強制終了、`.wslconfig`の変更を行いません。

<a id="stored-data"></a>

## 保存するもの・削除方法

| 場所 | 内容 |
| --- | --- |
| Windows: `%LOCALAPPDATA%\PLaMoLocalTranslator\controller.json` | WSL名、プロジェクトのパス、テーマ |
| Mac: `~/Library/Application Support/PLaMoLocalTranslator/controller.json` | プロジェクトのパス、テーマ |
| プロジェクトの `.data/` | API接続キー、ログ、原稿、翻訳結果、設定、キャッシュ |
| プロジェクトの `.runtime/` | モデル、Node.js、llama.cpp |

接続キーを起動・停止用アプリの設定ファイルやログへ保存しません。キーは明示的な表示操作で読み取り、コピーを押したときだけクリップボードへ渡します。表示したキーは設定変更や次の操作でクリアします。クリップボードの管理はOSに従います。

起動・停止用アプリの設定だけ消す場合はアプリを閉じて `controller.json` を削除します。原稿等はWeb画面から削除できます。`.data/` 全体を削除する場合はAPIを停止し、必要な原稿を先に出力してください。`.runtime/` の削除後は再セットアップが必要です。

## ビルド

Windows / WSLでは .NET Framework 付属のC#コンパイラーを使います。追加SDKは不要です。

```bash
python3 scripts/build_windows_controller.py
python3 scripts/build_windows_controller.py --tests
```

MacではXcode Command Line Toolsが必要です。

```bash
python3 scripts/build_macos_controller.py
python3 scripts/build_macos_controller.py --tests
```

ZIPは `artifacts/` に作成されます。Mac版はarm64/x86_64をそれぞれコンパイルし、`lipo` で統合してアドホック署名します。ソースから自分でビルドする場合も同じ手順です。

WSLの一覧・既定環境・共有パスは[Microsoft公式手順](https://learn.microsoft.com/en-us/windows/wsl/basic-commands)を参照しています。
