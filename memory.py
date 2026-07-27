#!/usr/bin/env python3
"""
记忆系统 — 轻量版
只记重要的事：配置、账户、项目状态
"""

import json, re
from pathlib import Path
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

BASE = Path(__file__).parent / "memory_data"
BASE.mkdir(exist_ok=True)
STORE = BASE / "store.json"


class Memory:
    def __init__(self):
        self.vec = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4), max_features=3000)
        self.items = self._load()

    def _load(self):
        if STORE.exists():
            return json.loads(STORE.read_text(encoding='utf-8'))
        return []

    def _save(self):
        STORE.write_text(json.dumps(self.items, ensure_ascii=False, indent=2), encoding='utf-8')

    def add(self, content: str, tags: list = None):
        """添加一条记忆（自动去重）"""
        content = content.strip()[:300]
        # 去重：检查前20个字符是否重复
        for item in self.items:
            if item['content'][:20] == content[:20]:
                item['hits'] = item.get('hits', 1) + 1
                item['updated'] = datetime.now().isoformat()
                self._save()
                return
        self.items.append({
            'content': content,
            'tags': tags or [],
            'hits': 1,
            'created': datetime.now().isoformat(),
            'updated': datetime.now().isoformat(),
        })
        self._save()

    def search(self, query: str, top_k: int = 3):
        """搜索记忆"""
        if not self.items or not query.strip():
            return []
        texts = [i['content'] for i in self.items]
        try:
            tfidf = self.vec.fit_transform(texts + [query])
            scores = cosine_similarity(tfidf[-1], tfidf[:-1]).flatten()
            # 关键词精确匹配加分
            q_words = set(query.lower().split())
            for i, item in enumerate(self.items):
                if q_words & set(item['content'].lower().split()):
                    scores[i] += 0.15
                scores[i] += min(item.get('hits', 1) * 0.02, 0.1)  # 访问频率加分
            idx = np.argsort(scores)[::-1][:top_k]
            return [{'score': round(float(scores[i]), 3), **self.items[i]}
                    for i in idx if scores[i] > 0.01]
        except:
            return []

    def recall(self, keyword: str):
        """快速回忆一条"""
        r = self.search(keyword, 1)
        return r[0]['content'] if r else None

    def count(self):
        return len(self.items)

    def clear(self):
        self.items = []
        self._save()


if __name__ == "__main__":
    m = Memory()
    print(f"📦 {m.count()} 条记忆\n")

    for q in ['邮箱', 'GitHub', '抖音', 'DeepSeek', '书籍']:
        r = m.search(q, 1)
        if r: print(f"  {q} → {r[0]['content'][:60]}")
