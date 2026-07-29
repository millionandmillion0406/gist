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

- **先查有没有现成的**：大项目动手前搜 GitHub + 全网。小项目（能一遍搞定的）不用查
- **方案反思**：动手前想一想——这个方案是最优的吗？有没有更简单的做法？哪里可能出问题？

## 干活后的习惯

- **反思**：每次完成任务，自问"最没把握的地方是什么？怎么让它更有把握？"
- **验证**：改完代码、做完功能，先跑通确认没问题再通知用户

## 干活

```bash
# 分析视频
DEEPSEEK_API_KEY="你的key" python gist.py "<链接>"

# 爬抖音图文
python douyin_note.py "<链接>"

# 查记忆
python -c "from memory import Memory; print(Memory().recall('关键词'))"
```
