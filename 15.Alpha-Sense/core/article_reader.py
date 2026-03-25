#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文章阅读器 — URL → 结构化内容 → 投资信号提取

支持来源：
- 微信公众号文章 (mp.weixin.qq.com)
- 一般网页文章

核心流程：
1. 抓取 URL 内容（带反爬头）
2. 解析 HTML → 干净文本
3. 提取关键数据（数字、百分比、金额）
4. 匹配标的、催化剂、技术阶段
5. 生成投资信号摘要
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class ArticleContent:
    """解析后的文章内容"""
    url: str
    title: str = ""
    source: str = ""
    publish_date: str = ""
    text: str = ""
    key_numbers: list[dict] = field(default_factory=list)
    success: bool = False
    error: str = ""


@dataclass
class ArticleSignal:
    """从文章中提取的投资信号"""
    title: str
    source_url: str
    summary: str
    key_data_points: list[str] = field(default_factory=list)
    bullish_signals: list[str] = field(default_factory=list)
    bearish_signals: list[str] = field(default_factory=list)
    related_tickers: list[str] = field(default_factory=list)
    matched_catalysts: list[str] = field(default_factory=list)
    tech_stage: str = ""
    signal_strength: str = "medium"  # weak / medium / strong
    suggested_prior: float = 0.50
    extracted_at: str = ""

    def __post_init__(self):
        if not self.extracted_at:
            self.extracted_at = datetime.now().isoformat()


# ---------------------------------------------------------------------------
# HTTP 请求（带反爬）
# ---------------------------------------------------------------------------

# 模拟正常浏览器
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def fetch_url(url: str, timeout: int = 20) -> ArticleContent:
    """
    抓取 URL 内容并解析为干净文本

    参数:
        url: 文章链接
        timeout: 超时秒数

    返回:
        ArticleContent 对象
    """
    if not HAS_REQUESTS:
        return ArticleContent(url=url, error="requests 库未安装，请运行: pip install requests")
    if not HAS_BS4:
        return ArticleContent(url=url, error="beautifulsoup4 未安装，请运行: pip install beautifulsoup4")

    # 基本 URL 校验
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return ArticleContent(url=url, error=f"不支持的协议: {parsed.scheme}")
    if not parsed.netloc:
        return ArticleContent(url=url, error="无效的 URL")

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=timeout)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        html = resp.text
    except requests.exceptions.Timeout:
        return ArticleContent(url=url, error="请求超时，请稍后重试")
    except requests.exceptions.RequestException as e:
        return ArticleContent(url=url, error=f"请求失败: {e}")

    # 判断来源类型并解析
    domain = parsed.netloc.lower()
    if "mp.weixin.qq.com" in domain:
        return _parse_wechat(url, html)
    else:
        return _parse_generic(url, html)


# ---------------------------------------------------------------------------
# 微信公众号专用解析
# ---------------------------------------------------------------------------

def _parse_wechat(url: str, html: str) -> ArticleContent:
    """解析微信公众号文章"""
    soup = BeautifulSoup(html, "html.parser")

    # 标题
    title = ""
    title_tag = soup.find("h1", class_="rich_media_title") or soup.find("h1")
    if title_tag:
        title = title_tag.get_text(strip=True)

    # 作者/公众号名
    source = ""
    source_tag = soup.find("a", id="js_name") or soup.find("strong", class_="profile_nickname")
    if source_tag:
        source = source_tag.get_text(strip=True)

    # 发布时间
    publish_date = ""
    # 微信文章的时间通常在 script 或 meta 中
    date_match = re.search(r'var\s+ct\s*=\s*"(\d+)"', html)
    if date_match:
        import time
        ts = int(date_match.group(1))
        publish_date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    if not publish_date:
        # 尝试从页面文本中提取日期
        date_match2 = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', html)
        if date_match2:
            publish_date = f"{date_match2.group(1)}-{int(date_match2.group(2)):02d}-{int(date_match2.group(3)):02d}"

    # 正文
    content_div = soup.find("div", class_="rich_media_content") or soup.find("div", id="js_content")
    if content_div:
        # 清理脚本和样式
        for tag in content_div.find_all(["script", "style", "noscript"]):
            tag.decompose()
        text = content_div.get_text(separator="\n", strip=True)
    else:
        # 回退：用整个 body
        body = soup.find("body")
        if body:
            for tag in body.find_all(["script", "style", "noscript", "nav", "header", "footer"]):
                tag.decompose()
            text = body.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

    # 清理空行
    text = _clean_text(text)

    # 提取关键数字
    key_numbers = _extract_key_numbers(text)

    return ArticleContent(
        url=url,
        title=title,
        source=source,
        publish_date=publish_date,
        text=text,
        key_numbers=key_numbers,
        success=True,
    )


