# PLaMo Local Translator

Chromeで選択した英文やページ全体を、日本語に翻訳するツールです。日本語から英語への翻訳や、論文原稿の下訳にも使えます。PLaMo 3 Translateを自分のPCで動かし、原文と訳文を見比べながら読んだり編集したりできます。

**Built with PLaMo。PFN等が提供・推奨する公式アプリではない、非公式の開発版です。**

![翻訳ワークスペース](docs/screenshots/workspace-light.png)

## できること

- **Webを読む**：選択文をその場で翻訳。通常のHTMLページは全文翻訳と原文への復帰にも対応します。英→日・日→英を切り替えられます。
- **原稿を下訳する**：テキスト貼り付け、UTF-8の.txt / .md / .texに対応。段落ごとの対訳、中断・再開、数式・引用キー・コードの保護と数値確認ができます。
- **用語をそろえてレビューへ渡す**：用語集や文脈を指定し、原文・下訳・設定・確認事項をMarkdown / JSONへ出力できます。

翻訳モデルは軽量な2Bを標準に、より大きな8Bも選べます。下訳は原文と照合して確認してください。PDFのOCRや元の紙面レイアウトの再現には対応していません。

## 初めて使う

使うものは、**Chrome拡張**と、**PC内でモデルを動かす翻訳環境**です。拡張が文章をPC内の翻訳環境へ渡し、返ってきた訳文を表示します。

### 1. PC内の翻訳環境を準備する

Pythonと翻訳モデルなどを初回に用意します。初回の準備にはターミナルを使います。Windowsでは、Windows上でLinuxを動かす仕組みであるWSL2を使います。OSに合う手順から始めてください。

