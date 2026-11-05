Built with PLaMo。出力の下訳はPLaMo 3 Translateによる生成物です。非公式ツールです。

# AgenticVibeへの引き渡し

接続APIの仕様はこのセッションと近隣リポジトリから確認できていません。自動送信は行わず、原稿画面の「レビュー用JSON」「レビュー用Markdown」でファイルを作成します。

1. 用語集・分野・文脈・翻訳方向・モデルを設定する。
2. 原稿を翻訳し、警告と未完了箇所を確認する。
3. MarkdownまたはJSONを出力する。
4. AgenticVibeの入力資料としてファイルを渡し、同梱のレビュー指示を使う。
5. 原文と下訳を照合した後、論理と英文を推敲する。修正は段落IDごとに確認する。

## JSON契約 v1.0

- `attribution`: 生成元・非公式表示・契約の日本語/英語全文。
- `schema_version`, `kind`, `id`, `title`, `format`, `status`
- `source_text`：投入した原稿全文。
- `source_language`, `target_language`
- `model`：モデルID、公式repository・revision・重みのハッシュ・実行エンジン・文脈上限。
- `settings`：翻訳方向、モデル、文体、分野、文脈、用語集。
- `glossary`
- `review_instructions`
- `segments[]`：`id`, `source`, `translation`, `separator`, `status`, `warnings`, 必要時`error`, `metrics`。

`segments[].source + separator` を順に連結すると原稿全文を復元できます。下訳だけを次工程へ渡さないでください。未完了の出力には未完了状態が残ります。

Markdownでは原文と下訳をインデントしたテキストとして出力します。原稿内にコードフェンスやHTMLがあっても、出力テンプレートの境界として解釈しません。

## レビューフロー

1. 意味：訳抜け、否定、条件、主張の強さ、数値・単位、数式、引用。
2. 論理：段落のつながり、指示対象、用語の統一。研究内容の不明点は質問として残す。
3. 英文：分野の用法、簡潔さ、読みやすさ。変更内容と理由を段落IDごとに示す。

出力には原稿そのものが含まれるので、外部のAgentへ渡すかどうかは利用者が判断できます。このツールは外部のAgentを起動・課金・呼び出しません。
