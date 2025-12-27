"""
Portrait Placeholder Generator
武将・大名の肖像画プレースホルダー生成スクリプト
"""
from PIL import Image, ImageDraw, ImageFont
import json
import os

# 画像仕様
IMAGE_WIDTH = 256
IMAGE_HEIGHT = 256

# 武将用の色（青系）
GENERAL_BACKGROUND_COLOR = (200, 200, 220)  # Light gray-blue
# 大名用の色（金系）
DAIMYO_BACKGROUND_COLOR = (220, 200, 160)  # Light gold
TEXT_COLOR = (50, 50, 50)  # Dark gray

# 出力フォルダ
GENERALS_OUTPUT_DIR = "assets/portraits/generals"
DAIMYO_OUTPUT_DIR = "assets/portraits/daimyo"
BACKGROUNDS_OUTPUT_DIR = "assets/backgrounds"

# 背景画像の仕様
BACKGROUND_WIDTH = 1280
BACKGROUND_HEIGHT = 720

def generate_placeholder_portrait(person_id: int, person_name: str, filename: str, output_dir: str, portrait_type: str = "general"):
    """プレースホルダー画像を生成

    Args:
        person_id: 人物ID
        person_name: 人物名
        filename: 出力ファイル名
        output_dir: 出力ディレクトリ
        portrait_type: "general" または "daimyo"
    """
    # 背景色を選択
    if portrait_type == "daimyo":
        bg_color = DAIMYO_BACKGROUND_COLOR
        border_color = (150, 120, 80)  # Dark gold
        type_label = "DAIMYO"
    else:
        bg_color = GENERAL_BACKGROUND_COLOR
        border_color = (100, 100, 120)  # Dark blue-gray
        type_label = "GENERAL"

    # 新しい画像を作成
    img = Image.new('RGB', (IMAGE_WIDTH, IMAGE_HEIGHT), bg_color)
    draw = ImageDraw.Draw(img)

    # 枠線を描画
    border_width = 3
    draw.rectangle(
        [(border_width, border_width),
         (IMAGE_WIDTH - border_width, IMAGE_HEIGHT - border_width)],
        outline=border_color,
        width=border_width
    )

    # テキストを描画（システムフォントを使用）
    try:
        # Windowsの場合、MSゴシックを試す
        font_large = ImageFont.truetype("msgothic.ttc", 32)
        font_small = ImageFont.truetype("msgothic.ttc", 20)
        font_tiny = ImageFont.truetype("msgothic.ttc", 16)
    except:
        # フォントが見つからない場合はデフォルトフォントを使用
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_tiny = ImageFont.load_default()

    # タイプラベルを最上部に描画
    bbox = draw.textbbox((0, 0), type_label, font=font_tiny)
    type_x = (IMAGE_WIDTH - (bbox[2] - bbox[0])) // 2
    draw.text((type_x, 15), type_label, fill=(120, 120, 120), font=font_tiny)

    # ID番号を上部に描画
    id_text = f"ID: {person_id}"
    bbox = draw.textbbox((0, 0), id_text, font=font_small)
    id_x = (IMAGE_WIDTH - (bbox[2] - bbox[0])) // 2
    draw.text((id_x, 40), id_text, fill=TEXT_COLOR, font=font_small)

    # 人物名を中央に描画
    bbox = draw.textbbox((0, 0), person_name, font=font_large)
    text_x = (IMAGE_WIDTH - (bbox[2] - bbox[0])) // 2
    text_y = (IMAGE_HEIGHT - (bbox[3] - bbox[1])) // 2
    draw.text((text_x, text_y), person_name, fill=TEXT_COLOR, font=font_large)

    # プレースホルダーテキストを下部に描画
    placeholder_text = "PLACEHOLDER"
    bbox = draw.textbbox((0, 0), placeholder_text, font=font_small)
    placeholder_x = (IMAGE_WIDTH - (bbox[2] - bbox[0])) // 2
    draw.text((placeholder_x, IMAGE_HEIGHT - 50), placeholder_text,
              fill=(150, 150, 150), font=font_small)

    # ファイルに保存
    output_path = os.path.join(output_dir, filename)
    img.save(output_path, 'PNG')
    try:
        print(f"生成: {output_path}")
    except:
        pass

