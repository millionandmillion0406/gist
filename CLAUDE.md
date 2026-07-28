# link-distill — 扔链接，AI 自动蒸馏

## 启动

```bash
python -c "
from memory import Memory
m=Memory(); print(f'{m.count()}条事实')
for k in ['邮箱','GitHub','抖音','DeepSeek','投稿']: print(f'  {k} → {m.recall(k)}')
"
cat FACTS.md | head -30
cat INSIGHTS.md 2>/dev/null | head -15
```

## 干活前的习惯

- **先查有没有现成的**：动手前看看 GitHub 上有没有类似项目，能用直接用，能参考就参考
- **做完想一想**：每个环节有必要吗？有没有可以砍掉的？尽量简化

## 干活

```bash
# 分析视频
DEEPSEEK_API_KEY="你的key" python gist.py "<链接>"

# 爬抖音图文
python douyin_note.py "<链接>"

# 查记忆
python -c "from memory import Memory; print(Memory().recall('关键词'))"
```
