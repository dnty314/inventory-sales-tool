"""アプリアイコン生成: 在庫ボックス＋上昇バーをモチーフに icon.ico を作成"""
from PIL import Image, ImageDraw

S = 512  # 高解像度で描き、最後に各サイズへリサンプル

img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# 背景: インディゴの角丸四角（アプリのプライマリ色 #4338ca）
bg = (67, 56, 202, 255)
margin = int(S * 0.04)
radius = int(S * 0.18)
d.rounded_rectangle([margin, margin, S - margin, S - margin], radius=radius, fill=bg)

# 上に乗せるバー（売上/推移）
bar_count = 3
bar_w = int(S * 0.07)
gap = int(S * 0.04)
total_w = bar_count * bar_w + (bar_count - 1) * gap
bars_left = (S - total_w) // 2
bar_top_pad = int(S * 0.035)  # 箱からの離間
heights = [int(S * 0.11), int(S * 0.18), int(S * 0.25)]
white = (255, 255, 255, 255)

# 在庫ボックス（白アウトライン＋蓋ライン）
box_l = int(S * 0.22)
box_r = int(S * 0.78)
box_t = int(S * 0.46)
box_b = int(S * 0.80)
lw = int(S * 0.035)
d.rounded_rectangle([box_l, box_t, box_r, box_b], radius=int(S * 0.05), outline=white, width=lw)
lid_y = int(S * 0.55)
d.line([(box_l + lw // 2, lid_y), (box_r - lw // 2, lid_y)], fill=white, width=lw)

# 蓋の中央に小さな取っ手線
handle_w = int(S * 0.10)
hx1 = (S - handle_w) // 2
hx2 = hx1 + handle_w
hy = (box_t + lid_y) // 2
d.line([(hx1, hy), (hx2, hy)], fill=white, width=int(S * 0.025))

# 上昇バー（角丸の縦バー）
for i in range(bar_count):
    x = bars_left + i * (bar_w + gap)
    h = heights[i]
    y_bot = box_t - bar_top_pad
    y_top = y_bot - h
    d.rounded_rectangle([x, y_top, x + bar_w, y_bot], radius=bar_w // 2, fill=white)

# ICO は複数サイズをひとつのファイルに埋め込む
sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
img.save("icon.ico", format="ICO", sizes=sizes)

# 確認用に PNG も書き出し
img.save("icon_preview.png", format="PNG")
print("Wrote icon.ico (sizes:", sizes, ")")
print("Wrote icon_preview.png")