# ---------------------------------------------------------------------------
# 通用网页解析
# ---------------------------------------------------------------------------

def _parse_generic(url: str, html: str) -> ArticleContent:
    """解析通用网页文章"""
    soup = BeautifulSoup(html, "html.parser")

    # 标题: <title> 或 <h1>
    title = ""
    if soup.title:
        title = soup.title.get_text(strip=True)
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True)

    # 来源
    source = urlparse(url).netloc

    # 正文: 尝试 <article>，回退到 <body>
    article = soup.find("article")
    if article:
        for tag in article.find_all(["script", "style", "noscript"]):
            tag.decompose()
        text = article.get_text(separator="\n", strip=True)
    else:
        body = soup.find("body")
        if body:
            for tag in body.find_all(["script", "style", "noscript", "nav", "header", "footer", "aside"]):
                tag.decompose()
            text = body.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

    text = _clean_text(text)
    key_numbers = _extract_key_numbers(text)

    return ArticleContent(
        url=url,
        title=title,
        source=source,
        text=text,
        key_numbers=key_numbers,
        success=True,
    )


# ---------------------------------------------------------------------------
# 文本清洗
# ---------------------------------------------------------------------------

def _clean_text(text: str) -> str:
    """清理文本：去除多余空行、空白"""
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 关键数字提取
# ---------------------------------------------------------------------------

# 金额模式：匹配"XXX亿美元"、"$XXB"等
_MONEY_PATTERNS = [
    # 中文
    re.compile(r'(\d+[\d,.]*)\s*([万亿千百])?\s*(美元|人民币|元|美金|港币|RMB|USD|HKD)', re.IGNORECASE),
    # 英文缩写
    re.compile(r'\$\s*(\d+[\d,.]*)\s*(B|M|T|billion|million|trillion)?', re.IGNORECASE),
]

# 百分比模式
_PCT_PATTERN = re.compile(r'(\d+[\d,.]*)\s*(%|倍|x)\b', re.IGNORECASE)

# 增长率/关键指标
_GROWTH_PATTERNS = [
    re.compile(r'(营收|收入|利润|净利|增长|增速|年化|ARR|revenue|income|profit|growth)\D{0,10}?(\d+[\d,.]*)\s*(%|亿|万|倍)', re.IGNORECASE),
    re.compile(r'(估值|市值|融资)\D{0,10}?(\d+[\d,.]*)\s*(亿|万|美元|billion|B)', re.IGNORECASE),
    re.compile(r'(用户|客户|DAU|MAU)\D{0,10}?(\d+[\d,.]*)\s*(万|亿|家|人|million|M)?', re.IGNORECASE),
]


def _extract_key_numbers(text: str) -> list[dict]:
    """从文本中提取关键财务数字"""
    results = []
    seen = set()

    for pattern in _GROWTH_PATTERNS:
        for m in pattern.finditer(text):
            # 取匹配前后的上下文
            start = max(0, m.start() - 20)
            end = min(len(text), m.end() + 20)
            context = text[start:end].replace("\n", " ").strip()
            key = f"{m.group(1)}_{m.group(2)}"
            if key not in seen:
                seen.add(key)
                results.append({
                    "metric": m.group(1),
                    "value": m.group(2),
                    "unit": m.group(3) if m.lastindex >= 3 else "",
                    "context": context,
                })

    return results[:20]  # 限制数量


# ---------------------------------------------------------------------------
# 投资信号提取
# ---------------------------------------------------------------------------

# 利好关键词
_BULLISH_KEYWORDS = [
    "增长", "翻倍", "超预期", "爆发", "突破", "创新高", "大幅提升",
    "加速", "领先", "颠覆", "革命", "垄断", "护城河", "飞轮",
    "规模化", "提价", "毛利率提升", "市占率提升", "渗透率提升",
    "beat", "outperform", "upgrade", "accelerate", "dominate",
    "10倍", "百倍", "指数级", "自我递归", "复利",
]

# 利空关键词
_BEARISH_KEYWORDS = [
    "下降", "下滑", "萎缩", "亏损", "裁员", "竞争加剧",
    "泡沫", "过热", "监管", "反垄断", "制裁", "关税",
    "放缓", "衰退", "见顶", "天花板", "瓶颈",
    "miss", "downgrade", "decline", "risk", "threat",
    "威胁", "挑战", "受损", "受冲击", "崩溃",
]


