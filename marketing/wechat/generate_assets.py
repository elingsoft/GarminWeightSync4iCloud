#!/usr/bin/env python3
"""Generate the WeChat article artwork for the Garmin weight sync project."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[2]
ASSETS = Path(__file__).resolve().parent / "assets"
FONT_PATH = "/System/Library/Fonts/Hiragino Sans GB.ttc"

BG_TOP = (6, 20, 33)
BG_BOTTOM = (8, 55, 59)
PANEL = (13, 35, 49)
PANEL_LIGHT = (17, 47, 61)
WHITE = (246, 249, 250)
MUTED = (160, 185, 194)
MINT = (87, 227, 178)
MINT_DARK = (28, 112, 99)
PINK = (255, 116, 146)
RED = (255, 125, 125)
YELLOW = (255, 207, 102)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_PATH, size, index=2 if bold else 0)


def gradient(size: tuple[int, int]) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size, BG_TOP)
    draw = ImageDraw.Draw(image)
    for y in range(height):
        ratio = y / max(1, height - 1)
        color = tuple(round(a + (b - a) * ratio) for a, b in zip(BG_TOP, BG_BOTTOM))
        draw.line((0, y, width, y), fill=color)
    return image


def add_glow(image: Image.Image, center: tuple[int, int], radius: int, color: tuple[int, int, int]) -> None:
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x, y = center
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(*color, 55))
    layer = layer.filter(ImageFilter.GaussianBlur(radius // 3))
    image.alpha_composite(layer) if image.mode == "RGBA" else image.paste(layer, (0, 0), layer)


def text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    value: str,
    size: int,
    color: tuple[int, int, int] = WHITE,
    bold: bool = False,
    anchor: str | None = None,
) -> None:
    draw.text(xy, value, font=font(size, bold), fill=color, anchor=anchor)


def pill(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    value: str,
    size: int,
    fg: tuple[int, int, int],
    outline: tuple[int, int, int],
    pad_x: int = 16,
    height: int = 38,
) -> None:
    x, y = xy
    f = font(size, True)
    width = int(draw.textlength(value, font=f)) + pad_x * 2
    draw.rounded_rectangle((x, y, x + width, y + height), radius=height // 2, outline=outline, width=2)
    draw.text((x + pad_x, y + height // 2), value, font=f, fill=fg, anchor="lm")


def arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: tuple[int, int, int]) -> None:
    draw.line((start, end), fill=color, width=3)
    x1, y1 = start
    x2, y2 = end
    if abs(y2 - y1) >= abs(x2 - x1):
        direction = 1 if y2 >= y1 else -1
        points = [(x2, y2), (x2 - 8, y2 - 13 * direction), (x2 + 8, y2 - 13 * direction)]
    else:
        direction = 1 if x2 >= x1 else -1
        points = [(x2, y2), (x2 - 13 * direction, y2 - 8), (x2 - 13 * direction, y2 + 8)]
    draw.polygon(points, fill=color)


def cover() -> None:
    size = (900, 383)
    image = gradient(size).convert("RGBA")
    add_glow(image, (780, 80), 210, MINT)
    add_glow(image, (90, 360), 190, (40, 120, 145))
    draw = ImageDraw.Draw(image)

    pill(draw, (50, 38), "OPEN SOURCE · MIT", 15, MINT, MINT_DARK)
    text(draw, (50, 92), "体重自动进", 58, WHITE, True)
    text(draw, (50, 157), "Garmin", 78, WHITE, True)
    text(draw, (52, 253), "Apple 健康 → Garmin Connect", 27, MINT, True)
    text(draw, (52, 315), "iPhone 快捷指令 × macOS 自动化", 18, MUTED)

    panel = (605, 52, 850, 331)
    draw.rounded_rectangle(panel, radius=26, fill=(*PANEL, 235), outline=(38, 88, 93), width=2)
    text(draw, (728, 78), "自动链路", 20, MUTED, True, "mm")
    items = [("01", "称重", MINT), ("02", "iCloud", YELLOW), ("03", "Garmin", PINK)]
    ys = [126, 199, 272]
    for index, ((number, label, color), y) in enumerate(zip(items, ys)):
        draw.ellipse((632, y - 20, 672, y + 20), fill=(*color, 240))
        text(draw, (652, y), number, 13, (7, 26, 36), True, "mm")
        text(draw, (690, y), label, 23, WHITE, True, "lm")
        if index < 2:
            arrow(draw, (652, y + 28), (652, y + 55), MINT)

    image.convert("RGB").save(ASSETS / "wechat-cover-2.35x1.png", quality=95)


def cover_square() -> None:
    size = (900, 900)
    image = gradient(size).convert("RGBA")
    add_glow(image, (760, 160), 260, MINT)
    add_glow(image, (120, 800), 250, (80, 70, 150))
    draw = ImageDraw.Draw(image)

    pill(draw, (62, 66), "OPEN SOURCE · LOCAL-FIRST", 17, MINT, MINT_DARK, height=44)
    text(draw, (62, 170), "体重自动进", 92, WHITE, True)
    text(draw, (62, 278), "Garmin", 126, WHITE, True)
    text(draw, (66, 435), "Apple 健康 → Garmin Connect", 31, MINT, True)
    text(draw, (66, 505), "称重后，什么都不用点", 35, WHITE, True)

    rows = [
        ("01", "Apple 健康", "体重先进入健康"),
        ("02", "iCloud 中转", "快捷指令保存 JSON"),
        ("03", "Garmin", "Mac 自动生成 FIT 并上传"),
    ]
    y = 585
    for number, title, subtitle in rows:
        draw.rounded_rectangle((62, y, 838, y + 72), radius=20, fill=(*PANEL_LIGHT, 235), outline=(36, 80, 86), width=1)
        draw.ellipse((82, y + 14, 126, y + 58), fill=MINT)
        text(draw, (104, y + 36), number, 14, (7, 26, 36), True, "mm")
        text(draw, (148, y + 15), title, 26, WHITE, True)
        text(draw, (148, y + 47), subtitle, 16, MUTED)
        y += 88

    text(draw, (450, 872), "免费 · 本地 · 可审计", 20, MUTED, False, "mm")
    image.convert("RGB").save(ASSETS / "wechat-cover-1x1.png", quality=95)


def architecture() -> None:
    size = (1080, 1080)
    image = gradient(size).convert("RGBA")
    add_glow(image, (920, 120), 230, MINT)
    draw = ImageDraw.Draw(image)

    text(draw, (64, 56), "数据怎么走", 62, WHITE, True)
    text(draw, (66, 136), "称重一次，后台自动完成", 25, MUTED)
    pill(draw, (806, 62), "本地优先", 18, MINT, MINT_DARK, height=42)

    steps = [
        ("体重秤", "称重后写入 Apple 健康"),
        ("Apple 健康", "保存最新体重"),
        ("iPhone 快捷指令", "读取体重并生成 JSON"),
        ("iCloud Drive", "WeightIn 文件夹跨设备传递"),
        ("Mac watcher", "生成 FIT 并上传 Garmin"),
        ("Garmin Connect", "体重记录自动出现"),
    ]
    start_y = 226
    gap = 126
    line_x = 126
    draw.line((line_x, start_y + 20, line_x, start_y + gap * (len(steps) - 1) + 20), fill=(42, 102, 102), width=3)
    for index, (title, subtitle) in enumerate(steps):
        y = start_y + index * gap
        draw.ellipse((line_x - 24, y - 4, line_x + 24, y + 44), fill=MINT if index < 5 else PINK)
        text(draw, (line_x, y + 20), str(index + 1), 17, (6, 26, 34), True, "mm")
        draw.rounded_rectangle((178, y - 20, 1000, y + 72), radius=18, fill=(*PANEL_LIGHT, 230), outline=(35, 80, 87), width=1)
        text(draw, (210, y - 2), title, 29, WHITE, True, "lm")
        text(draw, (210, y + 38), subtitle, 18, MUTED, False, "lm")

    text(draw, (540, 1010), "数据只在你自己的 iCloud、Mac 与 Garmin 之间流转", 19, MUTED, False, "mm")
    image.convert("RGB").save(ASSETS / "architecture.png", quality=95)


def who_for() -> None:
    size = (1080, 1080)
    image = gradient(size).convert("RGBA")
    add_glow(image, (930, 100), 200, MINT)
    add_glow(image, (80, 940), 220, (130, 55, 80))
    draw = ImageDraw.Draw(image)

    text(draw, (60, 56), "这套方案适合谁？", 60, WHITE, True)
    text(draw, (64, 136), "先看边界，再决定要不要折腾", 25, MUTED)

    left = (54, 200, 522, 946)
    right = (558, 200, 1026, 946)
    draw.rounded_rectangle(left, radius=28, fill=(*PANEL_LIGHT, 235), outline=MINT_DARK, width=3)
    draw.rounded_rectangle(right, radius=28, fill=(*PANEL_LIGHT, 235), outline=(124, 62, 70), width=3)
    text(draw, (92, 238), "适合", 38, MINT, True)
    text(draw, (596, 238), "可能不适合", 38, RED, True)

    left_items = [
        "同时使用 iPhone 和 Garmin",
        "体重秤能把数据写进 Apple 健康",
        "有一台能在固定时段在线的 Mac",
        "愿意按教程部署一次",
    ]
    right_items = [
        "没有 Mac，或 Mac 不常在线",
        "主要使用安卓手机",
        "希望安装后零配置",
        "不想维护任何后台任务",
    ]

    y = 330
    for item in left_items:
        draw.ellipse((92, y + 8, 114, y + 30), fill=MINT)
        text(draw, (132, y), item, 25, WHITE)
        y += 128
    y = 330
    for item in right_items:
        draw.ellipse((596, y + 8, 618, y + 30), fill=RED)
        text(draw, (636, y), item, 25, WHITE)
        y += 128

    text(draw, (540, 1004), "如果不符合，先别急着部署。", 22, YELLOW, True, "mm")
    image.convert("RGB").save(ASSETS / "who-is-this-for.png", quality=95)


def checklist() -> None:
    size = (1080, 1080)
    image = gradient(size).convert("RGBA")
    add_glow(image, (920, 120), 220, YELLOW)
    draw = ImageDraw.Draw(image)

    text(draw, (60, 56), "部署前，先确认 4 件事", 58, WHITE, True)
    text(draw, (64, 136), "全部满足再开始，预计 10–20 分钟", 25, MUTED)

    cards = [
        ("01", "Mac", "能在设定时段保持在线"),
        ("02", "iPhone + iCloud", "快捷指令可读健康，iCloud 已开启"),
        ("03", "Garmin 账号", "国际区已实测；中国区未测试"),
        ("04", "体重秤", "能把体重写入 Apple 健康"),
    ]
    positions = [(54, 220), (558, 220), (54, 585), (558, 585)]
    for (number, title, subtitle), (x, y) in zip(cards, positions):
        draw.rounded_rectangle((x, y, x + 468, y + 310), radius=28, fill=(*PANEL_LIGHT, 235), outline=(38, 86, 91), width=2)
        draw.ellipse((x + 28, y + 28, x + 92, y + 92), fill=MINT)
        text(draw, (x + 60, y + 60), number, 16, (7, 26, 36), True, "mm")
        text(draw, (x + 28, y + 130), title, 36, WHITE, True)
        text(draw, (x + 28, y + 196), subtitle, 20, MUTED)

    text(draw, (540, 1000), "缺一项，链路就会断。", 22, YELLOW, True, "mm")
    image.convert("RGB").save(ASSETS / "preflight-checklist.png", quality=95)


def shortcut_image() -> None:
    source = ROOT / "docs" / "images" / "iphone-shortcut.jpg"
    image = Image.open(source).convert("RGB")
    image.thumbnail((720, 3600), Image.Resampling.LANCZOS)
    image.save(ASSETS / "iphone-shortcut.jpg", quality=90, optimize=True)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    cover()
    cover_square()
    architecture()
    who_for()
    checklist()
    shortcut_image()
    print("generated:")
    for path in sorted(ASSETS.iterdir()):
        print(f"  {path.name}: {path.stat().st_size} bytes")


if __name__ == "__main__":
    main()
