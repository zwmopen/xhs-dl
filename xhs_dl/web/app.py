"""Web 入口 - 浏览器可视化版本"""

import sys
import json
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

from xhs_dl.core.downloader import extract_urls_from_text
from xhs_dl.core.v2_downloader import XhsV2Downloader, EngineNotReady

TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>xhs-dl 小红书笔记下载器</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB",sans-serif;
  background:linear-gradient(135deg,#ff2442 0%,#ff6b81 100%);min-height:100vh;
  display:flex;justify-content:center;align-items:center;padding:20px}
.card{background:#fff;border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,.15);
  width:100%;max-width:680px;padding:40px}
h1{text-align:center;font-size:28px;color:#ff2442;margin-bottom:6px}
.sub{text-align:center;color:#999;font-size:13px;margin-bottom:28px}
textarea{width:100%;height:160px;border:2px solid #eee;border-radius:12px;
  padding:14px;font-size:14px;resize:vertical;outline:none;
  font-family:inherit;transition:border-color .2s;line-height:1.6}
textarea:focus{border-color:#ff2442}
textarea::placeholder{color:#ccc}
.row{display:flex;gap:10px;margin-top:16px}
.row input{flex:1;padding:10px 14px;border:2px solid #eee;border-radius:12px;
  font-size:14px;outline:none;transition:border-color .2s}
.row input:focus{border-color:#ff2442}
.btn{background:#ff2442;color:#fff;border:none;border-radius:12px;
  padding:12px 32px;font-size:15px;font-weight:600;cursor:pointer;
  transition:all .2s;white-space:nowrap;min-width:120px}
.btn:hover{background:#e61e3a;transform:translateY(-1px)}
.btn:disabled{background:#ccc;cursor:not-allowed;transform:none}
.progress{margin-top:20px;display:none}
.progress.show{display:block}
.log{background:#f8f8f8;border-radius:10px;padding:14px;max-height:300px;
  overflow-y:auto;font-size:13px;line-height:1.8}
.log .item{padding:2px 0;border-bottom:1px solid #f0f0f0}
.log .item:last-child{border:none}
.log .ok{color:#52c41a}
.log .fail{color:#ff4d4f}
.log .info{color:#1890ff}
.summary{text-align:center;margin-top:16px;font-size:14px;color:#666}
.note{margin-top:14px;padding:10px 14px;background:#fff8e1;border-radius:8px;
  font-size:12px;color:#b8860b;line-height:1.6}
</style>
</head>
<body>
<div class="card">
  <h1>xhs-dl</h1>
  <p class="sub">小红书无水印下载器 V2.0 | 本地引擎 | 支持短链接 &amp; 分享文本</p>

  <textarea id="input" placeholder="粘贴小红书分享文本或链接，每行一个，也支持整段粘贴&#10;&#10;示例:&#10;快存下！vivo X300隐藏功能！ http://xhslink.com/o/xxxxx&#10;http://xhslink.com/o/yyyyy"></textarea>

  <div class="row">
    <input id="outdir" type="text" placeholder="保存目录（留空默认 ./xhs_downloads）">
    <select id="mode" style="padding:10px 14px;border:2px solid #eee;border-radius:12px;font-size:14px;outline:none;background:#fff;cursor:pointer;min-width:130px">
      <option value="fast">快速 3-8秒</option>
      <option value="normal">标准 8-15秒</option>
      <option value="cautious" selected>保守 25-45秒</option>
      <option value="slow">慢速 55-85秒</option>
      <option value="very-slow">极慢 110-160秒</option>
    </select>
    <button class="btn" id="go" onclick="start()">开始下载</button>
  </div>

  <div class="progress" id="progress">
    <div class="log" id="log"></div>
    <div class="summary" id="summary"></div>
  </div>

  <div class="note">提示: 默认提取无平台水印的原始媒体。批量任务会逐条慢速执行，请保持本窗口开启。</div>
</div>

<script>
let busy = false;
function start(){
  if(busy) return;
  const text = document.getElementById('input').value.trim();
  if(!text){alert('请粘贴链接或分享文本');return}
  busy = true;
  const btn = document.getElementById('go');
  btn.disabled = true; btn.textContent = '下载中...';
  const log = document.getElementById('log');
  const prog = document.getElementById('progress');
  const summary = document.getElementById('summary');
  log.innerHTML = ''; summary.textContent = '';
  prog.classList.add('show');

  fetch('/api/download',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({text, output_dir: document.getElementById('outdir').value.trim() || './xhs_downloads', mode: document.getElementById('mode').value})
  }).then(r=>r.json()).then(data=>{
    if(data.error){addLog(data.error,'fail')}
    else{data.items.forEach(it=>{
      const cls = it.success?'ok':'fail';
      const extra = it.image_count ? ` (${it.image_success}/${it.image_count}图)` : '';
      addLog(`[${it.success?'OK':'FAIL'}] ${it.title||it.error}${extra}`, cls);
    });summary.textContent=`完成! 成功 ${data.success} 失败 ${data.fail} 总计 ${data.total}`}
  }).catch(e=>addLog('请求失败: '+e.message,'fail'))
  .finally(()=>{busy=false;btn.disabled=false;btn.textContent='开始下载'});
}
function addLog(msg,cls){
  const d=document.createElement('div');d.className='item '+(cls||'');
  d.textContent=msg;document.getElementById('log').appendChild(d);
  document.getElementById('log').scrollTop=99999;
}
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    """HTTP 请求处理"""

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._html(TEMPLATE)
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path == "/api/download":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            text = body.get("text", "")
            output_dir = body.get("output_dir", "./xhs_downloads")
            mode = body.get("mode", "cautious")

            if not text.strip():
                self._json({"error": "请输入链接或分享文本"})
                return

            urls = extract_urls_from_text(text)
            if not urls:
                self._json({"error": "未检测到有效链接"})
                return

            from xhs_dl.core.downloader import DELAY_MODES
            delay = DELAY_MODES.get(mode, DELAY_MODES["cautious"])
            try:
                dl = XhsV2Downloader(output_dir=output_dir, delay=delay)
            except EngineNotReady as exc:
                self._json({"error": str(exc)}, 503)
                return
            result = dl.download(urls)

            items = []
            for r in result.results:
                items.append({
                    "success": r.success,
                    "title": r.title,
                    "error": r.error,
                    "image_count": r.image_count,
                    "image_success": r.image_success,
                })

            self._json({
                "items": items,
                "success": result.success_count,
                "fail": result.fail_count,
                "total": result.total,
            })
        else:
            self._json({"error": "not found"}, 404)

    def _html(self, html):
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        pass  # 静默 HTTP 日志


def main():
    host = "127.0.0.1"
    port = 5678
    server = HTTPServer((host, port), Handler)
    url = f"http://{host}:{port}"

    print(f"xhs-dl Web 版已启动: {url}")
    print("按 Ctrl+C 停止")

    # 自动打开浏览器
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
        server.server_close()


if __name__ == "__main__":
    main()
