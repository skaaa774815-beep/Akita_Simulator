import os
import requests
import json

def load_all_api_keys():
    config_file = "config.txt"
    keys_list = []
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or ":" not in line:
                    continue
                provider, key = line.split(":", 1)
                keys_list.append({"provider": provider.lower().strip(), "key": key.strip()})
    return keys_list

def clean_json_text(text):
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def test_event_api(provider, api_key, prompt):
    print(f"\n🚀 [{provider.upper()}] のAPIでイベントをジャッジ中...")
    
    if provider == "gemini":
        raw_url = "generativelanguage_googleapis_com/v1beta/models/gemini-2.5-flash:generateContent"
        url = "https://" + raw_url.replace("_", ".") + f"?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }
        headers = {"Content-Type": "application/json"}
    elif provider == "cohere":
        raw_url = "api_cohere_com/v1/chat"
        url = "https://" + raw_url.replace("_", ".")
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "command-r-08-2024",
            "message": prompt
        }
    else:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "messages": [{"role": "user", "content": prompt}]
        }
        
        if provider == "groq":
            raw_url = "api_groq_com/openai/v1/chat/completions"
            url = "https://" + raw_url.replace("_", ".")
            payload["model"] = "openai/gpt-oss-20b"
            payload["response_format"] = {"type": "json_object"}
        elif provider == "mistral":
            raw_url = "api_mistral_ai/v1/chat/completions"
            url = "https://" + raw_url.replace("_", ".")
            payload["model"] = "mistral-small-latest"
            payload["response_format"] = {"type": "json_object"}
        else:
            return f"❌ 未対応プロバイダ: {provider}"

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=25.0)
        
        if response.status_code == 200:
            res_data = response.json()
            
            if provider == "gemini":
                ai_text = res_data['candidates'][0]['content']['parts'][0]['text']
            elif provider == "cohere":
                ai_text = res_data.get("text", "")
            else:
                ai_text = res_data["choices"][0]["message"]["content"]
            
            cleaned_text = clean_json_text(ai_text)
            
            try:
                parsed_json = json.loads(cleaned_text)
                return (
                    f"✅ 【システムパース成功！】\n"
                    f"■ 判定結果文:\n{parsed_json.get('result_text')}\n"
                    f"■ パラメータ変動:\n"
                    f"   予算: {parsed_json.get('budget_change')} 億円 / "
                    f"満足度: {parsed_json.get('satisfaction_change')} % / "
                    f"人口: {parsed_json.get('population_change')} 人\n"
                    f"■ 成功判定: {parsed_json.get('success')}"
                )
            except json.JSONDecodeError:
                return f"❌ 【パース失敗】 JSON以外の文字が含まれています。\n生の返答内容:\n{ai_text}"
        else:
            return f"❌ 【エラー】 Status: {response.status_code}\n詳細: {response.text}"
            
    except Exception as e:
        return f"⚠️ 【通信失敗】 {e}"

if __name__ == "__main__":
    keys = load_all_api_keys()
    if not keys:
        print("エラー: config.txtが見つかりません。")
        exit()

    dummy_event = {
        "title": "ツキノワグマの市街地出没",
        "description": "秋田市周辺の住宅街や通学路付近でクマの目撃情報が相次いでいます。対策が必要です。",
        "ai_guideline": "猟友会との連携やパトロール強化があれば予算-5、満足度+10。放置は満足度-20、人口-5人。"
    }
    
    player_action = "猟友会へ緊急の出動要請を出し、市内の小中学校の登下校時の警戒を強める。また、目撃情報のあった地域に罠を設置する。"

    event_prompt = f"""
あなたは地方自治体（秋田県）の経営シミュレーションゲームの優秀なAI裁判官です。
以下の【事案】に対してプレイヤーが【実行した対策】を提示しました。
この対策の効果をリアルに判定し、指定された【JSONフォーマット】のみで返答してください。

【事案】: {dummy_event['title']}
【詳細】: {dummy_event['description']}
【ガイドライン】: {dummy_event['ai_guideline']}
【対策】: "{player_action}"

＜判定ルール＞
1. 対策が不十分な場合は大失敗と判定。
2. 予算、満足度、人口の変動は事案の規模に応じて調整。
3. result_text には評価理由を明記。
4. 以下のJSONフォーマットのみを出力し、他の文章は一切含めない。

{{
  "success": true,
  "result_text": "評価コメント(200文字程度)",
  "budget_change": -5,
  "satisfaction_change": 10,
  "population_change": 0
}}
"""

    print("==================================================")
    print(f"【検証中の事案】: {dummy_event['title']}")
    print(f"【知事の対策】: {player_action}")
    print("==================================================")

    for item in keys:
        result = test_event_api(item["provider"], item["key"], event_prompt)
        print(result)
        print("-" * 60)