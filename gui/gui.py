#!/usr/bin/env python3
"""WebView2 desktop interface for Link Distill."""
import json
import html as html_module
import os
import re
import subprocess
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from queue import Empty, Queue
from email.utils import parsedate_to_datetime
from pathlib import Path

try:
    import markdown
except ImportError:
    markdown = None


FROZEN = getattr(sys, "frozen", False)
BASE = Path(sys.executable).parent if FROZEN else Path(__file__).parent
DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "LinkDistill" if FROZEN else BASE
DATA_DIR.mkdir(parents=True, exist_ok=True)
GIST = Path(sys.executable) if FROZEN else BASE / "gist.py"
CONFIG_PATH = DATA_DIR / ".link_distill_config.json"
COOKIES_PATH = DATA_DIR / "browser_cookies.txt"
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")


def clean_url(value):
    match = re.search(r"https?://[^\s<>\"'，。！？；【】（）]+", value or "", re.IGNORECASE)
    return match.group(0).rstrip("，,。.!！?？:：;；)）]】") if match else ""


def normalize_api_base(value):
    value = (value or "").strip().rstrip("/")
    return value if re.match(r"^https?://", value, re.IGNORECASE) else ""


HTML = r"""
<!doctype html>
<html lang="zh-CN" data-theme="light">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Link Distill</title>
  <style>
    :root {
      --bg:#f2f2ef; --surface:#ffffff; --surface2:#e8e9e5; --text:#171917;
      --muted:#6a706b; --line:#d8dad5; --accent:#236b52; --accentText:#fff;
      --terminal:#111512; --terminalText:#dce9df; --danger:#b4382c;
      --shadow:0 18px 48px rgba(30,35,31,.11);
    }
    [data-theme="dark"] {
      --bg:#0d100e; --surface:#171b18; --surface2:#202521; --text:#edf1ed;
      --muted:#99a39b; --line:#303630; --accent:#6bc59d; --accentText:#0b1a13;
      --terminal:#080a09; --terminalText:#d5e4d9; --danger:#ff887b;
      --shadow:0 20px 55px rgba(0,0,0,.35);
    }
    *{box-sizing:border-box} body{margin:0;min-height:100vh;background:var(--bg);color:var(--text);font-family:"Segoe UI","Microsoft YaHei",sans-serif;transition:background .25s,color .25s}
    button,input,textarea,select{font:inherit} button{cursor:pointer}
    .app{min-height:100vh;display:grid;grid-template-rows:68px 1fr}
    header{display:flex;align-items:center;justify-content:space-between;padding:0 28px;border-bottom:1px solid var(--line);background:color-mix(in srgb,var(--surface) 88%,transparent);backdrop-filter:blur(16px)}
    .brand{display:flex;align-items:center;gap:11px;font-size:14px;font-weight:800;letter-spacing:1.4px}
    .mark{width:26px;height:26px;display:grid;place-items:center;background:var(--text);color:var(--bg);border-radius:5px;font-size:12px}
    .header-actions{display:flex;align-items:center;gap:9px}.status{display:flex;align-items:center;gap:7px;color:var(--muted);font-size:13px}.dot{width:7px;height:7px;border-radius:50%;background:#8d958f}.running .dot{background:var(--accent);animation:pulse 1.1s infinite}
    @keyframes pulse{50%{box-shadow:0 0 0 6px color-mix(in srgb,var(--accent) 20%,transparent)}}
    .icon-btn,.btn{height:38px;border:1px solid var(--line);border-radius:6px;background:var(--surface);color:var(--text);padding:0 13px;transition:transform .16s,background .16s,border-color .16s}.icon-btn{width:38px;padding:0;font-size:17px}.icon-btn:hover,.btn:hover{transform:translateY(-1px);border-color:var(--muted)}
    main{display:grid;grid-template-columns:minmax(300px,390px) minmax(420px,1fr);gap:18px;padding:22px;min-height:0}
    .panel{border:1px solid var(--line);border-radius:8px;background:var(--surface);box-shadow:var(--shadow);overflow:hidden}
    .compose{padding:22px;display:flex;flex-direction:column}.eyebrow{color:var(--muted);font-size:11px;font-weight:700;letter-spacing:1px}.compose h1{font-size:25px;line-height:1.25;margin:8px 0 20px;letter-spacing:0}
    textarea{width:100%;min-height:170px;resize:vertical;border:1px solid var(--line);border-radius:7px;background:var(--surface2);color:var(--text);padding:13px;line-height:1.55;outline:none;transition:border .15s,box-shadow .15s}textarea:focus,input:focus,select:focus{border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 18%,transparent)}
    .url-preview{min-height:38px;margin:10px 0 15px;padding:9px 10px;border-left:3px solid var(--accent);background:var(--surface2);font-size:12px;color:var(--muted);word-break:break-all}.url-preview.valid{color:var(--text)}
    .option{display:flex;align-items:center;justify-content:space-between;padding:13px 0;border-top:1px solid var(--line);font-size:14px}.option small{display:block;color:var(--muted);margin-top:3px}.switch{position:relative;width:42px;height:23px}.switch input{opacity:0}.slider{position:absolute;inset:0;background:var(--surface2);border:1px solid var(--line);border-radius:20px}.slider:before{content:"";position:absolute;width:17px;height:17px;left:2px;top:2px;border-radius:50%;background:var(--muted);transition:.18s}.switch input:checked+.slider:before{transform:translateX(19px);background:var(--accent)}
    .run{height:46px;border:0;border-radius:6px;background:var(--accent);color:var(--accentText);font-weight:750;margin-top:18px;transition:transform .15s,filter .15s}.run:hover{filter:brightness(1.06);transform:translateY(-1px)}button:disabled{opacity:.45;cursor:not-allowed;transform:none!important}
    .progress-wrap{margin-top:12px}.progress-meta{display:flex;justify-content:space-between;margin-bottom:6px;color:var(--muted);font-size:12px}.progress-track{height:7px;overflow:hidden;border-radius:4px;background:var(--surface2)}.progress-bar{width:0;height:100%;background:var(--accent);transition:width .35s ease}.metrics{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-top:10px}.metric{background:var(--surface2);padding:10px;border-radius:6px}.metric strong{display:block;font-size:16px}.metric span{font-size:11px;color:var(--muted)}
    .console{display:grid;grid-template-rows:52px 1fr;min-height:0}.console-head{display:flex;align-items:center;justify-content:space-between;padding:0 15px;border-bottom:1px solid var(--line);font-size:13px}.console-actions,.tabs{display:flex;gap:7px}.tab.active{background:var(--text);color:var(--bg);border-color:var(--text)}
    pre{margin:0;padding:16px;overflow:auto;background:var(--terminal);color:var(--terminalText);font:13px/1.6 Consolas,"Cascadia Mono",monospace;white-space:pre-wrap;word-break:break-word}.result{padding:22px 26px;overflow:auto;background:var(--surface);line-height:1.75}.result.streaming{white-space:pre-wrap}.result h1,.result h2,.result h3{line-height:1.35;margin:1.3em 0 .55em}.result h1{font-size:25px}.result h2{font-size:20px;border-bottom:1px solid var(--line);padding-bottom:7px}.result h3{font-size:16px}.result p{margin:.7em 0}.result ul,.result ol{padding-left:24px}.result blockquote{margin:1em 0;padding:8px 14px;border-left:3px solid var(--accent);background:var(--surface2);color:var(--muted)}.result code{font-family:Consolas,monospace;background:var(--surface2);padding:2px 5px;border-radius:4px}.result pre{background:var(--terminal);padding:14px;border-radius:6px;overflow:auto}.result pre code{background:none;padding:0}.empty-result{display:grid;place-items:center;height:100%;color:var(--muted)}
    dialog{width:min(720px,calc(100vw - 32px));max-height:88vh;padding:0;border:1px solid var(--line);border-radius:8px;background:var(--surface);color:var(--text);box-shadow:var(--shadow)}dialog::backdrop{background:rgba(0,0,0,.5);backdrop-filter:blur(4px)}
    .modal-head{height:60px;display:flex;align-items:center;justify-content:space-between;padding:0 20px;border-bottom:1px solid var(--line)}.modal-head h2{font-size:17px;margin:0}.modal-body{padding:20px;overflow:auto;max-height:calc(88vh - 120px)}.section{margin-bottom:24px}.section-title{font-size:12px;color:var(--muted);font-weight:800;letter-spacing:.8px;margin-bottom:11px}
    .field{margin-bottom:12px}.field label{display:block;font-size:12px;color:var(--muted);margin-bottom:6px}.field input,.field select{width:100%;height:40px;border:1px solid var(--line);border-radius:6px;background:var(--surface2);color:var(--text);padding:0 10px;outline:none}.inline{display:grid;grid-template-columns:1fr auto;gap:8px}.model-row{display:grid;grid-template-columns:1fr auto;gap:8px}.model-note{font-size:12px;color:var(--muted);margin-top:6px}
    .platforms{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.platform{height:42px;border:1px solid var(--line);border-radius:6px;background:var(--surface2);color:var(--text)}.cookie-state{margin-top:9px;font-size:12px;color:var(--muted)}
    .themes{display:grid;grid-template-columns:1fr 1fr;gap:9px}.theme-choice{height:52px;border:1px solid var(--line);border-radius:6px;background:var(--surface2);color:var(--text)}.theme-choice.active{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)}
    .modal-foot{height:60px;display:flex;align-items:center;justify-content:flex-end;gap:8px;padding:0 20px;border-top:1px solid var(--line)}.save{background:var(--accent);color:var(--accentText);border-color:var(--accent)}
    @media(max-width:850px){main{grid-template-columns:1fr;overflow:auto}.console{min-height:480px}.platforms{grid-template-columns:repeat(2,1fr)}}
  </style>
</head>
<body>
<div class="app">
  <header>
    <div class="brand"><span class="mark">LD</span>Link Distill</div>
    <div class="header-actions"><div id="status" class="status"><span class="dot"></span><span>空闲</span></div><button id="openSettings" class="icon-btn" title="设置">⚙</button></div>
  </header>
  <main>
    <section class="panel compose">
      <div class="eyebrow">内容蒸馏</div><h1>从分享文本中提取真正有用的内容</h1>
      <textarea id="input" placeholder="粘贴平台分享文本、口令或网址。程序只会保留其中有效的链接。"></textarea>
      <div id="urlPreview" class="url-preview">等待输入链接</div>
      <div class="option"><div>画面分析<small>使用本地 Ollama 视觉模型</small></div><label class="switch"><input id="vision" type="checkbox"><span class="slider"></span></label></div>
      <button id="run" class="run" disabled>开始蒸馏</button>
      <div class="progress-wrap"><div class="progress-meta"><span id="progressLabel">等待开始</span><span id="progressValue">0%</span></div><div class="progress-track"><div id="progressBar" class="progress-bar"></div></div></div>
      <div class="metrics"><div class="metric"><strong id="elapsed">0s</strong><span>运行时间</span></div><div id="modelMetric" class="metric" hidden><strong id="modelState"></strong><span>当前模型</span></div></div>
    </section>
    <section class="panel console"><div class="console-head"><div class="tabs"><button id="logTab" class="btn tab active">运行日志</button><button id="resultTab" class="btn tab">Markdown 结果</button></div><div class="console-actions"><button id="stop" class="btn" disabled>停止</button><button id="clear" class="btn">清空</button></div></div><pre id="log">准备就绪。\n</pre><article id="result" class="result" hidden><div class="empty-result">分析完成后在这里显示 Markdown 结果</div></article></section>
  </main>
</div>

<dialog id="settingsDialog">
  <div class="modal-head"><h2>设置</h2><button id="closeSettings" class="icon-btn">×</button></div>
  <div class="modal-body">
    <div class="section"><div class="section-title">接口与模型</div>
      <div class="field"><label>API Key</label><input id="apiKey" type="password" autocomplete="off"></div>
      <div class="field"><label>API 地址</label><input id="apiBase" placeholder="例如 https://api.example.com/v1"></div>
      <div class="field"><label>阿里百炼 ASR API Key</label><input id="asrApiKey" type="password" autocomplete="off" placeholder="用于 qwen3-asr-flash 在线语音识别"><div class="model-note">视频声音使用百炼 qwen3-asr-flash 在线识别。</div></div>
      <div class="field"><label>模型</label><div class="model-row"><select id="model"><option value="">等待获取或输入模型</option></select><button id="addModel" class="btn">手动输入</button></div><div id="modelNote" class="model-note">填写 API 地址和 Key 后自动读取服务器模型。</div></div>
      <div class="field"><label>自定义模型名称</label><div class="inline"><input id="customModel" placeholder="输入模型名"><button id="confirmModel" class="btn">加入列表</button></div></div>
    </div>
    <div class="section"><div class="section-title">网站登录</div><div class="platforms">
      <button class="platform" data-platform="douyin">抖音</button><button class="platform" data-platform="bilibili">哔哩哔哩</button><button class="platform" data-platform="xiaohongshu">小红书</button><button class="platform" data-platform="weibo">微博</button><button class="platform" data-platform="kuaishou">快手</button><button class="platform" data-platform="youtube">YouTube</button>
    </div><div class="field" style="margin-top:10px"><label>其他网站登录地址</label><div class="inline"><input id="customLogin" placeholder="https://example.com/login"><button id="customLoginBtn" class="btn">打开登录</button></div></div><div class="row" style="margin-top:10px"><button id="saveLogin" class="btn">保存当前登录</button></div><div id="cookieState" class="cookie-state">尚未保存网站登录信息</div></div>
    <div class="section"><div class="section-title">外观</div><div class="themes"><button class="theme-choice" data-theme="light">白色主题</button><button class="theme-choice" data-theme="dark">黑色主题</button></div></div>
  </div>
  <div class="modal-foot"><button id="cancelSettings" class="btn">取消</button><button id="saveSettings" class="btn save">保存设置</button></div>
</dialog>

<script>
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
async function callApi(method,...args){const r=await fetch('/api/'+method,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({args})});return await r.json()}
window.pywebview={api:{clean_url:v=>callApi('clean_url',v),get_config:()=>callApi('get_config'),save_config:v=>callApi('save_config',v),get_server_models:(b,k)=>callApi('get_server_models',b,k),login:(p,u)=>callApi('login',p,u),save_login:()=>callApi('save_login'),start:(u,v)=>callApi('start',u,v),stop:()=>callApi('stop'),get_result:()=>callApi('get_result')}};
const input=$('#input'), preview=$('#urlPreview'), run=$('#run'), log=$('#log'), dialog=$('#settingsDialog');
let currentUrl='', configuredModel='', timer=null, chosenTheme='light', customModels=[], modelTimer=null, streamingText='';
function append(t){log.textContent+=t;log.scrollTop=log.scrollHeight}
function setProgress(value,label){$('#progressBar').style.width=value+'%';$('#progressValue').textContent=value+'%';$('#progressLabel').textContent=label}
function showPane(name){const result=name==='result';$('#log').hidden=result;$('#result').hidden=!result;$('#logTab').classList.toggle('active',!result);$('#resultTab').classList.toggle('active',result)}
function setRunning(v){document.body.classList.toggle('running',v);run.disabled=v||!currentUrl;$('#stop').disabled=!v;$('#status span:last-child').textContent=v?'运行中':'空闲';if(v){const start=Date.now();setProgress(5,'正在读取链接');timer=setInterval(()=>$('#elapsed').textContent=Math.floor((Date.now()-start)/1000)+'s',500)}else{clearInterval(timer);timer=null}}
async function parseInput(){currentUrl=await window.pywebview.api.clean_url(input.value);preview.textContent=currentUrl||'没有检测到有效网址';preview.classList.toggle('valid',!!currentUrl);run.disabled=!currentUrl||document.body.classList.contains('running')}
function setOptions(models,selected){const unique=[...new Set(models.filter(Boolean))];$('#model').innerHTML='<option value="">等待获取或输入模型</option>'+unique.map(m=>`<option value="${m.replaceAll('"','&quot;')}">${m}</option>`).join('');$('#model').value=unique.includes(selected)?selected:''}
function showModel(model){$('#modelMetric').hidden=!model;$('#modelState').textContent=model||''}
async function loadConfig(){const c=await window.pywebview.api.get_config();chosenTheme=c.theme||'light';document.documentElement.dataset.theme=chosenTheme;customModels=c.custom_models||[];configuredModel=c.model||'';setOptions(customModels,configuredModel);$('#apiKey').value=c.api_key||'';$('#apiBase').value=c.api_base||'';$('#asrApiKey').value=c.asr_api_key||'';showModel(configuredModel);run.disabled=!currentUrl;$('#cookieState').textContent=c.cookies_saved?'登录信息已保存':'尚未保存网站登录信息';$$('.theme-choice').forEach(b=>b.classList.toggle('active',b.dataset.theme===chosenTheme))}
async function autoLoadModels(){const base=$('#apiBase').value.trim(),key=$('#apiKey').value.trim();if(!base||!key)return;$('#modelNote').textContent='正在读取服务器模型...';const selected=$('#model').value;const result=await window.pywebview.api.get_server_models(base,key);if(result.error){$('#modelNote').textContent=result.error;return}customModels=[...new Set([...customModels,...result.models])];setOptions(customModels,selected||result.models[0]||'');$('#modelNote').textContent=result.models.length?'已读取 '+result.models.length+' 个模型':'服务器没有返回模型'}
input.addEventListener('input',parseInput);
run.onclick=async()=>{log.textContent='';streamingText='';$('#result').classList.remove('streaming');setRunning(true);const ok=await window.pywebview.api.start(currentUrl,$('#vision').checked);if(!ok)setRunning(false)};
$('#stop').onclick=()=>window.pywebview.api.stop();$('#clear').onclick=()=>log.textContent='';
$('#logTab').onclick=()=>showPane('log');$('#resultTab').onclick=()=>showPane('result');
$('#openSettings').onclick=async()=>{await loadConfig();dialog.showModal()};$('#closeSettings').onclick=$('#cancelSettings').onclick=()=>dialog.close();
$$('.theme-choice').forEach(b=>b.onclick=()=>{chosenTheme=b.dataset.theme;document.documentElement.dataset.theme=chosenTheme;$$('.theme-choice').forEach(x=>x.classList.toggle('active',x===b))});
$('#addModel').onclick=()=>$('#customModel').focus();$('#confirmModel').onclick=()=>{const m=$('#customModel').value.trim();if(!m)return;customModels=[...new Set([...customModels,m])];setOptions(customModels,m);$('#customModel').value=''};
['#apiBase','#apiKey'].forEach(s=>$(s).addEventListener('input',()=>{clearTimeout(modelTimer);modelTimer=setTimeout(autoLoadModels,700)}));
$$('.platform').forEach(b=>b.onclick=()=>{append('[登录] 正在打开 '+b.textContent+'\n');window.pywebview.api.login(b.dataset.platform,'')});$('#customLoginBtn').onclick=()=>window.pywebview.api.login('custom',$('#customLogin').value.trim());
$('#saveLogin').onclick=async()=>{const r=await window.pywebview.api.save_login();$('#cookieState').textContent=r.message;append('[登录] '+r.message+'\n')};
$('#saveSettings').onclick=async()=>{if(!$('#model').value)await autoLoadModels();configuredModel=$('#model').value;await window.pywebview.api.save_config({api_key:$('#apiKey').value.trim(),api_base:$('#apiBase').value.trim(),asr_api_key:$('#asrApiKey').value.trim(),model:configuredModel,custom_models:customModels,theme:chosenTheme});showModel(configuredModel);run.disabled=!currentUrl;dialog.close();append('[设置] 已保存\n')};
window.onLog=append;window.onProgress=(value,label)=>setProgress(value,label);window.onAIChunk=chunk=>{if(!streamingText){$('#result').textContent='';$('#result').classList.add('streaming');showPane('result')}streamingText+=chunk;$('#result').textContent=streamingText;$('#result').scrollTop=$('#result').scrollHeight};window.onDone=async code=>{setRunning(false);setProgress(code===0?100:0,code===0?'处理完成':'处理未完成');append(code===0?'\n处理完成。\n':'\n处理没有完成，请按上面的提示检查后重试。\n');const data=await window.pywebview.api.get_result();if(data.html){$('#result').classList.remove('streaming');$('#result').innerHTML=data.html;showPane('result')}};
async function pollEvents(){for(;;){try{const r=await fetch('/events');const events=await r.json();for(const e of events){if(e.type==='log')window.onLog(e.text);else if(e.type==='progress')window.onProgress(e.value,e.label);else if(e.type==='chunk')window.onAIChunk(e.text);else if(e.type==='done')window.onDone(e.code)}}catch(e){}await new Promise(r=>setTimeout(r,150))}}
window.addEventListener('DOMContentLoaded',()=>{loadConfig();pollEvents()});
</script>
</body></html>
"""


