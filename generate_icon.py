"""アプリアイコン生成: マット背景＋白い箱＋アンバーの上昇バー"""
from PIL import Image, ImageDraw, ImageFilter

S = 1024  # 高解像度で描き、最後に各サイズへリサンプル
margin = int(S * 0.04)
radius = int(S * 0.20)

# === 背景: マットなフラット単色（深いインディゴ） ===
bg = (63, 58, 140, 255)  # #3f3a8c — 落ち着いたマットなインディゴ
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
ImageDraw.Draw(img).rounded_rectangle(
    [margin, margin, S - margin, S - margin], radius=radius, fill=bg
)

# 後段で使う角丸マスク（ドロップシャドウのクリップ用）
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle(
    [margin, margin, S - margin, S - margin], radius=radius, fill=255
)

# === 箱の位置 ===
box_l = int(S * 0.20)
box_r = int(S * 0.80)
box_t = int(S * 0.46)
box_b = int(S * 0.82)
box_radius = int(S * 0.05)

# ドロップシャドウ（背景の角丸内に収まるよう mask でクリップ）
sh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
ImageDraw.Draw(sh).rounded_rectangle(
    [box_l, box_t + int(S * 0.015), box_r, box_b + int(S * 0.015)],
    radius=box_radius, fill=(0, 0, 0, 110),
)
sh = sh.filter(ImageFilter.GaussianBlur(radius=int(S * 0.025)))
sh_masked = Image.new("RGBA", (S, S), (0, 0, 0, 0))
sh_masked.paste(sh, (0, 0), mask)
img = Image.alpha_composite(img, sh_masked)

# === 箱本体（白の角丸） ===
box_layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
ImageDraw.Draw(box_layer).rounded_rectangle(
    [box_l, box_t, box_r, box_b], radius=box_radius, fill=(255, 255, 255, 250)
)
img = Image.alpha_composite(img, box_layer)

# 箱の蓋ライン＋取っ手（インディゴでアクセント）
acc = (67, 56, 202, 230)  # #4338ca indigo
lid_y = int(box_t + (box_b - box_t) * 0.27)
lid = Image.new("RGBA", (S, S), (0, 0, 0, 0))
ld = ImageDraw.Draw(lid)
ld.line(
    [(box_l + box_radius, lid_y), (box_r - box_radius, lid_y)],
    fill=acc, width=int(S * 0.012),
)
# 蓋の上の小さな取っ手
hw = int(S * 0.13)
hh = int(S * 0.028)
hx1 = (S - hw) // 2
hx2 = hx1 + hw
hy1 = lid_y - hh - int(S * 0.018)
hy2 = hy1 + hh
ld.rounded_rectangle([hx1, hy1, hx2, hy2], radius=hh // 2, fill=acc)
img = Image.alpha_composite(img, lid)

# === 上昇バー（アンバーで補色アクセント） ===
amber = (251, 191, 36, 255)  # #fbbf24
bar_count = 3
bar_w = int(S * 0.075)
gap = int(S * 0.038)
total_w = bar_count * bar_w + (bar_count - 1) * gap
bars_left = (S - total_w) // 2
heights = [int(S * 0.10), int(S * 0.17), int(S * 0.24)]
bars = Image.new("RGBA", (S, S), (0, 0, 0, 0))
bd = ImageDraw.Draw(bars)
for i in range(bar_count):
    x = bars_left + i * (bar_w + gap)
    y_bot = box_t - int(S * 0.025)
    y_top = y_bot - heights[i]
    bd.rounded_rectangle(
        [x, y_top, x + bar_w, y_bot], radius=bar_w // 2, fill=amber
    )
img = Image.alpha_composite(img, bars)

# === 出力 ===
sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
img.save("icon.ico", format="ICO", sizes=sizes)
img.save("icon_preview.png", format="PNG")
print("Wrote icon.ico (sizes:", sizes, ")")
print("Wrote icon_preview.png")
