# Link Distill 桌面版（实验性）

社区贡献的 Windows 图形界面（贡献者：wanghao-dev2012），基于 WebView2 + Python。

> ⚠️ **实验性状态**：本目录代码由社区贡献，尚未经过完整验证，默认不启用 CI 发布。
> 核心功能请使用主目录的 CLI（`python gist.py <链接>`）。

## 运行

```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pywebview markdown
python gui.py
```

## 说明

- 界面：设置（API Key/地址/模型）、黑白主题、进度条、流式 AI 输出、Markdown 结果页
- 打包：`LinkDistill.spec`（PyInstaller）+ `installer.iss`（Inno Setup）+ `build_windows.ps1`
- 构建需要 WebView2 Runtime（Win10/11 自带）

## 已知限制

- **「网站登录」功能未实现**：设置页的登录按钮仅打开浏览器，不会抓取 cookie。
  需要登录态时请把 cookie 文件放到主目录（`douyin_cookies.txt`），CLI 会读取。
- 桌面版不打包本地转录模型（FunASR/Whisper），语音识别走百炼在线 ASR
  （需配置 `asr_api_key`）或回退到系统 Python 环境的本地转录。

## 贡献

GUI 的后续开发（真实登录、发布流程）欢迎继续贡献，请在主仓库提 issue/PR。