| 利用環境 | 導入手順 |
| --- | --- |
| Windows（WSL2）・Linux | [翻訳環境の初回準備](docs/SETUP.md#windows-linux) |
| Mac（Apple Silicon / Intel） | [Macの初回準備](docs/SETUP.md#mac) |

初回は公式配布先からモデルを取得します。2Bの重みは約1.8GBです。取得済みの旧モデルも使えます。[モデルの取得と更新](docs/MODEL-DOWNLOAD.md)

### 2. Chromeに拡張を追加する

[v0.1.5の拡張ZIP](https://github.com/kami9811/plamo-local-translator-public/releases/tag/v0.1.5)を展開するか、自分でビルドした`dist`フォルダーを使います。Chromeの`chrome://extensions`から、**`manifest.json`が直接入っているフォルダー**を読み込みます。

[フォルダーの用意からChromeへの追加まで](docs/SETUP.md#chrome-extension)

### 3. 翻訳環境を起動して、拡張へ接続する

翻訳環境を起動すると、拡張を自分のPCへ接続するための「接続キー」を取得できます。このキーを拡張の「接続と設定」へ登録し、**「接続済み · PC内で処理」**と表示されれば準備完了です。

起動には、Windows / Mac向けの**起動・停止用アプリ**を使えます。モデルとPythonの初回準備が済んだ環境を、ボタンで操作するための補助アプリです。「起動」「停止」「接続キーの表示・コピー」ができ、普段はターミナルを開く必要がなくなります。

[起動・停止用アプリをダウンロード（0.1.1）](https://github.com/kami9811/plamo-local-translator-public/releases/tag/controller-v0.1.1) · [実行先の設定と使い方](docs/DESKTOP.md)

アプリを使わず、`python3 scripts/start.py`で起動することもできます。[起動から接続キーの登録までの手順](docs/SETUP.md#pair-extension)

## 普段の使い方

1. 起動・停止用アプリの「起動」を押します。登録した接続キーが変わっていなければ、毎回貼り直す必要はありません。
2. 通常のWebページで英文を選択し、右クリック→「PLaMoで選択文を翻訳」を選びます。ページ全体は拡張のメニューから「ページ翻訳 / 原文へ戻す」を使います。
3. 利用を終えるときは、起動・停止用アプリの「停止」を押します。ウィンドウを閉じるだけでは翻訳環境は停止しません。

最初の翻訳ではモデルの読み込みを待ちます。Chromeの設定画面やChrome Web Storeなどは翻訳対象外です。

ショートカットは選択文がWindows/Linuxで`Ctrl+Shift+Y`、Macで`Command+Shift+Y`。ページ翻訳・復帰は`Alt+Shift+U`です。未割り当てや競合があれば`chrome://extensions/shortcuts`で変更できます。

### 論文原稿の下訳

拡張の「原稿・用語集・接続設定」を開き、「用語と文脈」で設定を保存してから、「原稿ワークスペース」に原稿を投入します。原文と下訳を見比べ、警告を確認してからレビュー用ファイルを出力してください。

AgenticVibe等の後段フローには、原文も含むファイルを渡します。外部Agentを自動で呼び出す連携はありません。[引き渡し形式](docs/HANDOFF.md)

## 動作環境と検証範囲

翻訳環境・拡張はv0.1.5、起動・停止用アプリは0.1.1です。それぞれ別に版を管理しており、この組み合わせで使います。Chrome 123以降とPython 3.10以上が必要です。

- WindowsはWSL2 Ubuntu、RTX 4090 24GB / CUDA 12.6での翻訳を確認しています。
- MacはApple Silicon / Intel向けの構成を用意しています。CPUでの実モデル検証と、通信境界・起動確認を分けて記録しています。MetalとApple Siliconでの8Bは未検証です。
- モデルの重みは2Bが約1.8GB、8Bが約5.3GB。両方を準備する場合、セットアップ全体で20GB程度以上の空き容量を推奨します。

[翻訳・速度の検証](docs/VALIDATION.md) · [起動・停止用アプリの検証](docs/DESKTOP-VALIDATION.md) · [通信検証と制限](docs/NETWORK-SECURITY.md)

### 翻訳速度の実測

RTX 4090で、モデル読み込み後・アプリの翻訳キャッシュ無効・各3回の中央値です。

| 入力 | 2B | 8B |
| --- | ---: | ---: |
| 英語127文字→日本語 | 0.095秒 | 0.200秒 |
| 日本語2,689文字→英語 | 3.963秒 | 8.766秒 |

UIの待ち時間や初回読み込みは含みません。llama.cppのプロンプトキャッシュは有効です。これは従来の測定で、v0.1.5で測り直した値ではありません。[測定条件・品質例](docs/VALIDATION.md)

## 通信と保存データ

通常の翻訳はPC内の翻訳環境で処理します。クラウド翻訳・利用状況送信・自動更新の処理はありません。モデルや依存関係の取得、利用者がGitHub等の案内リンクを開く場合はインターネット通信があります。

Chrome・閲覧先サイト・OSの通信全体を禁止するソフトではありません。ページに表示した訳文をサイト側のJavaScriptが読む場合があるため、機密原稿は拡張の原稿ワークスペースで扱ってください。[通信範囲・検証結果](docs/NETWORK-SECURITY.md)

原稿・訳文・設定・キャッシュは翻訳環境の`.data/`、モデル等は`.runtime/`へ保存します。Gitと配布ZIPには含めません。[保存先と削除方法](docs/DESKTOP.md#stored-data)

## ライセンス

独自のアプリコードは[MIT](LICENSE)。モデルとPLaMo生成部分には[PLaMo Community License](licenses/PLaMo-Community-License-ja.txt)が適用され、アプリのMITライセンスでその条件を緩和しません。商業目的のモデル利用には事前登録等の別条件があります。[第三者の権利・区分](NOTICE.md)

訳文サンプル、ベンチマークの訳文、画像内の訳文はPLaMo 3 Translateの生成物です。**Built with PLaMo。**

日本語UIにはNoto Sans JPを同梱しています。[フォントのOFL](licenses/fonts/NotoSansJP-OFL.txt)。デザインはMaterial 3 ExpressiveとCarbonの原則を参考にした自作CSSです。完全準拠・認証・提携を表すものではありません。[デザイン方針](docs/DESIGN.md)

## 開発

```bash
python3 -m unittest discover -s tests -v
scripts/node.sh npm run typecheck
scripts/node.sh npm run build
python3 scripts/package.py
```

実モデルのブラウザー検証は、専用のテスト環境で実施してください。[アーキテクチャ](docs/ARCHITECTURE.md)
