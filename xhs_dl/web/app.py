"""xhs-dl V2 浏览器可视化界面。"""

import copy
import json
import threading
import time
import uuid
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

from xhs_dl.core.downloader import DELAY_MODES, extract_urls_from_text
from xhs_dl.core.v2_downloader import XhsV2Downloader, EngineNotReady


JOBS = {}
JOBS_LOCK = threading.Lock()


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta name="color-scheme" content="light">
<title>xhs-dl · 无水印下载</title>
<style>
:root{--radius-xl:28px;--radius-lg:22px;--radius-md:14px;--ease:220ms ease}
*{box-sizing:border-box}
html,body{margin:0;min-height:100%;font-family:"Microsoft YaHei UI","PingFang SC","Noto Sans CJK SC",sans-serif}
body[data-theme="neo"]{
  --bg:#e8edf3;--panel:#e2eaf2;--soft:#dce4ec;--line:#d1dbe4;
  --text:#242a31;--muted:#61758a;--primary:#263442;--primary-hover:#17222e;
  --active:#d7e4ef;--input:rgba(255,255,255,.34);--ok:#2f7b62;--bad:#a95055;
  --shadow:8px 8px 20px #c8d0d8,-8px -8px 20px #fbfdff;
  --shadow-hover:10px 10px 22px #c0c8d0,-10px -10px 22px #fff;
  --shadow-small:5px 5px 12px #c7cfd7,-5px -5px 12px #fbfdff;
  --shadow-inset:inset 3px 3px 7px #c8d0d8,inset -3px -3px 7px #f8fbfe;
}
body[data-theme="glass"]{
  --bg:#dfeaf2;--panel:rgba(235,244,249,.86);--soft:rgba(216,229,238,.72);
  --line:rgba(117,145,166,.18);--text:#102b45;--muted:#617a91;
  --primary:#2f6f9f;--primary-hover:#245c86;--active:#d6e7f8;
  --input:rgba(245,250,253,.66);--ok:#27785d;--bad:#a44d55;
  --shadow:8px 9px 20px rgba(105,132,151,.18),-5px -5px 13px rgba(255,255,255,.72);
  --shadow-hover:10px 12px 24px rgba(95,123,143,.22),-5px -5px 15px rgba(255,255,255,.78);
  --shadow-small:5px 6px 13px rgba(105,132,151,.16),-3px -3px 9px rgba(255,255,255,.68);
  --shadow-inset:inset 2px 2px 5px rgba(117,145,166,.16),inset -2px -2px 5px rgba(255,255,255,.52);
}
body{background:var(--bg);color:var(--text);padding:32px;transition:background var(--ease),color var(--ease)}
body[data-theme="glass"]:before{content:"";position:fixed;inset:0;pointer-events:none;background:radial-gradient(circle at 14% 18%,rgba(255,255,255,.55),transparent 34%),radial-gradient(circle at 84% 76%,rgba(146,181,204,.22),transparent 36%)}
.shell{position:relative;z-index:1;max-width:1120px;margin:0 auto}
.topbar{display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;padding:4px 6px}
.brand{display:flex;align-items:center;gap:14px}
.mark{width:48px;height:48px;border-radius:16px;display:grid;place-items:center;background:var(--panel);box-shadow:var(--shadow-small);font-family:Georgia,serif;font-size:21px;font-weight:700;letter-spacing:-1px}
.brand h1{font-family:Georgia,"Noto Serif SC",serif;font-size:25px;line-height:1;margin:0 0 7px;letter-spacing:-.4px}
.brand p{margin:0;color:var(--muted);font-size:13px}
.theme-switch{flex:0 0 auto;white-space:nowrap;border:1px solid var(--line);background:var(--panel);color:var(--text);box-shadow:var(--shadow-small);border-radius:999px;padding:10px 15px;cursor:pointer;transition:box-shadow var(--ease),transform var(--ease)}
.theme-switch:hover{box-shadow:var(--shadow-hover)}
.theme-switch:active{box-shadow:var(--shadow-inset);transform:translateY(1px)}
.workspace{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(300px,.75fr);gap:24px;align-items:start}
.surface{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius-xl);box-shadow:var(--shadow);padding:28px;transition:background var(--ease),box-shadow var(--ease)}
body[data-theme="glass"] .surface{backdrop-filter:blur(16px) saturate(115%);-webkit-backdrop-filter:blur(16px) saturate(115%)}
.eyebrow{display:flex;align-items:center;gap:8px;color:var(--muted);font-size:12px;letter-spacing:.12em;text-transform:uppercase;margin-bottom:10px}
.eyebrow:before{content:"";width:24px;height:2px;border-radius:2px;background:var(--primary)}
h2{font-family:Georgia,"Noto Serif SC",serif;font-size:29px;line-height:1.28;margin:0 0 10px;letter-spacing:-.5px}
.lead{margin:0 0 24px;color:var(--muted);line-height:1.75;font-size:14px}
label{display:block;font-size:13px;font-weight:700;margin-bottom:9px}
textarea,input,select{width:100%;border:1px solid var(--line);background:var(--input);color:var(--text);border-radius:var(--radius-md);outline:none;box-shadow:var(--shadow-inset);transition:border-color var(--ease),box-shadow var(--ease);font:inherit}
textarea{min-height:218px;padding:17px;resize:vertical;line-height:1.72}
input,select{height:46px;padding:0 13px}
textarea:focus,input:focus,select:focus{border-color:#6f9ab8;box-shadow:var(--shadow-inset),0 0 0 3px rgba(75,129,168,.15)}
textarea::placeholder,input::placeholder{color:#8092a2}
.settings{display:grid;grid-template-columns:1fr 160px;gap:14px;margin-top:18px}
.primary{width:100%;height:52px;margin-top:20px;border:0;border-radius:16px;background:var(--primary);color:#f7fafc;font-size:15px;font-weight:800;letter-spacing:.04em;cursor:pointer;box-shadow:0 10px 22px rgba(38,52,66,.2);transition:background var(--ease),transform var(--ease),box-shadow var(--ease)}
.primary:hover{background:var(--primary-hover);transform:translateY(-1px);box-shadow:0 12px 26px rgba(38,52,66,.25)}
.primary:active{transform:translateY(1px);box-shadow:0 5px 12px rgba(38,52,66,.22)}
.primary:disabled{cursor:not-allowed;opacity:.58;transform:none;box-shadow:none}
.privacy{display:flex;gap:10px;margin-top:16px;color:var(--muted);font-size:12px;line-height:1.65}
.shield{flex:0 0 25px;height:25px;border-radius:9px;display:grid;place-items:center;background:var(--active);font-size:12px}
.status-card{min-height:420px;display:flex;flex-direction:column}
.status-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px}
.state-dot{width:11px;height:11px;border-radius:999px;background:#8da0af;box-shadow:0 0 0 6px rgba(141,160,175,.12);margin-top:6px;transition:background var(--ease)}
.state-dot.running{background:#477b9d;animation:pulse 1.8s infinite}
.state-dot.done{background:var(--ok);box-shadow:0 0 0 6px rgba(47,123,98,.12)}
.state-dot.error{background:var(--bad);box-shadow:0 0 0 6px rgba(169,80,85,.12)}
.status-title{font-size:17px;font-weight:800;margin:0}.status-sub{font-size:12px;color:var(--muted);margin:6px 0 0}
.progress-wrap{margin:24px 0 18px}.progress-track{height:9px;border-radius:999px;background:var(--soft);box-shadow:var(--shadow-inset);overflow:hidden}
.progress-bar{height:100%;width:0;background:linear-gradient(90deg,#426f8d,#6b91aa);border-radius:inherit;transition:width 360ms ease}
.progress-meta{display:flex;justify-content:space-between;margin-top:9px;color:var(--muted);font-size:12px}
.empty{margin:auto 0;text-align:center;color:var(--muted);padding:34px 16px}
.empty-symbol{width:72px;height:72px;border-radius:24px;margin:0 auto 18px;display:grid;place-items:center;background:var(--panel);box-shadow:var(--shadow-small);font-family:Georgia,serif;font-size:28px;color:#6d8192}
.empty strong{display:block;color:var(--text);font-size:14px;margin-bottom:8px}
.results{display:none;gap:10px;flex-direction:column;max-height:330px;overflow:auto;padding:4px 5px 4px 2px}
.results.show{display:flex}.result{padding:13px 14px;border-radius:14px;background:var(--soft);border:1px solid var(--line);font-size:13px;line-height:1.55}
.result-top{display:flex;justify-content:space-between;gap:10px}.result-name{font-weight:700;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.result-count{white-space:nowrap;color:var(--muted);font-size:12px}
.result.ok{border-left:3px solid var(--ok)}.result.fail{border-left:3px solid var(--bad)}
.result-error{color:var(--bad);font-size:12px;margin-top:4px}
.footnote{text-align:center;color:var(--muted);font-size:11px;margin-top:22px;line-height:1.7}
button:focus-visible,textarea:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid rgba(47,111,159,.32);outline-offset:3px}
@keyframes pulse{0%,100%{box-shadow:0 0 0 5px rgba(71,123,157,.13)}50%{box-shadow:0 0 0 10px rgba(71,123,157,.04)}}
@media(max-width:760px){body{padding:18px 14px}.workspace{grid-template-columns:1fr}.surface{padding:20px;border-radius:22px}.settings{grid-template-columns:1fr}.topbar{align-items:flex-start}.brand p{max-width:210px}.status-card{min-height:330px}h2{font-size:25px}}
@media(max-width:480px){.topbar{gap:10px}.brand{min-width:0;gap:10px}.brand p{display:none}.mark{width:40px;height:40px;border-radius:13px;font-size:18px}.brand h1{font-size:22px;margin:9px 0 0}.theme-switch{padding:9px 11px;font-size:12px}.surface{padding:18px}textarea{min-height:190px}}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation:none!important;transition:none!important;scroll-behavior:auto!important}}
@supports not ((backdrop-filter:blur(1px)) or (-webkit-backdrop-filter:blur(1px))){body[data-theme="glass"] .surface{background:#edf4f8}}
</style>
</head>
<body data-theme="neo">
<main class="shell">
  <header class="topbar">
    <div class="brand"><div class="mark">x·</div><div><h1>xhs-dl</h1><p>公开笔记原始媒体 · 本地保存 · 无需登录</p></div></div>
    <button class="theme-switch" id="themeButton" type="button" aria-label="切换视觉主题">克制玻璃</button>
  </header>
  <section class="workspace">
    <div class="surface">
      <div class="eyebrow">Original media</div>
      <h2>把分享文本放进来，<br>剩下的交给本地引擎。</h2>
      <p class="lead">支持短链接、长链接和整段分享口令。批量任务逐条执行，完成一条就保存一条。</p>
      <label for="input">分享文本或链接</label>
      <textarea id="input" placeholder="例如：复制小红书分享文本到这里，也可以一次粘贴多条链接。"></textarea>
      <div class="settings">
        <div><label for="outdir">保存位置</label><input id="outdir" type="text" placeholder="留空则保存到 ./xhs_downloads"></div>
        <div><label for="mode">下载节奏</label><select id="mode"><option value="fast">快速 · 3–8 秒</option><option value="normal">标准 · 8–15 秒</option><option value="cautious" selected>保守 · 25–45 秒</option><option value="slow">慢速 · 55–85 秒</option><option value="very-slow">极慢 · 110–160 秒</option></select></div>
      </div>
      <button class="primary" id="go" type="button">开始提取原始媒体</button>
      <div class="privacy"><span class="shield">✓</span><span>公开笔记无需账号、密码或 Cookie。链接默认只交给本机引擎，不会静默发送到在线解析网站。</span></div>
    </div>
    <aside class="surface status-card" aria-live="polite">
      <div class="status-head"><div><p class="status-title" id="statusTitle">等待任务</p><p class="status-sub" id="statusSub">还没有开始下载</p></div><span class="state-dot" id="stateDot"></span></div>
      <div class="progress-wrap"><div class="progress-track"><div class="progress-bar" id="progressBar"></div></div><div class="progress-meta"><span id="progressText">0 / 0</span><span id="successText">成功 0</span></div></div>
      <div class="empty" id="empty"><div class="empty-symbol">↓</div><strong>结果会在这里逐条出现</strong><span>关闭页面不会删除已经保存到本地的文件。</span></div>
      <div class="results" id="results"></div>
    </aside>
  </section>
  <p class="footnote">仅处理你有权保存的公开内容 · 创作者嵌入原图的署名会保留 · xhs-dl V2.2</p>
</main>
<script>
const THEME_KEY='xhs-dl-theme',OUTPUT_KEY='xhs-dl-output',MODE_KEY='xhs-dl-mode';
const $=id=>document.getElementById(id);let activeJob=null,pollTimer=null;
function applyTheme(theme){const next=theme==='glass'?'glass':'neo';document.body.dataset.theme=next;localStorage.setItem(THEME_KEY,next);$('themeButton').textContent=next==='neo'?'克制玻璃':'拟态悬浮'}
applyTheme(localStorage.getItem(THEME_KEY)||'neo');
$('themeButton').addEventListener('click',()=>applyTheme(document.body.dataset.theme==='neo'?'glass':'neo'));
$('outdir').value=localStorage.getItem(OUTPUT_KEY)||'';$('mode').value=localStorage.getItem(MODE_KEY)||'cautious';
$('outdir').addEventListener('change',e=>localStorage.setItem(OUTPUT_KEY,e.target.value.trim()));$('mode').addEventListener('change',e=>localStorage.setItem(MODE_KEY,e.target.value));
function setState(status,title,sub){$('stateDot').className='state-dot '+status;$('statusTitle').textContent=title;$('statusSub').textContent=sub}
function render(job){const total=job.total||0,done=job.done||0,success=job.success||0;$('progressBar').style.width=(total?Math.round(done/total*100):0)+'%';$('progressText').textContent=`${done} / ${total}`;$('successText').textContent=`成功 ${success}`;
  const items=job.items||[];$('empty').style.display=items.length?'none':'block';$('results').classList.toggle('show',items.length>0);$('results').innerHTML='';items.forEach(it=>{const d=document.createElement('div');d.className='result '+(it.success?'ok':'fail');const top=document.createElement('div');top.className='result-top';const name=document.createElement('span');name.className='result-name';name.textContent=it.title||it.error||'未命名笔记';const count=document.createElement('span');count.className='result-count';count.textContent=it.success?`${it.image_success||0} 张`:'失败';top.append(name,count);d.append(top);if(!it.success&&it.error){const err=document.createElement('div');err.className='result-error';err.textContent=it.error;d.append(err)}$('results').append(d)});
  if(job.status==='running'||job.status==='queued')setState('running','正在逐条提取',total?`已完成 ${done} 条，共 ${total} 条`:'正在准备本地引擎');else if(job.status==='completed')setState(job.failed?'error':'done',job.failed?'任务完成，有失败项':'全部保存完成',`成功 ${job.success||0} 条，失败 ${job.failed||0} 条`);else if(job.status==='error')setState('error','任务没有完成',job.error||'请稍后重试')}
async function poll(){if(!activeJob)return;try{const r=await fetch('/api/jobs/'+activeJob);const job=await r.json();if(!r.ok)throw new Error(job.error||'读取任务失败');render(job);if(job.status==='completed'||job.status==='error'){activeJob=null;$('go').disabled=false;$('go').textContent='开始提取原始媒体';return}pollTimer=setTimeout(poll,900)}catch(e){setState('error','连接中断',e.message);$('go').disabled=false;$('go').textContent='重新开始';activeJob=null}}
async function start(){if(activeJob)return;const text=$('input').value.trim();if(!text){$('input').focus();setState('error','还缺少分享文本','请先粘贴至少一条小红书链接');return}const output_dir=$('outdir').value.trim()||'./xhs_downloads',mode=$('mode').value;localStorage.setItem(OUTPUT_KEY,$('outdir').value.trim());localStorage.setItem(MODE_KEY,mode);$('go').disabled=true;$('go').textContent='正在创建任务…';$('results').innerHTML='';$('results').classList.remove('show');$('empty').style.display='block';setState('running','正在准备','本地引擎即将开始');try{const r=await fetch('/api/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,output_dir,mode})});const data=await r.json();if(!r.ok)throw new Error(data.error||'创建任务失败');activeJob=data.job_id;$('go').textContent='下载进行中';poll()}catch(e){setState('error','无法开始',e.message);$('go').disabled=false;$('go').textContent='重新开始'}}
$('go').addEventListener('click',start);$('input').addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter')start()});
</script>
</body>
</html>"""


def _item_payload(item):
    return {
        "success": item.success,
        "title": item.title,
        "error": item.error,
        "image_count": item.image_count,
        "image_success": item.image_success,
        "save_dir": item.save_dir,
        "note_id": item.note_id,
    }


def _update_job(job_id, **values):
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(values)


def _run_job(job_id, urls, output_dir, delay):
    _update_job(job_id, status="running")

    def on_progress(item, index, total):
        with JOBS_LOCK:
            job = JOBS[job_id]
            job["items"].append(_item_payload(item))
            job["done"] = index
            job["success"] = sum(1 for value in job["items"] if value["success"])
            job["failed"] = index - job["success"]

    try:
        downloader = XhsV2Downloader(
            output_dir=output_dir,
            delay=delay,
            on_progress=on_progress,
        )
        result = downloader.download(urls)
        _update_job(
            job_id,
            status="completed",
            done=result.total,
            success=result.success_count,
            failed=result.fail_count,
            output_dir=result.output_dir,
        )
    except Exception as exc:
        _update_job(job_id, status="error", error=str(exc))


class Handler(BaseHTTPRequestHandler):
    """HTTP 请求处理。"""

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._html(TEMPLATE)
            return
        if self.path.startswith("/api/jobs/"):
            job_id = self.path.rsplit("/", 1)[-1]
            with JOBS_LOCK:
                job = copy.deepcopy(JOBS.get(job_id))
            if job is None:
                self._json({"error": "任务不存在"}, 404)
            else:
                self._json(job)
            return
        self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path != "/api/jobs":
            self._json({"error": "not found"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._json({"error": "请求格式无效"}, 400)
            return

        text = body.get("text", "")
        urls = extract_urls_from_text(text)
        if not urls:
            self._json({"error": "未检测到有效链接"}, 400)
            return
        output_dir = body.get("output_dir", "./xhs_downloads")
        mode = body.get("mode", "cautious")
        delay = DELAY_MODES.get(mode, DELAY_MODES["cautious"])
        try:
            XhsV2Downloader(output_dir=output_dir, delay=delay)
        except EngineNotReady as exc:
            self._json({"error": str(exc)}, 503)
            return

        job_id = uuid.uuid4().hex
        with JOBS_LOCK:
            if len(JOBS) >= 50:
                oldest = min(JOBS, key=lambda key: JOBS[key]["created_at"])
                JOBS.pop(oldest, None)
            JOBS[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "created_at": time.time(),
                "total": len(urls),
                "done": 0,
                "success": 0,
                "failed": 0,
                "items": [],
                "error": "",
                "output_dir": output_dir,
            }
        worker = threading.Thread(
            target=_run_job,
            args=(job_id, urls, output_dir, delay),
            daemon=True,
        )
        worker.start()
        self._json({"job_id": job_id, "status": "queued", "total": len(urls)}, 202)

    def _html(self, html):
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        pass


def main():
    host = "127.0.0.1"
    port = 5678
    server = HTTPServer((host, port), Handler)
    url = "http://{}:{}".format(host, port)
    print("xhs-dl V2.2 Web: {}".format(url))
    print("Press Ctrl+C to stop")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
