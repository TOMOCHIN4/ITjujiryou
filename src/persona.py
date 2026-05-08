"""ペルソナ漏れ検査の共通モジュール。

クライアントへ届くテキスト (deliver の delivery_message, send_message の content)
に事務所内ペルソナ用語が混入していないか検査する。
"""
from __future__ import annotations

FORBIDDEN_TERMS: list[str] = [
    "帝王", "聖帝", "サウザー", "南斗", "鳳凰拳", "オウガイ", "お師さん",
    "ふん、", "下郎", "雑兵", "退かぬ", "媚びぬ", "省みぬ",
    # 平仮名表記
    "ひかぬ", "こびぬ", "かえりみぬ",
    "愛などいらぬ", "ケンシロウ", "北斗",
]


def find_forbidden_terms(text: str) -> list[str]:
    if not text:
        return []
    return [t for t in FORBIDDEN_TERMS if t in text]
