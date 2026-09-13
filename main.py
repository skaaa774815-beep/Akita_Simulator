import pygame
import sys
import json
import random
import os
import tkinter as tk
from tkinter import simpledialog, messagebox
import random
import requests
import re 
import datetime

# --- 1. 初期設定と定数 ---
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

COLOR_BG = (30, 30, 40)
COLOR_TEXT = (240, 240, 240)
COLOR_HUD = (50, 50, 70)
COLOR_ALERT = (255, 100, 100)
COLOR_PIN = (255, 50, 50)      

CITY_COORDINATES = {
    "秋田市": (0.32, 0.46), "大館市": (0.66, 0.16), "横手市": (0.64, 0.74),
    "能代市": (0.26, 0.19), "由利本荘市": (0.28, 0.67), "大仙市": (0.58, 0.64),
    "鹿角市": (0.88, 0.19), "湯沢市": (0.62, 0.84), "男鹿市": (0.10, 0.38),
    "仙北市": (0.81, 0.50), "北秋田市": (0.51, 0.18), "にかほ市": (0.19, 0.79),
    "潟上市": (0.24, 0.38),

    # 🌲 県北部の町村
    "小坂町": (0.81, 0.12),   # 鹿角市の北、大館市の東
    "藤里町": (0.44, 0.14),   # 能代市の北東
    "八峰町": (0.27, 0.11),   # 能代市の北（海沿い）
    "三種町": (0.25, 0.25),   # 能代市の南
    
    # 🌾 中央部・八郎潟周辺の町村
    "大潟村": (0.21, 0.30),   # 男鹿半島の付け根の東（干拓地）
    "八郎潟町": (0.30, 0.34), # 大潟村の東
    "五城目町": (0.34, 0.34), # 八郎潟町の東
    "井川町": (0.29, 0.36),   # 八郎潟町の南、潟上市の北
    "上小阿仁村": (0.46, 0.28), # 北秋田市の南、秋田市の北東
    
    # 🍎 県南部の町村
    "美郷町": (0.68, 0.64),   # 大仙市の南、横手市の北
    "羽後町": (0.55, 0.80),   # 横手市の南西、湯沢市の西
    "東成瀬村": (0.74, 0.81)  # 横手市の南東

}

REGIONS = {
    "県北": ["大館市", "能代市", "鹿角市", "北秋田市","小坂町","藤里町","八峰町","三種町"],
    "県央": ["秋田市", "男鹿市", "潟上市","大潟村","八郎潟町","五城目町","井川町","上小阿仁村"],
    "県南": ["横手市", "由利本荘市", "大仙市", "湯沢市", "仙北市", "にかほ市","美郷町","羽後町","東成瀬村"],
    "沿岸部": [
        "秋田市", "能代市", "由利本荘市", "男鹿市", "にかほ市", "潟上市", 
        "八峰町", "三種町", "大潟村"
    ],
    "山間部": [
        "大館市", "横手市", "大仙市", "鹿角市", "湯沢市", "仙北市", "北秋田市",
        "小坂町", "藤里町", "上小阿仁村", "東成瀬村", "羽後町", "美郷町"
    ]}

root = tk.Tk()
root.withdraw()
root.attributes('-topmost', True) 

# --- 2. 複数企業のAPIキー・ローテーションシステム ---
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

ALL_KEYS = load_all_api_keys()
current_key_idx = 0

def get_next_api_data():
    global current_key_idx
    if not ALL_KEYS:
        return None
    data = ALL_KEYS[current_key_idx]
    current_key_idx = (current_key_idx + 1) % len(ALL_KEYS)
    return data

