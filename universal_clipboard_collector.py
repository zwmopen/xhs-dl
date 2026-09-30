# -*- coding: utf-8 -*-
"""
小红书剪贴板极速无感自动采集入库守护程序 (Clipboard XHS Auto Collector) - V3.0 风控冷却与待下载队列增强版
核心特性：
1. 0 内存抢占与 0 剪贴板污染：仅在剪贴板含有 xhslink.cn / xiaohongshu.com 时无感触发，其余内容 100% 穿透放行；
2. 待下载持久化队列 (Pending Queue)：连续复制多个链接时自动进队列暂存，绝不并发爆破小红书；
3. 智能风控与拟人冷却 (Risk Control & Cooldown)：
   - 正常采集后拟人间隔 (8~15秒随机抖动)，保护 IP 与网络；
   - 遭遇频率限制/下载异常时自动进入深度冷却阶梯退避 (60s/120s/180s)，待下载链接 100% 留存，冷却完毕全自动续接下载；
4. 本地万能下载器 V2 核心直解：无水印原画组图 + 完整文案，0 Cookie、0 依赖浏览器；
5. 智能地名分流：自动识别精准流量城市目录（宁波/金华义乌/安吉/台州等），自动建立秋季四季硬链接；
6. 元数据标定：自动写入 metadata.json（打上"剪切板下载"、"万能下载器下载"等标签）；
7. 桌面原生轻量通知：屏幕右下角弹出拟态系统通知卡片，绝不打扰飞书；
8. 单实例进程互斥：Win32 Global Mutex 防多开防冲突。
"""

import os
import sys
import time
import re
import json
import shutil
import random
import threading
import subprocess
import traceback
import importlib.util
from pathlib import Path
import ctypes
from ctypes import wintypes

# ==================== 动态配置与解耦加载器 (MaterialHub Config Loader) ====================
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent

# 优先在自包含 lib 目录下寻找 xhs_dl
LIB_DIR = SCRIPT_DIR / "lib"
if (LIB_DIR / "xhs_dl").exists():
    sys.path.insert(0, str(LIB_DIR))

# 自动探测配置文件
CONFIG_FILE = None
for candidate in [
    os.environ.get("MATERIAL_HUB_CONFIG"),
    SKILL_ROOT / "config" / "config.json",
    SCRIPT_DIR / "config" / "config.json",
    SCRIPT_DIR / "config.json"
]:
    if candidate and Path(candidate).exists():
        CONFIG_FILE = Path(candidate)
        break

# 自愈配置：若无 config.json 则自动从 config.example.json 释放默认便携配置
if not CONFIG_FILE:
    for example_cand in [
        SKILL_ROOT / "config" / "config.example.json",
        SCRIPT_DIR / "config" / "config.example.json",
        SCRIPT_DIR / "config.example.json"
    ]:
        if example_cand and Path(example_cand).exists():
            target_cfg = example_cand.parent / "config.json"
            try:
                shutil.copy2(str(example_cand), str(target_cfg))
                CONFIG_FILE = target_cfg
                break
            except Exception:
                pass

LOADED_CONFIG = {}
if CONFIG_FILE and CONFIG_FILE.exists():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f_cfg:
            LOADED_CONFIG = json.load(f_cfg)
    except Exception:
        pass

storage_cfg = LOADED_CONFIG.get("storage", {})
bm_cfg = LOADED_CONFIG.get("benchmark", {})
rc_cfg = LOADED_CONFIG.get("risk_control", {})
notify_cfg = LOADED_CONFIG.get("notification", {})
feishu_cfg = notify_cfg.get("feishu", {})
rules_cfg = LOADED_CONFIG.get("classification_rules", {})

# 运行时数据与日志目录 (自适应解耦：优先 config -> 宿主历史兼容路径 -> 本地 data 目录)
configured_data_dir = storage_cfg.get("data_dir")
if configured_data_dir:
    DATA_DIR = Path(configured_data_dir)
elif Path(r"D:\AICode\工具开发\projects\xhs-dl").exists() and (Path(r"D:\AICode\工具开发\projects\xhs-dl") / "clipboard_history.json").exists():
    DATA_DIR = Path(r"D:\AICode\工具开发\projects\xhs-dl")
else:
    DATA_DIR = SKILL_ROOT / "data"

try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    DATA_DIR = Path.home() / ".material_hub"
    DATA_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_ROOT = DATA_DIR
DAEMON_LOG_FILE = DATA_DIR / "collector_daemon.log"
HISTORY_FILE = DATA_DIR / "clipboard_history.json"
QUEUE_FILE = DATA_DIR / "clipboard_pending_queue.json"

