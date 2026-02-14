
import os
import re
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
# 星評価を自動推定
# ---------------------------------------------------------------------------
def estimate_star_rating(model, review_text):
    prompt = f"""以下の口コミの感情を分析し、星評価（1〜5）を数字1つだけで回答してください。
他の文字は一切出力しないでください。

口コミ: {review_text}"""
    try:
        response = model.generate_content(prompt)
        rating = int(re.search(r'[1-5]', response.text).group())
        return rating
    except Exception:
        return 3  # デフォルト

# ---------------------------------------------------------------------------
# 返信生成ロジック
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
- 個人名（お客様名・スタッフ名）は絶対に書かないこと。「スタッフ」「担当者」などの一般名称を使うこと
- 指定されたトーンに合わせた3パターンの返信案を作成してください
- 各パターンは異なる切り口・表現で書き分けること（トーンは統一）
- 返信文の中では2〜3文ごとに必ず空行（改行2つ）を入れて段落を分けること。改行なしのベタ書きは禁止

【出力形式】
以下の形式で出力してください。各案の間には必ず空行を入れてください：

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
# 返信テキストを案ごとに分割
# ---------------------------------------------------------------------------
def parse_reply_sections(reply_text):
    pattern = r'###\s*(A案[^\n]*)\n(.*?)(?=###\s*[BC]案|$)'
    pattern_b = r'###\s*(B案[^\n]*)\n(.*?)(?=###\s*C案|$)'
    pattern_c = r'###\s*(C案[^\n]*)\n(.*?)$'

    sections = []
    for p in [pattern, pattern_b, pattern_c]:
        match = re.search(p, reply_text, re.DOTALL)
        if match:
            title = match.group(1).strip()
            body = match.group(2).strip()
            sections.append((title, body))
    return sections

# ---------------------------------------------------------------------------
# コピーボタン付きで表示するコンポーネント
# ---------------------------------------------------------------------------
def display_with_copy_button(title, text, key):
    st.markdown(f"#### {title}")
    st.markdown(text)
    # コピーボタン（JavaScript連携）
    copy_id = f"copy_{key}"
    escaped_text = text.replace('\\', '\\\\').replace('`', '\\`').replace('\n', '\\n').replace("'", "\\'")
    st.components.v1.html(f"""
        <button id="{copy_id}" onclick="
            navigator.clipboard.writeText('{escaped_text}').then(() => {{
                document.getElementById('{copy_id}').innerText = '✅ コピーしました！';
                setTimeout(() => {{ document.getElementById('{copy_id}').innerText = '📋 コピー'; }}, 2000);
            }});
        " style="
            background: #f0f2f6; border: 1px solid #ddd; border-radius: 8px;
            padding: 6px 16px; cursor: pointer; font-size: 14px;
            color: #333; transition: all 0.2s;
        ">📋 コピー</button>
    """, height=50)
    st.markdown("---")

# ---------------------------------------------------------------------------
# UI メイン
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="Googleマップ 口コミ返信AI", page_icon="📍")

    st.title("� Googleマップ 口コミ返信生成AI")
    st.write("お客様からの口コミを入力すると、AIが最適な返信文を3パターン提案します。")

    model = load_config()

    # --- 星評価の自動推定 ---
    if "auto_star" not in st.session_state:
        st.session_state.auto_star = 3

    review_text = st.text_area(
        "口コミをコピペ",
        height=150,
        placeholder="ここに口コミを貼り付けてください（例：接客が良かった、料理が遅かった等）",
        key="review_input"
    )

    # 星評価の自動判定ボタン
    col_auto, _ = st.columns([1, 3])
    with col_auto:
        if st.button("⚡ 星を自動判定"):
            if review_text:
                with st.spinner("分析中..."):
                    estimated = estimate_star_rating(model, review_text)
                    st.session_state.auto_star = estimated
                    st.success(f"★{estimated} と推定しました")
            else:
                st.warning("先に口コミを入力してください")

    # 入力エリア（フォーム）
    with st.form("review_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            star_rating = st.slider("評価（星の数）", 1, 5, st.session_state.auto_star)
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

            # 案ごとに分割して個別コピーボタン付きで表示
            sections = parse_reply_sections(reply)
            if sections:
                for i, (title, body) in enumerate(sections):
                    display_with_copy_button(title, body, i)
            else:
                # パースできない場合はそのまま表示
                st.markdown(reply)

    elif submitted:
        st.warning("⚠️ 口コミ内容を入力してください。")

if __name__ == "__main__":
    main()
