#!/usr/bin/env python3
"""Build a local HTML preview of the WeChat article."""

from pathlib import Path

import markdown


HERE = Path(__file__).resolve().parent
source = HERE / "article.md"
output = HERE / "article-preview.html"

body = markdown.markdown(
    source.read_text(encoding="utf-8"),
    extensions=["extra", "sane_lists"],
)

html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>公众号文章预览</title>
<style>
  body {{
    margin: 0;
    background: #eef1f2;
    color: #2e3338;
    font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans GB", "PingFang SC", sans-serif;
  }}
  article {{
    max-width: 760px;
    margin: 32px auto;
    padding: 44px 48px 56px;
    background: #fff;
    box-shadow: 0 8px 34px rgba(18, 43, 49, .08);
  }}
  h1 {{ font-size: 30px; line-height: 1.35; margin: 0 0 30px; }}
  h2 {{ font-size: 23px; line-height: 1.4; margin: 42px 0 18px; padding-left: 12px; border-left: 4px solid #28b894; }}
  p, li {{ font-size: 16px; line-height: 1.85; }}
  p {{ margin: 14px 0; }}
  ul, ol {{ padding-left: 25px; }}
  strong {{ color: #123f43; }}
  blockquote {{ margin: 18px 0; padding: 10px 18px; color: #607176; background: #f2f8f7; border-left: 3px solid #28b894; }}
  img {{ display: block; max-width: 100%; margin: 24px auto; border-radius: 8px; }}
  pre {{ overflow-x: auto; padding: 16px 18px; border-radius: 8px; background: #f5f7f8; font-size: 14px; line-height: 1.6; }}
  code {{ font-family: "SFMono-Regular", Consolas, monospace; }}
  hr {{ border: 0; border-top: 1px solid #e4e8e9; margin: 36px 0; }}
  @media (max-width: 820px) {{
    article {{ margin: 0; padding: 28px 22px 42px; box-shadow: none; }}
    h1 {{ font-size: 26px; }}
    h2 {{ font-size: 21px; }}
  }}
</style>
</head>
<body>
<article>
{body}
</article>
</body>
</html>
"""

output.write_text(html, encoding="utf-8")
print(output)
