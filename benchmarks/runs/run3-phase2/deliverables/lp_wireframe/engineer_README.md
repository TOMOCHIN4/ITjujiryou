# かたおか歯科クリニック 採用 LP ワイヤー初稿 v1

- case-id: 2026-05-13-kataoka-dental
- subtask-id: 02de47e4-87fc-40f5-b480-f815ef3d05b4
- 納期: ワイヤー初稿 6/15 (本納品はそれより前倒し)
- 実装本体: Phase 4 (2026-07-01 〜)

## 納品ファイル

| ファイル | 内容 |
|---|---|
| `lp_wireframe_v1.pdf` | ワイヤーフレーム本体 (PDF)。スマホ縦長 1 カラムの全 8 セクション + 注釈付き |
| `lp_wireframe_v1.png` | 上記の PNG プレビュー版 (チャット共有用) |
| `lp_wireframe_v1.html` | ワイヤーの元 HTML (ブラウザで開けば操作可能、修正もこのファイルで) |
| `lp_section_spec_v1.md` | 各セクションの想定内容 / CTA 配置 / 計測タグ位置 / フォーム項目 / Phase 4 申し送り |
| `README.md` | このファイル |

## 確認してほしいポイント (ユウコさんへ)

1. **訴求軸 ⓐ〜ⓓ の表示順位がスクロール順に正しく反映されているか** (ヒーロー直下に軸 ⓐ を置いた構成)
2. **応募 CTA 配置**: ヒーロー直下 + ページ末尾 + Sticky 追従バー の 3 箇所提案
3. **応募フォーム項目**: 6 項目 (氏名/フリガナ/所属/電話/メール/自由記述)。住所・生年月日・性別は意図的に取得しない
4. **所属欄に「徳島大学 歯学部 口腔保健科」プリセット候補**: 採否判断を仰ぎたい
5. **計測タグ (GA4)**: 実 ID は院長確認後で問題ないか
6. **Sticky 追従 CTA バー**: 採用推奨だが、トシのデザイン方針との衝突がないか

## 次工程

- 6/1 目処に writer (ハオウ) と designer (トシ) へ consult_peer で擦り合わせ予定
- 6/15 までに本ワイヤーを v2 へリビジョン可能 (院長レビュー反映)
- Phase 4 (7 月) で HTML/CSS/JS 実装着手

## 使い方

- PDF は単独で配布可能 (院長レビュー用)
- HTML はブラウザ (Chrome / Safari) で開くとそのまま閲覧可能。修正はこの HTML を編集して再度 Chrome ヘッドレスで PDF/PNG 出力する想定
- 仕様 MD は Phase 4 実装着手時の仕様書として再利用する

## PDF/PNG の再生成方法 (内部メモ)

```sh
cd outputs/<subtask-id>/
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu \
  --print-to-pdf=lp_wireframe_v1.pdf \
  --print-to-pdf-no-header \
  file://$(pwd)/lp_wireframe_v1.html

"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --window-size=1280,2400 \
  --screenshot=lp_wireframe_v1.png \
  file://$(pwd)/lp_wireframe_v1.html
```
