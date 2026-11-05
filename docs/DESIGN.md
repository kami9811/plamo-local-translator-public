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


## 2026-11-05: 日本語の文字組みと配置の見直し

未導入のフォントに依存して日本語が意図しない書体へ落ちていたため、Noto Sans JPの可変WOFF2を同梱しました。初回セットアップ後はフォントにも外部通信を行いません。原文・訳文・入力・吹き出しまで同じ書体を使い、日本語への負の字間指定を撤去しています。本文は400、ラベルは500、見出しは600を基本とし、見出し26px、本文15〜16px、補助情報11〜13pxに役割を整理しました。フォントはOFLの別ライセンスです。

画面先頭を機能名と短い説明に統一し、その下に翻訳設定、本文、操作を配置しました。大きな宣伝的コピーと装飾的な英字ラベルを取り除き、原文と訳文の見出し・本文・下端の操作をそろえています。原稿は段落対訳の幅を優先し、処理状況に不要な中断・再開操作は隠し、削除は「その他」へ移動しました。プロジェクトの読込と保存は別の行に分けています。

Carbonのproductive typographyの考え方を参照し、M3の主操作・状態の強調はアクセント色と限定した丸みに残しています。準拠認証を主張するものではありません。

参照: https://www.carbondesignsystem.com/building-blocks/foundations/typography/overview
フォントの取得元・変換条件・ハッシュ: `licenses/fonts/provenance.json`。


## 2026-11-05: 画像の取り違えと対訳画面の再修正

v0.1.2の紹介画像workspace-light.pngには、撮影開始時の保存テーマがダークであったため誤った画面が入っていた。フォント確認・axe成功だけでは画像とテーマの一致を保証できていなかった。撮影をscripts/capture_ui.mjsへ移し、名前・htmlのテーマ属性・color-scheme・実際の背景色を照合してから撮影する。

本文を18px、ナビゲーション・主要操作を14pxへ変更し、短文の入力欄は180pxから内容に応じて最大480pxまで伸ばす。左右のカードを一つの対訳領域にまとめ、共通の区切り・見出し・本文・操作の位置を使う。処理が終わった後のキャンセルは隠す。原稿の対訳は16pxへ上げる。
