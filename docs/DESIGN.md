# デザイン方針

## 一つのUIとしての優先順位

Material 3 Expressiveの色・形・文字の階層・主要操作の強調を視覚表現の基礎とし、Carbonの情報整理・比較・表・進捗・通知・操作の予測可能性を参考にしています。両システムへの完全準拠や認証を主張するものではありません。

- 低彩度の背景と、主要操作に限定した緑系のアクセント。
- 24pxの画面コンテナ、12pxの入力、ピル状の主要ボタン。形の役割を固定。
- 通常の翻訳は原文と訳文を左右に配置。狭い画面では縦に配置。
- 原稿は一覧と段落ごとの対訳。処理状態と確認事項を該当箇所に表示。
- 用語集は編集可能な表。設定は名前を付けて再利用。
- 接続、モデルの実状態、翻訳要求に使う設定を区別。

## 実装

独立したUIライブラリを二重導入せず、標準HTML、TypeScript、共通CSSトークンで実装。`extension/public/tokens.css` に共通の色・文字・角丸などを集約し、原稿画面と吹き出しの両方で利用します。`styles.css` は画面部品とレイアウトを担当します。拡張の吹き出しはShadow DOMと構築済みスタイルシートで分離し、閲覧先のCSSや厳しいCSPと干渉しにくくしています。

ライト・ダーク・システム連動を提供します。動きは操作の状態変化に限定。`prefers-reduced-motion` に従い、画面切替で本文を薄くするアニメーションは採用しません。

## アクセシビリティ

- ネイティブのbutton、label、select、textarea、table、progressを使う。
- 読み上げ可能なラベル、状態通知、スキップリンク、フォーカス表示。
- 操作対象は原則44px以上。色以外にも文言で状態を示す。
- 吹き出しを開くと閉じるボタンへフォーカス。Escapeで閉じ、元のフォーカスへ戻す。
- WCAG 2.2 AAを目標にaxeとキーボード操作を検証。

自動検査の成功は、全WCAG項目の手動適合確認やスクリーンリーダー全組み合わせの保証を意味しません。結果と範囲はVALIDATION.mdに記載します。

## 参照した公式資料

- Google Design: https://design.google/library/expressive-material-design-google-research
- Material Design 3: https://m3.material.io/
- Carbon Accessibility: https://www.carbondesignsystem.com/building-blocks/foundations/accessibility/overview
- Chrome extension network requests: https://developer.chrome.com/docs/extensions/develop/concepts/network-requests
