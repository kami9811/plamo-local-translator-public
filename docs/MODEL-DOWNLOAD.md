# モデル取得と更新

v0.1.5では、初回セットアップがHTTP 403で止まる問題を修正しました。通常の翻訳は引き続きPC内で処理します。

## 原因と変更

v0.1.4まで固定していた旧モデルの取得URLは、Hugging Faceの旧CDNでAccessDenied（403）になりました。一方、同じPFN公式リポジトリの現行版は、新しい固定コミットから取得できます。配布先全体が利用不能だったという説明を訂正します。CDN内部で旧データが取得できない理由までは確認していません。

公式リポジトリでは2026年11月6日にGGUFとchat_template.jinjaが更新されています。取得できる版へ固定し直し、モデルとテンプレートの両方をSHA256で検証します。mainへ自動追従する取得や、非公式の重み・ミラー、TLS証明書の検証無効化は使いません。

| モデル | 固定コミット | 重みのバイト数 | 重みのSHA256 |
| --- | --- | ---: | --- |
| 2B | `232fbd7916519edecddfdae0beae7e76fe70453f` | 1,807,199,392 | `f36d0813dd95573a852ab5d76e374c543632d9e292929e922bcdbf7e53b494e0` |
| 8B | `2234f168757f570714b333049c9d018161ec5277` | 5,280,442,080 | `47a04e86a67bcc352fa186f01159060aae594b73993e1d49dbfc0ef0081d01ad` |

テンプレートは同じ固定コミットから取得します。両モデルのテンプレートのSHA256は `18dcc169548d794897084a04cd150a5a633717f1eb6e62de4a0e0973b377e02a` です。

途中ファイルもSHA256ごとに分け、旧版のダウンロード途中のデータを新版へ継ぎ足しません。検証が成功してから完成ファイルへ置き換えます。

## 初めて導入する場合

[セットアップ手順](SETUP.md)でv0.1.5を取得し、公式モデルを準備してください。通常は2B、8Bを追加したいときは `--models 8b` を指定します。

```bash
python3 scripts/setup_runtime.py --accept-model-license --models 2b
```

## すでにモデルを取得している場合

取得済みの旧2B・8Bも使えます。コードと拡張を更新するために、重みを取り直す必要はありません。旧モデルを使っているときの出力・キャッシュには、旧モデルの版とハッシュを使います。v0.1.5へ更新しても実行中の環境を自動で再起動しません。[更新の操作](NETWORK-SECURITY.md#既存環境の更新)

セットアップを改めて実行すると、選択したモデルを今回固定した版へ更新します。元のファイルは、新しいモデルのダウンロードとSHA256検証が成功するまで残します。原稿の一括処理は完了させてから、翻訳を停止して実行してください。中断中の原稿は更新前のモデルで処理を終えるか、更新後に新しい原稿として投入してください。原稿単位のモデル記録は作成時のものを保持するため、途中で重みを更新してから再開すると複数の版が混在します。

アプリの既存モデルの版判定はファイルサイズに基づきます。起動ごとに重み全体を再ハッシュする仕組みではありません。改変・破損の検査が必要な場合は、セットアップを実行してSHA256を確認してください。

## 検証

- 旧固定版2Bの403と、新固定版2B/8Bの206を実際の公式URLで比較：[HTTP確認](validation/model-download/http-probes.json)。これは先頭128バイトの確認です。
- Apple Siliconの隔離Mac CIでは、新2Bの全体ダウンロード・モデルとテンプレートのSHA256・CPU翻訳・停止を確認済み：[実モデル記録](validation/model-download/macos-arm64.json)。Intelでも新2B/8Bの全体取得とSHA256、CPU翻訳、2B→8Bの切り替え、停止を確認済み：[実モデル記録](validation/model-download/macos-intel.json)。[CI 42210069931](https://github.com/kami9811/plamo-local-translator-public/actions/runs/42210069931)は両CPUで成功。
- 模擬テストは、固定URL・SHA256、旧途中ファイルの分離、検証失敗時の既存モデル保護、テンプレート更新、旧モデルの出所とキャッシュの識別を確認します。実モデルの証拠とは分けます。
- 利用者のPCのAPIや推論プロセスは、この検証のために起動・停止していません。

実行コードは `c58ee9e0d0105b2fe1e22b12af2af831763d5526`。[結果のまとめと未検証範囲](validation/model-download/summary.json)を参照してください。GPU/MetalとApple Siliconの8Bは今回試していません。

## 公式資料

- [PFNの重み公開告知](https://www.preferred.jp/ja/blog/tech/plamo-3-translate-weight-release)
- [2Bの固定版](https://huggingface.co/pfnet/plamo-3-translate-2b-GGUF/tree/232fbd7916519edecddfdae0beae7e76fe70453f)
- [8Bの固定版](https://huggingface.co/pfnet/plamo-3-translate-8b-GGUF/tree/2234f168757f570714b333049c9d018161ec5277)
- [Hugging Faceの固定revisionによる取得](https://huggingface.co/docs/huggingface_hub/guides/download#from-specific-version)
