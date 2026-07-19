"""xhs-dl Windows 本地桌面应用。"""

import os
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import requests

from xhs_dl import __version__
from xhs_dl.core.downloader import DELAY_MODES, extract_urls_from_text
from xhs_dl.core.v2_downloader import EngineNotReady, XhsV2Downloader
from xhs_dl.storage import history_path, load_settings, save_settings


RELEASE_API = "https://api.github.com/repos/zwmopen/xhs-dl/releases/latest"
MODE_LABELS = {
    "自动判断（推荐）": "auto",
    "快速（3–8 秒）": "fast",
    "标准（8–15 秒）": "normal",
    "稳妥（35–55 秒）": "cautious",
    "慢速（55–85 秒）": "slow",
    "极慢（110–160 秒）": "very-slow",
}
THEME_PALETTES = {
    "neo": {
        "bg": "#E8EDF2", "surface": "#F7F9FA", "input": "#EEF3F6",
        "status": "#E9EFF3", "line": "#D1DBE3", "text": "#182633",
        "muted": "#6C7F8F", "primary": "#203442", "primary_hover": "#142631",
        "secondary": "#DCE5EB", "secondary_hover": "#CDD9E1",
        "accent": "#527A93", "accent_hover": "#3F687F",
    },
    "glass": {
        "bg": "#DFEAF2", "surface": "#EDF4F8", "input": "#F5FAFD",
        "status": "#DCEAF4", "line": "#C4D7E4", "text": "#102B45",
        "muted": "#617A91", "primary": "#2F6F9F", "primary_hover": "#245C86",
        "secondary": "#D6E7F8", "secondary_hover": "#C5DAEB",
        "accent": "#4B86AC", "accent_hover": "#397395",
    },
}


def automatic_mode(count):
    if count <= 1:
        return "cautious"
    if count <= 20:
        return "cautious"
    if count <= 50:
        return "slow"
    return "very-slow"


def mode_description(mode, count=0):
    if count <= 1:
        return "单条直接采集"
    descriptions = {
        "fast": "快速 3–8 秒",
        "normal": "标准 8–15 秒",
        "cautious": "稳妥 35–55 秒",
        "slow": "慢速 55–85 秒",
        "very-slow": "极慢 110–160 秒",
    }
    return descriptions[mode]