def extract_signals(article: ArticleContent) -> ArticleSignal:
    """
    从文章内容中提取投资信号

    参数:
        article: ArticleContent 对象

    返回:
        ArticleSignal 结构化信号
    """
    from core.signal_capture import match_tickers, match_catalysts, guess_tech_stage

    full_text = f"{article.title}\n{article.text}"

    # 1. 标的匹配
    tickers = match_tickers(full_text)

    # 2. 催化剂匹配
    catalysts = match_catalysts(full_text)

    # 3. 技术阶段
    stage = guess_tech_stage(full_text)

    # 4. 利好/利空提取（带上下文）
    bullish = _extract_sentiment_signals(full_text, _BULLISH_KEYWORDS)
    bearish = _extract_sentiment_signals(full_text, _BEARISH_KEYWORDS)

    # 5. 关键数据点（从 key_numbers 格式化）
    data_points = []
    for kn in article.key_numbers:
        dp = f"{kn['metric']}: {kn['value']}{kn.get('unit', '')}"
        data_points.append(dp)

    # 6. 摘要（取前 300 字 + 数据亮点）
    summary = _generate_summary(article, tickers, bullish, bearish)

    # 7. 信号强度评估
    strength = _assess_strength(
        bull_count=len(bullish),
        bear_count=len(bearish),
        data_count=len(data_points),
        catalyst_count=len(catalysts),
        ticker_count=len(tickers),
    )

    # 8. 建议先验
    prior = _suggest_article_prior(strength, len(catalysts), len(bullish), len(bearish))

    return ArticleSignal(
        title=article.title,
        source_url=article.url,
        summary=summary,
        key_data_points=data_points,
        bullish_signals=bullish,
        bearish_signals=bearish,
        related_tickers=tickers,
        matched_catalysts=catalysts,
        tech_stage=stage,
        signal_strength=strength,
        suggested_prior=prior,
    )


def _extract_sentiment_signals(text: str, keywords: list[str]) -> list[str]:
    """提取带有特定情绪关键词的句子片段"""
    results = []
    seen_context = set()

    for kw in keywords:
        for m in re.finditer(re.escape(kw), text, re.IGNORECASE):
            # 取关键词前后 60 字符作为上下文
            start = max(0, m.start() - 40)
            end = min(len(text), m.end() + 40)
            context = text[start:end].replace("\n", " ").strip()

            # 去重：如果上下文前 30 字符相同则跳过
            context_key = context[:30]
            if context_key not in seen_context:
                seen_context.add(context_key)
                results.append(context)

    return results[:15]  # 限制数量


def _generate_summary(
    article: ArticleContent,
    tickers: list[str],
    bullish: list[str],
    bearish: list[str],
) -> str:
    """生成文章投资摘要"""
    parts = []

    if article.title:
        parts.append(f"【{article.title}】")
    if article.source:
        parts.append(f"来源: {article.source}")
    if article.publish_date:
        parts.append(f"日期: {article.publish_date}")

    # 核心信息
    text_preview = article.text[:200].replace("\n", " ")
    parts.append(f"\n要点: {text_preview}...")

    if tickers:
        parts.append(f"\n关联标的: {', '.join(tickers)}")
    parts.append(f"\n利好信号: {len(bullish)} 条 | 利空信号: {len(bearish)} 条")

    return "\n".join(parts)


def _assess_strength(
    bull_count: int,
    bear_count: int,
    data_count: int,
    catalyst_count: int,
    ticker_count: int,
) -> str:
    """评估信号强度"""
    score = 0
    score += min(bull_count, 5)        # 利好数（上限5分）
    score -= min(bear_count, 3)        # 利空惩罚
    score += min(data_count, 3)        # 数据支撑
    score += catalyst_count * 2        # 催化剂加权
    score += min(ticker_count, 3)      # 标的关联

    if score >= 8:
        return "strong"
    elif score >= 4:
        return "medium"
    else:
        return "weak"


def _suggest_article_prior(
    strength: str,
    catalyst_count: int,
    bull_count: int,
    bear_count: int,
) -> float:
    """根据文章分析结果建议先验概率"""
    base = {"weak": 0.45, "medium": 0.52, "strong": 0.58}.get(strength, 0.50)
    base += min(catalyst_count * 0.03, 0.09)
    # 利好/利空差值调整
    net_sentiment = min(bull_count, 8) - min(bear_count, 5)
    base += net_sentiment * 0.01
    return max(0.35, min(0.65, base))


# ---------------------------------------------------------------------------
# 整合入口
# ---------------------------------------------------------------------------

def read_and_analyze(url: str) -> tuple[ArticleContent, ArticleSignal | None]:
    """
    一键读取文章并提取投资信号

    参数:
        url: 文章链接

    返回:
        (ArticleContent, ArticleSignal | None)
    """
    article = fetch_url(url)
    if not article.success:
        return article, None

    signal = extract_signals(article)
    return article, signal
