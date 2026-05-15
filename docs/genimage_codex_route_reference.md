---
source: https://note.com/mauekusa/n/nf373aedc8664
title: Claude Code から Codex 経由で gpt-image-2 で画像を作る（ChatGPT サブスク内で完結）
author: Manabu Uekusa
published: 2026-04-23
tags: [画像, ClaudeCode, Codex, image2]
fetched: 2026-05-15
purpose: gen-image スキルの中身を将来入れ替える際の参考資料 (Codex 経由ルートの記録)
---

# Claude Code から Codex 経由で gpt-image-2 で画像を作る（ChatGPT サブスク内で完結）

**著者:** Manabu Uekusa
**公開日:** 2026年4月23日 19:11
**タグ:** #画像 #ClaudeCode #Codex #image2

今週、gpt-image-2がリリースされて、GPT-5.5もリリースされたので、Codexで画像生成が良さそうな感じになってきました！Claude CodeからもCodex経由でimage-2の画像が月額課金で利用できるようになりました〜
めっちゃ便利になったので、Claude Codeに記事化してもらましたｗ みなさんの参考になればと〜

## はじめに

コーディング中に「ちょっと画像が欲しい」と思うこと、ありませんか？
READMEに貼るキャラクター、資料のイメージ、テストデータの画像など、用途は日常にあふれています。

画像生成 API を叩けば解決するのですが、画像1枚ごとに従量課金が積み上がると地味に痛い。そこで今回は、Claude Code のシェルから Codex CLI 経由で gpt-image-2 を呼び、ChatGPT Plus / Pro サブスクの範囲内で画像を生成する方法を紹介します。API キーは一切不要です。

キーになるのは Codex CLI の組み込み image_gen ツール。Claude Code から Codex にバトンを渡すと、Codex が自分自身の組み込みツールで画像を作ってくれます。

## この方法のメリット

- ✅ ChatGPT サブスクの範囲内で完結（追加課金ゼロ）
- ✅ API キー不要
- ✅ gpt-image-2 の高品質な出力
- ✅ 自然言語のプロンプトでそのまま指示可能（style / composition / lighting などの補助フィールドあり）
- ✅ Claude Code の通常ワークフローに自然に組み込める

## 前提条件

| 項目 | 内容 |
| :--- | :--- |
| Claude Code | インストール済み |
| Codex CLI | インストール済み（公式案内を参照） |
| ChatGPT サブスク | Plus / Pro / Team いずれかに加入 |
| Codex 認証 | codex login で ChatGPT OAuth 済み |

**動作確認:**

```bash
codex --version
codex login status # 期待: "Logged in using ChatGPT"
codex features list | grep image_generation # 期待: image_generation stable true
```

`codex features list` で `image_generation` が `stable true` になっていれば準備 OK です。

## 手順

### Step 1: Claude Code を起動

作業したいディレクトリで Claude Code を立ち上げます。

```bash
cd /path/to/your-project
claude
```

### Step 2: Claude に画像生成を依頼

Claude に対して、Codex 経由で画像を作ってほしい旨を自然言語で指示します。

例: 「Codex の組み込み image_gen ツール（gpt-image-2）を使って、雪山に佇むシベリアンハスキーの画像を作って、./docs/images/husky.png に保存してください。API キーやスクリプトは書かず、Codex のネイティブツールで直接生成するようにお願いします。」

ポイントは 「API キーやスクリプトは書かず、組み込みの image_gen ツールを直接使って」と明記すること。これを言わないと、Codex は律儀に Node.js や Python のスクリプトを書いて外部 API を叩くルートを選んでしまい、そちらは API 従量課金になります（後述）。

### Step 3: Claude が裏で実行するコマンド（参考）

Claude は内部で以下のようなコマンドを実行します（自分で打つ必要はありません）。

```bash
codex exec --dangerously-bypass-approvals-and-sandbox --cd "$PWD" "Codex 組み込みの image_gen ツール（gpt-image-2）を直接呼んで画像を1枚作ってください。API キーも Python/Node スクリプトも不要です。 プロンプト: 'A majestic Siberian Husky with piercing blue eyes, thick fluffy coat, standing in fresh snow, photorealistic, cinematic lighting' サイズ: 1024x1024 保存先: ./docs/images/husky.png"
```

**重要な2つのフラグ:**

- `--dangerously-bypass-approvals-and-sandbox` — これを付けないと Codex のデフォルトサンドボックスがネットワークをブロックして `Could not resolve host: api.openai.com` エラーになります
- `--cd` — 作業ディレクトリを明示

### Step 4: 出力確認

Codex は生成画像をまず `~/.codex/generated_images/<session-id>/ig_*.png` に保存し、その後指定パスにコピーします。

```bash
file ./docs/images/husky.png # 期待: PNG image data, 1024 x 1024, 8-bit/color RGB, non-interlaced
```

## 本当にサブスク内で済んでいるか確認する

「API 経由になってない？」と不安になったら、Codex の認証モードを確認します。

```bash
grep auth_mode ~/.codex/auth.json
```

- `"auth_mode": "chatgpt"` → ChatGPT OAuth 経由、サブスクのクォータ内
- `"auth_mode": "api_key"` → API キー経由、API 従量課金

chatgpt なら、codex exec 経由で呼ばれた組み込み image_gen ツールは ChatGPT サブスクのインフラで実行されているので追加課金はありません。

## 2つのルートの使い分け

実は画像生成には 2 つの経路があり、課金先が違います。

- **ルート A: Codex 組み込み image_gen（今回紹介した方法）**
  - codex exec → Codex エージェントが組み込みツールを直接呼ぶ
  - 認証: `~/.codex/auth.json` の ChatGPT OAuth
  - 課金: ChatGPT サブスクのクォータ内（追加課金なし）