def version_tuple(value):
    return tuple(int(part) for part in value.lstrip("v").split(".") if part.isdigit())


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self.title("下载设置")
        self.geometry("680x560")
        self.minsize(600, 500)
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()
        p = master.palette
        self.configure(fg_color=p["bg"])

        settings = master.settings
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(
            self, text="下载设置", font=("Microsoft YaHei UI", 25, "bold"),
            text_color=p["text"],
        ).grid(row=0, column=0, sticky="w", padx=34, pady=(30, 5))
        ctk.CTkLabel(
            self, text="设置会保存在本机，下次打开自动沿用。",
            font=("Microsoft YaHei UI", 12), text_color=p["muted"],
        ).grid(row=1, column=0, sticky="w", padx=34, pady=(0, 24))

        content = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=p["secondary"],
            scrollbar_button_hover_color=p["secondary_hover"],
        )
        content.grid(row=2, column=0, sticky="nsew", padx=(26, 18), pady=(0, 88))
        content.grid_columnconfigure(0, weight=1)

        folder_frame = ctk.CTkFrame(content, fg_color="transparent")
        folder_frame.grid(row=0, column=0, sticky="ew", padx=8)
        folder_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(folder_frame, text="保存位置", font=("Microsoft YaHei UI", 13, "bold"), text_color=p["text"]).grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.folder_entry = ctk.CTkEntry(folder_frame, height=46, corner_radius=12, border_width=1, border_color=p["line"], fg_color=p["input"], text_color=p["text"])
        self.folder_entry.grid(row=1, column=0, sticky="ew")
        self.folder_entry.insert(0, settings["output_dir"])
        ctk.CTkButton(folder_frame, text="选择文件夹", height=42, corner_radius=12, fg_color=p["secondary"], hover_color=p["secondary_hover"], text_color=p["text"], command=self.choose_folder).grid(row=2, column=0, sticky="ew", pady=(10, 0))

        options = ctk.CTkFrame(content, fg_color="transparent")
        options.grid(row=1, column=0, sticky="ew", padx=8, pady=(22, 8))
        options.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(options, text="下载速度", font=("Microsoft YaHei UI", 13, "bold"), text_color=p["text"]).grid(row=0, column=0, sticky="w", pady=(0, 8))
        current_label = next((label for label, mode in MODE_LABELS.items() if mode == settings["mode"]), "自动判断（推荐）")
        self.mode_menu = ctk.CTkOptionMenu(options, values=list(MODE_LABELS), height=44, corner_radius=11, fg_color=p["secondary"], button_color=p["accent"], button_hover_color=p["accent_hover"], text_color=p["text"])
        self.mode_menu.set(current_label)
        self.mode_menu.grid(row=1, column=0, sticky="ew")
        self.update_switch = ctk.CTkSwitch(options, text="启动时自动检测新版本", font=("Microsoft YaHei UI", 12), text_color=p["text"], progress_color=p["accent"])
        self.update_switch.grid(row=2, column=0, sticky="w", pady=(18, 8))
        self.update_switch.select() if settings.get("auto_update", True) else self.update_switch.deselect()

        self.save_button = ctk.CTkButton(
            self, text="保存设置", height=50, corner_radius=13,
            fg_color=p["primary"], hover_color=p["primary_hover"],
            font=("Microsoft YaHei UI", 13, "bold"), command=self.save,
        )
        # 固定在可视窗口底部，不让系统 DPI 或内容请求尺寸把主操作裁掉。
        self.save_button.place(relx=0.5, rely=1.0, anchor="s", relwidth=0.88, y=-24)
        self.after(100, self._center)

    def _center(self):
        self.update_idletasks()
        x = self.master_app.winfo_x() + max(0, (self.master_app.winfo_width() - self.winfo_width()) // 2)
        y = self.master_app.winfo_y() + max(0, (self.master_app.winfo_height() - self.winfo_height()) // 2)
        self.geometry(f"+{x}+{y}")

    def choose_folder(self):
        selected = filedialog.askdirectory(initialdir=self.folder_entry.get() or str(Path.home()))
        if selected:
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, selected)

    def save(self):
        folder = self.folder_entry.get().strip() or str(Path.home() / "Downloads")
        self.master_app.settings = save_settings({
            "output_dir": folder,
            "mode": MODE_LABELS[self.mode_menu.get()],
            "auto_update": bool(self.update_switch.get()),
            "theme": self.master_app.theme,
        })
        self.master_app.refresh_folder_label()
        self.destroy()


class DesktopApp(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        super().__init__()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        if screen_width <= 1280:
            ctk.set_widget_scaling(0.8)
        self.settings = load_settings()
        self.theme = self.settings.get("theme", "neo")
        self.palette = THEME_PALETTES[self.theme]
        self.running = False
        self._placeholder = True
        self._clipboard_text = ""
        self.title("小红书无水印下载器")
        window_width = min(1080, max(900, screen_width - 40))
        window_height = min(700, max(620, screen_height - 80))
        self.geometry(f"{window_width}x{window_height}")
        self.minsize(min(900, window_width), min(620, window_height))
        self.configure(fg_color=self.palette["bg"])
        self._build_ui()
        self.after(250, self._center_window)
        if self.settings.get("auto_update", True):
            threading.Thread(target=self._check_update, daemon=True).start()
        self.after(700, self._watch_clipboard)

    def _center_window(self):
        self.update_idletasks()
        x = max(0, (self.winfo_screenwidth() - self.winfo_width()) // 2)
        y = max(0, (self.winfo_screenheight() - self.winfo_height()) // 2)
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        p = self.palette
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=38, pady=(30, 20))
        header.grid_columnconfigure(0, weight=1)
        brand = ctk.CTkFrame(header, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(brand, text="小红书原图", font=("STSong", 30, "bold"), text_color=p["text"]).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(brand, text="公开笔记 · 本地保存 · 无需登录", font=("Microsoft YaHei UI", 12), text_color=p["muted"]).grid(row=1, column=0, sticky="w", pady=(4, 0))
        next_theme = "克制玻璃" if self.theme == "neo" else "拟态悬浮"
        self.theme_button = ctk.CTkButton(header, text=next_theme, width=104, height=40, corner_radius=12, fg_color=p["secondary"], hover_color=p["secondary_hover"], text_color=p["text"], command=self.switch_theme)
        self.theme_button.grid(row=0, column=1, padx=(0, 8))
        self.update_button = ctk.CTkButton(header, text="", width=0, height=38, fg_color="transparent", hover_color=p["secondary_hover"], text_color=p["accent"])
        self.update_button.grid(row=0, column=2, padx=(0, 8))
        self.update_button.grid_remove()
        ctk.CTkButton(header, text="⚙  设置", width=104, height=40, corner_radius=12, fg_color=p["secondary"], hover_color=p["secondary_hover"], text_color=p["text"], font=("Microsoft YaHei UI", 13, "bold"), command=self.open_settings).grid(row=0, column=3)

        body = ctk.CTkFrame(self, corner_radius=24, fg_color=p["surface"], border_width=1, border_color=p["line"])
        body.grid(row=1, column=0, sticky="nsew", padx=38, pady=(0, 24))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(body, text="粘贴分享内容", font=("Microsoft YaHei UI", 15, "bold"), text_color=p["text"]).grid(row=0, column=0, sticky="w", padx=(28, 12), pady=(26, 10))
        self.folder_label = ctk.CTkLabel(body, text="", font=("Microsoft YaHei UI", 11), text_color=p["muted"], anchor="e")
        self.folder_label.grid(row=0, column=1, sticky="e", padx=(12, 28), pady=(26, 10))
        self.refresh_folder_label()

        self.input_box = ctk.CTkTextbox(body, corner_radius=16, border_width=1, border_color=p["line"], fg_color=p["input"], text_color=p["text"], font=("Microsoft YaHei UI", 14), wrap="word")
        self.input_box.grid(row=1, column=0, sticky="nsew", padx=(28, 12), pady=(0, 22))
        self.input_box.insert("1.0", "把小红书链接或整段分享文字粘贴到这里……")
        self.input_box.configure(text_color=p["muted"])
        self.input_box.bind("<FocusIn>", self._clear_placeholder, add="+")

        status = ctk.CTkFrame(body, corner_radius=17, fg_color=p["status"])
        status.grid(row=1, column=1, sticky="nsew", padx=(12, 28), pady=(0, 22))
        status.grid_columnconfigure(0, weight=1)
        status.grid_rowconfigure(4, weight=1)
        ctk.CTkLabel(status, text="下载状态", font=("Microsoft YaHei UI", 12, "bold"), text_color=p["muted"]).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 6))
        self.status_title = ctk.CTkLabel(status, text="等待开始", font=("Microsoft YaHei UI", 20, "bold"), text_color=p["text"])
        self.status_title.grid(row=1, column=0, sticky="w", padx=20)
        self.status_detail = ctk.CTkLabel(status, text="结果将逐条显示", font=("Microsoft YaHei UI", 11), text_color=p["muted"])
        self.status_detail.grid(row=2, column=0, sticky="w", padx=20, pady=(5, 14))
        self.progress = ctk.CTkProgressBar(status, height=9, corner_radius=6, fg_color=p["line"], progress_color=p["accent"], mode="determinate")
        self.progress.grid(row=3, column=0, sticky="ew", padx=20)
        self.progress.set(0)
        self.result_box = ctk.CTkTextbox(status, fg_color="transparent", border_width=0, text_color=p["text"], font=("Microsoft YaHei UI", 11), wrap="word")
        self.result_box.grid(row=4, column=0, sticky="nsew", padx=14, pady=(13, 10))
        self.result_box.configure(state="disabled")

        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.grid(row=2, column=0, columnspan=2, sticky="ew", padx=28, pady=(0, 26))
        actions.grid_columnconfigure(0, weight=1)
        self.download_button = ctk.CTkButton(actions, text="开始采集", height=50, corner_radius=14, fg_color=p["primary"], hover_color=p["primary_hover"], font=("Microsoft YaHei UI", 14, "bold"), command=self.start_download)
        self.download_button.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.paste_button = ctk.CTkButton(actions, text="粘贴并采集", width=132, height=50, corner_radius=14, fg_color=p["accent"], hover_color=p["accent_hover"], command=self.paste_and_start)
        self.paste_button.grid(row=0, column=1, padx=(0, 10))
        self.paste_button.grid_remove()
        ctk.CTkButton(actions, text="打开下载文件夹", width=150, height=50, corner_radius=14, fg_color=p["secondary"], hover_color=p["secondary_hover"], text_color=p["text"], command=self.open_output).grid(row=0, column=2)

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=40, pady=(0, 18))
        ctk.CTkLabel(footer, text="原始媒体直存 · 作者嵌入的署名会保留", font=("Microsoft YaHei UI", 10), text_color=p["muted"]).pack(side="left")
        ctk.CTkLabel(footer, text=f"V{__version__}", font=("Microsoft YaHei UI", 10, "bold"), text_color=p["muted"]).pack(side="right")

    def _clear_placeholder(self, _event=None):
        if self._placeholder:
            self.input_box.delete("1.0", "end")
            self.input_box.configure(text_color=self.palette["text"])
            self._placeholder = False

    def refresh_folder_label(self):
        path = Path(self.settings["output_dir"])
        label = path.name or str(path)
        self.folder_label.configure(text="保存到  " + label)

    def open_settings(self):
        if not self.running:
            SettingsDialog(self)

    def switch_theme(self):
        if self.running:
            return
        content = self.input_box.get("1.0", "end").rstrip("\n")
        was_placeholder = self._placeholder
        self.theme = "glass" if self.theme == "neo" else "neo"
        self.settings = save_settings({
            "output_dir": self.settings["output_dir"],
            "mode": self.settings.get("mode", "auto"),
            "auto_update": self.settings.get("auto_update", True),
            "theme": self.theme,
        })
        self.palette = THEME_PALETTES[self.theme]
        self.configure(fg_color=self.palette["bg"])
        for child in self.winfo_children():
            child.destroy()
        self._build_ui()
        if not was_placeholder:
            self.input_box.delete("1.0", "end")
            self.input_box.insert("1.0", content)
            self.input_box.configure(text_color=self.palette["text"])
            self._placeholder = False

    def open_output(self):
        folder = Path(self.settings["output_dir"])
        folder.mkdir(parents=True, exist_ok=True)
        os.startfile(str(folder))

    def _watch_clipboard(self):
        try:
            value = self.clipboard_get().strip()
            if extract_urls_from_text(value) and value != self.input_box.get("1.0", "end").strip():
                self._clipboard_text = value
                if not self.running:
                    self.paste_button.grid()
            else:
                self.paste_button.grid_remove()
        except Exception:
            self.paste_button.grid_remove()
        if not self.running:
            self._refresh_detection()
        self.after(900, self._watch_clipboard)

    def _refresh_detection(self):
        if self._placeholder:
            return
        urls = extract_urls_from_text(self.input_box.get("1.0", "end"))
        if not urls:
            self.status_title.configure(text="等待开始")
            self.status_detail.configure(text="还没有识别到小红书链接")
            return
        configured = self.settings.get("mode", "auto")
        selected = automatic_mode(len(urls)) if configured == "auto" else configured
        prefix = "自动" if configured == "auto" else "手动"
        self.status_title.configure(text=f"已识别 {len(urls)} 条")
        self.status_detail.configure(text=f"{prefix}使用：{mode_description(selected, len(urls))}")

    def paste_and_start(self):
        if self.running or not self._clipboard_text:
            return
        self._clear_placeholder()
        self.input_box.delete("1.0", "end")
        self.input_box.insert("1.0", self._clipboard_text)
        self.paste_button.grid_remove()
        self.start_download()

    def start_download(self):
        if self.running:
            return
        text = self.input_box.get("1.0", "end").strip()
        urls = extract_urls_from_text(text)
        if not urls:
            messagebox.showwarning("还缺少链接", "请先粘贴至少一条小红书分享链接。")
            return
        self.running = True
        self.download_button.configure(state="disabled", text="采集中")
        self.status_title.configure(text="正在准备")
        configured = self.settings.get("mode", "auto")
        selected_mode = automatic_mode(len(urls)) if configured == "auto" else configured
        self.status_detail.configure(text=f"共 {len(urls)} 条 · {mode_description(selected_mode, len(urls))}")
        self._set_results("")
        self.progress.configure(mode="indeterminate")
        self.progress.start()
        threading.Thread(target=self._download_worker, args=(urls, selected_mode), daemon=True).start()

    def _download_worker(self, urls, selected_mode):
        lines = []

        def on_progress(item, index, total):
            state = "完成" if item.success else "失败"
            lines.append(f"{index}/{total}  {state}  {item.title or item.error}")
            self.after(0, lambda: self._update_progress(index, total, lines))

        try:
            downloader = XhsV2Downloader(
                output_dir=self.settings["output_dir"],
                delay=DELAY_MODES[selected_mode],
                on_progress=on_progress,
            )
            result = downloader.download(urls)
            self.after(0, lambda: self._finish_download(result.success_count, result.fail_count))
        except EngineNotReady as exc:
            self.after(0, lambda: self._fail_download(str(exc)))
        except Exception as exc:
            self.after(0, lambda: self._fail_download(str(exc)))

    def _update_progress(self, index, total, lines):
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress.set(index / max(total, 1))
        self.status_title.configure(text="正在逐条保存" if index < total else "正在整理文件")
        self.status_detail.configure(text=f"已完成 {index} / {total}")
        self._set_results("\n\n".join(lines))

    def _finish_download(self, success, failed):
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress.set(1)
        self.status_title.configure(text="全部保存完成" if not failed else "任务完成")
        self.status_detail.configure(text=f"成功 {success} 条，失败 {failed} 条")
        self.download_button.configure(state="normal", text="继续采集")
        self.running = False

    def _fail_download(self, error):
        self.progress.stop()
        self.progress.set(0)
        self.status_title.configure(text="没有完成")
        self.status_detail.configure(text=error[:100])
        self.download_button.configure(state="normal", text="重新采集")
        self.running = False
        messagebox.showerror("下载失败", error)

    def _set_results(self, text):
        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", text)
        self.result_box.configure(state="disabled")

    def _check_update(self):
        try:
            response = requests.get(RELEASE_API, timeout=5, headers={"User-Agent": "xhs-dl-desktop"})
            response.raise_for_status()
            data = response.json()
            latest = data.get("tag_name", "")
            if latest and version_tuple(latest) > version_tuple(__version__):
                url = data.get("html_url", "https://github.com/zwmopen/xhs-dl/releases/latest")
                self.after(0, lambda: self._show_update(latest, url))
        except Exception:
            pass

    def _show_update(self, version, url):
        self.update_button.configure(text=f"发现 {version}", width=104, command=lambda: webbrowser.open(url))
        self.update_button.grid()


def main():
    app = DesktopApp()
    app.mainloop()


if __name__ == "__main__":
    main()
