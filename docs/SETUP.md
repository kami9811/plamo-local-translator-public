# セットアップ

Built with PLaMo。非公式ツールです。モデルの契約条件は[日本語](../licenses/PLaMo-Community-License-ja.txt)と[English](../licenses/PLaMo-Community-License-en.txt)。商用利用の登録・売上条件は別途確認してください。

## 導入の流れ

**PC内の翻訳環境を準備 → Chromeに拡張を追加 → 翻訳環境を起動 → 接続キーを拡張へ登録 → 翻訳**の順に進めます。初回のモデル取得やビルドにはターミナルを使います。準備後の日常的な起動・停止には、ボタンで操作する補助アプリも使えます。

Chrome 123以降、Python 3.10以上、Gitが必要です。初回はインターネット接続と、2B・8Bの両方を用意する場合で20GB程度以上の空き容量を推奨します。Pythonサーバーの実行依存は標準ライブラリのみです。

コマンドの途中でエラーが出たら、そこで止めて原因を確認してください。次の段階へ進む目印は、各手順の末尾に記載しています。

モデルとテンプレートは公式リポジトリの固定コミットから取得し、SHA256を確認します。[取得版と既存モデルの扱い](MODEL-DOWNLOAD.md)

<a id="windows-linux"></a>

## 1-A. Windows（WSL2）・Linuxで翻訳環境を準備する

