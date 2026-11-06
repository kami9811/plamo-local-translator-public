# セットアップ

Built with PLaMo。非公式ツールです。モデルの契約条件は[日本語](../licenses/PLaMo-Community-License-ja.txt)と[English](../licenses/PLaMo-Community-License-en.txt)。商用利用の登録・売上条件は別途確認してください。

## 対象

Linux x86_64 / WSL2 Ubuntu / Python 3.10以上。検証済みGPUはRTX 4090。Chrome 123以降。初回はネット接続と約20GB以上の空き容量を推奨。Pythonサーバーの実行依存は標準ライブラリのみです。

Mac版は[Windows / Mac操作アプリの手順](DESKTOP.md#macの初回セットアップ)を参照してください。Apple SiliconとIntelに対応するセットアップを用意しています。

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

日常の起動・停止・キーのコピーには[Windowsコントローラー](DESKTOP.md)を使えます。最初にプロジェクトの場所を保存すれば、以降はボタン操作だけで使えます。以下は従来の補助スクリプトを使う方法です。

ソースはWSL内の任意のディレクトリに置きます。Windows補助スクリプトには自分のLinux側チェックアウト先を指定します。

```bat
set "PLAMO_REPO=/absolute/linux/path/plamo-local-translator-public"
start-windows.cmd
```

`PLAMO_WSL_DISTRO`を設定した場合はそのディストリビューションを、未設定ならWSLの既定を使います。停止は同じ変数で`stop-windows.cmd`。固定のユーザー名やホームディレクトリを含めていません。

<a id="chrome-extension"></a>

## Chrome拡張を追加する

### 1. 読み込むファイルを用意する

拡張には、ビルドしたファイルかリリースの拡張ZIPを使います。

| 用意する方法 | 必要な操作 |
| --- | --- |
| 自分でビルドした場合 | `scripts/node.sh npm run build` の後、プロジェクト直下の `dist` を開く。 |
| リリースのZIPを使う場合 | WindowsでZIPを右クリックし、「すべて展開」する。 |

ビルドした場合、ファイルは次の場所にあります。

```text
plamo-local-translator-public/
  scripts/
  extension/
  dist/                  ← ビルド済みの拡張
    manifest.json
    background.js
    content.js
    app.html
    ...
```

**Windows ChromeとWSLを使う場合**は、拡張のファイル一式をWindows側へコピーします。

1. ビルドを実行したWSLのターミナルで、次を実行します。

   ```bash
   explorer.exe .
   ```

2. Windowsのエクスプローラーでプロジェクトのフォルダーが開くので、その中の `dist` を開きます。
3. `dist` の中身をすべてコピーします。`manifest.json` だけでなく、JavaScript・CSS・フォント・ライセンスのフォルダーも一緒にコピーしてください。
4. Windowsの「ダウンロード」など、分かりやすい場所に `PLaMoLocalExtension` というフォルダーを作り、そこへ貼り付けます。

この例では、Chromeで読み込むのはWindows側の `PLaMoLocalExtension` です。ZIPを展開して使う場合も、`manifest.json` が直接入っているフォルダーを選びます。Linuxの `/home/...` というパスを、Windowsのフォルダー選択画面へそのまま入力する必要はありません。

### 2. Chromeへ追加する

1. Chromeで新しいタブを開き、アドレスバーに `chrome://extensions` と入力してEnterを押します。
2. 拡張機能の管理画面が開いたら、右上の「デベロッパーモード」をオンにします。
3. 「パッケージ化されていない拡張機能を読み込む」をクリックします。
4. フォルダー選択画面で、先ほど用意した `PLaMoLocalExtension` を選び、「フォルダーの選択」を押します。
5. 拡張一覧に「PLaMo Local」のカードが表示され、オンになっていることを確認します。

フォルダー選択画面では、`manifest.json` などのファイルが表示されないことがあります。選択するのはファイルを含むフォルダーです。エクスプローラーで、中に `manifest.json` があることを確認してください。ZIPの中を開いたままの状態や、ソースコード全体を指定すると読み込めません。

読み込んだフォルダーは、その後もChromeが使います。別の場所へ移動したり削除したりせず、そのまま置いてください。

<a id="pair-extension"></a>

## 拡張とローカルAPIを接続する

### 1. 接続キーをコピーする

Windows / Macコントローラーを使う場合は「起動」→「接続キーを表示」→「コピー」を押し、次の「Chrome拡張側の設定を開く」へ進んでください。以下はCLIでコピーする方法です。

モデルを実行する側のターミナルで、リポジトリのルートから次を実行します。

```bash
python3 scripts/start.py
```

起動すると、URLと接続キーが表示されます。

```text
PLaMo Local: http://127.0.0.1:8765/app.html
拡張の接続設定に貼り付けるキー（公開しないでください）: <接続キー>
```

コロン `:` より後ろに表示された実際の文字列だけをコピーします。上の `<接続キー>` は説明用の記号です。URLや「拡張の接続設定に貼り付けるキー」という見出しは入力しません。

### 2. Chrome拡張側の設定を開く

1. Chrome右上のパズルアイコン（拡張機能）をクリックします。
2. 一覧にある「PLaMo Local」をクリックします。横のピンを押すと、次回からツールバーに固定したアイコンで開けます。
3. 小さなメニューの「原稿・用語集・接続設定」ボタンをクリックします。
4. 新しいタブで開いた画面の、左メニュー「接続と設定」を選びます。未接続の場合は、最初からこの画面が開くこともあります。
5. アドレスバーが **`chrome-extension://` で始まっている**ことを確認します。

`http://127.0.0.1:8765/app.html` を直接開いた画面はブラウザ版です。ブラウザ版はローカルAPIへ自動接続するため、「接続済み」と表示されても拡張への登録が済んだことにはなりません。拡張の接続キーは、上の手順で開いた `chrome-extension://...` の画面から登録してください。

### 3. キーを登録して接続を確認する

1. 「ローカルエンジンとの接続」にある「接続キー」欄へ、コピーしたキーを貼り付けます。
2. 「接続する」をクリックします。
3. 画面上部に「接続済み · PC内で処理」、通知に「接続しました。」と表示されることを確認します。登録後に入力欄が空になるのは正常です。

これで拡張から翻訳できるようになります。通常のWebページを開き、英文を選択して右クリック →「PLaMoで選択文を翻訳」で試してください。初回の翻訳ではモデルの読み込みが発生する場合があります。

接続できない場合は、APIを起動したリポジトリと接続キーを表示したリポジトリが同じか、キーの前後に見出しや空白を含めていないかを確認します。既定の接続先は `http://127.0.0.1:8765` です。

## 拡張を更新したとき

再ビルドした場合は、Windows側へコピーした拡張ファイルも更新します。その後 `chrome://extensions` を開き、「PLaMo Local」のカードにある再読み込みボタンを押します。翻訳するWebページも再読み込みしてください。

参照: [Chrome公式の拡張読み込み手順](https://developer.chrome.com/docs/extensions/get-started/tutorial/hello-world#load-unpacked)、[Microsoft公式のWSLからエクスプローラーを開く方法](https://learn.microsoft.com/en-us/windows/wsl/filesystems#view-your-current-directory-in-windows-file-explorer)。

## 接続範囲とポート

既定はAPI `127.0.0.1:8765`、推論 `127.0.0.1:8766`。LANへ公開しません。Windows ChromeからWSLのlocalhost転送が使える環境が必要です。接続キーの登録は、上の「拡張とローカルAPIを接続する」の手順を参照してください。

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