def log_daemon(msg: str):
    try:
        with open(DAEMON_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except:
        pass

# 如果由 pythonw.exe 无窗口静默拉起，重定向输出至日志文件
if sys.stdout is None:
    try:
        sys.stdout = open(DAEMON_LOG_FILE, "a", encoding="utf-8", buffering=1)
    except:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    try:
        sys.stderr = open(DAEMON_LOG_FILE, "a", encoding="utf-8", buffering=1)
    except:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")

if hasattr(sys.stdout, "reconfigure") and sys.stdout:
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    except:
        pass

# 基础存储路径自适应 (优先读取 config.json，若配置相对路径则基于 SKILL_ROOT；缺省时智能适配)
def _resolve_dir(cfg_path: str, default_name: str) -> Path:
    if cfg_path:
        p = Path(cfg_path)
        if not p.is_absolute():
            p = (SKILL_ROOT / p).resolve()
        return p
    native_cand = Path(r"D:\AICode\项目推进\projects\江湖有旅人\主项目\01-素材库")
    if native_cand.exists():
        return native_cand if not default_name else (native_cand / default_name)
    fallback_cand = Path.home() / "Downloads" / "MaterialHub" / "素材库"
    return fallback_cand if not default_name else (fallback_cand / default_name)

BASE_MATERIAL_DIR = _resolve_dir(storage_cfg.get("material_root_dir"), "")
PRECISION_DIR = _resolve_dir(storage_cfg.get("precision_dir"), "精准流量") if storage_cfg.get("precision_dir") else (BASE_MATERIAL_DIR / "精准流量")
AUTUMN_DIR = _resolve_dir(storage_cfg.get("autumn_dir"), "秋季（9—11月·智能分类）") if storage_cfg.get("autumn_dir") else (BASE_MATERIAL_DIR / "秋季（9—11月·智能分类）")
ALL_SEASON_DIR = _resolve_dir(storage_cfg.get("all_season_dir"), "四季通用（全年·无季节限制）") if storage_cfg.get("all_season_dir") else (BASE_MATERIAL_DIR / "四季通用（全年·无季节限制）")

temp_cfg = storage_cfg.get("temp_download_dir")
if temp_cfg:
    p = Path(temp_cfg)
    TEMP_DOWNLOAD_DIR = (SKILL_ROOT / p).resolve() if not p.is_absolute() else p
elif Path(r"D:\AICode\运行数据\临时文件\xhs_clipboard_staging").parent.exists():
    TEMP_DOWNLOAD_DIR = Path(r"D:\AICode\运行数据\临时文件\xhs_clipboard_staging")
else:
    TEMP_DOWNLOAD_DIR = DATA_DIR / "temp_staging"

C_DOWNLOADS_DIR = Path(storage_cfg.get("unclassified_downloads_dir", str(Path.home() / "Downloads")))

# 对标账号清单
SECOND_BRAIN_BENCHMARK_FILE = Path(bm_cfg.get("second_brain_benchmark_file", r"D:\SecondBrain\zwm-second-brain\03-项目\01-团建项目—江湖有旅人\对标账号与样板观察清单.md"))
PROJECT_BENCHMARK_FILE = Path(bm_cfg.get("project_benchmark_file", r"D:\AICode\项目推进\projects\江湖有旅人\主项目\05-知识库\06-数据与复盘\复盘文件\素材库归档文档\对标账号完整清单.md"))
BENCHMARK_FILE = PROJECT_BENCHMARK_FILE if PROJECT_BENCHMARK_FILE.exists() else SECOND_BRAIN_BENCHMARK_FILE

# 风控与冷却配置
NORMAL_COOLDOWN_RANGE = tuple(rc_cfg.get("normal_cooldown_range", [15.0, 28.0]))
DEEP_COOLDOWN_BASE = rc_cfg.get("deep_cooldown_base_seconds", 60)
MAX_RETRIES = rc_cfg.get("max_retries", 4)

# 引入万能下载器 CLI
try:
    from xhs_dl.cli import main as xhs_dl_main
except Exception as e:
    if sys.stdout:
        print(f"Warning: Failed to import xhs_dl.cli directly: {e}")

# 引入本地桌面通知模块
NOTIFY_PY = None
_notify_candidates = [
    SKILL_ROOT.parent / "shared-notification" / "scripts" / "shared_notify.py",
    Path(r"D:\AICode\.agents\skills\shared-notification\scripts\shared_notify.py"),
    Path(r"D:\AICode\AI\skills\技能包\技能\shared-notification\scripts\shared_notify.py"),
]
for candidate in _notify_candidates:
    if candidate.exists():
        NOTIFY_PY = candidate
        break

if not NOTIFY_PY and SKILL_ROOT.parent.exists():
    for root, dirs, files in os.walk(str(SKILL_ROOT.parent)):
        if "shared_notify.py" in files:
            NOTIFY_PY = Path(root) / "shared_notify.py"
            break

def send_desktop_notification(msg: str, title: str = "小红书剪贴板采集", status: str = "success", action_target: str = ""):
    if not notify_cfg.get("enable_desktop_toast", True):
        return False
    if NOTIFY_PY and NOTIFY_PY.exists():
        try:
            spec = importlib.util.spec_from_file_location("shared_notify", str(NOTIFY_PY))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.notify(
                msg,
                title=title,
                status=status,
                app_name="万能下载器",
                position="BottomRight",
                duration_ms=8000,
                icon_key="download",
                action_target=action_target,
                action_label="点击打开素材目录" if action_target else "点击查看"
            )
            return True
        except Exception as ex:
            if sys.stdout:
                print(f"[Notify Error]: {ex}")
    # Windows 原生 Toast 弹窗保底 (无需任何第三方包)
    try:
        clean_msg = msg.replace('"', ' ').replace("'", " ")[:120]
        clean_title = title.replace('"', ' ').replace("'", " ")[:40]
        ps_cmd = (
            f"[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null; "
            f"$t = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
            f"$t.GetElementsByTagName('text')[0].AppendChild($t.CreateTextNode('{clean_title}')) | Out-Null; "
            f"$t.GetElementsByTagName('text')[1].AppendChild($t.CreateTextNode('{clean_msg}')) | Out-Null; "
            f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('MaterialHub').Show([Windows.UI.Notifications.ToastNotification]::new($t))"
        )
        subprocess.run(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd], check=False, timeout=3)
        return True
    except Exception:
        pass
    return False

# 飞书同步通知配置 (用户指令：推送到飞书采集通知群，已采集啥啥啥，入库啥啥啥就行)
ENABLE_FEISHU_SYNC = feishu_cfg.get("enabled", True)
FEISHU_SYNC_TARGET = feishu_cfg.get("target_chat_name") or feishu_cfg.get("target_chat_id") or "素材采集通知群"
_feishu_script_cfg = feishu_cfg.get("feishu_notify_script")
FEISHU_NOTIFY_PY = Path(_feishu_script_cfg) if _feishu_script_cfg and Path(_feishu_script_cfg).exists() else None
if not FEISHU_NOTIFY_PY:
    _feishu_candidates = [
        SKILL_ROOT.parent / "shared-notification" / "scripts" / "feishu_notify.py",
        Path(r"D:\AICode\.agents\skills\shared-notification\scripts\feishu_notify.py"),
        Path(r"D:\AICode\AI\skills\技能包\技能\shared-notification\scripts\feishu_notify.py")
    ]
    for candidate in _feishu_candidates:
        if candidate.exists():
            FEISHU_NOTIFY_PY = candidate
            break