class Api:
    def __init__(self):
        self.process = None
        self.window = None
        self.login_window = None
        self.result_started_at = 0
        self.events = Queue()

    def bind(self, window):
        self.window = window

    def clean_url(self, value):
        return clean_url(value)

    def get_config(self):
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8")) if CONFIG_PATH.exists() else {}
        except Exception:
            data = {}
        return {
            "api_key": data.get("api_key", ""), "api_base": data.get("api_base", ""),
            "asr_api_key": data.get("asr_api_key", ""),
            "model": data.get("model", ""), "custom_models": data.get("custom_models", []),
            "theme": data.get("theme") or "light", "cookies_saved": COOKIES_PATH.exists(),
        }

    def save_config(self, data):
        clean = {
            "api_key": str(data.get("api_key", "")).strip(),
            "api_base": normalize_api_base(str(data.get("api_base", ""))),
            "asr_api_key": str(data.get("asr_api_key", "")).strip(),
            "model": str(data.get("model") or "").strip(),
            "custom_models": list(dict.fromkeys(data.get("custom_models") or [])),
            "theme": "dark" if data.get("theme") == "dark" else "light",
        }
        CONFIG_PATH.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
        return True

    def get_server_models(self, api_base, api_key=""):
        api_base = normalize_api_base(api_base)
        if not api_base:
            return {"models": [], "error": "请先填写 API 地址"}
        try:
            payload = None
            last_error = None
            for path in ("/models", "/model"):
                try:
                    req = urllib.request.Request(api_base.rstrip("/") + path)
                    req.add_header("Authorization", f"Bearer {api_key}")
                    req.add_header("Accept", "application/json")
                    with urllib.request.urlopen(req, timeout=20) as response:
                        payload = json.loads(response.read().decode("utf-8"))
                    break
                except Exception as exc:
                    last_error = exc
            if payload is None:
                raise last_error or RuntimeError("服务器没有返回模型")
            items = payload.get("data", payload.get("models", payload)) if isinstance(payload, dict) else payload
            models = []
            for item in items if isinstance(items, list) else []:
                name = item if isinstance(item, str) else item.get("id") or item.get("name") or item.get("model")
                if name:
                    models.append(str(name))
            return {"models": list(dict.fromkeys(models)), "error": ""}
        except Exception as exc:
            message = str(exc).lower()
            if "401" in message or "unauthorized" in message:
                tip = "API Key 不正确"
            elif "403" in message or "forbidden" in message:
                tip = "这个 API Key 没有读取模型的权限"
            elif "404" in message or "not found" in message:
                tip = "API 地址不正确"
            elif "timeout" in message or "timed out" in message:
                tip = "服务器响应太慢，请检查网络"
            else:
                tip = "连接不到服务器，请检查 API 地址和网络"
            return {"models": [], "error": f"读取失败：{tip}"}

    def login(self, platform, url=""):
        urls = {
            "douyin": "https://www.douyin.com/", "bilibili": "https://www.bilibili.com/",
            "xiaohongshu": "https://www.xiaohongshu.com/", "weibo": "https://weibo.com/",
            "kuaishou": "https://www.kuaishou.com/", "youtube": "https://www.youtube.com/",
        }
        target = urls.get(platform, "")
        if platform == "custom":
            target = clean_url(url)
            if not target:
                self._log("[登录] 自定义地址无效\n")
                return False
        try:
            webbrowser.open(target)
            self.login_window = target
            return True
        except Exception as exc:
            self._log("[登录] 登录窗口没有打开，请稍后重试\n")
            return False

    def save_login(self):
        if not self.login_window:
            return {"ok": False, "message": "请先打开一个网站登录窗口"}
        return {"ok": True, "message": "登录页面已打开；程序会优先使用网页播放器读取内容"}

    def start(self, url, vision=False):
        if self.process and self.process.poll() is None:
            self._log("[错误] 已有任务正在运行\n")
            return False
        cleaned = clean_url(url)
        if not cleaned:
            self._log("[错误] 没有有效链接\n")
            return False
        cmd = ([str(GIST), "--worker"] if FROZEN else [sys.executable, str(GIST)]) + [cleaned] + (["--vision"] if vision else [])
        result_path = DATA_DIR / "last_analysis.json"
        self.result_started_at = result_path.stat().st_mtime if result_path.exists() else 0
        env = os.environ.copy(); env["PYTHONIOENCODING"] = "utf-8"
        try:
            self.process = subprocess.Popen(cmd, cwd=str(DATA_DIR), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", creationflags=CREATE_NO_WINDOW)
        except Exception as exc:
            self._log("[启动失败] 程序没有成功开始处理，请重新启动软件后重试\n"); self._done(-1); return False
        self._log(f"链接: {cleaned}\n\n")
        threading.Thread(target=self._pump, daemon=True).start()
        return True

    def get_result(self):
        path = DATA_DIR / "last_analysis.json"
        if not path.exists() or path.stat().st_mtime <= self.result_started_at:
            return {"html": "", "markdown": ""}
        try:
            try:
                raw = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                raw = path.read_text(encoding="gbk")
            text = json.loads(raw).get("analysis", "")
            if not text:
                return {"html": "", "markdown": ""}
            safe = html_module.escape(text, quote=False)
            rendered = markdown.markdown(safe, extensions=["fenced_code", "sane_lists", "nl2br"]) if markdown else f"<pre>{safe}</pre>"
            return {"html": rendered, "markdown": text}
        except Exception as exc:
            return {"html": "<p>结果文件没有正确生成，请重新处理一次。</p>", "markdown": ""}

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate(); self._log("\n[已请求停止]\n")
        return True

    def _pump(self):
        stages = {
            "[下载]": (15, "正在获取视频"), "[网页]": (20, "正在读取视频正文"),
            "[浏览器视频]": (28, "正在从播放器读取视频"),
            "[YouTube 字幕]": (25, "正在获取视频字幕"), "[图文]": (20, "正在读取图文内容"),
            "[百炼 ASR]": (45, "百炼正在识别视频语音"),
            "[画面]": (65, "正在分析视频画面"), "[AI]": (78, "AI 正在生成结果"),
        }
        for line in self.process.stdout or []:
            if line.startswith("__AI_CHUNK__"):
                try:
                    chunk = json.loads(line[len("__AI_CHUNK__"):])
                    self._ai_chunk(chunk)
                    self._progress(88, "AI 正在逐字输出")
                except Exception:
                    pass
                continue
            for marker, (value, label) in stages.items():
                if line.startswith(marker):
                    self._progress(value, label)
                    break
            self._log(line)
        self._done(self.process.wait())

    def _log(self, text):
        self.events.put({"type": "log", "text": text})

    def _progress(self, value, label):
        self.events.put({"type": "progress", "value": int(value), "label": label})

    def _ai_chunk(self, text):
        self.events.put({"type": "chunk", "text": text})

    def _done(self, code):
        self.events.put({"type": "done", "code": int(code)})


def main():
    api = Api()
    class Handler(BaseHTTPRequestHandler):
        def send_json(self, value, status=200):
            data = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

        def do_GET(self):
            if self.path == "/":
                data = HTML.encode("utf-8")
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
            elif self.path == "/events":
                events = []
                while len(events) < 100:
                    try: events.append(api.events.get_nowait())
                    except Empty: break
                self.send_json(events)
            else:
                self.send_json({"error": "not found"}, 404)

        def do_POST(self):
            try:
                size = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(size) or b"{}")
                method = self.path.removeprefix("/api/")
                if method.startswith("_") or not hasattr(api, method):
                    raise ValueError("unknown method")
                self.send_json(getattr(api, method)(*(body.get("args") or [])))
            except Exception:
                self.send_json({"error": "请求没有完成"}, 500)

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    profile = DATA_DIR / "webview2_profile"
    url = f"http://127.0.0.1:{port}/"
    host = BASE / "LinkDistill.WebView2Host.exe"
    try:
        if not host.exists():
            raise RuntimeError("WebView2 host is missing")
        process = subprocess.Popen([str(host), url, str(profile)])
        process.wait()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()


if __name__ == "__main__":
    if "--worker" in sys.argv:
        sys.argv.remove("--worker")
        from gist import main as worker_main
        worker_main()
    else:
        main()
