import tkinter as tk
from tkinter import messagebox
import json
import os
import re

JSON_FILE = "events.json"
event_list = []

akita_locations = [
    "ランダム", "山間部", "沿岸部", "県北", "県央", "県南",
    "秋田市", "能代市", "横手市", "大館市", "男鹿市", "湯沢市", "鹿角市", "由利本荘市", 
    "潟上市", "大仙市", "北秋田市", "にかほ市", "仙北市", 
    "小坂町", "上小阿仁村", "藤里町", "三種町", "八峰町", "五城目町", "八郎潟町", "井川町", 
    "大潟村", "美郷町", "羽後町", "東成瀬村"
]

def load_existing_json():
    global event_list
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                event_list = json.load(f)
            update_event_preview()
        except Exception as e:
            messagebox.showerror("エラー", f"JSONの読み込みに失敗しました:\n{e}")

def parse_ai_json():
    raw_text = text_ai_paste.get("1.0", tk.END).strip()
    if not raw_text:
        return
    
    try:
        # 配列 [...] または 単体 {...} を抽出
        match_array = re.search(r'\[.*\]', raw_text, re.DOTALL)
        match_obj = re.search(r'\{.*\}', raw_text, re.DOTALL)

        if match_array:
            data = json.loads(match_array.group(0))
        elif match_obj:
            # 単体の場合でもリストに変換して処理を共通化
            data = [json.loads(match_obj.group(0))] 
        else:
            data = json.loads(raw_text)
            if isinstance(data, dict):
                data = [data]

        if not isinstance(data, list):
            raise ValueError("JSONの形式が正しくありません")

        # 複数データを一気に event_list に追加
        added_count = 0
        for item in data:
            ev_id = item.get("id", "")
            title = item.get("title", "")
            desc = item.get("description", "")
            guideline = item.get("ai_guideline", "")
            weight_val = item.get("weight", 100) # 💡AIデータにweightがあれば取得、なければ100
            seasons_data = item.get("seasons", [])
            
            locations_data = item.get("locations", [])
            if "location" in item and not locations_data:
                locations_data = [item["location"]]
            
            event_data = {
                "id": ev_id,
                "title": title,
                "seasons": seasons_data,
                "locations": locations_data,
                "description": desc,
                "ai_guideline": guideline,
                "weight": weight_val # 💡weightをデータに含める
            }
            event_list.append(event_data)
            added_count += 1

        update_event_preview()
        messagebox.showinfo("大成功！", f"AIのデータから {added_count} 件のイベントを一気にリストに追加しました！\n問題なければ「JSONへ保存」を押してください。")
        text_ai_paste.delete("1.0", tk.END)
        clear_inputs()

    except Exception as e:
        messagebox.showerror("解析エラー", f"JSONの解析に失敗しました。詳細: {e}")

def add_event():
    ev_id = entry_id.get().strip()
    title = entry_title.get().strip()
    desc = text_desc.get("1.0", tk.END).strip()
    guideline = text_guideline.get("1.0", tk.END).strip()
    weight_str = entry_weight.get().strip() # 💡weightの入力値を取得
    
    # weightの数値チェック
    try:
        weight_val = int(weight_str) if weight_str else 100
    except ValueError:
        messagebox.showwarning("警告", "発生確率(weight)は半角数字で入力してください！")
        return

    selected_seasons = [s for s, var in season_vars.items() if var.get()]
    # 選択された場所のインデックスから文字リストを取得
    selected_loc_indices = listbox_loc.curselection()
    selected_locations = [akita_locations[i] for i in selected_loc_indices]

    if not ev_id or not title or not selected_locations or not desc or not guideline or not selected_seasons:
        messagebox.showwarning("警告", "すべての項目を入力し、場所と季節を1つ以上選択してください！")
        return

    event_data = {
        "id": ev_id,
        "title": title,
        "seasons": selected_seasons,
        "locations": selected_locations, # 配列として保存
        "description": desc,
        "ai_guideline": guideline,
        "weight": weight_val # 💡リスト追加時にweightを保存
    }

    event_list.append(event_data)
    update_event_preview()
    clear_inputs()

def save_to_json():
    if not event_list:
        return
    try:
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(event_list, f, indent=2, ensure_ascii=False)
        messagebox.showinfo("保存完了", f"「{JSON_FILE}」に保存しました！")
    except Exception as e:
        messagebox.showerror("エラー", f"保存に失敗しました:\n{e}")

def update_event_preview():
    listbox_preview.delete(0, tk.END)
    for ev in event_list:
        seasons_str = ",".join(ev['seasons'])
        locs_str = ",".join(ev.get('locations', []))
        weight_val = ev.get('weight', 100)
        # 💡プレビューにも発生確率を表示
        listbox_preview.insert(tk.END, f"[確率:{weight_val}][{seasons_str}] 地点:{locs_str} - {ev['title']}")