def get_material_library_stats(target_city: str):
    """统计当前素材库实时大盘数据 (毫秒级)"""
    try:
        city_count = 0
        total_precision = 0
        total_autumn = 0
        if PRECISION_DIR.exists():
            city_dir = PRECISION_DIR / target_city
            if city_dir.exists():
                city_count = len([d for d in city_dir.iterdir() if d.is_dir()])
            for sub in PRECISION_DIR.iterdir():
                if sub.is_dir():
                    total_precision += len([d for d in sub.iterdir() if d.is_dir()])
        if AUTUMN_DIR.exists():
            total_autumn = len([d for d in AUTUMN_DIR.iterdir() if d.is_dir()])
        return {
            "city_count": city_count,
            "total_precision": total_precision,
            "total_autumn": total_autumn
        }
    except Exception:
        return {"city_count": 0, "total_precision": 0, "total_autumn": 0}

def send_feishu_material_sync(metadata: dict, queue_rem_count: int = 0):
    """
    向飞书专属【素材采集通知群】同步详细入库卡片
    用户明确要求：纯文本，不要图，包含标题、链接、入库情况、分类情况及素材库大盘当前状态
    """
    if not ENABLE_FEISHU_SYNC or not FEISHU_NOTIFY_PY or not FEISHU_NOTIFY_PY.exists():
        return
    try:
        title = metadata.get("title", "精选图文作品")
        url = metadata.get("share_url", "")
        city = metadata.get("city", "精选")
        img_cnt = metadata.get("images_count", 0)
        target_dir = metadata.get("target_dir", "")
        is_unclassified = metadata.get("is_unclassified", False)
        platform = metadata.get("platform", "小红书")
        season = metadata.get("season", "四季通用")
        content_len = metadata.get("content_length", 0)
        
        # 统计素材库大盘
        stats = get_material_library_stats(city)
        city_cnt = stats["city_count"]
        tot_prec = stats["total_precision"]
        tot_aut = stats["total_autumn"]
        
        queue_str = "队列已清空 (0 篇排队)" if queue_rem_count == 0 else f"剩余 {queue_rem_count} 篇排队下载中"

        if is_unclassified:
            text = (
                f"📌 标题：《{title}》\n"
                f"🔗 链接：{url}\n\n"
                f"📂 入库情况：\n"
                f"· 平台来源：{platform}图文\n"
                f"· 资源规格：{img_cnt} 张高清原图 + 完整文案 ({content_len}字)\n"
                f"· 存储目录：{target_dir}\n\n"
                f"🏷️ 分类情况：\n"
                f"· 城市分类：⚠️ 未识别到江浙沪地名（已安全暂存至 C盘下载目录）\n"
                f"· 待办提示：请人工移入对应城市素材库\n\n"
                f"📊 素材库当前状态：\n"
                f"· 精准流量库总计：{tot_prec} 套\n"
                f"· 秋季智能库总计：{tot_aut} 套\n"
                f"· 队列状态：{queue_str}"
            )
            title_header = f"⚠️ 待分类暂存：{title[:24]}"
        else:
            text = (
                f"📌 标题：《{title}》\n"
                f"🔗 链接：{url}\n\n"
                f"📂 入库情况：\n"
                f"· 平台来源：{platform}图文\n"
                f"· 资源规格：{img_cnt} 张高清原图 + 完整文案 ({content_len}字)\n"
                f"· 存储目录：{target_dir}\n\n"
                f"🏷️ 分类情况：\n"
                f"· 城市分类：【{city}】（命中地名规则精准归库）\n"
                f"· 季节归档：【{season}】（NTFS 零占盘硬链接已就绪）\n\n"
                f"📊 素材库当前状态：\n"
                f"· 【{city}】类目现存：{city_cnt} 套素材\n"
                f"· 精准流量库总计：{tot_prec} 套素材\n"
                f"· 秋季智能库总计：{tot_aut} 套素材\n"
                f"· 队列状态：{queue_str}"
            )
            title_header = f"已采集：{title[:26]}"

        # 用户严格指定：不要图，纯文本通知
        cmd = [
            sys.executable, str(FEISHU_NOTIFY_PY),
            "--target", FEISHU_SYNC_TARGET,
            "--title", title_header,
            "--text", text
        ]
        log_daemon(f"📢 向飞书推送采集详细通知: 《{title[:20]}》 -> {FEISHU_SYNC_TARGET}")
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as ex:
        log_daemon(f"❌ 飞书通知推送异常: {ex}")
        if sys.stdout:
            print(f"[Feishu Notify Error]: {ex}")

def send_feishu_error_sync(title_hint: str, url: str, reason: str):
    """向飞书素材采集通知群同步错误复制或异常提示"""
    if not ENABLE_FEISHU_SYNC or not FEISHU_NOTIFY_PY.exists():
        return
    try:
        text = (
            f"❌ 错误复制 / 采集异常提示：\n"
            f"内容：《{title_hint[:35]}》\n"
            f"原因：{reason}\n"
            f"🔗 链接：{url}"
        )
        cmd = [
            sys.executable, str(FEISHU_NOTIFY_PY),
            "--target", FEISHU_SYNC_TARGET,
            "--title", f"❌ 采集异常：{title_hint[:20]}",
            "--text", text
        ]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as ex:
        if sys.stdout:
            print(f"[Feishu Notify Error]: {ex}")

# 城市词库映射表 (优先从 config.json 获取，若无则使用标准江浙沪地名词库)
CITY_RULES = rules_cfg.get("city_rules") or {
    "金华义乌": ["义乌", "金华", "东阳", "横店", "武义", "永康", "浦江", "磐安", "兰溪"],
    "宁波": ["宁波", "余姚", "宁海", "象山", "慈溪", "奉化", "镇海", "东钱湖", "四明山"],
    "台州": ["台州", "温岭", "石塘", "仙居", "神仙居", "天台", "临海", "紫阳古街"],
    "舟山": ["舟山", "普陀山", "朱家尖", "东极岛", "嵊泗", "岱山", "衢山岛"],
    "安吉": ["安吉", "中南百草原", "云上草原", "大竹海", "藏龙百瀑", "浙北大峡谷"],
    "莫干山": ["莫干山", "德清", "下渚湖", "碧坞"],
    "千岛湖": ["千岛湖", "淳安"],
    "桐庐": ["桐庐", "大奇山", "瑶琳仙境", "严子陵", "omg心跳乐园"],
    "临安": ["临安", "青山湖", "风之谷", "大明山", "天目山", "太湖源"],
    "杭州": ["杭州", "西湖", "九溪", "良渚", "西溪", "湘湖", "富阳", "建德", "萧山", "余杭"],
    "绍兴": ["绍兴", "柯桥", "诸暨", "上虞", "新昌", "安昌古镇", "鲁迅故里"],
    "南京": ["南京", "栖霞山", "牛首山", "汤山", "高淳", "江宁", "玄武湖", "紫金山"],
    "宜兴溧阳": ["宜兴", "溧阳", "南山竹海", "天目湖", "善卷洞"],
    "苏州": ["苏州", "西山岛", "东山", "太湖", "昆山", "常熟", "同里", "周庄", "阳澄湖"],
    "上海": ["上海", "崇明", "青浦", "奉贤", "金山", "淀山湖", "滴水湖"],
    "特色拓展地": ["婺源", "篁岭", "婺女洲", "黄山", "宏村", "西递", "丽水", "松阳", "缙云", "景德镇", "三清山", "望仙谷", "葛仙村", "衢州", "江山", "温州", "雁荡山", "楠溪江", "嘉兴", "乌镇", "西塘", "武夷山"]
}

