PLaMo Local コントローラー — macOS

初回だけPython 3.10以降と翻訳環境のセットアップが必要です。
HomebrewのPython、またはpython.orgのPythonを使用してください。

1. ZIPを展開し、PLaMo Local Controller.appをアプリケーションに移動します。
2. アプリを開き、「選択…」で scripts/start.py があるプロジェクトフォルダーを指定して保存します。
3. 「起動」を押します。翻訳モデルはChromeから最初に翻訳するときに読み込みます。
4. 「接続キーを表示」→「コピー」を押し、Chrome拡張の「接続と設定」に貼り付けます。
5. 翻訳環境を終了するときは「停止」を押します。アプリを閉じるだけではAPIは停止しません。

アプリを開くだけではAPIを起動しません。モデルや原稿、接続キーをアプリに同梱していません。
Apple Developer IDでの署名・公証は行っていません。配布バイナリはアドホック署名です。
初回にmacOSで実行を拒否された場合は、配布元とSHA256を確認したうえで、
システム設定 → プライバシーとセキュリティの「このまま開く」から許可します。
管理されたMacでは管理者のポリシーに従ってください。

設定の保存先：~/Library/Application Support/PLaMoLocalTranslator/controller.json
保存するのはプロジェクトの場所と表示テーマだけです。接続キーは保存しません。
APIのログ・原稿・接続キーは、プロジェクト内の .data/ に保存されます。
削除する場合はAPIを停止してから .data/ を削除します。原稿も消えるので必要な出力を先に保存してください。

初回セットアップ、詳細、ソース：
https://github.com/kami9811/plamo-local-translator-public/blob/fix/japanese-typography-layout/docs/DESKTOP.md

Built with PLaMo · 非公式ツール。アプリのコードはMITです。
PLaMoモデルと生成物の条件は同梱のlicensesとNOTICE.mdを参照してください。
