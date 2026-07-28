#!/usr/bin/env python3
"""知识库适配器 — 蒸馏笔记 → 各种知识库"""
import json, subprocess, shutil, urllib.request
from pathlib import Path

BASE = Path(__file__).parent
INSIGHTS = BASE / "INSIGHTS.md"

# ── 适配器 ──

def sync_obsidian(vault_path):
    """同步到 Obsidian（复制为 .md 文件）"""
    vault = Path(vault_path).expanduser()
    if not vault.exists():
        print(f"⚠ Obsidian 知识库不存在: {vault}")
        return
    shutil.copy2(INSIGHTS, vault / "gist蒸馏笔记.md")
    print(f"✅ → Obsidian: 已同步")

def sync_trilium(server_url, api_token):
    """通过 Trilium REST API 同步（需 Trilium 服务运行中）
    server_url: http://localhost:8080
    api_token: 从 Trilium 设置中获取
    """
    try:
        # 读取 INSIGHTS.md 内容
        content = INSIGHTS.read_text(encoding='utf-8')
        
        # 创建或更新笔记
        data = json.dumps({
            "content": content,
            "title": "gist蒸馏笔记",
            "parentNoteId": "root",
            "type": "text"
        }).encode()
        req = urllib.request.Request(
            f"{server_url}/api/notes",
            data=data,
            headers={"Authorization": api_token, "Content-Type": "application/json"},
            method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=10)
        print(f"✅ → Trilium: 已同步 ({resp.status})")
    except Exception as e:
        print(f"⚠ Trilium 同步失败: {e}")

def sync_swarmvault():
    """同步到 SwarmVault"""
    try:
        subprocess.run(["npx.cmd", "swarmvault", "ingest", str(INSIGHTS)], capture_output=True, timeout=30)
        subprocess.run(["npx.cmd", "swarmvault", "compile"], capture_output=True, timeout=60)
        print("✅ → SwarmVault: 已同步")
    except:
        print("⚠ SwarmVault 同步失败")

def sync_markdown(output_dir):
    """导出为标准 markdown"""
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(INSIGHTS, out / "gist蒸馏笔记.md")
    print(f"✅ → Markdown: {out / 'gist蒸馏笔记.md'}")

def status():
    """查看知识库状态"""
    print(f"📄 蒸馏笔记: {INSIGHTS}")
    n = INSIGHTS.stat().st_size if INSIGHTS.exists() else 0
    c = len([l for l in INSIGHTS.read_text().split('\n') if l.startswith('## ')]) if INSIGHTS.exists() else 0
    print(f"   大小: {n} 字 | 条目: {c} 条\n")
    
    print("📚 已适配的知识库：")
    print("   · SwarmVault  ✅ 已接入（自动同步）")
    print("   · Obsidian    → python kb.py sync-obsidian <vault路径>")
    print("   · Trilium     → python kb.py sync-trilium <url> <token>")
    print("   · Markdown    → python kb.py sync-markdown <目录>")
    print()
    print("   SwarmVault 状态：")
    try: subprocess.run(["npx.cmd", "swarmvault", "next"], timeout=15)
    except: print("   未运行")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python kb.py <命令> [参数]")
        print("   status              查看知识库状态")
        print("   sync-swarmvault     同步到 SwarmVault")
        print("   sync-obsidian <路径>  同步到 Obsidian")
        print("   sync-trilium <url> <token>  同步到 Trilium")
        print("   sync-markdown <目录>  导出 markdown")
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == "status": status()
    elif cmd == "sync-swarmvault": sync_swarmvault()
    elif cmd == "sync-obsidian" and len(sys.argv) > 2: sync_obsidian(sys.argv[2])
    elif cmd == "sync-trilium" and len(sys.argv) > 3: sync_trilium(sys.argv[2], sys.argv[3])
    elif cmd == "sync-markdown" and len(sys.argv) > 2: sync_markdown(sys.argv[2])
    else: print(f"未知命令")