def detect_city(title: str, content: str) -> str:
    # 1. 优先从标题中匹配（最精准，避免被文案末尾蹭流量的 #杭州周边 #上海团建 等标签带偏）
    t_lower = title.lower()
    for city, keywords in CITY_RULES.items():
        for kw in keywords:
            if kw.lower() in t_lower:
                return city

    # 2. 剥除 #话题 干扰后匹配正文主体
    clean_body = re.sub(r'#[^#\s]+', '', content).lower()
    for city, keywords in CITY_RULES.items():
        for kw in keywords:
            if kw.lower() in clean_body:
                return city

    # 3. 兜底全文本匹配
    full_text = (title + " " + content).lower()
    for city, keywords in CITY_RULES.items():
        for kw in keywords:
            if kw.lower() in full_text:
                return city

    return "地点待确认"

def is_autumn_content(title: str, content: str) -> bool:
    text = (title + " " + content).lower()
    autumn_keywords = ["秋", "桂花", "红叶", "枫叶", "采摘", "围炉", "柿子", "银杏", "徒步", "露营", "国庆", "中秋", "9月", "10月", "11月", "土灶", "户外"]
    return any(k in text for k in autumn_keywords)

def extract_title_hint(raw_text: str) -> str:
    """从分享口令文本中提取有意义的笔记标题提示（兼容小红书与抖音图文）"""
    clean = re.sub(r'https?://\S+', '', raw_text)
    clean = re.sub(r'[，。！？\s\r\n]+', ' ', clean).strip()
    clean = re.sub(r'(带走口令|先复制这段文字|再进|发现精彩|来【小红书】|查看完整笔记|复制这段|小红书).*', '', clean).strip()
    clean = re.sub(r'^[\d.]+ 复制打开抖音[，,]?\s*看看【[^】]+】\s*', '', clean).strip()
    clean = re.sub(r'【[^】]+的图文作品】', '', clean).strip()
    return clean[:35] if clean else "精选图文作品"

def extract_creator_name(url: str, raw_text: str, title_hint: str) -> tuple[str, str]:
    """提取博主名字与平台"""
    platform = "小红书" if ("xhs" in url.lower() or "xiaohongshu" in url.lower() or "小红书" in raw_text) else "抖音"
    m_at = re.search(r'@([^\s，。！？\n\r]+)', raw_text)
    if m_at:
        return m_at.group(0), platform
    m_bracket = re.search(r'【([^】]+?)(?:的图文作品|的作品)?】', raw_text)
    if m_bracket:
        return f"@{m_bracket.group(1)}", platform
    return f"@{title_hint[:15]}", platform

def register_benchmark_account(target_url: str, raw_text: str, title_hint: str) -> tuple[bool, str]:
    """将复制的主页口令全自动双向建档至：
    1. 原团建项目《对标账号完整清单.md》（带 Axxx 编号大表 + 四维业务分类）
    2. 第二大脑《对标账号与样板观察清单.md》（带详细档案与拆解要点）
    """
    creator_name, platform = extract_creator_name(target_url, raw_text, title_hint)
    is_new = False
    now_str = time.strftime("%Y-%m-%d %H:%M")
    now_date = time.strftime("%Y-%m-%d")

    # 1. 录入原团建项目对标大表
    if PROJECT_BENCHMARK_FILE.exists():
        try:
            content_proj = PROJECT_BENCHMARK_FILE.read_text(encoding="utf-8")
            if target_url not in content_proj and (not creator_name or creator_name not in content_proj):
                # 寻找最大的 Axxx 编号
                all_ids = [int(m) for m in re.findall(r'\| A(\d{3}) \|', content_proj)]
                next_id = f"A{(max(all_ids) + 1):03d}" if all_ids else "A030"
                
                # 构建表格新行
                new_row = f"| {next_id} | {now_date} | {platform} | {creator_name} | {target_url} | 剪贴板自动识别对标主页 | 待拆解 | 剪贴板复制主页自动建档 | 是 |\n"
                
                # 寻找表格末尾（分割线或分类索引标记）
                if "\n---\n" in content_proj:
                    parts = content_proj.split("\n---\n", 1)
                    content_proj = parts[0].rstrip() + "\n" + new_row + "\n---\n" + parts[1]
                else:
                    content_proj += "\n" + new_row

                # 追加变更记录
                log_marker = "|---|---|---|"
                if log_marker in content_proj:
                    p1, p2 = content_proj.split(log_marker, 1)
                    log_row = f"\n| {now_str} | 反重力 | 剪贴板自动建档 {platform} 对标账号 {creator_name}（{next_id}） |"
                    content_proj = p1 + log_marker + log_row + p2
                
                PROJECT_BENCHMARK_FILE.write_text(content_proj, encoding="utf-8")
                is_new = True
                if sys.stdout:
                    print(f"[Benchmark] Recorded {creator_name} ({next_id}) into Project benchmark file.")
        except Exception as ex:
            if sys.stdout:
                print(f"[Project Benchmark Error]: {ex}")

    # 2. 录入第二大脑对标档案
    if SECOND_BRAIN_BENCHMARK_FILE.exists():
        try:
            content_sb = SECOND_BRAIN_BENCHMARK_FILE.read_text(encoding="utf-8")
            if target_url not in content_sb and (not creator_name or creator_name not in content_sb):
                new_entry = f"""
### 账号：{creator_name}（{platform}垂直对标）

| 属性 | 详情数据 / 说明 |
| :--- | :--- |
| **平台** | {platform} |
| **主页链接** | `{target_url}` |
| **录入来源** | 剪贴板自动识别对标主页口令 |
| **录入时间** | {now_str} |
| **原始口令** | `{raw_text[:80]}` |
| **业务定位** | 江浙沪团建/周边游对标参考 |
"""
                marker = "## 🔬 制作参考与拆解要点"
                if marker in content_sb:
                    parts = content_sb.split(marker, 1)
                    content_sb = parts[0].rstrip() + "\n" + new_entry + "\n---\n\n" + marker + parts[1]
                else:
                    content_sb += "\n" + new_entry
                
                log_marker = "|---|---|---|"
                if log_marker in content_sb:
                    p1, p2 = content_sb.split(log_marker, 1)
                    log_row = f"\n| {now_str} | 反重力 | 剪贴板自动识别并归档 {platform} 对标账号 {creator_name} |"
                    content_sb = p1 + log_marker + log_row + p2
                
                SECOND_BRAIN_BENCHMARK_FILE.write_text(content_sb, encoding="utf-8")
                is_new = True
                if sys.stdout:
                    print(f"[Benchmark] Recorded {creator_name} into Second Brain benchmark file.")
        except Exception as ex:
            if sys.stdout:
                print(f"[SecondBrain Benchmark Error]: {ex}")

    return is_new, creator_name