def clear_inputs():
    entry_id.delete(0, tk.END)
    entry_title.delete(0, tk.END)
    listbox_loc.selection_clear(0, tk.END)
    text_desc.delete("1.0", tk.END)
    text_guideline.delete("1.0", tk.END)
    
    # 💡入力欄クリア時にweightをデフォルトの100に戻す
    entry_weight.delete(0, tk.END)
    entry_weight.insert(0, "100")
    
    for var in season_vars.values():
        var.set(False)

# --- GUI構築 ---
root = tk.Tk()
root.title("秋田県シミュレーター - 複数位置対応JSON作成ツール")
root.geometry("680x950") # 💡項目が増えたためウィンドウサイズを少し拡大

main_frame = tk.Frame(root)
main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

frame_ai = tk.LabelFrame(main_frame, text=" 1. AIの出力をここに貼り付け ", font=("Arial", 10, "bold"), fg="blue")
frame_ai.pack(fill=tk.X, pady=5)
text_ai_paste = tk.Text(frame_ai, height=4, width=65)
text_ai_paste.pack(padx=5, pady=5)
btn_parse = tk.Button(frame_ai, text="↓ AIのデータを自動入力 ↓", command=parse_ai_json, bg="#ffe0b2", font=("Arial", 10, "bold"))
btn_parse.pack(pady=5)

frame_edit = tk.LabelFrame(main_frame, text=" 2. 内容の確認・微調整 ", font=("Arial", 10, "bold"))
frame_edit.pack(fill=tk.BOTH, expand=True, pady=5)

tk.Label(frame_edit, text="イベントID:").grid(row=0, column=0, sticky="e", pady=4)
entry_id = tk.Entry(frame_edit, width=45)
entry_id.grid(row=0, column=1, sticky="w", pady=4)

tk.Label(frame_edit, text="タイトル:").grid(row=1, column=0, sticky="e", pady=4)
entry_title = tk.Entry(frame_edit, width=45)
entry_title.grid(row=1, column=1, sticky="w", pady=4)

tk.Label(frame_edit, text="発生場所\n(複数クリック可):").grid(row=2, column=0, sticky="ne", pady=4)
# 複数選択用のリストボックスとスクロールバー
loc_frame = tk.Frame(frame_edit)
loc_frame.grid(row=2, column=1, sticky="w", pady=4)
scrollbar = tk.Scrollbar(loc_frame)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
listbox_loc = tk.Listbox(loc_frame, selectmode=tk.MULTIPLE, yscrollcommand=scrollbar.set, height=4, width=30, exportselection=False)
for loc in akita_locations:
    listbox_loc.insert(tk.END, loc)
listbox_loc.pack(side=tk.LEFT, fill=tk.BOTH)
scrollbar.config(command=listbox_loc.yview)

tk.Label(frame_edit, text="季節 (複数可):").grid(row=3, column=0, sticky="ne", pady=4)
season_frame = tk.Frame(frame_edit)
season_frame.grid(row=3, column=1, sticky="w", pady=4)
seasons = ["春", "夏", "秋", "冬", "通年"]
season_vars = {s: tk.BooleanVar() for s in seasons}
for s in seasons:
    tk.Checkbutton(season_frame, text=s, variable=season_vars[s]).pack(side=tk.LEFT)

tk.Label(frame_edit, text="説明文:").grid(row=4, column=0, sticky="ne", pady=4)
text_desc = tk.Text(frame_edit, width=50, height=4)
text_desc.grid(row=4, column=1, sticky="w", pady=4)

tk.Label(frame_edit, text="AIガイドライン:").grid(row=5, column=0, sticky="ne", pady=4)
text_guideline = tk.Text(frame_edit, width=50, height=5)
text_guideline.grid(row=5, column=1, sticky="w", pady=4)

# 💡【新規追加】発生確率 (weight) の入力欄
tk.Label(frame_edit, text="発生確率 (Weight)\n※基本100, 災害5〜15:").grid(row=6, column=0, sticky="ne", pady=4)
entry_weight = tk.Entry(frame_edit, width=15)
entry_weight.insert(0, "100") # デフォルト値を100に設定
entry_weight.grid(row=6, column=1, sticky="w", pady=4)

btn_frame = tk.Frame(root)
btn_frame.pack(pady=5)
tk.Button(btn_frame, text="リストに追加", command=add_event, bg="#e1f5fe", width=15).pack(side=tk.LEFT, padx=10)
tk.Button(btn_frame, text="JSONへ保存", command=save_to_json, bg="#c8e6c9", width=15).pack(side=tk.LEFT, padx=10)

listbox_preview = tk.Listbox(root, width=90, height=6)
listbox_preview.pack(padx=15, pady=5)

load_existing_json()
root.mainloop()