WindowsではWSL2のUbuntuを使います。WSL2が未導入の場合は、先に[Microsoftの導入手順](https://learn.microsoft.com/ja-jp/windows/wsl/install)で用意してください。以降のコマンドは、WindowsのPowerShellではなく、**使うUbuntuのターミナル**で実行します。Linuxではそのままターミナルを使います。

この構成はLinux x86_64 / WSL2 Ubuntu向けで、RTX 4090 / CUDA 12.6で検証しています。他のGPUやLinuxのCPUのみの構成は未検証です。

まず `python3 --version` と `git --version` を実行し、Python 3.10以上とGitが使えることを確認します。Ubuntuでコマンドが見つからない場合は、`sudo apt update` の後に `sudo apt install python3 git` で用意します。

ソースコードを置きたい場所で次を実行します。保存場所に迷う場合は、先に `cd ~` で自分のホームフォルダーへ移動してください。配布物と同じv0.1.5を取得する例です。すでにこのプロジェクトを取得している場合は重ねてcloneせず、そのフォルダーで作業してください。

```bash
git clone --branch v0.1.5 https://github.com/kami9811/plamo-local-translator-public.git
cd plamo-local-translator-public

# licenses/の条件に同意する場合。通常使う2Bを先に取得します。
python3 scripts/setup_runtime.py --accept-model-license --models 2b &&
  scripts/node.sh npm ci &&
  scripts/node.sh npm run build
```

同意フラグを省くとモデル取得前に停止します。8Bも一緒に用意する場合は `--models all`、後から8Bを追加する場合は `--models 8b` を指定します。重みは2B約1.8GB、8B約5.3GBです。公式Hugging Faceの固定revisionとSHA256で取得します。モデルなしでランタイムだけ準備する場合は `--runtime-only` を使います。

配布llama.cppがOSのglibcと非互換の場合は公式ソースをCUDAでビルドします。その場合はCMake、C++コンパイラ、CUDA開発ツールが必要です。CUDA 12.6で確認しています。

```bash
# CUDAのソースビルドが必要な場合だけ、自分の環境に合わせて指定します。
PLAMO_CUDA_COMPILER=/path/to/cuda/bin/nvcc PLAMO_CUDA_ARCH=89 \
  python3 scripts/setup_runtime.py --accept-model-license --models 2b
```

GPUアーキテクチャ89はRTX 4090向けです。OSのglibcやセキュリティ設定を自動で置き換えません。

`Built unpacked Chrome extension in dist/` と表示されたら準備完了です。このプロジェクトのフォルダーの場所を控え、[2. Chrome拡張を追加する](#chrome-extension)へ進みます。後で起動・停止用アプリにも同じフォルダーを指定します。

<a id="mac"></a>

## 1-B. Macで翻訳環境を準備する

macOS 12以上のApple Silicon / Intel向けです。Python 3.10以上を[python.org](https://www.python.org/downloads/macos/)またはHomebrewでインストールしてください。起動・停止用アプリは `/opt/homebrew/bin/python3`、`/usr/local/bin/python3`、python.orgのCurrentを探します。OS付属の開発ツール用Pythonは使いません。

ターミナルで `python3 --version` と `git --version` を実行して、Python 3.10以上とGitが使えることを確認します。Gitが未導入の場合は、`git --version` をきっかけに表示されるCommand Line Toolsのインストール案内を完了してください。

ソースコードを置きたい場所で次を実行します。保存場所に迷う場合は、先に `cd ~` で自分のホームフォルダーへ移動してください。すでにこのプロジェクトを取得している場合は重ねてcloneせず、そのフォルダーで作業してください。

```bash
git clone --branch v0.1.5 https://github.com/kami9811/plamo-local-translator-public.git
cd plamo-local-translator-public

# licenses/の条件に同意する場合。通常使う2Bを先に取得します。
python3 scripts/setup_runtime.py --accept-model-license --models 2b &&
  scripts/node.sh npm ci &&
  scripts/node.sh npm run build
```

8Bも一緒に使う場合は `--models all`、後から追加する場合は `--models 8b` を指定します。重みは2B約1.8GB、8B約5.3GBです。8Bはメモリーに余裕のあるMac向けです。

セットアップはCPU種別を検出し、SHA256を確認した公式llama.cpp配布物とモデルを取得します。通常のMac推論はMetalを有効にする設定です。CPUでの実モデル検証と、起動・通信境界の検証は分けて記録しています。MetalとApple Siliconでの8Bは未検証です。[起動・通信の検証範囲](DESKTOP-VALIDATION.md)・[モデル取得と翻訳の再検証](MODEL-DOWNLOAD.md)

`Built unpacked Chrome extension in dist/` と表示されたら準備完了です。[2. Chrome拡張を追加する](#chrome-extension)へ進みます。

<a id="chrome-extension"></a>

## 2. Chrome拡張を追加する

### 1. 読み込むファイルを用意する

上の手順でビルドした場合は、その `dist` を使います。配布済みファイルを使う場合は、[v0.1.5のリリース](https://github.com/kami9811/plamo-local-translator-public/releases/tag/v0.1.5)の「Assets」から `plamo-local-translator-extension-0.1.5.zip` をダウンロードして展開します。

| 用意する方法 | 必要な操作 |
| --- | --- |
| 自分でビルドした場合 | `scripts/node.sh npm run build` の後、プロジェクト直下の `dist` を開く。 |
| リリースのZIPを使う場合 | ZIPを展開する。Windowsでは右クリック→「すべて展開」。 |

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
4. フォルダー選択画面で、`manifest.json` が直接入るフォルダーを選びます。Windowsで上記のコピーをした場合は `PLaMoLocalExtension`、Mac / Linuxでビルドした場合はプロジェクトの `dist` です。選択を確定してください。
5. 拡張一覧に「PLaMo Local」のカードが表示され、オンになっていることを確認します。

フォルダー選択画面では、`manifest.json` などのファイルが表示されないことがあります。選択するのはファイルを含むフォルダーです。エクスプローラーやFinderで、中に `manifest.json` があることを確認してください。ZIPの中を開いたままの状態や、ソースコード全体を指定すると読み込めません。

読み込んだフォルダーは、その後もChromeが使います。別の場所へ移動したり削除したりせず、そのまま置いてください。拡張が一覧に表示されたら、[3. 起動して拡張へ接続する](#pair-extension)へ進みます。

<a id="pair-extension"></a>

## 3. 起動して拡張へ接続する

### 1. 翻訳環境を起動し、接続キーをコピーする

接続キーは、Chrome拡張を自分のPC内の翻訳環境へ接続するために使います。公開したり、他のWebサイトへ貼り付けたりしないでください。

Windows / Macでは、準備済みの翻訳環境をボタンで操作する**起動・停止用アプリ**を使えます。[ダウンロードと実行先の設定](DESKTOP.md)を済ませ、「起動」→「接続キーを表示」→「コピー」を押してください。その後、次の「Chrome拡張側の設定を開く」へ進みます。

アプリを使わず、ターミナルから起動する場合は次の操作をします。

初回準備に使ったUbuntu / Mac / Linuxのターミナルを開きます。`scripts` と `runtime-manifest.json` が直接入るプロジェクトのフォルダーへ移動し、次を実行します。ホームフォルダーに取得した例では、`cd ~/plamo-local-translator-public` で移動できます。

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

`http://127.0.0.1:8765/app.html` を直接開いた画面はブラウザー版で、v0.1.5ではこちらにも接続キーの入力が必要です。ブラウザー版とChrome拡張の登録は別です。拡張を使うためのキーは、上の手順で開いた `chrome-extension://...` の画面へ登録してください。

### 3. キーを登録して接続を確認する

1. 「ローカルエンジンとの接続」にある「接続キー」欄へ、コピーしたキーを貼り付けます。
2. 「接続する」をクリックします。
3. 画面上部に「接続済み · PC内で処理」、通知に「接続しました。」と表示されることを確認します。登録後に入力欄が空になるのは正常です。

これで拡張から翻訳できるようになります。通常のWebページを開き、英文を選択して右クリック →「PLaMoで選択文を翻訳」で試してください。初回の翻訳ではモデルの読み込みが発生する場合があります。

接続できない場合は、起動したプロジェクトと接続キーを表示したプロジェクトが同じか、キーの前後に見出しや空白を含めていないかを確認します。既定の接続先は `http://127.0.0.1:8765` です。

## 4. 使い終わったら停止する

起動・停止用アプリの「停止」を押します。アプリのウィンドウを閉じるだけでは停止しません。ターミナルから止める場合は、起動に使ったプロジェクトで次を実行します。

```bash
python3 scripts/stop.py
```

次回は起動して、そのまま拡張を使えます。同じ接続キーを使う間は、毎回の再登録は不要です。最初の翻訳ではモデルを読み込みます。

## Windowsの補助スクリプトを使う場合

起動・停止用アプリのほかに、Windowsのコマンドプロンプトから使う補助スクリプトもあります。`PLAMO_REPO` には、初回準備をしたLinux側のプロジェクトの場所を指定します。

```bat
set "PLAMO_REPO=/absolute/linux/path/plamo-local-translator-public"
start-windows.cmd
```

`PLAMO_WSL_DISTRO` を設定した場合はそのディストリビューションを、未設定ならWSLの既定を使います。停止は同じ変数で `stop-windows.cmd` を実行します。

## 拡張を更新したとき

再ビルドした場合は、Windows側へコピーした拡張ファイルも更新します。その後 `chrome://extensions` を開き、「PLaMo Local」のカードにある再読み込みボタンを押します。翻訳するWebページも再読み込みしてください。

参照: [Chrome公式の拡張読み込み手順](https://developer.chrome.com/docs/extensions/get-started/tutorial/hello-world#load-unpacked)、[Microsoft公式のWSLからエクスプローラーを開く方法](https://learn.microsoft.com/en-us/windows/wsl/filesystems#view-your-current-directory-in-windows-file-explorer)。

## 接続範囲とポート

既定はAPI `127.0.0.1:8765`、推論 `127.0.0.1:8766`。LANへ公開しません。Windows ChromeからWSLのlocalhost転送が使える環境が必要です。接続キーの登録は、上の[起動して拡張へ接続する](#pair-extension)を参照してください。

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