- **ルート B: Python CLI を直接叩く**
  - `~/.codex/skills/.system/imagegen/scripts/image_gen.py` をシェルから直接実行
  - 要件: 環境変数 `OPENAI_API_KEY`, Python, openai パッケージ
  - 課金: OpenAI API 従量（画像1枚あたり数セント〜数十セント）

自動化スクリプトに組み込みたい時、複数プロジェクトで大量生成したい時、透過背景が必要な時はルート B を使います。

## gpt-image-2 の制約（ハマりポイント）

- **サイズの制約**
  - 辺は 16 の倍数
  - 最大辺長 3840px
  - アスペクト比 3:1 以下
  - 総ピクセル数 655,360〜8,294,400
  - 既知の OK サイズ: 1024x1024, 1536x1024, 1024x1536, 2048x2048, 2048x1152, 3840x2160
- **透過背景は非対応**
  - gpt-image-2 では `--background transparent` がエラーになります。透過 PNG が必要な場合は gpt-image-1.5 にフォールバックしてください（こちらはルート B、API 課金）。

## プロジェクトにルール化する（CLAUDE.md への追加例）

継続的にこの方法を使うなら、プロジェクトの CLAUDE.md に使い分けルールを書いておくと、次のセッションでも Claude が迷わず動けます。

```markdown
## 🎨 画像生成ツールの使い分け
画像を生成する時は用途に応じて以下から選択する。

### `gpt-image-2`（Codex 経由）
高品質・フォトリアル・キャラクター確定稿・テキスト入り画像に使う。
- **ルートA（サブスク内）**: `codex exec --dangerously-bypass-approvals-and-sandbox --cd <dir>` で Codex 組み込み `image_gen` ツールを呼ばせる。プロンプトに 「API キーやスクリプトは書かないで、組み込みの image_gen ツールを直接使って」と明記する
- **ルートB（API 課金）**: `~/.codex/skills/.system/imagegen/scripts/image_gen.py` を直接叩く
- **制約**: 透過背景は非対応 → 必要なら `gpt-image-1.5` に切替。辺は16の倍数、最大3840px

### 軽量画像生成（例: Nano Banana 系など他 MCP）
軽量な草案・アイコン、既存画像の編集・合成、大量試作に使う。

### 判断の目安
| 用途 | 推奨 |
|------|------|
| 写真調の高品質シーン・人物・動物 | gpt-image-2 |
| テキスト/ロゴを含む画像 | gpt-image-2 |
| キャラクター確定稿 | gpt-image-2 |
| UI アイコン・軽量イラスト | 軽量ツール |
| 既存画像の編集・合成 | 軽量ツール |
| 透過背景が必要 | `gpt-image-1.5`（ルートB）または軽量ツール |

- 保存先: `docs/images/` 配下、命名は `<topic>-v<N>.png`
```

このルールを置いておくと、次に「画像作って」と頼んだ時、Claude が自動的に適切なルートを選んでくれます。

## トラブルシューティング

- **❌ fetch failed / Could not resolve host: api.openai.com**
  - → `codex exec --full-auto` を使っていませんか？ デフォルトサンドボックスがネットワークをブロックします。 `--dangerously-bypass-approvals-and-sandbox` に変更してください。
- **❌ Codex が Node.js/Python スクリプトを書き出す**
  - → プロンプトが曖昧です。「API キーやスクリプトは不要、組み込みの image_gen ツールを直接使って」と明記してください。「OpenAI Images API を叩いて」などと書くと、律儀にスクリプトを書いて API ルートを選びます（= 従量課金）。
- **❌ 透過背景が欲しい**
  - → gpt-image-2 は非対応。ルート B で `--model gpt-image-1.5 --background transparent` を使います。
- **❌ サブスク内で済んでるか確証が欲しい**
  - → `grep auth_mode ~/.codex/auth.json` で "chatgpt" なら OAuth 経由（サブスク）、"api_key" なら API 経由（従量）。

## まとめ

- Claude Code から codex exec で Codex にバトン → Codex の組み込み image_gen を呼ばせる → ChatGPT サブスク内で gpt-image-2 画像生成が完結
- API キー不要、追加課金なし
- プロンプトで「組み込みツールを直接使って」と明記するのが肝
- `--dangerously-bypass-approvals-and-sandbox` を忘れない
- CLAUDE.md に使い分けを書いておくと長く使える

開発の流れを止めずに高品質な画像が手に入ります。README のイメージ画像、スライドの挿絵、テストデータなど、気軽に使ってみてください。

## 補足: なぜこの構成になるのか

Claude Code 自身は画像生成ツールを持っていません。一方で Codex Desktop / CLI には組み込みの画像生成ツールがあり、これは ChatGPT の認証で動きます。

Claude Code は他の CLI ツールをシェル経由で呼び出せるので、「Claude Code ⇒ codex exec ⇒ Codex エージェント ⇒ 組み込み image_gen」というバトンリレーを組むことで、Claude Code のワークフローに画像生成を統合できます。

MCP サーバーで画像生成ツールを自作する手もありますが、既に手元に ChatGPT 有料プランがあるなら、この方法が一番手軽で追加コストもかかりません。

## さいごに

自分で設定しても良いけど、実は、Claude CodeとCodexに頼みながら方法模索しても、同じ事ができます＾＾
Codexでgpt-image-2 で画像の作り方をテキストでまとめてもらって、Claude Codeに引き継いで画像生成のルール化しました。そっちの方が、みなさんも環境に合わせてできるから楽かも

ちなみに、記事の挿絵画像も gpt-image-2 で作ってもらってます
少しでも参考になれば「スキ」とかしてもらえると嬉しいです！