def is_profile_or_homepage(url: str, raw_text: str = "") -> bool:
    """快速识别口令或链接是否为博主主页，避免将主页当作单篇笔记下载"""
    u_lower = url.lower()
    t_lower = raw_text.lower()
    if "user/profile" in u_lower or "user/profile" in t_lower:
        return True
    if "/user/" in u_lower:
        return True
    if "ta的主页" in t_lower or "查看ta的主页" in t_lower or "的主页" in t_lower:
        return True
    return False

def check_url_type(target_url: str) -> tuple[bool, str]:
    """检查链接是否为单篇笔记。如果确定是主页返回 (False, 'UNSUPPORTED_PROFILE: 博主个人主页')"""
    u_lower = target_url.lower()
    if "user/profile" in u_lower or "/user/" in u_lower:
        return False, "UNSUPPORTED_PROFILE: 博主个人主页"
    if "xhslink" in u_lower:
        try:
            import urllib.request
            req = urllib.request.Request(target_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                final_url = resp.geturl().lower()
                if "user/profile" in final_url or "/user/" in final_url:
                    return False, "UNSUPPORTED_PROFILE: 短链重定向至博主个人主页"
        except Exception:
            pass
    return True, "OK"

# 历史防重库
def load_history() -> set:
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("urls", []))
        except:
            return set()
    return set()