def generate_background(bg_type: str, filename: str):
    """背景画像プレースホルダーを生成

    Args:
        bg_type: 背景タイプ ("main", "power_map", "battle_vs", "battle_combat", "battle_result")
        filename: 出力ファイル名
    """
    # 背景タイプごとの色設定
    bg_colors = {
        "main": (40, 30, 20),           # ダークブラウン（メイン画面）
        "power_map": (30, 40, 30),      # ダークグリーン（勢力図）
        "battle_vs": (20, 15, 10),      # 非常に暗い（VS画面）
        "battle_combat": (25, 20, 15),  # 暗いブラウン（戦闘画面）
        "battle_result": (30, 25, 20)   # ブラウン（結果画面）
    }

    # ラベルテキスト
    labels = {
        "main": "MAIN BACKGROUND",
        "power_map": "POWER MAP BACKGROUND",
        "battle_vs": "BATTLE VS BACKGROUND",
        "battle_combat": "BATTLE COMBAT BACKGROUND",
        "battle_result": "BATTLE RESULT BACKGROUND"
    }

    bg_color = bg_colors.get(bg_type, (40, 40, 40))
    label = labels.get(bg_type, "BACKGROUND")

    # 新しい画像を作成
    img = Image.new('RGB', (BACKGROUND_WIDTH, BACKGROUND_HEIGHT), bg_color)
    draw = ImageDraw.Draw(img)

    # 装飾的な枠線を描画
    border_width = 5
    border_color = (100, 80, 60)
    draw.rectangle(
        [(border_width, border_width),
         (BACKGROUND_WIDTH - border_width, BACKGROUND_HEIGHT - border_width)],
        outline=border_color,
        width=border_width
    )

    # 内側の装飾線
    inner_margin = 20
    draw.rectangle(
        [(inner_margin, inner_margin),
         (BACKGROUND_WIDTH - inner_margin, BACKGROUND_HEIGHT - inner_margin)],
        outline=(80, 60, 40),
        width=2
    )

    # テキストを描画
    try:
        font_large = ImageFont.truetype("msgothic.ttc", 48)
        font_medium = ImageFont.truetype("msgothic.ttc", 24)
        font_small = ImageFont.truetype("msgothic.ttc", 18)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # ラベルを中央に描画
    bbox = draw.textbbox((0, 0), label, font=font_large)
    text_x = (BACKGROUND_WIDTH - (bbox[2] - bbox[0])) // 2
    text_y = (BACKGROUND_HEIGHT - (bbox[3] - bbox[1])) // 2
    draw.text((text_x, text_y), label, fill=(150, 130, 100), font=font_large)

    # サイズ情報を描画
    size_text = f"{BACKGROUND_WIDTH}x{BACKGROUND_HEIGHT}"
    bbox = draw.textbbox((0, 0), size_text, font=font_medium)
    size_x = (BACKGROUND_WIDTH - (bbox[2] - bbox[0])) // 2
    size_y = text_y + 80
    draw.text((size_x, size_y), size_text, fill=(120, 100, 80), font=font_medium)

    # プレースホルダーテキストを下部に描画
    placeholder_text = "PLACEHOLDER - Replace with actual background image"
    bbox = draw.textbbox((0, 0), placeholder_text, font=font_small)
    placeholder_x = (BACKGROUND_WIDTH - (bbox[2] - bbox[0])) // 2
    draw.text((placeholder_x, BACKGROUND_HEIGHT - 50), placeholder_text,
              fill=(100, 80, 60), font=font_small)

    # グリッド線を描画（デザイン用ガイド）
    grid_color = (60, 50, 40)
    # 縦線
    for i in range(1, 4):
        x = BACKGROUND_WIDTH * i // 4
        draw.line([(x, inner_margin), (x, BACKGROUND_HEIGHT - inner_margin)],
                  fill=grid_color, width=1)
    # 横線
    for i in range(1, 3):
        y = BACKGROUND_HEIGHT * i // 3
        draw.line([(inner_margin, y), (BACKGROUND_WIDTH - inner_margin, y)],
                  fill=grid_color, width=1)

    # ファイルに保存
    output_path = os.path.join(BACKGROUNDS_OUTPUT_DIR, filename)
    img.save(output_path, 'PNG')
    try:
        print(f"生成: {output_path}")
    except:
        pass

def main():
    """全武将・大名・背景のプレースホルダー画像を生成"""
    try:
        print("=" * 60)
        print("Game Asset Placeholder Generator")
        print("=" * 60)
        print(f"Portrait size: {IMAGE_WIDTH}x{IMAGE_HEIGHT}px")
        print(f"Background size: {BACKGROUND_WIDTH}x{BACKGROUND_HEIGHT}px")
        print()
    except:
        # Windows console encoding issue
        pass

    # === 武将の画像を生成 ===
    try:
        print("[1/3] Generating general portraits...")
    except:
        pass

    with open('data/generals.json', 'r', encoding='utf-8') as f:
        generals_data = json.load(f)

    for general in generals_data["generals"]:
        general_id = general["id"]
        general_name = general["name"]
        filename = f"general_{general_id:02d}.png"
        generate_placeholder_portrait(
            general_id,
            general_name,
            filename,
            GENERALS_OUTPUT_DIR,
            "general"
        )

    try:
        print(f"  -> {len(generals_data['generals'])} general portraits created")
        print()
    except:
        pass

    # === 大名の画像を生成 ===
    try:
        print("[2/3] Generating daimyo portraits...")
    except:
        pass

    with open('data/daimyo.json', 'r', encoding='utf-8') as f:
        daimyo_data = json.load(f)

    for daimyo in daimyo_data["daimyo"]:
        daimyo_id = daimyo["id"]
        # 氏族名 + 名前を表示
        daimyo_full_name = f"{daimyo['clan']}{daimyo['name']}"
        filename = f"daimyo_{daimyo_id:02d}.png"
        generate_placeholder_portrait(
            daimyo_id,
            daimyo_full_name,
            filename,
            DAIMYO_OUTPUT_DIR,
            "daimyo"
        )

    try:
        print(f"  -> {len(daimyo_data['daimyo'])} daimyo portraits created")
        print()
    except:
        pass

    # === 背景画像を生成 ===
    try:
        print("[3/3] Generating background images...")
    except:
        pass

    backgrounds = [
        ("main", "main_background.png"),
        ("power_map", "power_map_background.png"),
        ("battle_vs", "battle_vs_background.png"),
        ("battle_combat", "battle_combat_background.png"),
        ("battle_result", "battle_result_background.png")
    ]

    for bg_type, filename in backgrounds:
        generate_background(bg_type, filename)

    try:
        print(f"  -> {len(backgrounds)} background images created")
        print()
        print("=" * 60)
        print("Complete!")
        print("=" * 60)
        print()
        print("NOTE: These are placeholder images.")
        print("Please replace them with actual images manually.")
        print("- Portraits: 256x256px (PNG)")
        print("- Backgrounds: 1280x720px (PNG)")
    except:
        pass

if __name__ == "__main__":
    main()
