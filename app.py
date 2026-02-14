
import os
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# 設定
# ---------------------------------------------------------------------------
def load_config():
    load_dotenv()
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        st.error("⚠️ .env ファイルに GEMINI_API_KEY が設定されていません。")
        st.stop()
    genai.configure(api_key=gemini_key)
    return genai.GenerativeModel("gemini-2.0-flash")

# ---------------------------------------------------------------------------
# 生成ロジック
# ---------------------------------------------------------------------------
def generate_review_reply(model, review_text, star_rating, tone, length):
    if length == "短め（2〜3文）":
        length_instruction = "各返信は2〜3文程度の短くコンパクトな文章にしてください。"
    else:
        length_instruction = "各返信は5〜8文程度のしっかりとした丁寧な文章にしてください。"

    prompt = f"""
あなたはGoogleマップの口コミに返信する【店舗オーナー】です。
以下のお客様からの口コミに対して、魅力的で誠実な返信文を作成してください。

【口コミ情報】
- 評価: {'★' * star_rating} ({star_rating}/5)
- 内容: {review_text}

【返信の方針】
- トーン: {tone}
- 文字数: {length_instruction}
- 感謝の意を示すこと
- （評価が低い場合）誠実な謝罪と改善提案を含めること
- （評価が高い場合）また来たくなるような言葉を含めること
- 日本語で、自然な文章で作成すること
- 同じ語尾（〜ます。〜ます。〜ます。）を3回以上連続させないこと
- 実際の店舗スタッフが書いたような生っぽい文体にすること
- 口コミの具体的な内容に触れて、テンプレート感を消すこと
- 指定されたトーンに合わせた3パターンの返信案を作成してください
- 各パターンは異なる切り口・表現で書き分けること（トーンは統一）
- 返信文の中では2〜3文ごとに必ず空行（改行2つ）を入れて段落を分けること。改行なしのベタ書きは禁止

【出力形式】
以下の形式で出力してください：

### A案（共感型）
(返信文)

### B案（行動型）
(返信文)

### C案（シンプル）
(返信文)
"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"エラーが発生しました: {e}"

# ---------------------------------------------------------------------------
# UI メイン
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="Googleマップ 口コミ返信AI", page_icon="�")
    
    st.title("💬 Googleマップ 口コミ返信生成AI")
    st.write("お客様からの口コミを入力すると、AIが最適な返信文を3パターン提案します。")
    
    model = load_config()

    # 入力エリア
    with st.form("review_form"):
        review_text = st.text_area("口コミをコピペ", height=150, placeholder="例：料理は美味しかったけど、提供が遅かったです。")
        col1, col2, col3 = st.columns(3)
        with col1:
            star_rating = st.slider("評価（星の数）", 1, 5, 3)
        with col2:
            tone = st.selectbox("返信のトーン", ["丁寧・誠実", "フレンドリー", "おわび重視"])
        with col3:
            length = st.selectbox("返信の長さ", ["短め（2〜3文）", "長め（5〜8文）"])
        
        submitted = st.form_submit_button("✏️ 返信を作成する")

    # 結果表示
    if submitted and review_text:
        with st.spinner("AIが返信を考えています..."):
            reply = generate_review_reply(model, review_text, star_rating, tone, length)
            st.markdown("---")
            st.subheader("📝 生成された返信案")
            st.markdown(reply)
            st.success("気に入った返信をコピーして使用してください！")
    elif submitted:
        st.warning("⚠️ 口コミ内容を入力してください。")

if __name__ == "__main__":
    main()
