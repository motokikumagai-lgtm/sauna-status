# sui kawahigashi sauna - 空き状況自動更新システム

Chillnn の予約データから空き状況カレンダーを毎朝8時に自動生成し、STUDIO サイトに iframe で埋め込みます。

## 構成

```
GitHub Actions (毎朝 8:00 JST)
  → Playwright で Chillnn にログイン
  → CSV ダウンロード（チェックイン日: 当月初日 〜 翌月末日）
  → Python で集計・HTML生成
  → GitHub Pages にデプロイ
  → 失敗時メール通知
```

## ローカル実行

```bash
# 依存インストール
pip install -r requirements.txt
python -m playwright install chromium

# .env を設定（.env.example をコピーして編集）
cp .env.example .env

# パイプライン実行
python src/pipeline.py

# 既存CSVで再生成のみ
python src/pipeline.py --skip-download
```

## ディレクトリ

- `src/` - Python ソース
- `config/` - 営業カレンダー設定
- `output/` - 生成HTML
- `data/` - DL済CSV（gitignore）
- `.github/workflows/` - GitHub Actions

## STUDIO への埋め込み

GitHub Pages 公開後、以下のURLをSTUDIOの埋め込みブロックに設定：

```
https://motokikumagai-lgtm.github.io/sauna-status/
```
