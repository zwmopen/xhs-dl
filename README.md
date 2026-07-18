# xhs-dl

小红书笔记下载器，支持提取笔记正文和图片到本地。

**无需登录账号。**

## 支持的链接格式

工具自动识别两种小红书链接格式，可混用：

1. **短链接**：`http://xhslink.com/o/xxxxx`（分享按钮复制，自动 302 重定向获取完整 URL）
2. **长链接**：`https://www.xiaohongshu.com/explore/{note_id}?xsec_token=...` 或 `https://www.xiaohongshu.com/discovery/item/{note_id}?xsec_token=...`

> 长链接必须带 `xsec_token` 参数，否则会被安全系统拦截返回 404。短链接重定向后会自动带上。
> 分享文本中 URL 后面的中英文标点（逗号、句号等）会被自动清理。

## 已知限制

- 下载的图片带有小红书平台水印（水印是服务端在图片上烧录的，技术上无法通过修改 URL 去除）
- 视频笔记暂仅下载封面图，不下载视频文件
- 频繁请求可能触发风控，工具内置 5 种延迟模式（默认 cautious 25-45 秒）

## 安装

```bash
# 克隆仓库
git clone https://github.com/zwmopen/xhs-dl.git
cd xhs-dl

# 安装依赖
pip install -r requirements.txt
```

或者直接安装为命令行工具：

```bash
pip install .
```

## 使用方式

### 方式一：命令行 (CLI)

```bash
# 下载单个笔记
xhs-dl "http://xhslink.com/o/xxxxx"

# 下载多个笔记
xhs-dl "链接1" "链接2" "链接3"

# 直接粘贴分享文本（自动提取链接）
xhs-dl "快存下！vivo X300隐藏功能！ http://xhslink.com/o/xxxxx"

# 从文件批量读取链接
xhs-dl -f links.txt

# 指定保存目录
xhs-dl -f links.txt -o ./我的笔记

# 指定延迟模式（默认 cautious）
xhs-dl -f links.txt --mode fast          # 快速 3-8秒，测试少量用
xhs-dl -f links.txt --mode cautious      # 保守 25-45秒，20条左右推荐
xhs-dl -f links.txt --mode slow          # 慢速 55-85秒，50条以上
```

#### 延迟模式

| 模式 | 间隔 | 适用场景 |
|------|------|---------|
| `fast` | 3-8秒 | 测试少量用，风险高 |
| `normal` | 8-15秒 | 日常 10 条以内 |
| `cautious` | 25-45秒 | 20 条左右推荐（默认）|
| `slow` | 55-85秒 | 50 条以上 |
| `very-slow` | 110-160秒 | 已被风控过才用 |

> 20 条笔记用 cautious 模式约需 8-15 分钟。CLI 会自动显示预计耗时。

### 方式二：Web 界面

```bash
# 启动 Web 服务（自动打开浏览器）
xhs-dl-web

# 或直接运行
python -m xhs_dl.web.app
```

然后在浏览器中打开 `http://127.0.0.1:5678`，粘贴链接或分享文本，点击"开始下载"即可。

### 方式三：Python 代码调用

```python
from xhs_dl import XhsDownloader, extract_urls_from_text

dl = XhsDownloader(output_dir="./notes")

# 从分享文本提取并下载
text = "快存下！vivo X300隐藏功能！ http://xhslink.com/o/xxxxx"
result = dl.download_text(text)

# 或直接传链接列表
result = dl.download([
    "http://xhslink.com/o/xxxxx",
    "http://xhslink.com/o/yyyyy",
])

print(f"成功: {result.success_count}, 失败: {result.fail_count}")
for r in result.results:
    print(f"  {'OK' if r.success else 'FAIL'} {r.title}")
```

## 输出结构

每个笔记自动创建以标题命名的文件夹：

```
xhs_downloads/
├── vivo X300隐藏功能！/
│   ├── 正文.txt          # 标题、作者、正文
│   ├── img_001.jpg       # 笔记图片
│   ├── img_002.jpg
│   └── ...
├── 红米 Watch 6 隐藏功能/
│   ├── 正文.txt
│   ├── img_001.jpg
│   └── ...
└── ...
```

## 原理

```
xhslink.com 短链接
    ↓ 302 重定向
完整 URL（含 xsec_token 等参数）
    ↓ HTTP GET（模拟 iPhone Safari）
笔记页面 HTML（SSR 渲染）
    ↓ 解析 window.__INITIAL_STATE__
笔记数据（标题、正文、图片 URL）
    ↓ 下载图片
本地文件
```

关键点：必须使用短链接重定向后的完整 URL（带 xsec_token），否则会被安全系统拦截。

## 项目结构

```
xhs-dl/
├── xhs_dl/
│   ├── __init__.py          # 包入口
│   ├── cli.py               # 命令行入口
│   ├── core/
│   │   ├── downloader.py    # 核心下载逻辑
│   │   └── models.py        # 数据模型
│   └── web/
│       └── app.py           # Web 界面（内置 HTML）
├── tests/                   # 测试
├── pyproject.toml           # 包配置
├── requirements.txt         # 依赖
├── LICENSE
└── README.md
```

## 常见问题

**Q: 图片有水印怎么办？**
A: 水印是小红书服务端在存储时就烧录到图片文件上的，不是通过 URL 参数添加的。这是平台行为，目前无法通过技术手段去除。

**Q: 下载失败 / 被拦截了？**
A: 稍等几分钟后重试。工具已内置随机延迟避免触发风控。如果持续失败，可能是你的 IP 被临时限制。

**Q: 支持视频下载吗？**
A: V1 版本暂不支持视频文件下载，仅下载封面图。后续版本会考虑支持。

**Q: 需要登录吗？**
A: 不需要。工具通过短链接自带的安全令牌（xsec_token）获取公开笔记数据。

## License

MIT