# 画面画像の再生成

個人原稿を使用しない分離APIで実行する。既存の設定は終了時に復帰するが、翻訳キャッシュや実モデルの読み込みは発生する。

```bash
PLAMO_CAPTURE_URL=http://127.0.0.1:8765/ scripts/node.sh node scripts/capture_ui.mjs
```

ブラウザはPlaywrightのChromiumを使用する。PLAYWRIGHT_BROWSERS_PATHで取得済みブラウザを指定できる。画像と検証JSONはwork/ui-captureへ出力する。PLAMO_CAPTURE_OUTPUTで出力先を変更できる。

ライト/ダークを明示的に切り替え、DOMのテーマ・color-scheme・背景色を確認してからworkspace-light.pngとworkspace-dark.pngを撮影する。全4画面のaxe検査、390px幅のはみ出し、実フォント、短文と長文の入力欄の伸縮も確認する。撮影した画像は目視確認後にdocs/screenshotsへ反映する。