def save_history(urls: set):
    try:
        tmp_file = HISTORY_FILE.with_suffix(".tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump({"urls": list(urls), "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")}, f, ensure_ascii=False, indent=2)
        tmp_file.replace(HISTORY_FILE)
    except Exception as e:
        if sys.stdout:
            print(f"[History Save Error]: {e}")

# 待下载队列管理器 (Thread-safe Pending Queue)
class QueueManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.queue = []         # 待下载项列表
        self.failed = []        # 彻底失败项列表
        self.cooldown_until = 0.0
        self.cooldown_reason = ""
        self.load()

    def load(self):
        with self.lock:
            if QUEUE_FILE.exists():
                try:
                    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.queue = data.get("queue", [])
                        self.failed = data.get("failed", [])
                        self.cooldown_until = data.get("cooldown_until", 0.0)
                        self.cooldown_reason = data.get("cooldown_reason", "")
                except Exception as e:
                    if sys.stdout:
                        print(f"[Queue Load Error]: {e}")
                    self.queue = []
                    self.failed = []

    def save(self):
        try:
            tmp_file = QUEUE_FILE.with_suffix(".tmp")
            data = {
                "queue": self.queue,
                "failed": self.failed,
                "cooldown_until": self.cooldown_until,
                "cooldown_reason": self.cooldown_reason,
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            tmp_file.replace(QUEUE_FILE)
        except Exception as e:
            if sys.stdout:
                print(f"[Queue Save Error]: {e}")

    def add(self, url: str, raw_text: str, title_hint: str) -> tuple[bool, int, dict]:
        with self.lock:
            # 查重：已经在队列中则不重复入队
            for idx, item in enumerate(self.queue):
                if item.get("url") == url:
                    return False, idx + 1, item
            
            new_item = {
                "id": f"xhs_{int(time.time()*1000)}_{random.randint(100, 999)}",
                "url": url,
                "title_hint": title_hint,
                "raw_text": raw_text[:200],
                "added_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "pending",
                "retry_count": 0,
                "last_error": None
            }
            self.queue.append(new_item)
            pos = len(self.queue)
            self.save()
            return True, pos, new_item

    def peek(self) -> dict | None:
        with self.lock:
            if self.queue:
                return dict(self.queue[0])
            return None

    def pop_success(self, item_id: str):
        with self.lock:
            self.queue = [x for x in self.queue if x.get("id") != item_id]
            self.save()

    def pop_discard(self, item_id: str, reason: str):
        with self.lock:
            target = None
            for item in self.queue:
                if item.get("id") == item_id:
                    target = item
                    break
            if target:
                target["status"] = "discarded"
                target["last_error"] = str(reason)[:200]
                self.queue.remove(target)
                self.failed.append(target)
            self.save()

    def mark_retry(self, item_id: str, error_msg: str, cooldown_seconds: float):
        with self.lock:
            target = None
            for item in self.queue:
                if item.get("id") == item_id:
                    target = item
                    break
            if target:
                target["retry_count"] = target.get("retry_count", 0) + 1
                target["last_error"] = str(error_msg)[:200]
                target["last_attempt"] = time.strftime("%Y-%m-%d %H:%M:%S")
                
                if target["retry_count"] >= MAX_RETRIES:
                    target["status"] = "failed"
                    self.queue.remove(target)
                    self.failed.append(target)
                else:
                    target["status"] = "cooling_down"
            
            self.cooldown_until = time.time() + cooldown_seconds
            self.cooldown_reason = f"风控退避保护: {error_msg[:40]}"
            self.save()

    def set_cooldown(self, seconds: float, reason: str = "拟人间隔"):
        with self.lock:
            self.cooldown_until = time.time() + seconds
            self.cooldown_reason = reason
            self.save()

    def get_remaining_count(self) -> int:
        with self.lock:
            return len(self.queue)

    def is_cooling_down(self) -> tuple[bool, float, str]:
        with self.lock:
            now = time.time()
            if now < self.cooldown_until:
                return True, self.cooldown_until - now, self.cooldown_reason
            return False, 0.0, ""

# 剪贴板读取器 (pywin32 优先 + 64位 ctypes 兜底)
def get_clipboard_text() -> str:
    try:
        import win32clipboard
        import win32con
        win32clipboard.OpenClipboard()
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                return data or ""
            return ""
        finally:
            win32clipboard.CloseClipboard()
    except Exception:
        pass

    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        user32.OpenClipboard.argtypes = [wintypes.HWND]
        user32.OpenClipboard.restype = wintypes.BOOL
        user32.CloseClipboard.argtypes = []
        user32.CloseClipboard.restype = wintypes.BOOL
        user32.GetClipboardData.argtypes = [wintypes.UINT]
        user32.GetClipboardData.restype = wintypes.HANDLE
        kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalLock.restype = wintypes.LPVOID
        kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalUnlock.restype = wintypes.BOOL

        if not user32.OpenClipboard(None):
            return ""
        try:
            CF_UNICODETEXT = 13
            h_clip = user32.GetClipboardData(CF_UNICODETEXT)
            if not h_clip:
                return ""
            ptr = kernel32.GlobalLock(h_clip)
            if not ptr:
                return ""
            text = ctypes.wstring_at(ptr)
            kernel32.GlobalUnlock(h_clip)
            return text or ""
        finally:
            user32.CloseClipboard()
    except Exception:
        return ""

MEDIA_LINK_REGEX = re.compile(
    r'https?://(?:xhslink\.com|xhslink\.cn|www\.xiaohongshu\.com|v\.douyin\.com|www\.douyin\.com|iesdouyin\.com)/[A-Za-z0-9_/.\-]+(?:\?[^\s\u4e00-\u9fa5]+)?'
)

# 核心下载执行函数
def execute_download_and_file(target_url: str) -> tuple[bool, str, dict]:
    """
    执行万能下载器无感解包，并完成城市分流、四季硬链接、元数据打标。
    返回: (成功标志, 错误原因或最终文件夹名, 元数据字典)
    """
    is_note, type_msg = check_url_type(target_url)
    if not is_note:
        return False, type_msg, {}

    if TEMP_DOWNLOAD_DIR.exists():
        shutil.rmtree(TEMP_DOWNLOAD_DIR, ignore_errors=True)
    TEMP_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    saved_argv = sys.argv[:]
    try:
        sys.argv = ["xhs-dl", target_url, "-o", str(TEMP_DOWNLOAD_DIR), "--mode", "fast"]
        xhs_dl_main()
    except SystemExit:
        pass
    except Exception as e:
        return False, f"下载引擎异常: {e}", {}
    finally:
        sys.argv = saved_argv

    downloaded_dirs = [d for d in TEMP_DOWNLOAD_DIR.iterdir() if d.is_dir()]
    if not downloaded_dirs:
        return False, "未能成功解析或图片资源受限(0目录产出)", {}

    work_dir = downloaded_dirs[0]
    folder_name = work_dir.name

    # 读取文案
    txt_file = work_dir / "文案.txt"
    content_text = ""
    title_text = folder_name
    if txt_file.exists():
        try:
            content_text = txt_file.read_text(encoding="utf-8", errors="ignore")
            m_title = re.search(r"标题[：:]\s*(.+)", content_text)
            if m_title:
                title_text = m_title.group(1).strip()
        except:
            pass

    # 校验是否真正下载到了图片 (防风控空壳)
    images = [f for f in work_dir.iterdir() if f.suffix.lower() in [".jpg", ".png", ".jpeg", ".webp"]]
    img_count = len(images)
    if img_count == 0:
        return False, "解析未包含有效图片资源(可能触发页面验证)", {}

    # 智能地名识别与城市分流
    target_city = detect_city(title_text, content_text)
    is_unclassified = (target_city == "地点待确认")

    if is_unclassified:
        # 用户明确要求：无法判断分类时，下载到 C 盘下载文件夹 (C:\Users\z\Downloads)
        city_dest_dir = C_DOWNLOADS_DIR
        target_city = "未分类(暂存C盘下载)"
        final_target_dir = city_dest_dir / folder_name
    else:
        city_dest_dir = PRECISION_DIR / target_city
        final_target_dir = city_dest_dir / folder_name

    city_dest_dir.mkdir(parents=True, exist_ok=True)
    if final_target_dir.exists():
        shutil.rmtree(final_target_dir, ignore_errors=True)

    shutil.move(str(work_dir), str(final_target_dir))

    # 从标准文件夹名解析作者与赞评互动元数据: 评X-赞Y-标题-作者
    author = ""
    comments_cnt = 0
    likes_cnt = 0
    m_stat = re.match(r"^评(\d+)-赞(\d+)-(.*?)(?:-([^-]+))?$", folder_name)
    if m_stat:
        try:
            comments_cnt = int(m_stat.group(1))
            likes_cnt = int(m_stat.group(2))
            if m_stat.group(4):
                author = m_stat.group(4).strip()
        except:
            pass

    # 季节判断与硬链接目录预备
    is_autumn = is_autumn_content(title_text, content_text)
    season_name = "秋季（9—11月·智能分类）" if is_autumn else "四季通用（全年·无季节限制）"
    season_work_dir = None
    if not is_unclassified:
        season_target_base = AUTUMN_DIR if is_autumn else ALL_SEASON_DIR
        season_target_base.mkdir(parents=True, exist_ok=True)
        season_work_dir = season_target_base / folder_name

    # 元数据打标 (metadata.json) - 100% 完备规范元数据
    platform = "抖音" if ("douyin" in target_url.lower()) else "小红书"
    metadata = {
        "title": title_text,
        "author": author,
        "likes_count": likes_cnt,
        "comments_count": comments_cnt,
        "city": target_city,
        "season": season_name,
        "is_unclassified": is_unclassified,
        "source": "剪贴板监听",
        "engine": "万能下载器 v2.8.2",
        "platform": platform,
        "tags": ["剪切板下载", "万能下载器下载", f"{platform}图文", target_city, "秋季素材" if is_autumn else "四季通用"],
        "downloaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "share_url": target_url,
        "images_count": img_count,
        "images_list": [f.name for f in images],
        "content_length": len(content_text),
        "content_preview": content_text[:120].strip() if content_text else "",
        "folder_name": folder_name,
        "target_dir": str(final_target_dir),
        "season_hardlink_dir": str(season_work_dir) if season_work_dir else "",
        "version": "3.5.0",
        "status": "success",
        "captured_by": "universal-clipboard-collector"
    }
    try:
        (final_target_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        log_daemon(f"📝 元数据打标完成: {final_target_dir / 'metadata.json'} (包含 {len(metadata)} 项核心属性)")
    except Exception as e:
        log_daemon(f"❌ 元数据打标异常: {e}")
        if sys.stdout:
            print(f"[Metadata Error]: {e}")

    # 四季分类与 NTFS 原生硬链接分发 (已识别地名才分发，未分类保留在C盘供人工整理)
    if not is_unclassified and season_work_dir:
        try:
            season_work_dir.mkdir(parents=True, exist_ok=True)
            for src_file in final_target_dir.iterdir():
                if src_file.is_file():
                    dest_file = season_work_dir / src_file.name
                    if not dest_file.exists():
                        try:
                            os.link(src_file, dest_file)
                        except:
                            pass
            log_daemon(f"🔗 四季硬链接建立成功: {season_work_dir}")
        except Exception as ex_link:
            log_daemon(f"❌ 建立硬链接异常: {ex_link}")
            if sys.stdout:
                print(f"[Hardlink Error]: {ex_link}")

    return True, folder_name, metadata


# 消费工作线程 (Queue Worker Thread)
def queue_worker_loop(queue_mgr: QueueManager, history_set: set):
    """
    负责从待下载队列中按顺序消费链接。
    严格受风控冷却与拟人间隔控制，下载成功即入库并通知，失败则退避并保留队列。
    """
    while True:
        try:
            # 1. 检查是否处于风控或拟人冷却状态
            is_cooling, remain_sec, reason = queue_mgr.is_cooling_down()
            if is_cooling:
                time.sleep(min(remain_sec, 2.0))
                continue

            # 2. 查看是否有待下载任务
            item = queue_mgr.peek()
            if not item:
                time.sleep(1.0)
                continue

            item_id = item["id"]
            url = item["url"]
            title_hint = item.get("title_hint", "小红书笔记")
            retry_count = item.get("retry_count", 0)

            if sys.stdout:
                print(f"\n[Worker] Start downloading: {url} (Retry: {retry_count})")

            # 3. 执行下载
            success, result_msg, metadata = execute_download_and_file(url)

            if success:
                # 记录到历史去重账本
                history_set.add(url)
                save_history(history_set)
                
                # 从待下载队列中移除
                queue_mgr.pop_success(item_id)
                rem_count = queue_mgr.get_remaining_count()

                # 设置正常平缓拟人冷却
                cooldown_sec = random.uniform(*NORMAL_COOLDOWN_RANGE)
                queue_mgr.set_cooldown(cooldown_sec, "平缓拟人间隔")

                # 发送桌面原生通知
                final_title = metadata.get("title", title_hint)
                short_title = final_title[:24] + ("..." if len(final_title) > 24 else "")
                city = metadata.get("city", "精选")
                img_cnt = metadata.get("images_count", 0)
                target_folder = metadata.get("target_dir", "")
                is_unclassified = metadata.get("is_unclassified", False)
                
                platform = metadata.get("platform", "精选")
                queue_tip = f" (剩余 {rem_count} 篇排队中)" if rem_count > 0 else ""
                
                if is_unclassified:
                    notify_text = f"⚠️ 未能识别地名（已暂存至C盘下载）：《{short_title}》\n📍 点击可直接打开 Downloads 文件夹{queue_tip}"
                    send_desktop_notification(notify_text, title="素材待手动分类", status="warning", action_target=target_folder)
                else:
                    notify_text = f"✅ 已自动采集入库（{platform}图文）：《{short_title}》\n📍 已归入【{city}】库（含 {img_cnt} 张原画大图+文案）{queue_tip}"
                    send_desktop_notification(notify_text, title=f"{platform}剪贴板采集", status="success", action_target=target_folder)

                # 同步向飞书发送耗材入库卡片 (详细内容，不要图)
                send_feishu_material_sync(metadata, rem_count)
                
                if sys.stdout:
                    print(f"[Worker Success]: {final_title} filed to {city}")

            elif "UNSUPPORTED_PROFILE" in result_msg or "提取小红书作品链接失败" in result_msg:
                # 链接类型不符 (如博主主页等)，直接移出队列，不触发风控退避！
                queue_mgr.pop_discard(item_id, result_msg)
                rem_count = queue_mgr.get_remaining_count()
                short_hint = title_hint[:22] + ("..." if len(title_hint) > 22 else "")
                warn_notify = (
                    f"⚠️ 链接类型不符或非单篇图文笔记：《{short_hint}》\n"
                    f"💡 提示：万能下载器专精单篇图文笔记采集，非图文已跳过"
                )
                send_desktop_notification(warn_notify, title="跳过非单篇笔记", status="warning")
                send_feishu_error_sync(title_hint, url, f"链接类型不符或非单篇图文作品 ({result_msg[:40]})")
                if sys.stdout:
                    print(f"[Worker Discard]: Discarded non-note item {url} ({result_msg})")
                time.sleep(1.0)
                continue

            else:
                # 失败处理：进入阶梯式风控退避冷却，绝不丢失队列中的笔记
                curr_retries = retry_count + 1
                backoff_sec = DEEP_COOLDOWN_BASE * curr_retries
                queue_mgr.mark_retry(item_id, result_msg, backoff_sec)
                rem_count = queue_mgr.get_remaining_count()

                if curr_retries >= MAX_RETRIES:
                    short_hint = title_hint[:20] + ("..." if len(title_hint) > 20 else "")
                    err_notify = f"❌ 连续多次下载异常，已移入异常待查：《{short_hint}》\n⚠️ 原因: {result_msg[:40]}"
                    send_desktop_notification(err_notify, title="采集异常挂起", status="error")
                    send_feishu_error_sync(title_hint, url, f"连续多次重试失败（错误复制或网络限制）: {result_msg[:40]}")
                else:
                    short_hint = title_hint[:20] + ("..." if len(title_hint) > 20 else "")
                    cd_notify = (
                        f"⚠️ 小红书触发临时风控/下载异常，已启动冷却保护\n"
                        f"⏳ 剩余 {rem_count} 篇已安全保存在【待下载队列】，将在 {int(backoff_sec)} 秒后自动续接重试"
                    )
                    send_desktop_notification(cd_notify, title="风控冷却保护中", status="warning")

                if sys.stdout:
                    print(f"[Worker Warning]: {result_msg}, enter deep cooldown {backoff_sec}s")

        except Exception as ex:
            if sys.stdout:
                print(f"[Worker Loop Exception]: {ex}")
            time.sleep(2.0)


# 主剪贴板监听程序 (Producer Thread)
def main():
    # Win32 全局互斥锁，确保同一时刻仅有唯一后台守护进程
    mutex_name = "Global\\XHS_Clipboard_Collector_Daemon_Mutex"
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    h_mutex = kernel32.CreateMutexW(None, False, mutex_name)
    last_err = kernel32.GetLastError()
    ERROR_ALREADY_EXISTS = 183
    if last_err == ERROR_ALREADY_EXISTS:
        log_daemon("⚠️ 检测到已有守护实例运行中，本进程原子退出。")
        if sys.stdout:
            print("⚠️ 守护程序已在后台运行中，无需重复拉起。")
        sys.exit(0)

    log_daemon("🚀 万能素材剪贴板采集守护神进程正式就绪并启动。")
    if sys.stdout:
        print("=" * 65)
        print("  🚀 万能素材剪贴板智能采集守护神已就绪 (万能下载器内核 V3.4)")
        print("  · 多平台图文：深度支持小红书与抖音全平台高清无水印原画+文案")
        print("  · 待下载队列：支持连续多次复制链接，全自动暂存排队")
        print("  · 智能风控冷却：拟人化 15~28s 间隔 + 异常阶梯式 60s/120s 自动退避")
        print("  · 智能分流建档：博主主页双向建档入对标库、单篇笔记自动分流地名+秋季硬链接")
        print("  · 飞书即时同频：素材采集通知群同步卡片、未分类暂存与错误报警")
        print("=" * 65)

    history_set = load_history()
    queue_mgr = QueueManager()

    # 启动后台消费线程
    worker_t = threading.Thread(target=queue_worker_loop, args=(queue_mgr, history_set), daemon=True)
    worker_t.start()

    last_clipboard = ""

    while True:
        try:
            current_text = get_clipboard_text()
            if current_text and current_text != last_clipboard:
                last_clipboard = current_text
                
                # 检查是否包含小红书或抖音图文链接
                m = MEDIA_LINK_REGEX.search(current_text)
                if m:
                    target_url = m.group(0).strip()
                    title_hint = extract_title_hint(current_text)
                    
                    if target_url in history_set:
                        if sys.stdout:
                            print(f"[Skip] URL already captured previously: {target_url}")
                    elif is_profile_or_homepage(target_url, current_text):
                        if sys.stdout:
                            print(f"[Benchmark] Detected profile page: {target_url}")
                        is_new, creator = register_benchmark_account(target_url, current_text, title_hint)
                        if is_new:
                            notify_msg = (
                                f"🎯 已自动双向建档至【团建对标库】：《{creator}》\n"
                                f"📊 已同步记入项目《对标账号完整清单》与第二大脑观察库\n"
                                f"💡 点击卡片可直接查看原项目对标大表"
                            )
                            send_desktop_notification(
                                notify_msg,
                                title="对标账号自动建档",
                                status="success",
                                action_target=str(PROJECT_BENCHMARK_FILE)
                            )
                        else:
                            notify_msg = (
                                f"ℹ️ 该博主主页已在【团建对标库】中：《{creator}》\n"
                                f"💡 无需重复登记，对标清单已为最新"
                            )
                            send_desktop_notification(
                                notify_msg,
                                title="对标库已有记录",
                                status="info",
                                action_target=str(PROJECT_BENCHMARK_FILE)
                            )
                    else:
                        # 加入待下载队列
                        added, pos, item = queue_mgr.add(target_url, current_text, title_hint)
                        if added:
                            if sys.stdout:
                                print(f"[Enqueued] Added to queue: {target_url} (Pos: {pos})")
                            
                            # 如果当前工作线程正忙或处于冷却中，且当前排在第 2 篇及以后，弹窗提示用户已安全入队
                            is_cooling, rem_sec, _ = queue_mgr.is_cooling_down()
                            if pos > 1 or is_cooling:
                                short_hint = title_hint[:24] + ("..." if len(title_hint) > 24 else "")
                                cool_tip = f" (风控冷却剩余 {int(rem_sec)}s)" if is_cooling and rem_sec > 1 else ""
                                notify_msg = (
                                    f"📥 已加入待下载队列：《{short_hint}》\n"
                                    f"⏳ 当前排队: 第 {pos} 篇 (风控保护中{cool_tip}，稍后自动下载入库)"
                                )
                                send_desktop_notification(notify_msg, title="待下载队列暂存", status="info")
                        else:
                            if sys.stdout:
                                print(f"[Skip] Already waiting in pending queue: {target_url}")

        except Exception as e:
            if sys.stdout:
                print(f"[Clipboard Monitor Error]: {e}")
            time.sleep(1.0)
        
        time.sleep(0.5)  # 500ms 极低负载轮询，0.0% CPU 占用


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log_daemon(f"FATAL CRASH: {traceback.format_exc()}")
        raise
