# セットアップ

Built with PLaMo。非公式ツールです。モデルの契約条件は[日本語](../licenses/PLaMo-Community-License-ja.txt)と[English](../licenses/PLaMo-Community-License-en.txt)。商用利用の登録・売上条件は別途確認してください。

## 対象

Linux x86_64 / WSL2 Ubuntu / Python 3.10以上。検証済みGPUはRTX 4090。Chrome 123以降。初回はネット接続と約20GB以上の空き容量を推奨。Pythonサーバーの実行依存は標準ライブラリのみです。

## 初回

```bash
python3 scripts/setup_runtime.py --accept-model-license
scripts/node.sh npm ci
scripts/node.sh npm run build
python3 scripts/start.py
```

同意フラグを省くとモデル取得前に停止します。モデルを取得せずランタイムだけ準備する場合は`--runtime-only`を使います。モデルは公式Hugging Faceの固定revisionとSHA256で取得します。

配布llama.cppがOSのglibcと非互換の場合は公式ソースをCUDAでビルドします。CMakeとC++コンパイラ、CUDA 12.6開発ツールを使う構成で確認しています。

```bash
# 必要な場合に自分の環境へ合わせて指定します。
PLAMO_CUDA_COMPILER=/path/to/cuda/bin/nvcc PLAMO_CUDA_ARCH=89 \
  python3 scripts/setup_runtime.py --accept-model-license
```

GPUアーキテクチャ89はRTX 4090向けです。別GPUへ変更した構成は未検証です。OSのglibcやセキュリティ設定を自動で置き換えません。

## Windowsから起動

ソースはWSL内の任意のディレクトリに置きます。Windows補助スクリプトには自分のLinux側チェックアウト先を指定します。

```bat
set "PLAMO_REPO=/absolute/linux/path/plamo-local-translator-public"
start-windows.cmd
```

`PLAMO_WSL_DISTRO`を設定した場合はそのディストリビューションを、未設定ならWSLの既定を使います。停止は同じ変数で`stop-windows.cmd`。固定のユーザー名やホームディレクトリを含めていません。

## 接続

既定はAPI `127.0.0.1:8765`、推論 `127.0.0.1:8766`。LANへ公開しません。Windows ChromeからWSLのlocalhost転送が使える環境が必要です。接続キーは`python3 scripts/start.py`で私的な端末に表示し、拡張の接続設定へ入力します。

既存のローカルサービスと並行してテストする場合はポートを分けます。

```bash
PLAMO_API_PORT=8875 PLAMO_INFERENCE_PORT=8876 python3 scripts/start.py
PLAMO_API_BASE=http://127.0.0.1:8875 scripts/node.sh npm run build
# テスト終了後、配布ビルドは既定の接続先へ戻します。
scripts/node.sh npm run build
```

APIのポートと拡張のビルド時接続先を一致させてください。`PLAMO_API_PORT`を変更した場合は停止時にも指定します。

## データ

`.data/state.sqlite3`に原稿・対訳・設定・キャッシュ、`.data/token`に接続キーを保存します。削除は設定画面から行えます。安全消去を保証する機能ではありません。モデルは`.runtime/`へ保存し、いずれも公開・Git管理しません。

## 問題が起きたら

- 未接続: APIの起動、ポート、接続キーを確認。
- 推論エラー: `.data/llama.log`を確認。
- 入力上限: 用語集や文脈を短くする。
- マーカー/数値の警告: 原文と照合する。独自TeXマクロは完全対応ではありません。
- キー未割り当て: `chrome://extensions/shortcuts`。
- Chrome内部画面、ストア、PDF、iframeは対象外。
