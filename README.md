# PLaMo Local Translator

**Built with PLaMo — 非公式のローカル翻訳ツールです。**

PLaMo 3 Translateを使って、Chromeの選択文・ページ・論文原稿をPC内で翻訳します。PFN等が提供・推奨する公式アプリではありません。

![翻訳ワークスペース](docs/screenshots/workspace-light.png)

## 機能

- Chromeの選択文翻訳、吹き出し、右クリック、ショートカット、通常HTMLページの全文翻訳と原文復帰。
- 公式GGUFの2B / 8B切り替え、ローカル推論、状態表示。
- UTF-8のtxt / md / tex原稿、段落ごとの対訳、中断再開、数式・引用・コードの保護と数値確認。
- 用語集、分野・文脈、対訳履歴、名前付きプロファイル。
- 原文・下訳・設定・確認指示を含むレビュー用Markdown / JSON。生成元の表示とPLaMo契約全文も含めます。

## 動作確認環境

開発版 v0.1.2。WSL2 Ubuntu / Python 3.10 / NVIDIA RTX 4090 24GB / CUDA 12.6 / Windows Chromeで確認しています。Chrome 123以降が必要です。Mac、CPUのみ、他のGPUでの動作を保証するものではありません。

モデル・Node.js・推論ランタイム・開発依存は初回に取得します。重みだけで約7.1GB、セットアップ全体には20GB程度以上の空き容量を推奨します。取得後の翻訳はローカルで実行します。

## セットアップ

```bash
git clone https://github.com/kami9811/plamo-local-translator-public.git
cd plamo-local-translator-public

# licenses/のPLaMo利用条件を読み、同意する場合のみ実行します。
python3 scripts/setup_runtime.py --accept-model-license
scripts/node.sh npm ci
scripts/node.sh npm run build
python3 scripts/start.py
```

商業目的でのモデル利用には事前登録等の別条件があります。上のフラグで登録が完了するわけではありません。[ライセンスの区分](NOTICE.md)を確認してください。

起動すると `http://127.0.0.1:8765/app.html` と拡張用の接続キーが表示されます。接続キーは公開しないでください。

1. リリースの拡張ZIPを展開するか、ビルドした`dist`フォルダーを用意する。
2. Chromeの`chrome://extensions`でデベロッパーモードを有効にし、「パッケージ化されていない拡張機能を読み込む」から`manifest.json`のあるフォルダーを選ぶ。
3. 拡張の「接続と設定」で接続キーを登録する。
4. Webページで文章を選択して右クリック、または拡張のボタンから翻訳する。

推奨キーは選択文`Ctrl+Shift+Y`、ページ翻訳/復帰`Alt+Shift+U`。未割り当てや競合があれば`chrome://extensions/shortcuts`で変更できます。

停止は`python3 scripts/stop.py`。[詳しい導入手順](docs/SETUP.md)を参照してください。

## 論文の下訳とレビュー

「用語と文脈」で設定を保存し、「原稿ワークスペース」で原稿を投入します。下訳と原文を見比べ、警告を確認してからレビュー用ファイルを出力してください。

AgenticVibe等の後段フローへは原文付きファイルを渡す構成です。外部Agentを自動で呼び出すAPI連携はありません。[引き渡し形式](docs/HANDOFF.md)

## 実測

RTX 4090で、モデル読み込み後・アプリの翻訳キャッシュ無効・各3回の中央値。

| 入力 | 2B | 8B |
|---|---:|---:|
| 英語127文字→日本語 | 0.095秒 | 0.200秒 |
| 日本語2,689文字→英語 | 3.963秒 | 8.766秒 |

UIの待ち時間や初回読み込みは含みません。llama.cppのプロンプトキャッシュは有効です。測定は同じ翻訳コアで行ったもので、今回の帰属表示追加による性能差を主張しません。[条件・品質例・制限](docs/VALIDATION.md)

## ライセンス

独自のアプリコードは[MIT](LICENSE)。モデルとPLaMo生成部分には[PLaMo Community License](licenses/PLaMo-Community-License-ja.txt)が適用され、アプリのMITライセンスでその条件を緩和しません。

訳文サンプル、ベンチマークの訳文、画像内の訳文はPLaMo 3 Translateの生成物です。**Built with PLaMo。** [第三者の権利・区分](NOTICE.md)

デザインはMaterial 3 ExpressiveとCarbonの原則を参考にした自作CSSです。公式の準拠認証や、各社との提携を表すものではありません。[デザイン方針](docs/DESIGN.md)

## 開発

```bash
python3 -m unittest discover -s tests -v
scripts/node.sh npm run typecheck
scripts/node.sh npm run build
python3 scripts/package.py
```

実モデルのブラウザ検証は作業データ・設定を作成するため、専用のテスト環境で実施してください。保存データは`.data/`、モデル等は`.runtime/`。いずれもGitとリリースに含めません。[アーキテクチャ](docs/ARCHITECTURE.md)

日本語UIにはNoto Sans JPを同梱しています。フォントのための外部通信は不要です。書体のOFLは `licenses/fonts/`、文字組みと配置の判断は [デザイン方針](docs/DESIGN.md) を参照してください。
