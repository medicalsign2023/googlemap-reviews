
import os
import re
import json
from datetime import datetime
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
from streamlit_js_eval import streamlit_js_eval

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------
MAX_DAILY_USES = 5

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
    if length == "短め":
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
- 【絶対厳守】個人名の扱いルール：
  - 評価が星4〜5の場合のみ：口コミに個人名が書かれていれば、その名前をそのまま使ってよい
  - 評価が星1〜3の場合：口コミに個人名が含まれていても、返信文には絶対に個人名を書いてはいけない。必ず「担当医」「スタッフ」「担当者」などの一般名称に100%置き換えること。これは最優先ルールである
- 指定されたトーンに合わせた3パターンの返信案を作成してください
- 各パターンは異なる切り口・表現で書き分けること（トーンは統一）
- 返信文の中では2〜3文ごとに必ず空行（改行2つ）を入れて段落を分けること。改行なしのベタ書きは禁止

【出力形式】
以下の形式で出力してください。各案の間には必ず空行を入れてください：

### A案（共感型）
(返信文)

### B案（行動型）
(返信文)

### C案（シンプル型）
(返信文)
"""
    try:
        response = model.generate_content(prompt)
        reply = response.text
        # 低評価時：口コミに含まれる個人名を返信文から除去する後処理
        if star_rating <= 3:
            reply = remove_personal_names(reply, review_text, model)
        return reply
    except Exception as e:
        return f"エラーが発生しました: {e}"

# ---------------------------------------------------------------------------
# 低評価時の個人名除去（後処理）
# ---------------------------------------------------------------------------
def remove_personal_names(reply, review_text, model):
    """AIに個人名を検出させ、返信文から除去する"""
    prompt = f"""以下の口コミに含まれる人名（医師名、スタッフ名、個人名）をすべて抽出してください。
人名がない場合は「なし」と回答してください。
人名だけをカンマ区切りで出力し、他の文字は一切出力しないでください。
敬称（先生、医師、ドクター、さん等）は含めず、名前部分だけを出力してください。

口コミ: {review_text}"""
    try:
        response = model.generate_content(prompt)
        names_text = response.text.strip()
        if names_text == "なし" or not names_text:
            return reply
        names = [n.strip() for n in names_text.split(",") if n.strip()]
        # 敬称付きのパターンを先に置換（「古山先生」→「担当医」）
        suffixes = ["先生", "医師", "ドクター", "Dr.", "dr."]
        for name in names:
            for suffix in suffixes:
                reply = reply.replace(name + suffix, "担当医")
            # 敬称なしの名前単体も置換
            reply = reply.replace(name, "担当医")
        return reply
    except Exception:
        return reply

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
# 1日の利用回数制限（localStorage使用）
# ---------------------------------------------------------------------------
def get_daily_usage():
    """ブラウザのlocalStorageから今日の利用回数を取得"""
    today = datetime.now().strftime("%Y-%m-%d")
    js_code = f"""
    (function() {{
        try {{
            var stored = localStorage.getItem('gmap_review_usage');
            var data = stored ? JSON.parse(stored) : null;
            if (!data || data.date !== '{today}') {{
                return 0;
            }}
            return data.count || 0;
        }} catch(e) {{
            return 0;
        }}
    }})()
    """
    count = streamlit_js_eval(js_expressions=js_code, key="daily_usage_reader")
    if count is not None:
        st.session_state["_daily_usage_count"] = int(count)
    return st.session_state.get("_daily_usage_count", 0)

def save_daily_usage(count):
    """利用回数をlocalStorageに保存"""
    today = datetime.now().strftime("%Y-%m-%d")
    st.session_state["_daily_usage_count"] = count
    st.components.v1.html(f"""
    <script>
    localStorage.setItem('gmap_review_usage', JSON.stringify({{
        "date": "{today}",
        "count": {count}
    }}));
    </script>
    """, height=0)

# ---------------------------------------------------------------------------
# UI メイン
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="Googleマップ 口コミ返信AI", page_icon="📍")

    st.title("\U0001f4cd Googleマップ 口コミ返信生成AI")
    st.write("お客様からの口コミを入力すると、AIが最適な返信文を3パターン提案します。")

    # 利用回数の表示
    usage_count = get_daily_usage()
    remaining = MAX_DAILY_USES - usage_count
    if remaining > 0:
        st.info(f"📊 本日の残り利用回数: **{remaining} / {MAX_DAILY_USES}回**")
    else:
        st.error(f"⚠️ 本日の利用上限（{MAX_DAILY_USES}回）に達しました。明日またご利用ください。")

    model = load_config()

    # --- 星評価の自動推定 ---
    if "auto_star" not in st.session_state:
        st.session_state.auto_star = 3

    # クリアボタンのコールバック
    def clear_input():
        st.session_state.review_input = ""
        st.session_state.auto_star = 3

    review_text = st.text_area(
        "口コミをコピペ",
        height=150,
        placeholder="ここに口コミを貼り付けてください（例：接客が良かった、料理が遅かった等）",
        key="review_input"
    )

    # 消去ボタン・自動判定ボタン
    col_clear, col_auto, _ = st.columns([1, 1, 2])
    with col_clear:
        st.button("🗑️ クリア", on_click=clear_input)
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
            length = st.selectbox("返信の文字数", ["短め", "長め"])

        submitted = st.form_submit_button("✏️ 返信を作成する")

    # 結果表示
    if submitted and review_text:
        # 利用回数チェック
        current_usage = st.session_state.get("_daily_usage_count", 0)
        if current_usage >= MAX_DAILY_USES:
            st.error(f"⚠️ 本日の利用上限（{MAX_DAILY_USES}回）に達しました。明日またご利用ください。")
        else:
            with st.spinner("AIが返信を考えています..."):
                reply = generate_review_reply(model, review_text, star_rating, tone, length)

                # 利用回数を更新
                new_count = current_usage + 1
                save_daily_usage(new_count)

                st.markdown("---")
                st.subheader("📝 生成された返信案")
                st.success(f"✅ 本日 {new_count}/{MAX_DAILY_USES} 回目の利用")

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
