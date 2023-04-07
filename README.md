# XBRL for Qiita
XBRLをBeautifulSoupで解析するコード

## 使い方

### 前提

- GitからこのリポジトリをCloneしていること（特に`taxonomy_global_label.tsv`が必要です）
- EDINETまたTDNetから、XBRLデータをダウンロードし、ダウンロードしたzipファイルが解凍済みであること
- 必要なライブラリをインストールしていること（必要なライブラリはpythonコードをご確認ください）

### 設定

1. 解凍済みのXBRLデータのパスを記載する

   ![image](https://user-images.githubusercontent.com/50011756/230587366-1bfdab55-7efd-4706-9b67-26c8dd1b6283.png)

1. Cloneしたパスを記載する（↓ の `****` を埋めて `taxonomy_global_label.tsv` の場所を指定してください）

   ![image](https://user-images.githubusercontent.com/50011756/230587623-8f51fc1d-787a-402d-94d3-79f4178b8ccb.png)

### 実行

- `get_df_fs()` を実行

   ![image](https://user-images.githubusercontent.com/50011756/230587874-7753d7bd-8bb6-42cc-8aef-4de0db868718.png)
