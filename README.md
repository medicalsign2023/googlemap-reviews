# 💬 Googleマップ 口コミ返信生成AI

お客様からのGoogleマップ口コミを入力すると、AIが最適な返信文を3パターン提案するWebアプリです。

## 機能
- 口コミ内容と星評価を入力
- トーン選択（丁寧・フレンドリー・謝罪重視）
- 返信の長さ選択（短め・長め）
- 3パターンの返信案を生成

## セットアップ

### 必要なもの
- Python 3.9+
- Gemini API Key（[Google AI Studio](https://aistudio.google.com/) で取得）

### ローカル実行
```bash
pip install -r requirements.txt
cp .env.example .env
# .env に GEMINI_API_KEY を設定
streamlit run app.py
```
