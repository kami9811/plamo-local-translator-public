# Windows / Macの操作アプリ

起動・停止・Chrome拡張に登録する接続キーの表示とコピーを行う、小さなデスクトップアプリです。モデルとChrome拡張の初回セットアップ後は、ターミナルを開かずに操作できます。

アプリを開くだけではAPIを起動しません。ウィンドウを閉じてもAPIは動作を続けます。停止するときは「停止」を押します。翻訳モデルは最初の翻訳時に読み込みます。

## ダウンロード

[コントローラーのリリース](https://github.com/kami9811/plamo-local-translator-public/releases/tag/controller-v0.1.0)から、OSに合うZIPをダウンロードして展開してください。

| OS | ファイル | 実行環境 |
| --- | --- | --- |
| Windows | `plamo-local-controller-windows-0.1.0.zip` | Windows 10/11、.NET Framework 4.7.2以上、WSL2 |
| Mac | `plamo-local-controller-macos-0.1.0.zip` | macOS 12以上、Apple Silicon / Intel、Python 3.10以上 |

Windows版はWPF、Mac版はAppKitを使います。モデル、原稿、接続キー、Python、WSLはZIPに含めません。MacのアプリはUniversalバイナリです。Developer ID署名・Appleの公証は行っていません。MacのMetal推論と、Apple Siliconでの8Bの動作は別途未検証です。実際に確認した範囲は[検証記録](DESKTOP-VALIDATION.md)を参照してください。

## 初回セットアップ済みのWindowsで使う

1. ZIPを右クリック→「すべて展開」します。
2. 中の `PLaMoLocalController.exe` をダブルクリックします。
3. 「実行先の設定」に、使っているWSLプロジェクトのパスを貼り付けます。`scripts/start.py` があるフォルダーです。Linuxの絶対パス、またはエクスプローラーの `\\wsl.localhost\Ubuntu\...` のパスを使えます。WSLフォルダーのドラッグにも対応します。
4. WSL名は、普段使う既定の環境なら空欄で構いません。共有パスからは自動で読み取ります。別のディストリビューションを使うときだけ、その名前を指定します。
5. 「設定を保存」を押します。次回から入力は不要です。
6. 「起動」を押します。
7. 「接続キーを表示」→「コピー」を押し、[Chrome拡張の「接続と設定」](SETUP.md#pair-extension)へ貼り付けます。登録済みのキーが変わっていなければ毎回貼り直す必要はありません。
8. 終了時は、このアプリの「停止」を押します。

Windows側へプロジェクト全体をコピーする必要はありません。アプリはWSLのPythonを使います。起動済みの別のプロジェクトが8765番ポートを使っている場合は、そのAPIを勝手に停止せず、実行先の確認を促します。

旧版v0.1.1〜v0.1.3のチェックアウトも、セットアップが完了していれば操作できます。コントローラー自身に共通ブリッジを同梱しているため、使っているフォルダーへのファイル追加は不要です。

## Macの初回セットアップ

最初の準備だけターミナルを使います。Python 3.10以降を[python.org](https://www.python.org/downloads/macos/)またはHomebrewでインストールしてください。コントローラーは `/opt/homebrew/bin/python3`、`/usr/local/bin/python3`、python.orgのCurrentを探します。OS付属の開発ツール用Pythonは使いません。

Mac対応のソースが入ったリリースタグを使います。既存のmainには未マージの場合があります。

```bash
git clone --branch controller-v0.1.0 https://github.com/kami9811/plamo-local-translator-public.git
cd plamo-local-translator-public

# licenses/の条件に同意する場合。まず2Bだけ取得する例です。
python3 scripts/setup_runtime.py --accept-model-license --models 2b
scripts/node.sh npm ci
scripts/node.sh npm run build
```

8Bも使う場合は `--models all`、後から8Bを追加する場合は `--models 8b` を指定します。重みは2B約1.8GB、8B約5.3GBです。8Bはメモリーに余裕のあるMac向けです。セットアップはMacのCPU種別を検出し、SHA256を確認した公式llama.cpp配布物とモデルを取得します。通常のMac推論はMetalを有効にします。

1. Mac版ZIPを展開し、`PLaMo Local Controller.app` を「アプリケーション」へ移動します。
2. アプリを開きます。初回にmacOSがブロックした場合は、配布元とSHA256を確認したうえで「システム設定」→「プライバシーとセキュリティ」→「このまま開く」から許可します。管理されたMacでは管理者の方針に従います。
3. 「選択…」で、先ほどの `plamo-local-translator-public` フォルダーを選び、「設定を保存」を押します。
4. 「起動」を押します。
5. Chromeで `chrome://extensions` を開き、デベロッパーモード→「パッケージ化されていない拡張機能を読み込む」から、このプロジェクトの **`dist` フォルダー**を選びます。`manifest.json` が直接入る場所です。[詳しい画面操作](SETUP.md#chrome-extension)
6. アプリで「接続キーを表示」→「コピー」を押し、Chrome拡張の「接続と設定」に登録します。
7. 終了時は「停止」を押します。

CLIの `python3 scripts/start.py` / `python3 scripts/stop.py` も同じ起動・停止処理を使います。MacのChromeショートカットは `chrome://extensions/shortcuts` で確認・変更できます。

## 保存するもの・削除方法

| 場所 | 内容 |
| --- | --- |
| Windows: `%LOCALAPPDATA%\PLaMoLocalTranslator\controller.json` | WSL名、プロジェクトのパス、テーマ |
| Mac: `~/Library/Application Support/PLaMoLocalTranslator/controller.json` | プロジェクトのパス、テーマ |
| プロジェクトの `.data/` | API接続キー、ログ、原稿、翻訳結果、設定、キャッシュ |
| プロジェクトの `.runtime/` | モデル、Node.js、llama.cpp |

接続キーをコントローラーの設定ファイルやログへ保存しません。キーは明示的な表示操作で読み取り、コピーを押したときだけクリップボードへ渡します。表示したキーは設定変更や次の操作でクリアします。クリップボードの管理はOSに従います。

コントローラーの設定だけ消す場合はアプリを閉じて `controller.json` を削除します。原稿等はWeb画面から削除できます。`.data/` 全体を削除する場合はAPIを停止し、必要な原稿を先に出力してください。`.runtime/` の削除後は再セットアップが必要です。

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