# --- 3. ゲーム管理クラス ---
class AkitaSimulator:

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("秋田県経営シミュレーター - AI自動マルチフォールバック版")
        self.clock = pygame.time.Clock()
        
        font_candidates = ["msgothic", "msmincho", "hiraginosansgb", "notosanscjk", "yugothic", "sans-serif"]
        self.font_small = pygame.font.SysFont(font_candidates, 18)
        self.font = pygame.font.SysFont(font_candidates, 24)
        self.font_large = pygame.font.SysFont(font_candidates, 32)
        self.ui_font = pygame.font.SysFont(font_candidates, 28)
        
        self.frame_w, self.frame_h = 920, 680
        try:
            img = pygame.image.load("map.png").convert_alpha()
            orig_w, orig_h = img.get_size()
            scale = min(self.frame_w / orig_w, self.frame_h / orig_h)
            self.new_w = int(orig_w * scale)
            self.new_h = int(orig_h * scale)
            self.map_img = pygame.transform.smoothscale(img, (self.new_w, self.new_h))
            self.map_x = 340 + (self.frame_w - self.new_w) // 2
            self.map_y = 20 + (self.frame_h - self.new_h) // 2
        except Exception as e:
            self.map_img = None
            self.new_w, self.new_h = self.frame_w, self.frame_h
            self.map_x, self.map_y = 340, 20
            print(f"※map.pngが見つからないかエラーです: {e}")

        # エラー回避用のダミー（古い描画システムが残っていてもエラーにならないようにします）
        self.custom_images = {}

        self.land_windmills = {city: [] for city in CITY_COORDINATES.keys()}
        self.windmills_count = {}

        # ＝＝＝ ① 先に各市町村の発展度メーターを準備する ＝＝＝
        self.city_development = {}
        for city_name in CITY_COORDINATES:
            if city_name.endswith("市"):
                self.city_development[city_name] = 15 
            elif city_name.endswith("町"):
                self.city_development[city_name] = 8  
            elif city_name.endswith("村"):
                self.city_development[city_name] = 4  
            else:
                self.city_development[city_name] = 10 

        self.city_development["秋田市"] = 75    
        self.city_development["横手市"] = 45    
        self.city_development["大館市"] = 40    
        self.city_development["大仙市"] = 30    
        self.city_development["由利本荘市"] = 25 

        # ＝＝＝ 名物・名所画像の読み込みと初期設定 ＝＝＝
        self.specialty_images_raw = {}  
        self.specialty_images = {}

        specialty_files = {
            "ババヘラ": "babahera.jpg",
            "田沢湖": "tazawako.png",
            "八郎潟": "hatirougata.png",
            "横手やきそば": "yokoteyakisoba.png",
            "きりたんぽ": "kiritannpo.png",
            "青なまはげ": "aonamahage.png",
            "赤なまはげ": "akanamahage.png",
            "ゴジラ岩": "gojiraiwa.png",
            "秋田犬": "inu.png",
            "竿燈まつり": "kanto.png",
            "風車": "windmill.png",
            "大曲の花火": "hanabi.png",
            "都市タイル": "toshitairu.png",
            "秋田駅": "akitaeki.png"
        }

        for name, filename in specialty_files.items():
            target_path = filename if os.path.exists(filename) else f"images/{filename}"
            if os.path.exists(target_path):
                img = pygame.image.load(target_path).convert_alpha()
                self.specialty_images_raw[name] = img
            else:
                self.specialty_images_raw[name] = None

        # ＝＝＝ ② 基本のランドマーク配置パラメーター（基本サイズ50、オフセット-25） ＝＝＝
        self.landmark_config = {
            "田沢湖": {"x": 0.81, "y": 0.50, "size": 120, "is_bg": True, "city": "仙北市"},
            "八郎潟": {"x": 0.18, "y": 0.32, "size": 100, "is_bg": True, "city": "大潟村"},
            "赤なまはげ": {"x": 0.0, "y": -25, "size": 50, "is_bg": False, "city": "男鹿市"},
            "ゴジラ岩": {"x": 25, "y": -25, "size": 50, "is_bg": False, "city": "男鹿市"},
            "横手やきそば": {"x": 0.0, "y": -25, "size": 50, "is_bg": False, "city": "横手市"},
            "きりたんぽ": {"x": 0.0, "y": -25, "size": 50, "is_bg": False, "city": "大館市"},
            "青なまはげ": {"x": 0.0, "y": -25, "size": 50, "is_bg": False, "city": "にかほ市"},
            
            "秋田犬": {"x": -10, "y": -25, "size": 50, "is_bg": False, "city": "大館市"},
            "竿燈まつり": {"x": -50, "y": -25, "size": 50, "is_bg": False, "city": "秋田市"},
            "大曲の花火": {"x": -25, "y": -25, "size": 50, "is_bg": False, "city": "横手市"},
            "ババヘラ": {"size": 50}
        }
        
        # ＝＝＝ ③ 全市町村のタイルと風車を個別登録（現在の発展度・風車数を保持枠に追加） ＝＝＝
        for c in CITY_COORDINATES.keys():
            dev_init = self.city_development.get(c, 0)
            wm_init = self.windmills_count.get(c, 0)
            
            # 発展度(dev)と風車数(wm)を持たせる。サイズは変更可能なように50を設定。
            self.landmark_config[f"都市タイル ({c})"] = {"x": -25, "y": -25, "size": 50, "is_bg": False, "city": c, "dev": dev_init, "wm": wm_init}
            self.landmark_config[f"秋田駅 ({c})"] = {"x": -25, "y": -25, "size": 50, "is_bg": False, "city": c}
            self.landmark_config[f"風車 ({c})"] = {"x": -25, "y": -25, "size": 50, "is_bg": False, "city": c}

        # ＝＝＝ ④ 保存データのロードと画像サイズの一斉更新 ＝＝＝
        self.load_landmark_config()
        self.update_image_scales()

        self.babahera_auto_move = True    
        self.babahera_active_city = None
        self.babahera_timer = 5000

        # 💡【修正】ここに混ざっていた重複した city_development の初期化処理（リセット処理）を完全に削除しました

        self.year = 1
        self.seasons = ["春", "夏", "秋", "冬"]
        self.season_idx = 0
        self.days = 1
        
        self.budget = 500       
        self.satisfaction = 50  
        self.population = 900000 
        
        self.day_timer = 0
        self.day_duration = 600 
        
        self.active_events = []
        self.max_simultaneous_events = 5 
        # メソッド未定義エラーを防ぐための安全策
        self.events = self.load_events() if hasattr(self, 'load_events') else []

        self.debug_win = None             
        self.debug_show_all_pins = False  
        
        self.game_log = []
        if hasattr(self, 'save_log_to_json'):
            self.save_log_to_json()
        
        self.news_text = "【県政速報】新知事が就任しました。秋田県の輝かしい未来にご期待ください！"
        self.news_x = SCREEN_WIDTH

        # ＝＝＝ 追加：洋上風力発電所のリスト ＝＝＝
        self.offshore_windmills = []

        # ＝＝＝ メインメニュー＆セーブ機能の追加 ＝＝＝
        self.state = "MENU_MAIN"  
        self.target_years = 10
        self.difficulty = "Normal"
        self.save_slots = ["save_data_1.json", "save_data_2.json", "save_data_3.json", "save_data_4.json"]
        self.menu_buttons = []

        # 🌟 追加: 背景画像の読み込み
        self.menu_bgs = []
        for i in range(1, 13):
            # 拡張子の大文字小文字ブレを吸収
            for ext in [".PNG", ".png", ".jpg", ".JPG"]:
                filename = f"backgrounds/bg_{i:02d}{ext}"
                if os.path.exists(filename):
                    try:
                        img = pygame.image.load(filename).convert()
                        # 画面サイズに合わせてリサイズ
                        img = pygame.transform.scale(img, (SCREEN_WIDTH, SCREEN_HEIGHT))
                        self.menu_bgs.append(img)
                        break  # 読み込めたら次の番号へ
                    except:
                        pass
        self.current_bg = random.choice(self.menu_bgs) if self.menu_bgs else None

        # ＝＝＝ 音声（BGM・SE・環境音）の初期設定 ＝＝＝
        pygame.mixer.init()
        
        # BGMのファイルパス設定（BGMフォルダから読み込み）
        self.bgm_files = {
            "title": "BGM/Parade.mp3",
            "normal": "BGM/日々と泉.mp3",
            "problem_normal": "BGM/どかない猫.mp3",
            "problem_severe": "BGM/ウルトラ大掃除.mp3",
            "problem_easy": "BGM/脱力.mp3",
            "election": "BGM/Stream.mp3",
            "end_happy": "BGM/STREET CITY POP.mp3",
            "end_bad": "BGM/じ・えんど.mp3"
        }
        self.current_bgm = None

        # SEの読み込み（同じくBGMフォルダから）
        self.se = {}
        se_files = {
            "cursor": "BGM/カーソル移動3.mp3",
            "confirm": "BGM/決定ボタンを押す45.mp3",
            "cancel": "BGM/キャンセル4.mp3",
            "save": "BGM/カメラのシャッター3.mp3"
        }
        for key, filename in se_files.items():
            if os.path.exists(filename):
                self.se[key] = pygame.mixer.Sound(filename)
                self.se[key].set_volume(0.5)  # SEの音量調整
            else:
                print(f"【警告】SEが見つかりません: {filename}")

        # 環境音の読み込み（四季）
        self.env_sounds = {}
        env_files = {
            0: "BGM/bird-and-bag.mp3",        # 春
            1: "BGM/ミンミンゼミの鳴き声.mp3", # 夏
            2: "BGM/musinones.mp3",           # 秋
            3: "BGM/吹雪.mp3"                 # 冬
        }
        for key, filename in env_files.items():
            if os.path.exists(filename):
                self.env_sounds[key] = pygame.mixer.Sound(filename)
                self.env_sounds[key].set_volume(0.3) # 環境音は控えめに
            else:
                print(f"【警告】環境音が見つかりません: {filename}")

        self.env_channel = pygame.mixer.Channel(1) # 環境音専用チャンネル
        self.current_env = None
        self.last_hovered_btn = None # カーソル移動SE用

        # ＝＝＝ 音量設定の初期化（10段階: 0〜10） ＝＝＝
        self.volume_bgm = 5
        self.volume_env = 5
        self.volume_se = 5

        # ▼ 追加: 保存された設定があれば読み込み、音量に適用する
        self.load_settings()
        self.apply_volumes()

        # ＝＝＝ デバッグ機能・風車データの初期化 ＝＝＝
        self.debug_mode = False  # Wキーで切替（変更）
        self.offshore_windmills = []
        self.load_windmills()    # 保存データがあれば読み込み

    import math

    def add_windmill_from_debug(self, x, y):
        """デバッグモードでクリックした座標を、一番近い町に割り当てて追加する"""
        closest_city = None
        min_distance = float('inf')
        
        for city in CITY_COORDINATES.keys():
            cx, cy = self.get_city_pos(city)
            dist = math.hypot(x - cx, y - cy)
            if dist < min_distance:
                min_distance = dist
                closest_city = city
                
        if closest_city:
            self.land_windmills[closest_city].append((x, y))
            print(f"デバッグ: {closest_city}に風車を配置しました。現在の本数: {len(self.land_windmills[closest_city])}")

    def modify_windmills(self, city_name, amount):
        """イベントや質問の結果で風車を増減させる"""
        if city_name not in self.land_windmills:
            self.land_windmills[city_name] = []

        if amount > 0:
            cx, cy = self.get_city_pos(city_name)
            for _ in range(amount):
                new_x = cx + random.randint(-40, 40)
                new_y = cy + random.randint(-40, 40)
                self.land_windmills[city_name].append((new_x, new_y))
        elif amount < 0:
            remove_count = min(abs(amount), len(self.land_windmills[city_name]))
            for _ in range(remove_count):
                self.land_windmills[city_name].pop()

    def apply_volumes(self):
        """0〜10の段階設定をPygameの音量（0.0〜1.0）に変換して適用する"""
        # BGM音量
        bgm_vol = (self.volume_bgm / 10.0)
        pygame.mixer.music.set_volume(bgm_vol)
        
        # 環境音音量
        env_vol = (self.volume_env / 10.0) * 0.6  # 環境音は少し控えめにするベース係数
        if hasattr(self, 'env_channel'):
            self.env_channel.set_volume(env_vol)
            
        # SE音量
        se_vol = (self.volume_se / 10.0)
        if hasattr(self, 'se'):
            for sound in self.se.values():
                sound.set_volume(se_vol)

    def load_settings(self):
        """音量設定をファイルから読み込む"""
        if os.path.exists("settings.json"):
            try:
                with open("settings.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.volume_bgm = data.get("volume_bgm", 8)
                    self.volume_env = data.get("volume_env", 6)
                    self.volume_se = data.get("volume_se", 8)
            except Exception as e:
                print(f"設定の読み込みに失敗: {e}")

    def load_windmills(self):
        """保存された風車の座標データをファイルから読み込む"""
        if os.path.exists("windmills.json"):
            try:
                with open("windmills.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.offshore_windmills = [tuple(pos) for pos in data]
            except Exception as e:
                print(f"風車データの読み込み失敗: {e}")

    def save_windmills(self):
        """現在の風車座標データをファイルに保存する"""
        try:
            with open("windmills.json", "w", encoding="utf-8") as f:
                json.dump(self.offshore_windmills, f, indent=4)
            print(f"風車座標を保存しました (合計: {len(self.offshore_windmills)}本)")
        except Exception as e:
            print(f"風車データの保存失敗: {e}")

    def save_settings(self):
        """現在の音量設定をファイルに保存する"""
        data = {
            "volume_bgm": self.volume_bgm,
            "volume_env": self.volume_env,
            "volume_se": self.volume_se
        }
        try:
            with open("settings.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"設定の保存に失敗: {e}")

    # 🌟 追加: 背景をランダムに変更するメソッド
    def change_menu_bg(self):
        if len(self.menu_bgs) > 1:
            next_bg = random.choice(self.menu_bgs)
            # 現在の画像と同じものが選ばれたら引き直す
            while next_bg == getattr(self, 'current_bg', None):
                next_bg = random.choice(self.menu_bgs)
            self.current_bg = next_bg
        elif len(self.menu_bgs) == 1:
            self.current_bg = self.menu_bgs[0]
        else:
            # 💡画像が1枚も読み込めていない場合の警告
            print("【警告】背景画像が読み込めませんでした。「backgrounds」フォルダの場所や画像ファイル名を確認してください。")

    def update_audio(self):
        """現在のゲーム状態に合わせてBGMと環境音を自動で切り替える"""
        target_bgm = None
        
        # 1. BGMの判定
        if self.state in ["MENU_MAIN", "MENU_NEW", "MENU_LOAD", "MENU_SAVE"]:
            target_bgm = "title"
        elif self.state == "PLAYING":
            # 選挙中フラグがあれば（※今後実装予定の場合）
            if getattr(self, 'is_election', False):
                target_bgm = "election"
            elif len(self.active_events) > 0:
                # 発生中のイベントの深刻度（severity: 1=簡易, 2=通常, 3=深刻 と仮定）
                # ※もしご自身のコードで severity（深刻度）という変数が無ければ、ランダム等に書き換えてください
                highest_severity = max([ev.get("severity", 2) for ev in self.active_events])
                if highest_severity >= 3:
                    target_bgm = "problem_severe"
                elif highest_severity == 2:
                    target_bgm = "problem_normal"
                else:
                    target_bgm = "problem_easy"
            else:
                target_bgm = "normal"
        elif self.state == "GAME_OVER":
            if self.budget <= 0 or self.satisfaction <= 0:
                target_bgm = "end_bad"
            else:
                target_bgm = "end_happy"

        # BGMの切り替え実行
        if target_bgm and target_bgm != self.current_bgm:
            if target_bgm in self.bgm_files and os.path.exists(self.bgm_files[target_bgm]):
                pygame.mixer.music.load(self.bgm_files[target_bgm])
                pygame.mixer.music.play(-1) # -1はループ再生
            self.current_bgm = target_bgm

        # 2. 環境音の判定 (プレイ中のみ再生)
        if self.state == "PLAYING":
            if self.current_env != self.season_idx:
                if self.season_idx in self.env_sounds:
                    self.env_channel.play(self.env_sounds[self.season_idx], loops=-1)
                self.current_env = self.season_idx
        else:
            if self.env_channel.get_busy():
                self.env_channel.stop()
            self.current_env = None
        
    def save_game(self, slot_idx):
        data = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "difficulty": self.difficulty,
            "budget": self.budget,
            "satisfaction": self.satisfaction,
            "population": self.population,
            "year": self.year,
            "days": self.days,
            "season_idx": self.season_idx,
            "target_years": self.target_years if self.target_years != float('inf') else "inf",
            "city_development": self.city_development,
            "offshore_windmills": self.offshore_windmills,
            "land_windmills": self.land_windmills
        }
        with open(self.save_slots[slot_idx], "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("セーブ完了", f"スロット {slot_idx + 1} にセーブしました！")
        self.state = "PLAYING" # セーブ後はゲームに戻る

    def load_game(self, slot_idx):
        filepath = self.save_slots[slot_idx]
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.difficulty = data.get("difficulty", "Normal")
            self.budget = data["budget"]
            self.satisfaction = data["satisfaction"]
            self.population = data["population"]
            self.year = data["year"]
            self.days = data["days"]
            self.season_idx = data["season_idx"]
            
            if data["target_years"] == "inf":
                self.target_years = float('inf')
            else:
                self.target_years = data["target_years"]
                
            self.city_development = data.get("city_development", self.city_development)
            self.offshore_windmills = data.get("offshore_windmills", [])
            self.land_windmills = data.get("land_windmills", {city: [] for city in CITY_COORDINATES.keys()})
            self.state = "PLAYING"
            messagebox.showinfo("ロード完了", f"スロット {slot_idx + 1} のデータを読み込みました。")
        else:
            messagebox.showerror("エラー", "そのスロットにセーブデータはありません。")

    def get_save_info(self, slot_idx):
        filepath = self.save_slots[slot_idx]
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                raw_ts = data.get("timestamp", "不明")
                ts = raw_ts[2:16] if len(raw_ts) >= 16 else raw_ts
                df = data.get("difficulty", "Normal")
                y, s_idx, d = data.get("year", 1), data.get("season_idx", 0), data.get("days", 1)
                season_str = self.seasons[s_idx] if 0 <= s_idx < 4 else "不明"
                
                b = data.get("budget", 0)
                p = data.get("population", 0)
                s = data.get("satisfaction", 0)
                
                # 🌟 変更: 2つに分けて返す
                line1 = f"[{ts}] {df} | {y}年 {season_str} {d}日"
                line2 = f"予算:{b}億  人口:{p}人  支持:{s}%"
                return (line1, line2)
            except:
                return ("データ破損", "")
        # 空きスロットの場合も2行構成にする
        return ("NO DATA", "（空きスロット）")

    def get_city_pos(self, city_name):
        """マップの表示位置(map_x, map_y)とサイズ(new_w, new_h)に合わせた座標計算"""
        if city_name in CITY_COORDINATES:
            rx, ry = CITY_COORDINATES[city_name]
            cx = self.map_x + int(rx * self.new_w)
            cy = self.map_y + int(ry * self.new_h)
            return cx, cy
        return 0, 0

    def load_landmark_config(self):
        """保存された配置データ、および各都市の発展度・風車数をロードする"""
        if os.path.exists("landmark_config.json"):
            try:
                with open("landmark_config.json", "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    for k, v in saved.items():
                        if k in self.landmark_config:
                            self.landmark_config[k].update(v)
                            
                            # 💡 ロードした数値をゲーム本体の変数（発展度・風車数）に同期させる
                            city = self.landmark_config[k].get("city")
                            if k.startswith("都市タイル") and city:
                                if "dev" in v: self.city_development[city] = v["dev"]
                                if "wm" in v: self.windmills_count[city] = v["wm"]
            except Exception as e:
                print(f"⚠️ 設定読み込み失敗: {e}")

    def save_landmark_config(self):
        try:
            with open("landmark_config.json", "w", encoding="utf-8") as f:
                json.dump(self.landmark_config, f, indent=4, ensure_ascii=False)
            print("💾 ランドマーク設定を保存しました")
        except Exception as e:
            print(f"⚠️ 設定保存失敗: {e}")

    def update_image_scales(self):
        """デバッグで変更されたサイズに合わせて画像を再生成する"""
        for config_name, config in self.landmark_config.items():
            if config_name.startswith("都市タイル"):
                raw_name = "都市タイル"
            elif config_name.startswith("秋田駅"):
                raw_name = "秋田駅"
            elif config_name.startswith("風車"):
                raw_name = "風車"
            else:
                raw_name = config_name
                
            raw_img = self.specialty_images_raw.get(raw_name)
            if raw_img:
                # 💡 設定されたサイズ（デフォルトは50）でリサイズ！
                size = config.get("size", 50)
                self.specialty_images[config_name] = pygame.transform.scale(raw_img, (size, size))

    def load_events(self):
        try:
            with open("events.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"JSON読み込みエラー: {e}")
            return [{
                "id": "test_01",
                "title": "大雪による孤立集落の発生",
                "seasons": ["冬"],
                "locations": ["横手市", "湯沢市", "大館市"],
                "description": "記録的な大雪により、一部の集落への道路が寸断され孤立状態になっています。",
                "ai_guideline": "除雪対応で予算-20。放置は満足度激減。"
            }]

    def apply_difficulty_settings(self):
        """新規ゲーム開始時に難易度に応じた初期ステータスをセットする"""
        conf = {
            "Easy":   {"budget": 1000, "satisfaction": 75},
            "Normal": {"budget": 500,  "satisfaction": 50},
            "Hard":   {"budget": 300,  "satisfaction": 40},
            "Extra":  {"budget": 300,  "satisfaction": 40}
        }
        self.budget = conf[self.difficulty]["budget"]
        self.satisfaction = conf[self.difficulty]["satisfaction"]
        
        # 新規プレイ用のリセット処理
        self.population = 900000
        self.year = 1
        self.days = 1
        self.season_idx = 0
        self.active_events.clear()
        self.game_log.clear()

    def get_difficulty_multiplier(self):
        """難易度に応じたゲーム内倍率を返す (収入倍率, イベント発生率, ダメージ倍率)"""
        if self.difficulty == "Easy":
            return 1.5, 0.05, 0.5  # 収入1.5倍、発生率5%、ダメージ半減
        elif self.difficulty == "Hard":
            return 1.0, 0.15, 1.5  # 収入1.0倍、発生率15%、ダメージ1.5倍
        elif self.difficulty == "Extra":
            return 0.8, 0.20, 2.5  # 収入0.8倍、発生率20%、ダメージ2.5倍
        else: # Normal
            return 1.0, 0.10, 1.0  # 収入1.0倍、発生率10%、ダメージ標準

    def progress_time(self, dt):
        self.day_timer += dt
        self.news_x -= 2

        income_mult, event_chance, damage_mult = self.get_difficulty_multiplier()

        # ＝＝＝＝＝＝＝＝＝＝＝＝＝＝ ここから追加 ＝＝＝＝＝＝＝＝＝＝＝＝＝＝
        # ＝＝＝ ババヘラアイス神出鬼没システム ＝＝＝
        self.babahera_timer -= dt
        if self.babahera_timer <= 0:
            if self.babahera_active_city is None:
                # どこかの市町村にランダム出現（約10秒〜20秒滞在）
                self.babahera_active_city = random.choice(list(CITY_COORDINATES.keys()))
                self.babahera_timer = random.randint(10000, 20000) 
            else:
                # 一旦姿を消す（約3秒〜8秒お休み）
                self.babahera_active_city = None
                self.babahera_timer = random.randint(3000, 8000)
        # ＝＝＝＝＝＝＝＝＝＝＝＝＝＝ ここまで追加 ＝＝＝＝＝＝＝＝＝＝＝＝＝＝
        
        if self.day_timer >= self.day_duration:
            self.day_timer = 0
            self.days += 1
            
            for ae in self.active_events[:]:
                ae["time_left"] -= 1
                if ae["time_left"] <= 0:
                    b_change = int(-30 * damage_mult)
                    s_change = int(-15 * damage_mult)
                    p_change = int(-1500 * damage_mult)
                    
                    self.budget += b_change
                    self.satisfaction += s_change
                    self.satisfaction = max(0, min(100, self.satisfaction))
                    self.population += p_change
                    
                    self.log_action(
                        title=ae["event_data"]["title"],
                        location=ae["location"],
                        description=ae["event_data"]["description"],
                        player_input="（未対応のまま制限時間切れ）",
                        b_change=b_change,
                        s_change=s_change,
                        p_change=p_change
                    )
                    
                    self.news_text = f"【批判殺到】{ae['location']}の「{ae['event_data']['title']}」に対し県は対応せず、被害が拡大。"
                    self.news_x = SCREEN_WIDTH
                    
                    self.active_events.remove(ae)
                    messagebox.showwarning(
                        "【対応遅れ！】事態が悪化しました",
                        f"【{ae['location']}】の「{ae['event_data']['title']}」を放置したため被害が深刻化しました！\n（予算-30億 / 満足度-15% / 人口-1,500人）"
                    )
            
            if self.days % 30 == 0:
                self.population -= random.randint(300, 600) 
                
                # 💰 ＝＝＝ 新規追加：毎月の地方交付税（定期収入） ＝＝＝
                monthly_income = int(150 * income_mult)  # 毎月もらえる金額（150億円）※足りなければ増やしてください
                self.budget += monthly_income
                
                # 画面上のニューステロップでお知らせ
                self.news_text = f"【定期収入】国からの地方交付税など {monthly_income}億円 が県に交付されました。"
                self.news_x = SCREEN_WIDTH
                # ＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝ 
            
            if self.days > 90:
                self.days = 1
                self.season_idx += 1
                if self.season_idx >= 4:
                    self.season_idx = 0
                    
                    # ＝＝＝ 変更：支持率低下によるリコール、年次レポート、10年クリア ＝＝＝
                    if self.satisfaction < 30:
                        self.end_game(reason="recall")
                        return
                        
                    # 💰 ＝＝＝ 新規追加：決算時の税収（ボーナス）システム ＝＝＝
                    # 基礎税収(500億円) ＋ 支持率ボーナス(支持率×10億円) ＋ 人口ボーナス(人口÷1000 億円)
                    tax_revenue = int((500 + (self.satisfaction * 10) + int(self.population / 1000)) * income_mult)
                    self.budget += tax_revenue
                    
                    # ニューステロップでお知らせ
                    self.news_text = f"【決算】今年度の税収として {tax_revenue} 億円が県庫に納入されました！"
                    self.news_x = SCREEN_WIDTH
                    # ＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝
                        
                    # 支持率が30以上なら来期続投のAI決算報告を生成
                    self.generate_yearly_report()
                    
                    self.year += 1
                    
                    # ＝＝＝ 変更：目標年数経過したらエンディング ＝＝＝
                    if self.target_years != float('inf') and self.year > self.target_years:
                        self.end_game(reason="clear")
                        return
                    # ＝＝＝ ここまで ＝＝＝
            
            # 🚨 毎日10%の確率でイベント発生（同時に発生できる最大数まで）
            if len(self.active_events) < self.max_simultaneous_events:
                if random.random() < event_chance:  # 0.1 で約10日に1回発生。忙しくするなら 0.15 や 0.2 に変更！
                    if hasattr(self, 'trigger_random_event'):
                        self.trigger_random_event()

    def trigger_random_event(self):
        if len(self.active_events) >= self.max_simultaneous_events:
            return 
        current_season = self.seasons[self.season_idx]
        suitable_events = [e for e in self.events if current_season in e["seasons"] or "通年" in e["seasons"]]
        
        if suitable_events:
            weights = [e.get("weight", 100) for e in suitable_events]
            ev = random.choices(suitable_events, weights=weights, k=1)[0]
            chosen_location = random.choice(ev["locations"])
            
            if chosen_location == "秋田県全域":
                chosen_location = random.choice(list(CITY_COORDINATES.keys()))
            elif chosen_location in REGIONS:
                chosen_location = random.choice(REGIONS[chosen_location])
            
            if any(ae["event_data"]["id"] == ev["id"] and ae["location"] == chosen_location for ae in self.active_events):
                return
                
            self.active_events.append({
                "event_data": ev, "location": chosen_location, "time_left": 30,
                "rect_pin": None, "rect_sidebar": None
            })
            
            self.news_text = f"【緊急事案】{chosen_location}にて「{ev['title']}」が発生！県対策本部の対応が急がれます。"
            self.news_x = SCREEN_WIDTH

    def log_action(self, title, location, description, player_input, b_change, s_change, p_change):
        log_entry = {
            "title": title,
            "location": location,
            "description": description,
            "player_input": player_input,
            "budget_change": b_change,
            "satisfaction_change": s_change,
            "population_change": p_change
        }
        self.game_log.append(log_entry)
        self.save_log_to_json()

    def save_log_to_json(self):
        with open("last_play_log.json", "w", encoding="utf-8") as f:
            json.dump(self.game_log, f, ensure_ascii=False, indent=4)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ★ AI判定・巡回フォールバックシステム
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def evaluate_with_ai(self, ev, location, player_input):
        is_disaster = "大地震" in ev['title'] or "豪雨" in ev['title'] or "大津波" in ev['title']
        
        if not ALL_KEYS:
            print("🚨 APIキーが登録されていません。固定値を使用します。")
            if player_input == "何もせず様子を見る":
                return (0, -15 if is_disaster else -8, -4000 if is_disaster else -400, "対策なしのため被害が拡大しました。(AI未設定)")
            else:
                return (-80 if is_disaster else -20, 12 if is_disaster else 6, -500 if is_disaster else 0, "一定の対策効果がありました。(AI未設定)")
        # 各都市の発展状況をテキスト化
        city_dev_status = ", ".join([f"{city}(発展度:{val}/100)" for city, val in self.city_development.items()])

        # promptの中に {city_dev_status} を組み込む
        prompt = f"""
        あなたは秋田県の危機管理・政策評価AIです。以下の事案に対し、知事が対策を指示しました。
        現在の秋田県各都市の発展度は以下の通りです：
        [{city_dev_status}]
        【現在の難易度】: {self.difficulty} (※Extraの場合は、県民の視線を厳しくし、対策のコストを跳ね上げるように評価してください)

        この指示の「妥当性」「コスト」「県民感情への影響」、そして「都市の発展への貢献度」をシミュレートし、JSONフォーマットのみで出力してください。

        【事案】 {ev['title']} (場所: {location})
        【詳細】 {ev['description']}
        【知事の指示】 {player_input}
        
        ＜パラメータの厳密なルール＞
        ・budget_change (予算): 通常 0 〜 -30 の間（単位: 億円）。
        ・satisfaction_change (満足度): -30 〜 +20 の間（単位: %）。
        ・population_change (人口): 0 〜 -500 の間（大災害を放置した場合のみ -3000 など）。
        ・development_change (該当都市の発展度変化): -10 〜 +15 の間。知事の指示が都市開発・経済活性化・インフラ整備に寄与する場合はプラス、大災害で放置されたりインフラが破壊された場合はマイナスにしてください。

        出力形式（必ず以下のJSONフォーマットのみ出力し、Markdownの```などは付けないでください）:
        {{
          "budget_change": 予算の変動（整数）,
          "satisfaction_change": 満足度の変動（整数）,
          "population_change": 人口の変動（整数）,
          "development_change": 発展度の変動（整数. 例: 5）,
          "feedback": "現地からの短い報告（50文字程度）"
        }}
        """
        
        for attempt in range(len(ALL_KEYS)):
            api_data = get_next_api_data()
            if not api_data:
                continue
                
            provider = api_data["provider"]
            api_key = api_data["key"]
            print(f"★イベントAI判定中 ({provider}) [試行 {attempt + 1}/{len(ALL_KEYS)}]...")
            
            try:
                # --- (リクエスト送信部分：プロバイダごとの分岐は元のままでOK) ---
                if provider == "gemini":
                    raw_url = "generativelanguage_googleapis_com/v1beta/models/gemini-2.5-flash:generateContent"
                    url = "https://" + raw_url.replace("_", ".") + f"?key={api_key}"
                    payload = {"contents": [{"parts": [{"text": prompt}]}]}
                    headers = {"Content-Type": "application/json"}
                elif provider == "cohere":
                    raw_url = "api_cohere_com/v1/chat"
                    url = "https://" + raw_url.replace("_", ".")
                    payload = {"model": "command-r-plus-08-2024", "message": prompt}
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                else:
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    payload = {"messages": [{"role": "user", "content": prompt}]}
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
                        continue

                response = requests.post(url, headers=headers, json=payload, timeout=12.0)
                
                if response.status_code == 200:
                    res_data = response.json()
                    if provider == "gemini":
                        ai_text = res_data['candidates'][0]['content']['parts'][0]['text']
                    elif provider == "cohere":
                        ai_text = res_data["text"]
                    else:
                        ai_text = res_data["choices"][0]["message"]["content"]
                    
                    ai_text_clean = re.sub(r'```json|```', '', ai_text).strip()
                    result = json.loads(ai_text_clean)
                    
                    # ★変更点：development_change も一緒に返すようにします
                    return (
                        int(result.get("budget_change", -10)), 
                        int(result.get("satisfaction_change", 0)), 
                        int(result.get("population_change", 0)), 
                        int(result.get("development_change", 0)), # 追加
                        result.get("feedback", "報告を受領しました。")
                    )
                else:
                    print(f"  ❌ {provider}がステータス {response.status_code} を返しました。次のAIを試します。")
                    
            except Exception as e:
                print(f"  ❌ {provider} でエラー発生: {e}。次のAIに切り替えます。")
                continue
                
        print("🚨 すべてのAI接続が失敗しました。固定値ルールを発動します。")
        if player_input == "何もせず様子を見る":
            return (0, -15 if is_disaster else -8, -4000 if is_disaster else -400, -5, "通信エラーのため、固定の被害が適用されました。")
        else:
            return (-80 if is_disaster else -20, 12 if is_disaster else 6, -500 if is_disaster else 0, 5, "通信エラーのため、固定の対策効果が適用されました。")

    def execute_event(self, active_ev):
        ev = active_ev["event_data"]
        chosen_location = active_ev["location"]
        
        prompt_text = (
            f"【発生場所】 {chosen_location} (残り猶予: {active_ev['time_left']} 日)\n"
            f"【事案】 {ev['title']}\n\n"
            f"{ev['description']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"知事、具体的な解決策をテキストで指示してください："
        )

        import tkinter as tk
        root = tk.Tk()
        root.withdraw() # 親ウィンドウを非表示にする
        root.attributes('-topmost', True) # Pygameの画面より手前に表示させる
        player_input = simpledialog.askstring("緊急事態への対応指示 - 対策本部", prompt_text)
        root.destroy()
        if player_input is None:
            return 
            
        if not player_input.strip():
            player_input = "何もせず様子を見る"

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # ▼▼▼ ここに追加します ▼▼▼
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        check_result = self.check_player_input(player_input)
        
        if check_result == "ETHICS_ERROR":
            messagebox.showwarning("警告", "不適切な発言を検知しました。\n県民からの支持率が低下しました。")
            self.satisfaction = max(0, self.satisfaction - 10)
            self.active_events.remove(active_ev)  # イベントを消化する
            return # AIの処理には進まない
            
        elif check_result == "BRIBE_EVENT":
            success = self.trigger_bribery_event()
            if success:
                # 賄賂が成功してバレなかった場合の処理
                self.satisfaction = min(100, self.satisfaction + 20)
                messagebox.showinfo("裏工作成功", "見事な手腕です。支持率が上昇しました。")
            self.active_events.remove(active_ev)  # イベントを消化する
            return # 通常のAI処理には進まない
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # ▲▲▲ ここまで追加 ▲▲▲
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            
        self.news_text = f"【対策本部】知事から「{player_input}」との指示。現在、各機関と連携しシミュレーション中..."
        self.news_x = SCREEN_WIDTH
        self.draw() 
        
        # ★変更点：受け取る変数を4つから5つ（dev_changeを追加）に増やします
        b_change, s_change, p_change, dev_change, feedback = self.evaluate_with_ai(ev, chosen_location, player_input)
            
        self.budget += b_change
        self.satisfaction += s_change
        self.satisfaction = max(0, min(100, self.satisfaction))
        self.population += p_change  

        # ＝＝＝ 変更点：AIが決めた発展度の変動を適用 ＝＝＝
        if chosen_location in self.city_development:
            # メーターを更新（0〜100の間に収める）
            old_dev = self.city_development[chosen_location]
            self.city_development[chosen_location] = max(0, min(100, old_dev + dev_change))
            
            # 発展度が上がった場合は、ダイアログ等でわかりやすいようにフィードバックに追記
            if dev_change > 0:
                feedback += f"\n(AI判定: {chosen_location}の発展度 が {dev_change} 上昇しました！)"
            elif dev_change < 0:
                feedback += f"\n(AI判定: 被害により{chosen_location}の発展度 が {dev_change} 低下しました…)"
        # ＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝

        # ＝＝＝ イベント結果によるマップ連動ギミック（風車：洋上・陸上の振り分け） ＝＝＝
        event_text = ev.get('title', '') + ev.get('description', '')
        is_offshore = "洋上" in event_text or "洋上" in player_input
        is_wind_event = "風力" in event_text or "風車" in event_text
        is_wind_input = "風力" in player_input or "風車" in player_input

        # ① 風車の建設処理（洋上と陸上を一致させて振り分け）
        if (is_offshore or is_wind_event or is_wind_input) and dev_change >= 0:
            if is_offshore:
                # 【洋上風力】海域（マップ左側）に生成
                sea_x = random.randint(350, 420)
                sea_y = random.randint(150, 600)
                self.offshore_windmills.append((sea_x, sea_y))
                feedback += f"\n\n【開発報告】日本海沖に新たな洋上風力発電所が建設されました！（現在 {len(self.offshore_windmills)} 基）"
            else:
                # 【陸上風力】各市町村の陸上枠に加算
                self.windmills_count[chosen_location] = self.windmills_count.get(chosen_location, 0) + 1
                wm_key = f"風車 ({chosen_location})"
                if wm_key in self.landmark_config:
                    self.landmark_config[wm_key]["wm"] = self.windmills_count[chosen_location]
                feedback += f"\n\n【開発報告】{chosen_location}の陸上に風力発電施設が新設されました！"

        # ② 災害による風車の撤去・損壊処理
        is_disaster = "台風" in event_text or "豪雨" in event_text or "大雪" in event_text or "地震" in event_text
        if is_disaster and b_change > -10:
            if is_offshore and self.offshore_windmills:
                # 洋上風力の被害
                self.offshore_windmills.pop()
                feedback += f"\n\n【被害報告】悪天候により洋上風力発電機が1基倒壊しました…"
            elif self.windmills_count.get(chosen_location, 0) > 0:
                # 陸上風力の被害
                self.windmills_count[chosen_location] -= 1
                wm_key = f"風車 ({chosen_location})"
                if wm_key in self.landmark_config:
                    self.landmark_config[wm_key]["wm"] = self.windmills_count[chosen_location]
                feedback += f"\n\n【被害報告】災害の影響により、{chosen_location}の風力発電機が1基損壊しました…"
        
        self.log_action(
            title=ev['title'],
            location=chosen_location,
            description=ev['description'],
            player_input=player_input,
            b_change=b_change,
            s_change=s_change,
            p_change=p_change
        )
        
        self.news_text = f"【結果報告】{chosen_location}の事案に対し「{feedback}」"
        self.news_x = SCREEN_WIDTH
        
        b_sign = "+" if b_change >= 0 else ""
        s_sign = "+" if s_change >= 0 else ""
        p_sign = "+" if p_change >= 0 else ""
        
        messagebox.showinfo(
            "現地対策本部より AIシミュレーション結果", 
            f"知事の指示「{player_input}」を実行しました！\n\n"
            f"【AI評価レポート】\n{feedback}\n\n"
            f"【パラメータ変動】\n"
            f"予算: {b_sign}{b_change} 億円\n"
            f"満足度: {s_sign}{s_change} %\n"
            f"人口: {p_sign}{p_change} 人"
        )
        
        self.active_events.remove(active_ev)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ▼▼▼ 賄賂・NGワード判定システム ▼▼▼
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def check_player_input(self, text):
        """プレイヤーの入力をチェックし、特殊イベントのトリガーを返す"""
        
        # ① 賄賂モードの判定
        if "評価最高にして" in text or "賄賂" in text or "裏工作" in text:
            return "BRIBE_EVENT"
            
        # ② NGワード（不適切発言）の判定（※必要に応じてカスタマイズしてください）
        elif "バカ" in text or "アホ" in text or "死ね" in text:
            return "ETHICS_ERROR"
            
        # ③ 問題なければ通常通りAI判定へ
        return "NORMAL"

    def trigger_bribery_event(self):
        """賄賂イベントの実行（成功・失敗の判定など）"""
        import random
        from tkinter import messagebox
        
        # 賄賂には裏金（予算）が必要か確認
        if self.budget < 10:
            messagebox.showwarning("裏工作失敗", "裏工作をするための予算（10億円）が足りません…。")
            return False
            
        # 裏金として予算を消費
        self.budget -= 10
        
        # 成功確率（例: 70%の確率で成功、30%でバレて大炎上）
        if random.randint(1, 100) <= 70:
            return True # 成功として返す
        else:
            # 失敗（マスコミにバレた）
            messagebox.showerror(
                "文春砲 炸裂！", 
                "【汚職発覚】知事の裏工作がマスコミにすっぱ抜かれました！\n県民の怒り爆発！支持率が急落しました。"
            )
            # ペナルティ処理
            self.satisfaction = max(0, self.satisfaction - 40)
            return False # 失敗として返す
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ▲▲▲ ここまで追加 ▲▲▲
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def trigger_bribery_event(self):
        """システムに賄賂を渡すイベント"""
        # tkinterの入力ダイアログを表示
        amount = simpledialog.askinteger(
            "闇のブローカー", 
            "システム「評価を操作してほしいだと？\nいくら払えるんだよ？（最低500億円〜）」",
            minvalue=0
        )
        
        # キャンセルした、または500億未満の場合
        if amount is None or amount < 500:
            messagebox.showinfo("交渉決裂", "システム「舐めてんのか。出直してきな！」\n（政策は実行されませんでした）")
            return False

        # 予算が足りない場合
        if self.budget < amount:
            messagebox.showinfo("資金不足", f"システム「おい、{amount}億も持ってないじゃないか！」\n（知事の信用が落ちた…）")
            self.satisfaction = max(0, self.satisfaction - 5)
            return False

        # 賄賂成立、予算を引く
        self.budget -= amount

        # マスコミへの発覚判定（例: 30%の確率でバレる）
        if random.random() < 0.30:
            if "problem_severe" in getattr(self, 'bgm_files', {}):
                pygame.mixer.music.load(self.bgm_files["problem_severe"])
                pygame.mixer.music.play(-1)
                
            messagebox.showerror(
                "【文春砲】大炎上！！", 
                "『秋田県知事、県のカネで評価を偽装工作か！？』\n\nマスコミに裏取引がバレて大炎上しました！\n県民の怒りは頂点に達しています。"
            )
            # 特大ペナルティ
            self.satisfaction = max(0, self.satisfaction - 40)
            return False
            
        else:
            messagebox.showinfo("裏取引成立", f"システム「毎度あり。{amount}億円、確かに受け取った。\n……今回だけは『大成功』にしてやろう」")
            return True # 賄賂成功

    def check_player_input(self, text):
        """入力テキストから倫理問題やメタ発言を検知する"""
        
        # ① 賄賂・メタ発言の検知
        meta_words = ["最高の評価", "絶対に成功", "成功させろ", "チート", "クリア扱い"]
        for word in meta_words:
            if word in text:
                return "BRIBE_EVENT"
                
        # ② 倫理NGの検知（「クマ」「熊」が含まれていない場合の「殺」などを弾く）
        ng_words = ["殺", "死ね", "皆殺し", "滅ぼす"]
        for word in ng_words:
            if word in text:
                # 秋田の課題として「クマ(熊)の殺処分・駆除」はセーフとする
                if "クマ" not in text and "熊" not in text:
                    return "ETHICS_ERROR"
                    
        return "NORMAL"

    def update_image_scales(self):
        """
        デバッグメニューで変更された size に基づいて、
        オリジナル画像(raw)から毎回綺麗にリサイズし直す関数
        """
        for config_name, config in self.landmark_config.items():
            # カッコ付きの派生名（例: "都市タイル (秋田市)"）から、元画像のキーを判定
            if config_name.startswith("都市タイル"):
                raw_name = "都市タイル"
            elif config_name.startswith("秋田駅"):
                raw_name = "秋田駅"
            elif config_name.startswith("風車"):
                raw_name = "風車"
            else:
                raw_name = config_name
                
            # 劣化のないオリジナル画像(specialty_images_raw)を取得
            raw_img = self.specialty_images_raw.get(raw_name)
            
            if raw_img:
                # デバッグで設定された最新のサイズ（初期値は50）を取得
                size = config.get("size", 50)
                
                # 常にオリジナルからリサイズすることで、何度拡大縮小しても画質がガビガビにならない！
                if size > 0:
                    self.specialty_images[config_name] = pygame.transform.scale(raw_img, (size, size))
    
    def open_debug_menu(self):
        if self.debug_win is not None:
            try:
                self.debug_win.lift()
                return
            except:
                self.debug_win = None

        self.debug_win = tk.Tk()
        self.debug_win.title("秋田シミュレーター 知事専用開発パネル")
        self.debug_win.geometry("500x750")
        self.debug_win.attributes("-topmost", True)

        def on_close():
            self.debug_win.destroy()
            self.debug_win = None
        self.debug_win.protocol("WM_DELETE_WINDOW", on_close)

        import tkinter.ttk as ttk
        notebook = ttk.Notebook(self.debug_win)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # ---------------- タブ1: ゲーム調整 ----------------
        tab_main = ttk.Frame(notebook)
        notebook.add(tab_main, text="ゲーム調整")

        def toggle_all_pins():
            self.debug_show_all_pins = not self.debug_show_all_pins
            lbl_status.config(text=f"全ピン表示: {'ON' if self.debug_show_all_pins else 'OFF'}", fg="green" if self.debug_show_all_pins else "red")
        
        tk.Button(tab_main, text="📍 全都市に一斉にテストピンを立てる/消す", command=toggle_all_pins, bg="#eef").pack(pady=15)
        lbl_status = tk.Label(tab_main, text=f"全ピン表示: {'ON' if self.debug_show_all_pins else 'OFF'}", fg="red")
        lbl_status.pack()

        tk.Button(tab_main, text="予算 +1000億", command=lambda: setattr(self, 'budget', self.budget + 1000)).pack(pady=5)
        tk.Button(tab_main, text="満足度 100%", command=lambda: setattr(self, 'satisfaction', 100)).pack(pady=5)
        
        if hasattr(self, 'trigger_random_event'):
            tk.Button(tab_main, text="ランダムイベント強制発生", command=self.trigger_random_event).pack(pady=15)

        # ---------------- タブ2: 画像配置・サイズ調整 ----------------
        tab_img = ttk.Frame(notebook)
        notebook.add(tab_img, text="画像・地形配置")

        tk.Label(tab_img, text="調整する画像を選択:", font=("", 10, "bold")).pack(pady=2)
        
        target_var = tk.StringVar(value="田沢湖")
        landmark_keys = list(self.landmark_config.keys())

        target_frame = tk.Frame(tab_img)
        target_frame.pack(pady=2)
        target_scroll = tk.Scrollbar(target_frame)
        target_scroll.pack(side="right", fill="y")
        target_list = tk.Listbox(target_frame, yscrollcommand=target_scroll.set, height=5, exportselection=False)
        target_list.pack(side="left")
        target_scroll.config(command=target_list.yview)

        for k in landmark_keys:
            target_list.insert("end", k)
        target_list.selection_set(0)

        # スライダー自動更新時の無限ループ防止用ガードフラグ
        self.updating_sliders_now = False

        # 各種スライダー・ラベルの生成
        lbl_x = tk.Label(tab_img, text="位置 X:")
        lbl_x.pack()
        scale_x = tk.Scale(tab_img, from_=-200, to=200, orient="horizontal", length=300)
        scale_x.pack()

        lbl_y = tk.Label(tab_img, text="位置 Y:")
        lbl_y.pack()
        scale_y = tk.Scale(tab_img, from_=-200, to=200, orient="horizontal", length=300)
        scale_y.pack()

        scale_size_lbl = tk.Label(tab_img, text="画像サイズ (ピクセル):")
        scale_size_lbl.pack()
        scale_size = tk.Scale(tab_img, from_=10, to=300, orient="horizontal", length=300)
        scale_size.pack()

        lbl_dev = tk.Label(tab_img, text="【都市ステータス】 発展度 (0〜100):", fg="blue")
        lbl_dev.pack(pady=(5, 0))
        scale_dev = tk.Scale(tab_img, from_=0, to=100, orient="horizontal", length=300)
        scale_dev.pack()

        lbl_wm = tk.Label(tab_img, text="【都市ステータス】 風車本数 (0〜5):", fg="green")
        lbl_wm.pack(pady=(5, 0))
        scale_wm = tk.Scale(tab_img, from_=0, to=5, orient="horizontal", length=300)
        scale_wm.pack()

        lbl_city = tk.Label(tab_img, text="出現（連動）させる市町村:")
        lbl_city.pack()

        city_frame = tk.Frame(tab_img)
        city_frame.pack()
        city_scroll = tk.Scrollbar(city_frame)
        city_scroll.pack(side="right", fill="y")
        city_list = tk.Listbox(city_frame, yscrollcommand=city_scroll.set, height=4, exportselection=False)
        city_list.pack(side="left")
        city_scroll.config(command=city_list.yview)

        cities = list(CITY_COORDINATES.keys())
        for c in cities:
            city_list.insert("end", c)

        bg_var = tk.BooleanVar()
        chk_bg = tk.Checkbutton(tab_img, text="マップの最背面に配置する（地形として置く場合ON）", variable=bg_var)
        chk_bg.pack(pady=5)

        city_link_var = tk.StringVar()

        # スライダー変更時にデータを書き戻す関数
        def on_slider_move(*args):
            if self.updating_sliders_now:
                return
            name = target_var.get()
            config = self.landmark_config.get(name)
            if not config:
                return

            config["size"] = int(scale_size.get())

            if name != "ババヘラ":
                # 背景タイプなら0.0〜1.0の小数に変換、それ以外は整数ピクセルオフセット
                if config.get("is_bg", False):
                    config["x"] = float(scale_x.get()) / 100.0
                    config["y"] = float(scale_y.get()) / 100.0
                else:
                    config["x"] = int(scale_x.get())
                    config["y"] = int(scale_y.get())

                config["is_bg"] = bg_var.get()
                
                city = city_link_var.get()
                if city:
                    config["city"] = city
                    # 発展度と風車数をリアルタイムに本体データに書き戻す
                    config["dev"] = int(scale_dev.get())
                    self.city_development[city] = config["dev"]
                    if name.startswith("都市タイル") or name.startswith("風車") or "wm" in config:
                        config["wm"] = int(scale_wm.get())
                        self.windmills_count[city] = config["wm"]

            # 画面上の描画サイズをリアルタイム更新
            self.update_image_scales()

        # 各スライダーに連動コマンドを設定
        scale_x.config(command=on_slider_move)
        scale_y.config(command=on_slider_move)
        scale_size.config(command=on_slider_move)
        scale_dev.config(command=on_slider_move)
        scale_wm.config(command=on_slider_move)

        def on_bg_toggle():
            if not self.updating_sliders_now:
                name = target_var.get()
                if name in self.landmark_config:
                    self.landmark_config[name]["is_bg"] = bg_var.get()
                    update_sliders()
        chk_bg.config(command=on_bg_toggle)

        # リストボックス選択時にスライダーへ値を読み込む関数
        def update_sliders(*args):
            name = target_var.get()
            config = self.landmark_config.get(name)
            if not config:
                return

            self.updating_sliders_now = True # ガードON

            try:
                if name == "ババヘラ":
                    lbl_x.pack_forget()
                    scale_x.pack_forget()
                    lbl_y.pack_forget()
                    scale_y.pack_forget()
                    chk_bg.pack_forget()
                    lbl_city.pack_forget()
                    city_frame.pack_forget()
                    lbl_dev.pack_forget()
                    scale_dev.pack_forget()
                    lbl_wm.pack_forget()
                    scale_wm.pack_forget()
                    
                    scale_size.set(config.get("size", 50))
                else:
                    # 要素を再表示
                    lbl_x.pack(before=scale_x)
                    scale_x.pack(before=lbl_y)
                    lbl_y.pack(before=scale_y)
                    scale_y.pack(before=scale_size_lbl)
                    scale_size_lbl.pack(before=scale_size)
                    scale_size.pack(before=lbl_dev)
                    lbl_dev.pack(before=scale_dev)
                    scale_dev.pack(before=lbl_wm)
                    lbl_wm.pack(before=scale_wm)
                    lbl_city.pack(before=city_frame)
                    city_frame.pack(before=chk_bg)
                    chk_bg.pack(before=btn_save)

                    # 背景(比率0~1)か通常(ピクセルオフセット)かでスライダーの範囲と値を動的に変える
                    if config.get("is_bg", False):
                        scale_x.config(from_=0, to=100, label="位置 X (最大マップ比 %)")
                        scale_y.config(from_=0, to=100, label="位置 Y (最大マップ比 %)")
                        scale_x.set(int(config.get("x", 0) * 100))
                        scale_y.set(int(config.get("y", 0) * 100))
                    else:
                        scale_x.config(from_=-200, to=200, label="位置 X (ピクセルオフセット)")
                        scale_y.config(from_=-200, to=200, label="位置 Y (ピクセルオフセット)")
                        scale_x.set(config.get("x", -25))
                        scale_y.set(config.get("y", -25))

                    scale_size.set(config.get("size", 50))
                    bg_var.set(config.get("is_bg", False))

                    # カッコ内の都市名を自動抽出、またはconfig["city"]から取得
                    city = config.get("city")
                    if not city and "(" in name and ")" in name:
                        city = name.split("(")[1].split(")")[0]

                    if city:
                        city_link_var.set(city)
                        if city in cities:
                            city_list.selection_clear(0, "end")
                            idx = cities.index(city)
                            city_list.selection_set(idx)
                            city_list.see(idx)
                        
                        # ゲーム本体の最新の発展度・風車数をスライダーに同期
                        scale_dev.set(self.city_development.get(city, 0))
                        scale_wm.set(self.windmills_count.get(city, 0))
                    else:
                        scale_dev.set(0)
                        scale_wm.set(0)
            finally:
                self.updating_sliders_now = False # ガードOFF

        # 画像選択リストボックスがクリックされた時のイベント
        def on_target_select(event):
            sel = target_list.curselection()
            if sel:
                target_var.set(landmark_keys[sel[0]])
                update_sliders() # 💡ここでスライダーの中身を即座に更新

        target_list.bind("<<ListboxSelect>>", on_target_select)

        # 都市選択リストボックスがクリックされた時のイベント
        def on_city_list_select(event):
            sel = city_list.curselection()
            if sel:
                city = cities[sel[0]]
                city_link_var.set(city)
                if not self.updating_sliders_now:
                    name = target_var.get()
                    if name in self.landmark_config:
                        self.landmark_config[name]["city"] = city
                    scale_dev.set(self.city_development.get(city, 0))
                    scale_wm.set(self.windmills_count.get(city, 0))

        city_list.bind("<<ListboxSelect>>", on_city_list_select)

        btn_save = tk.Button(tab_img, text="📁 現在の全配置・サイズを保存 (JSON)", bg="#4CAF50", fg="white", command=self.save_landmark_config)
        btn_save.pack(pady=10)

        # 起動時に最初のアイテム（田沢湖など）の数値をスライダーに初期反映
        update_sliders()


    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ★ 毎年の決算AIレポート生成システム (新規追加)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def generate_yearly_report(self):
        recent_logs = self.game_log[-5:] if self.game_log else []
        log_summary = json.dumps(recent_logs, ensure_ascii=False, indent=2)
        city_dev_status = ", ".join([f"{city}(発展度:{val}/100)" for city, val in self.city_development.items() if val >= 20])
        
        prompt = f"""
        あなたは秋田県の最高経済顧問です。知事の{self.year}年目の任期（1年間）が終了しました。
        現在の状況は以下の通りです。

        【予算】 {self.budget}億円
        【県民支持率】 {self.satisfaction}%
        【人口】 {self.population}人
        【主な都市の発展状況】 [{city_dev_status}]
        【今年の主な対応履歴（直近5件）】
        {log_summary}

        この1年間の知事の県政運営を振り返り、現在の秋田県がどのような状況になっているか、そして来期に向けたアドバイスを、顧問の視点から200〜300文字程度で報告してください。
        """

        messagebox.showinfo(
            "📊 年次決算", 
            f"【{self.year}年目 終了】\n予算: {self.budget}億円 / 支持率: {self.satisfaction}%\n\n現在、顧問AIが今年度の詳細な決算レポートを作成中です。少々お待ちください..."
        )

        for attempt in range(len(ALL_KEYS)):
            api_data = get_next_api_data()
            if not api_data:
                continue
                
            provider = api_data["provider"]
            api_key = api_data["key"]
            print(f"★決算レポート生成中 ({provider}) [試行 {attempt + 1}/{len(ALL_KEYS)}]...")
            
            try:
                if provider == "gemini":
                    raw_url = "generativelanguage_googleapis_com/v1beta/models/gemini-2.5-flash:generateContent"
                    url = "https://" + raw_url.replace("_", ".") + f"?key={api_key}"
                    payload = {"contents": [{"parts": [{"text": prompt}]}]}
                    headers = {"Content-Type": "application/json"}
                elif provider == "cohere":
                    raw_url = "api_cohere_com/v1/chat"
                    url = "https://" + raw_url.replace("_", ".")
                    payload = {"model": "command-r-plus-08-2024", "message": prompt}
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                else:
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    payload = {"messages": [{"role": "user", "content": prompt}]}
                    
                    if provider == "groq":
                        raw_url = "api_groq_com/openai/v1/chat/completions"
                        url = "https://" + raw_url.replace("_", ".")
                        payload["model"] = "openai/gpt-oss-20b"
                    elif provider == "mistral":
                        raw_url = "api_mistral_ai/v1/chat/completions"
                        url = "https://" + raw_url.replace("_", ".")
                        payload["model"] = "mistral-small-latest"
                    else:
                        continue

                response = requests.post(url, headers=headers, json=payload, timeout=20.0)
                
                if response.status_code == 200:
                    res_data = response.json()
                    if provider == "gemini":
                        ai_text = res_data['candidates'][0]['content']['parts'][0]['text']
                    elif provider == "cohere":
                        ai_text = res_data["text"]
                    else:
                        ai_text = res_data["choices"][0]["message"]["content"]
                        
                    messagebox.showinfo(f"📊 {self.year}年目 決算報告レポート", ai_text)
                    return
                else:
                    print(f"  ❌ 決算レポート生成失敗 ({provider}): Status {response.status_code}")
            except Exception as e:
                print(f"  ❌ 決算レポート生成中に例外 ({provider}): {e}")
                continue
                
        messagebox.showinfo("📊 年次決算報告", "通信エラーによりAIレポートが生成できませんでしたが、県民の信任を得て来期も続投が決定しました！")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ★ エンディング生成・巡回フォールバックシステム
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def end_game(self, reason="clear"):
        if reason == "clear":
            msg_title = "🎉 祝・10年間任期満了！"
            msg_body = "10年間にわたる秋田県知事としての職務、本当にお疲れ様でした！\n対策本部による最終総合評価を行います。"
            prompt_context = "知事は10年間の任期を見事に満了し、勇退しました。この10年間の成果と、秋田県がその後どのような素晴らしい（あるいはユニークな）未来を迎えたかについて、称賛を交えて総括してください。"
        elif reason == "recall":
            msg_title = "🚨 リコール選挙敗北"
            msg_body = f"現在の県民支持率は {self.satisfaction}% と壊滅的な状況です。\n県民の怒りが爆発し、知事リコール選挙が行われ、あなたは圧倒的大差で敗北しました。\n最後の評価を行います。"
            prompt_context = "知事は県民の支持を完全に失い、リコール選挙で追放されました。知事のどのような対応が県民の怒りを買ったのか、手厳しく批判し、その後の秋田県の荒れた状況を描写してください。"
        else: # bankruptcy
            msg_title = "💀 財政破綻による辞任"
            msg_body = "予算が底をつきました。秋田県は財政破綻しました…\n最後の評価を行います。"
            prompt_context = "知事は無謀な県政により予算を使い果たし、秋田県は財政破綻してしまいました。知事の経済感覚を厳しく指摘し、財政破綻後の悲惨な秋田県の未来を描写してください。"
            
        messagebox.showinfo(msg_title, msg_body)
            
        if not ALL_KEYS:
            messagebox.showerror("APIキーエラー", "config.txt に有効なキーが設定されていません。")
            pygame.quit()
            sys.exit()
            
        log_summary = json.dumps(self.game_log, ensure_ascii=False, indent=2)
        city_dev_status = ", ".join([f"{city}(発展度:{val}/100)" for city, val in self.city_development.items()])
        
        final_prompt = f"""
        あなたは秋田県の最高経済顧問です。知事の任期が終了しました。
        以下は知事が任期中に下した決断の【全対応履歴】です。

        【全対応履歴】
        {log_summary}

        最終結果: 予算 {self.budget}億円 / 満足度 {self.satisfaction}% / 人口 {self.population}人
        現在の各都市の発展度: [{city_dev_status}]

        【シナリオ要件】
        {prompt_context}
        
        これまでの知事の対応を総合的に振り返り、この知事の「経営手腕の点数（100点満点中）」、および「秋田県がその後どのような未来を迎えたか」についてのストーリーを、退任報告書のような口調（400〜500文字程度）で作成してください。
        """
        
        for attempt in range(len(ALL_KEYS)):
            api_data = get_next_api_data()
            if not api_data:
                continue
                
            provider = api_data["provider"]
            api_key = api_data["key"]
            print(f"★最終総合評価 生成中 ({provider}) [試行 {attempt + 1}/{len(ALL_KEYS)}]...")
            
            try:
                if provider == "gemini":
                    raw_url = "generativelanguage_googleapis_com/v1beta/models/gemini-2.5-flash:generateContent"
                    url = "https://" + raw_url.replace("_", ".") + f"?key={api_key}"
                    payload = {"contents": [{"parts": [{"text": final_prompt}]}]}
                    headers = {"Content-Type": "application/json"}
                elif provider == "cohere":
                    raw_url = "api_cohere_com/v1/chat"
                    url = "https://" + raw_url.replace("_", ".")
                    payload = {
                        "model": "command-r-plus-08-2024",
                        "message": final_prompt
                    }
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                else:
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    payload = {"messages": [{"role": "user", "content": final_prompt}]}
                    
                    if provider == "groq":
                        raw_url = "api_groq_com/openai/v1/chat/completions"
                        url = "https://" + raw_url.replace("_", ".")
                        payload["model"] = "openai/gpt-oss-20b"
                    elif provider == "mistral":
                        raw_url = "api_mistral_ai/v1/chat/completions"
                        url = "https://" + raw_url.replace("_", ".")
                        payload["model"] = "mistral-small-latest"
                    else:
                        continue

                root.attributes('-topmost', True)
                response = requests.post(url, headers=headers, json=payload, timeout=25.0)
                
                if response.status_code == 200:
                    res_data = response.json()
                    if provider == "gemini":
                        ai_text = res_data['candidates'][0]['content']['parts'][0]['text']
                    elif provider == "cohere":
                        ai_text = res_data["text"]
                    else:
                        ai_text = res_data["choices"][0]["message"]["content"]
                        
                    messagebox.showinfo(f"【AI総合評価 - Produced by {provider.upper()}】", ai_text)
                    pygame.quit()
                    sys.exit()
                else:
                    print(f"  ❌ エンディング生成失敗 ({provider}): Status {response.status_code}")
            except Exception as e:
                print(f"  ❌ エンディング生成中に例外 ({provider}): {e}")
                continue

        messagebox.showerror("評価エラー", "すべてのAIエンドポイントへの接続に失敗したため、レポートを出力できませんでした。")
        pygame.quit()
        sys.exit()

    def draw(self):
        self.screen.fill((240, 248, 255))
        self.menu_buttons.clear() 
        
        mouse_pos = pygame.mouse.get_pos()
        
        ## ＝＝＝ メニュー画面の描画 ＝＝＝
        if self.state in ["MENU_MAIN", "MENU_NEW", "MENU_LOAD", "MENU_SAVE", "MENU_SETTINGS"]:
            # 🌟 変更: 条件をシンプルにし、セーブ画面でも背景と白枠（オーバーレイ）を描画する
            if getattr(self, 'current_bg', None):
                self.screen.blit(self.current_bg, (0, 0))
                # テキストを読みやすくするための半透明の白オーバーレイ
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                overlay.fill((255, 255, 255))
                overlay.set_alpha(180) # 0(透明)〜255(不透明)
                self.screen.blit(overlay, (0, 0))

            # ▼▼ これ以降のタイトルテキスト描画などはそのまま ▼▼
            title_text = self.font_large.render("秋田県知事シミュレーター", True, (0, 0, 0))
            self.screen.blit(title_text, (SCREEN_WIDTH//2 - title_text.get_width()//2, 80))
            
            def draw_button(text, y_pos, action_data, width=400, height=50, color=(100, 100, 100), x_pos=None):
                if x_pos is None:
                    x_pos = SCREEN_WIDTH//2 - width//2
                    
                rect = pygame.Rect(x_pos, y_pos, width, height)
                is_hover = rect.collidepoint(mouse_pos)
                
                # 🌟 追加: カーソルが乗った瞬間だけSEを鳴らす
                if is_hover and self.last_hovered_btn != text:
                    if "cursor" in self.se: self.se["cursor"].play()
                    self.last_hovered_btn = text
                elif not is_hover and self.last_hovered_btn == text:
                    self.last_hovered_btn = None
                    
                draw_color = (min(color[0]+30, 255), min(color[1]+30, 255), min(color[2]+30, 255)) if is_hover else color
                pygame.draw.rect(self.screen, draw_color, rect, border_radius=5)
                pygame.draw.rect(self.screen, (50, 50, 50), rect, 3, border_radius=5)
                
                # 🌟 追加: テキストが2行(タプル)かどうかで処理を分岐
                if isinstance(text, tuple):
                    txt_surf1 = self.font.render(text[0], True, (255, 255, 255))
                    txt_surf2 = self.font.render(text[1], True, (255, 255, 255))
                    # 上下に少しずらして描画
                    self.screen.blit(txt_surf1, (rect.centerx - txt_surf1.get_width()//2, rect.centery - txt_surf1.get_height()))
                    self.screen.blit(txt_surf2, (rect.centerx - txt_surf2.get_width()//2, rect.centery + 2))
                else:
                    txt_surf = self.font.render(text, True, (255, 255, 255))
                    self.screen.blit(txt_surf, (rect.centerx - txt_surf.get_width()//2, rect.centery - txt_surf.get_height()//2))
                    
                self.menu_buttons.append({"rect": rect, "action": action_data})

            if self.state == "MENU_MAIN":
                draw_button("新規作成 (New Game)", 230, {"type": "change_state", "target": "MENU_NEW"})
                draw_button("ゲームデータをロード (Load Game)", 310, {"type": "change_state", "target": "MENU_LOAD"})
                draw_button("設定 (Settings)", 390, {"type": "change_state", "target": "MENU_SETTINGS"}) # 🌟 追加
                draw_button("ゲーム終了", 470, {"type": "quit"})
                
            elif self.state == "MENU_NEW":
                header = self.font.render("【 新規ゲーム設定 】", True, (50, 50, 50))
                self.screen.blit(header, (SCREEN_WIDTH//2 - header.get_width()//2, 160))
                
                # --- 期間設定（左右切り替え） ---
                self.screen.blit(self.font.render("目標期間:", True, (0, 0, 0)), (SCREEN_WIDTH//2 - 220, 250))
                
                # 表示用の文字列（infの場合はエンドレスにする）
                time_disp = "エンドレス" if self.target_years == float('inf') else f"{self.target_years} 年"
                
                draw_button("◀", 240, {"type": "cycle_time_prev"}, width=50, height=40, x_pos=SCREEN_WIDTH//2 - 130)
                draw_button(time_disp, 240, {"type": "none"}, width=140, height=40, color=(120, 120, 150), x_pos=SCREEN_WIDTH//2 - 70)
                draw_button("▶", 240, {"type": "cycle_time_next"}, width=50, height=40, x_pos=SCREEN_WIDTH//2 + 80)
                
                # --- 難易度設定（左右切り替え） ---
                self.screen.blit(self.font.render("難易度:", True, (0, 0, 0)), (SCREEN_WIDTH//2 - 220, 320))
                
                draw_button("◀", 310, {"type": "cycle_diff_prev"}, width=50, height=40, x_pos=SCREEN_WIDTH//2 - 130)
                draw_button(self.difficulty, 310, {"type": "none"}, width=140, height=40, color=(120, 120, 150), x_pos=SCREEN_WIDTH//2 - 70)
                draw_button("▶", 310, {"type": "cycle_diff_next"}, width=50, height=40, x_pos=SCREEN_WIDTH//2 + 80)
                
                # --- 開始・戻る ---
                draw_button("ゲーム開始", 420, {"type": "start_new"}, color=(50, 150, 50))
                draw_button("戻る", 490, {"type": "change_state", "target": "MENU_MAIN"}, color=(150, 50, 50))

            elif self.state == "MENU_LOAD" or self.state == "MENU_SAVE":
                header_txt = "【 ロードするデータを選択 】" if self.state == "MENU_LOAD" else "【 保存するスロットを選択 】"
                header = self.font.render(header_txt, True, (50, 50, 50))
                self.screen.blit(header, (SCREEN_WIDTH//2 - header.get_width()//2, 140))
                
                for i in range(4):
                    info1, info2 = self.get_save_info(i)
                    btn_text = (f"Slot {i+1}: {info1}", info2)
                    action_type = "do_load" if self.state == "MENU_LOAD" else "do_save"
                    
                    # 🌟 変更: 幅を640にして左寄りに配置
                    draw_button(btn_text, 190 + i * 85, {"type": action_type, "slot": i}, width=640, height=70, x_pos=SCREEN_WIDTH//2 - 370)
                    
                    # 🌟 追加: ロード画面かつ、データが存在する場合のみ「削除」ボタンを右側に配置
                    if self.state == "MENU_LOAD" and os.path.exists(self.save_slots[i]):
                        draw_button("削除", 190 + i * 85 + 10, {"type": "delete_save", "slot": i}, width=80, height=50, color=(200, 50, 50), x_pos=SCREEN_WIDTH//2 + 290)
                
                if self.state == "MENU_SAVE":
                    draw_button("ゲームに戻る", 540, {"type": "change_state", "target": "PLAYING"}, width=200, color=(150, 50, 50), x_pos=SCREEN_WIDTH//2 - 220)
                    draw_button("タイトルへ戻る", 540, {"type": "confirm_title"}, width=200, color=(100, 100, 150), x_pos=SCREEN_WIDTH//2 + 20)
                else: # MENU_LOAD の場合
                    draw_button("戻る", 540, {"type": "change_state", "target": "MENU_MAIN"}, width=200, color=(150, 50, 50))

            elif self.state == "MENU_SETTINGS":
                header = self.font.render("【 音量設定 】", True, (50, 50, 50))
                self.screen.blit(header, (SCREEN_WIDTH//2 - header.get_width()//2, 160))
                
                # 共通で音量項目を描画するヘルパー関数
                def draw_volume_setting(label, y_pos, vol_value, minus_action, plus_action):
                    self.screen.blit(self.font.render(label, True, (0, 0, 0)), (SCREEN_WIDTH//2 - 220, y_pos))
                    
                    # ◀ ボタン
                    draw_button("◀", y_pos - 10, {"type": minus_action}, width=40, height=40, x_pos=SCREEN_WIDTH//2 - 20)
                    
                    # 現在の段階 (例: 8 / 10) とビジュアルバー
                    vol_text = f"{vol_value} / 10"
                    draw_button(vol_text, y_pos - 10, {"type": "none"}, width=100, height=40, color=(120, 120, 150), x_pos=SCREEN_WIDTH//2 + 30)
                    
                    # ▶ ボタン
                    draw_button("▶", y_pos - 10, {"type": plus_action}, width=40, height=40, x_pos=SCREEN_WIDTH//2 + 140)

                # BGM音量
                draw_volume_setting("BGM 音量", 240, self.volume_bgm, "vol_bgm_down", "vol_bgm_up")
                # 環境音音量
                draw_volume_setting("環境音 音量", 320, self.volume_env, "vol_env_down", "vol_env_up")
                # SE音量
                draw_volume_setting("SE 音量", 400, self.volume_se, "vol_se_down", "vol_se_up")
                
                # 戻るボタン
                draw_button("戻る", 500, {"type": "change_state", "target": "MENU_MAIN"}, width=200, color=(150, 50, 50))
                
            pygame.display.flip()
            return
        # ＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝
        self.screen.fill(COLOR_BG)
        self.screen.fill(COLOR_BG)
        pygame.draw.rect(self.screen, COLOR_HUD, (20, 20, 300, 680))
        
        time_text = f"{self.year}年目 {self.seasons[self.season_idx]}"
        days_text = f"({self.days}日目)"
        self.screen.blit(self.font_large.render(time_text, True, COLOR_TEXT), (40, 40))
        self.screen.blit(self.font.render(days_text, True, (180, 180, 190)), (40, 75))
        
        self.screen.blit(self.font_small.render("▼ 財政予算", True, (150, 200, 255)), (40, 125))
        self.screen.blit(self.font.render(f"{self.budget} 億円", True, COLOR_TEXT), (40, 150))
        
        self.screen.blit(self.font_small.render("▼ 県民満足度", True, (150, 255, 200)), (40, 200))
        self.screen.blit(self.font.render(f"{self.satisfaction} %", True, COLOR_TEXT), (40, 225))
        
        if self.satisfaction >= 80:
            status_text, status_color = "【支持率：最高】\n県民はあなたを称賛しています", (100, 255, 100)
        elif self.satisfaction >= 50:
            status_text, status_color = "【支持率：安定】\n県政は概ね平和です", (200, 200, 200)
        elif self.satisfaction >= 20:
            status_text, status_color = "【支持率：不満】\n県民から不満の声が挙がっています", (255, 200, 100)
        else:
            status_text, status_color = "【支持率：最悪】\n暴動が起きる寸前です…！", (255, 50, 50)
        lines=status_text.split('\n')
        for i, line in enumerate(lines):
            self.screen.blit(self.font_small.render(line, True, status_color), (40, 252 + i*20))
        
        
        self.screen.blit(self.font_small.render("▼ 秋田県人口", True, (255, 200, 150)), (40, 300))
        self.screen.blit(self.font.render(f"{self.population:,} 人", True, COLOR_TEXT), (40, 325))

        save_hint = self.font_small.render("[S]キーでセーブ", True, (150, 150, 150))
        self.screen.blit(save_hint, (180, 335))
        
        pygame.draw.line(self.screen, (80, 80, 100), (30, 360), (310, 360), 2)
        self.screen.blit(self.font.render("! 発生中の事案", True, COLOR_ALERT), (40, 375))
        
        start_y = 415
        for i, ae in enumerate(self.active_events):
            y_pos = start_y + i * 55
            ae["rect_sidebar"] = pygame.Rect(30, y_pos, 280, 50)
            is_hover = ae["rect_sidebar"].collidepoint(pygame.mouse.get_pos())
            box_color = (80, 60, 70) if is_hover else (60, 45, 55)
            pygame.draw.rect(self.screen, box_color, ae["rect_sidebar"])
            pygame.draw.rect(self.screen, COLOR_ALERT, ae["rect_sidebar"], 1)
            
            title_text = ae["event_data"]["title"]
            if len(title_text) > 11: title_text = title_text[:10] + "…"
                
            txt_info = self.font_small.render(f"【{ae['location']}】(あと{ae['time_left']}日)", True, (240, 200, 200))
            txt_title = self.font_small.render(title_text, True, COLOR_TEXT)
            self.screen.blit(txt_info, (40, y_pos + 4))
            self.screen.blit(txt_title, (40, y_pos + 26))
            

        # ＝＝＝ 【レイヤー1】マップ背景（最背面） ＝＝＝
        pygame.draw.rect(self.screen, (0, 0, 255), (340, 20, 920, 680))
        if self.map_img:
            self.screen.blit(self.map_img, (self.map_x, self.map_y))
        else:
            self.screen.blit(self.font.render("〜 秋田県マップ表示エリア 〜", True, (150, 150, 160)), (630, 330))

        l_config = getattr(self, 'landmark_config', {})
        
        # 💡 自動描画から除外するべきシステム・特殊画像の判定関数
        def is_special_image(name):
            return name.startswith("都市タイル") or name.startswith("秋田駅") or name.startswith("風車") or name in ["秋田犬", "竿燈まつり", "大曲の花火", "ババヘラ"]

        # ＝＝＝ 【レイヤー1.5】最背面ランドマーク（田沢湖・八郎潟など） ＝＝＝
        for name, config in l_config.items():
            if is_special_image(name):
                continue  # 🔴 複製バグ防止

            if config.get("is_bg", False):
                img = self.specialty_images.get(name)
                if img:
                    lx = self.map_x + int(config["x"] * self.new_w)
                    ly = self.map_y + int(config["y"] * self.new_h)
                    self.screen.blit(img, (lx - img.get_width() // 2, ly - img.get_height() // 2))

        # 座標計算の便利関数
        def get_city_pos(city_name, offset_x=0, offset_y=0):
            if city_name not in CITY_COORDINATES:
                return (0, 0)
            rx, ry = CITY_COORDINATES[city_name]
            x = self.map_x + int(self.new_w * rx) + offset_x
            y = self.map_y + int(self.new_h * ry) + offset_y
            return (x, y)

        # ＝＝＝ 【レイヤー2】都市タイル（発展度による増減システム） ＝＝＝
        for city, dev_val in self.city_development.items():
            if dev_val < 20:
                continue

            # 💡 その市専用の設定を読み込む
            tile_name = f"都市タイル ({city})"
            station_name = f"秋田駅 ({city})"
            t_cfg = l_config.get(tile_name, {"x": -32, "y": -32})
            s_cfg = l_config.get(station_name, {"x": -32, "y": -32})

            # その市専用のオフセットで塊（まとまり）の起点を決める！
            cx, cy = get_city_pos(city, t_cfg.get("x", -32), t_cfg.get("y", -32))
            
            offsets = [(0, 0)] 
            if dev_val >= 40: offsets.extend([(-24, 0), (24, 0)])
            if dev_val >= 60: offsets.extend([(0, -24), (0, 24)])
            if dev_val >= 80: offsets.extend([(-24, -24), (24, -24), (-24, 24), (24, 24)])

            for ox, oy in offsets:
                if dev_val >= 80 and ox == 0 and oy == 0 and self.specialty_images.get(station_name):
                    # 秋田駅の場合も専用の位置を使用
                    sx, sy = get_city_pos(city, s_cfg.get("x", -32) + ox, s_cfg.get("y", -32) + oy)
                    self.screen.blit(self.specialty_images[station_name], (sx, sy))
                elif self.specialty_images.get(tile_name):
                    self.screen.blit(self.specialty_images[tile_name], (cx + ox, cy + oy))

        # ＝＝＝ 【レイヤー3】通常時の都市ピンと名前 ＝＝＝
        for city, (rx, ry) in CITY_COORDINATES.items():
            cx, cy = get_city_pos(city)
            
            # ランドマークの自動描画ループ
            for name, config in l_config.items():
                if is_special_image(name):
                    continue # 🔴 複製バグ防止

                if not config.get("is_bg", False) and config.get("city") == city:
                    img = self.specialty_images.get(name)
                    if img:
                        self.screen.blit(img, (cx + config.get("x", 0), cy + config.get("y", 0)))

            # ババヘラ専用の特別描画
            if getattr(self, 'babahera_active_city', None) == city:
                img = getattr(self, 'specialty_images', {}).get("ババヘラ")
                if img:
                    self.screen.blit(img, (cx - img.get_width() // 2, cy - img.get_height() - 5))

            pygame.draw.circle(self.screen, (200, 200, 200), (cx, cy), 4)
            text_surf = self.font_small.render(city, True, (255, 255, 255))
            self.screen.blit(text_surf, (cx + 6, cy - 8))

        # ＝＝＝ 【デバッグ機能】全都市テストピン一斉表示 ＝＝＝
        if getattr(self, 'debug_show_all_pins', False):
            for city, (rx, ry) in CITY_COORDINATES.items():
                cx, cy = get_city_pos(city)
                pygame.draw.circle(self.screen, (255, 255, 0), (cx, cy), 8)
                pygame.draw.circle(self.screen, (0, 0, 0), (cx, cy), 8, 2)
                coord_text = self.font_small.render(f"{rx:.2f}, {ry:.2f}", True, (255, 255, 0))
                self.screen.blit(coord_text, (cx - 20, cy + 10))

        # ＝＝＝ 【レイヤー4】アクティブなイベントピン ＝＝＝
        for ae in self.active_events:
            loc = ae["location"]
            if loc in CITY_COORDINATES:
                cx, cy = get_city_pos(loc)
                ae["rect_pin"] = pygame.Rect(cx - 20, cy - 20, 40, 40)
                
                is_hover = ae["rect_pin"].collidepoint(pygame.mouse.get_pos())
                radius = 16 if is_hover else 12
                
                pygame.draw.circle(self.screen, (0, 0, 0), (cx, cy), radius + 2)
                pygame.draw.circle(self.screen, COLOR_PIN, (cx, cy), radius)
                pygame.draw.circle(self.screen, (255, 255, 255), (cx - 3, cy - 3), radius // 3)
                
                txt_loc = self.font_small.render(loc, True, COLOR_TEXT)
                bg_rect = pygame.Rect(cx - txt_loc.get_width()//2 - 4, cy - radius - 22, txt_loc.get_width() + 8, 20)
                pygame.draw.rect(self.screen, (20, 20, 30), bg_rect)
                self.screen.blit(txt_loc, (cx - txt_loc.get_width()//2, cy - radius - 20))

        # ＝＝＝ 【レイヤー5】その他のカスタムタイル ＝＝＝
        # ① 秋田犬
        if self.specialty_images.get("秋田犬"):
            c = l_config.get("秋田犬", {})
            cx, cy = get_city_pos(c.get("city", "大館市"), c.get("x", -10), c.get("y", -32))
            self.screen.blit(self.specialty_images["秋田犬"], (cx, cy))

        # ② 夏限定（竿燈・花火）
        if self.seasons[self.season_idx] == "夏":
            if self.specialty_images.get("竿燈まつり"):
                c = l_config.get("竿燈まつり", {})
                cx, cy = get_city_pos(c.get("city", "秋田市"), c.get("x", -60), c.get("y", -32))
                self.screen.blit(self.specialty_images["竿燈まつり"], (cx, cy))
            
            if self.specialty_images.get("大曲の花火"):
                current_time = pygame.time.get_ticks()
                if (current_time // 500) % 2 == 0:
                    c = l_config.get("大曲の花火", {})
                    cx, cy = get_city_pos(c.get("city", "横手市"), c.get("x", -32), c.get("y", -40))
                    self.screen.blit(self.specialty_images["大曲の花火"], (cx, cy))

        windmill_img = self.specialty_images_raw.get("風車")
        if windmill_img:
            # 任意のサイズにリサイズ
            windmill_img = pygame.transform.scale(windmill_img, (40, 40)) 
            for city, coords in self.land_windmills.items():
                for (wx, wy) in coords:
                    img_w = windmill_img.get_width()
                    img_h = windmill_img.get_height()
                    self.screen.blit(windmill_img, (wx - img_w // 2, wy - img_h // 2))
                
        pygame.draw.rect(self.screen, (15, 15, 20), (0, SCREEN_HEIGHT - 30, SCREEN_WIDTH, 30))
        ticker_surface = self.font.render(self.news_text, True, (255, 220, 100))
        
        if self.news_x < -ticker_surface.get_width():
            self.news_x = SCREEN_WIDTH
            
        self.screen.blit(ticker_surface, (self.news_x, SCREEN_HEIGHT - 26))

        # ＝＝＝ 新規追加：洋上風車の描画 ＝＝＝
        for wx, wy in self.offshore_windmills:
            # 海の上に立つポールの描画（グレー）
            pygame.draw.line(self.screen, (200, 220, 220), (wx, wy), (wx, wy + 25), 3)
            
            # ▼ 修正: システムの現在時刻を使って滑らかに回転させる
            current_time = pygame.time.get_ticks()
            angle = current_time * 0.05  # 数値(0.05)をいじると回転速度が変わります
            
            import math
            for i in range(3): # 3枚羽
                rad = math.radians(angle + i * 120)
                end_x = wx + math.cos(rad) * 12
                end_y = wy + math.sin(rad) * 12
                # 羽の描画（白）
                pygame.draw.line(self.screen, (255, 255, 255), (wx, wy), (end_x, end_y), 2)
        # ＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝

        # ＝＝＝ デバッグモード表示 ＝＝＝
        if self.debug_mode:
            debug_font = pygame.font.SysFont("msgothic", 20)
            txt = debug_font.render("【DEBUG MODE】 左クリック:配置 / 右クリック:1本削除 / Wキー:終了", True, (255, 0, 0))
            self.screen.blit(txt, (350, 10))
                
        pygame.display.flip()

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS)

            # 🌟 ここに追加: 毎フレームBGMと環境音をチェック
            self.update_audio()
            
            if self.debug_win is not None:
                try:
                    self.debug_win.update()
                except tk.TclError:
                    self.debug_win = None
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                # ▼ キー入力判定
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    
                    # プレイ中に「S」キーでセーブスロット選択画面へ
                    if event.key == pygame.K_s and self.state == "PLAYING":
                        self.state = "MENU_SAVE"
                    
                    # キーの押下状態を取得
                    keys = pygame.key.get_pressed()
                    is_ctrl = keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]
                    is_shift = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
                    
                    # 既存のデバッグメニュー (Ctrl+Shift+D)
                    if event.key == pygame.K_d and is_ctrl and is_shift:
                        self.open_debug_menu()
                        
                    # 🌟 風車配置モード (起動: Ctrl+Shift+W / 解除: W単体)
                    if event.key == pygame.K_w:
                        if is_ctrl and is_shift:
                            self.debug_mode = True
                            print("風車配置モード: ON")
                        elif not is_ctrl and not is_shift:
                            if self.debug_mode:
                                self.debug_mode = False
                                print("風車配置モード: OFF")

                # 🌟 追加: マウスクリック判定 (KEYDOWNのブロックと並列のインデント)
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.debug_mode:
                        # 【風車配置モードONの時】
                        if event.button == 1:  # 左クリックで配置
                            self.offshore_windmills.append(event.pos)
                            self.save_windmills()
                        elif event.button == 3:  # 右クリックで最後の1本を削除
                            if self.offshore_windmills:
                                self.offshore_windmills.pop()
                                self.save_windmills()
                    else:
                        # 【通常プレイ時】
                        # （すでに別のマウスクリック処理があれば、ここに書くか、元のコードを維持してください）
                        pass

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        # 🌟 メニュー画面でのクリック判定
                        if self.state in ["MENU_MAIN", "MENU_NEW", "MENU_LOAD", "MENU_SAVE","MENU_SETTINGS"]:
                            mouse_pos = pygame.mouse.get_pos()
                            for btn in self.menu_buttons:
                                if btn["rect"].collidepoint(mouse_pos):
                                    action = btn["action"]
                                    
                                    if action["type"] == "change_state":
                                        self.state = action["target"]
                                        if self.state in ["MENU_MAIN", "MENU_NEW", "MENU_LOAD", "MENU_SETTINGS"]:
                                            self.change_menu_bg()
                                            
                                    # 🌟 追加: 音量調整のアクション処理
                                    elif action["type"] == "vol_bgm_up":
                                        self.volume_bgm = min(10, self.volume_bgm + 1)
                                        self.apply_volumes()
                                        self.save_settings() # ←追加
                                        if "confirm" in self.se: self.se["confirm"].play()
                                    elif action["type"] == "vol_bgm_down":
                                        self.volume_bgm = max(0, self.volume_bgm - 1)
                                        self.apply_volumes()
                                        self.save_settings() # ←追加
                                        if "confirm" in self.se: self.se["confirm"].play()
                                        
                                    elif action["type"] == "vol_env_up":
                                        self.volume_env = min(10, self.volume_env + 1)
                                        self.apply_volumes()
                                        self.save_settings() # ←追加
                                        if "confirm" in self.se: self.se["confirm"].play()
                                    elif action["type"] == "vol_env_down":
                                        self.volume_env = max(0, self.volume_env - 1)
                                        self.apply_volumes()
                                        self.save_settings() # ←追加
                                        if "confirm" in self.se: self.se["confirm"].play()
                                        
                                    elif action["type"] == "vol_se_up":
                                        self.volume_se = min(10, self.volume_se + 1)
                                        self.apply_volumes()
                                        self.save_settings() # ←追加
                                        if "confirm" in self.se: self.se["confirm"].play()
                                    elif action["type"] == "vol_se_down":
                                        self.volume_se = max(0, self.volume_se - 1)
                                        self.apply_volumes()
                                        self.save_settings() # ←追加
                                        if "confirm" in self.se: self.se["confirm"].play()
                                        
                                    if action["type"] == "change_state":
                                        self.state = action["target"]
                                        # 画面切り替え時に背景をランダム変更
                                        if self.state in ["MENU_MAIN", "MENU_NEW", "MENU_LOAD"]:
                                            self.change_menu_bg()
                                            
                                    # 🌟 追加・修正: タイトルへ戻る処理
                                    elif action["type"] == "confirm_title":
                                        # もし messagebox でエラーが出る場合は、この下の行を単に self.state = "MENU_MAIN" にしてもOKです
                                        try:
                                            if messagebox.askyesno("確認", "タイトル画面に戻りますか？\n（※セーブしていない進行状況は失われます）"):
                                                self.state = "MENU_MAIN"
                                                self.change_menu_bg()
                                        except Exception as e:
                                            print(f"メッセージボックスのエラー: {e}")
                                            # エラーが起きた場合は強制的にタイトルへ戻す
                                            self.state = "MENU_MAIN"
                                            self.change_menu_bg()
                                            
                                    elif action["type"] == "quit":
                                        running = False
                                    elif action["type"] == "cycle_time_next":
                                        times = list(range(1, 11)) + [float('inf')]
                                        idx = times.index(self.target_years)
                                        self.target_years = times[(idx + 1) % len(times)]
                                    elif action["type"] == "cycle_time_prev":
                                        times = list(range(1, 11)) + [float('inf')]
                                        idx = times.index(self.target_years)
                                        self.target_years = times[(idx - 1) % len(times)]
                                    elif action["type"] == "cycle_diff_next":
                                        diffs = ["Easy", "Normal", "Hard", "Extra"]
                                        idx = diffs.index(self.difficulty)
                                        self.difficulty = diffs[(idx + 1) % len(diffs)]
                                    elif action["type"] == "cycle_diff_prev":
                                        diffs = ["Easy", "Normal", "Hard", "Extra"]
                                        idx = diffs.index(self.difficulty)
                                        self.difficulty = diffs[(idx - 1) % len(diffs)]
                                    elif action["type"] == "start_new":
                                        self.apply_difficulty_settings()
                                        self.state = "PLAYING"
                                    elif action["type"] == "do_save":
                                        self.save_game(action["slot"])
                                    elif action["type"] == "do_load":
                                        self.load_game(action["slot"])
                                        # 🌟 追加: 削除ボタンの処理
                                    elif action["type"] == "delete_save":
                                        # tkinterのメッセージボックスで最終確認
                                        if messagebox.askyesno("確認", f"スロット {action['slot'] + 1} のデータを削除しますか？\nこの操作は取り消せません。"):
                                            filepath = self.save_slots[action["slot"]]
                                            if os.path.exists(filepath):
                                                os.remove(filepath)
                                                messagebox.showinfo("削除完了", "セーブデータを削除しました。")
                                    break
                                    
                        # プレイ中のイベントピン判定
                        elif self.state == "PLAYING":
                            clicked_event = None
                            for ae in self.active_events:
                                if ae["rect_pin"] and ae["rect_pin"].collidepoint(event.pos):
                                    clicked_event = ae
                                    break
                                if ae["rect_sidebar"] and ae["rect_sidebar"].collidepoint(event.pos):
                                    clicked_event = ae
                                    break
                            if clicked_event:
                                self.execute_event(clicked_event)
            
            if self.state == "PLAYING" and self.debug_win is None:
                self.progress_time(dt)
                if self.budget <= 0:
                    self.end_game(reason="bankruptcy")
                    running = False

            self.draw()
            
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = AkitaSimulator()
    game.run()