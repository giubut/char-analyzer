"""
GUI 主界面（四标签页版）
运行前自动清理旧缓存，退出保存配置，跑完保存历史。
"""
import os
import sys
import json
import glob
import time as _time
import threading
import traceback
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# 启动清理
if getattr(sys, 'frozen', False):
    temp_dir = os.environ.get('TEMP', '')
    if temp_dir:
        current = getattr(sys, '_MEIPASS', '').lower()
        for f in glob.glob(os.path.join(temp_dir, '_MEI*')):
            if os.path.isdir(f) and f.lower() != current:
                try: shutil.rmtree(f, ignore_errors=True)
                except: pass

from config import DEFAULT_BASE_URL, AVAILABLE_MODELS, load_config, save_config
from pipeline import Pipeline
from utils import log_info, log_error, log_warning, save_history, list_history, clean_temp_cache, start_analysis_log, write_analysis_log, get_analysis_log_path, LOG_DIR, _exe_dir as utils_exe_dir


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("角色性格变化分析工具")
        self.root.geometry("1050x820")
        self.root.minsize(900, 650)

        # 主题美化 - 二次元可爱风
        self.style = ttk.Style()
        self.style.theme_use("clam")
        colors = {
            'bg': '#fff5f7',      # 软粉底
            'fg': '#5a5a7a',      # 紫灰文字
            'primary': '#ff9eb5',  # 粉红主色
            'secondary': '#a8d8ea',# 天蓝
            'accent': '#aa96da',   # 薰衣草紫
            'success': '#8bc9a5',  # 薄荷绿
            'error': '#ff7b7b',    # 浅红
            'card': '#ffffff',     # 白
            'border': '#f0dce8',   # 粉边框
        }
        font_family = "Microsoft YaHei"
        self.style.configure(".", font=(font_family, 10), background=colors['bg'])
        self.style.configure("TLabel", foreground=colors['fg'], background=colors['bg'])
        self.style.configure("Header.TLabel", font=(font_family, 11, "bold"), foreground=colors['primary'])
        self.style.configure("Title.TLabel", font=(font_family, 14, "bold"), foreground=colors['accent'])
        self.style.configure("Success.TLabel", foreground=colors['success'], font=(font_family, 10, "bold"))
        self.style.configure("Error.TLabel", foreground=colors['error'], font=(font_family, 10, "bold"))
        self.style.configure("TButton", padding=(10, 5), foreground=colors['fg'], background=colors['card'],
                             bordercolor=colors['border'], focuscolor='none', borderwidth=1)
        self.style.map("TButton", background=[('active', colors['secondary']), ('pressed', colors['primary'])])
        self.style.configure("Folder.TButton", foreground=colors['secondary'], font=(font_family, 9),
                             background=colors['bg'], bordercolor=colors['border'])
        self.style.map("Folder.TButton", background=[('active', colors['card'])])
        self.style.configure("Run.TButton", foreground="#ffffff", background=colors['success'],
                             font=(font_family, 11, "bold"), borderwidth=0)
        self.style.map("Run.TButton", background=[('active', '#7ab892'), ('pressed', '#6aa882')])
        self.style.configure("TFrame", background=colors['bg'])
        self.style.configure("TLabelframe", background=colors['card'], foreground=colors['accent'],
                             bordercolor=colors['border'], lightcolor=colors['border'], darkcolor=colors['border'])
        self.style.configure("TLabelframe.Label", foreground=colors['accent'], font=(font_family, 10, "bold"),
                             background=colors['card'])
        self.style.configure("Horizontal.TProgressbar", troughcolor=colors['border'], background=colors['secondary'],
                             bordercolor=colors['border'], lightcolor=colors['secondary'], darkcolor=colors['card'])
        self.style.configure("TNotebook", background=colors['card'], bordercolor=colors['border'])
        self.style.configure("TNotebook.Tab", padding=(12, 4), background=colors['bg'], foreground=colors['fg'],
                             font=(font_family, 10))
        self.style.map("TNotebook.Tab", background=[('selected', colors['card'])],
                       foreground=[('selected', colors['accent'])])
        self.style.configure("TEntry", fieldbackground=colors['card'], foreground=colors['fg'],
                             bordercolor=colors['border'])
        self.style.configure("TCombobox", fieldbackground=colors['card'], foreground=colors['fg'],
                             bordercolor=colors['border'])
        self.root.configure(bg=colors['bg'])

        self._running = False
        self._drop_watcher_running = False
        self._scores = {}
        self._overseer_json = ""
        self._report_text = ""

        # 加载配置
        cfg = load_config()
        self._cfg = cfg

        self._build_ui()
        self._load_cfg_to_ui(cfg)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        nb = ttk.Notebook(self.root)
        nb.pack(fill=tk.BOTH, expand=True)

        self._tab_setup = ttk.Frame(nb, padding=10)
        self._tab_run = ttk.Frame(nb, padding=10)
        self._tab_trace = ttk.Frame(nb, padding=10)
        self._tab_history = ttk.Frame(nb, padding=10)
        nb.add(self._tab_setup, text=" 设置 ")
        nb.add(self._tab_run, text=" 运行 ")
        nb.add(self._tab_trace, text=" 监工对话 ")
        nb.add(self._tab_history, text=" 历史 ")
        self._nb = nb

        self._build_setup_tab()
        self._build_run_tab()
        self._build_trace_tab()
        self._build_history_tab()

    # ---- 设置标签页 ----
    def _build_setup_tab(self):
        f = self._tab_setup

        # API
        sf = ttk.LabelFrame(f, text="API设置", padding=8)
        sf.pack(fill=tk.X, pady=(0, 8))

        r1 = ttk.Frame(sf); r1.pack(fill=tk.X, pady=2)
        ttk.Label(r1, text="Base URL", width=12).pack(side=tk.LEFT)
        self._url_var = tk.StringVar(value=DEFAULT_BASE_URL)
        ttk.Entry(r1, textvariable=self._url_var, width=70).pack(side=tk.LEFT, padx=5)

        r2 = ttk.Frame(sf); r2.pack(fill=tk.X, pady=2)
        ttk.Label(r2, text="API Key", width=12).pack(side=tk.LEFT)
        self._key_var = tk.StringVar()
        e = ttk.Entry(r2, textvariable=self._key_var, width=70, show="*")
        e.pack(side=tk.LEFT, padx=5)
        self._key_vis_btn = ttk.Button(r2, text="显示", width=4,
                                       command=lambda: e.configure(show="" if e.cget("show") == "*" else "*"))
        self._key_vis_btn.pack(side=tk.LEFT)

        r3 = ttk.Frame(sf); r3.pack(fill=tk.X, pady=2)
        ttk.Label(r3, text="模型", width=12).pack(side=tk.LEFT)
        self._model_var = tk.StringVar(value=AVAILABLE_MODELS[0])
        ttk.Combobox(r3, textvariable=self._model_var, values=AVAILABLE_MODELS, width=30).pack(side=tk.LEFT, padx=5)
        self._test_btn = ttk.Button(r3, text="测试连接", command=self._test_api)
        self._test_btn.pack(side=tk.LEFT, padx=5)
        self._test_status = tk.StringVar(value="")
        ttk.Label(r3, textvariable=self._test_status, foreground="gray", width=40).pack(side=tk.LEFT, padx=5)

        # 文件
        ff = ttk.LabelFrame(f, text="输入文件", padding=8)
        ff.pack(fill=tk.X, pady=(0, 8))

        self._front_path = tk.StringVar()
        self._back_path = tk.StringVar()

        # 前段：文件行 + 按钮 + 文件夹
        f1 = ttk.LabelFrame(ff, text="前段文本", padding=5)
        f1.pack(fill=tk.X, pady=3)
        r1 = ttk.Frame(f1); r1.pack(fill=tk.X)
        self._front_drop = tk.Text(r1, height=2, relief=tk.RIDGE, bg="#ffffff", cursor="hand2")
        self._front_drop.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        self._front_drop.insert("1.0", " 拖放文件或点击选择")
        self._front_drop.configure(state=tk.DISABLED)
        self._front_drop.bind("<Button-1>", lambda e: self._pick_front())
        self._front_drop.bind('<<Drop>>', self._on_drop_front_native)
        self.root.bind('<Control-v>', self._on_paste_path)
        ttk.Button(r1, text="选择", command=self._pick_front).pack(side=tk.LEFT, padx=1)
        ttk.Button(r1, text="\u2716", command=self._clear_front, width=3).pack(side=tk.LEFT, padx=1)
        fd1 = ttk.Frame(f1); fd1.pack(fill=tk.X, pady=(3, 0))
        ttk.Button(fd1, text="\U0001f4c2 前段投放文件夹", command=lambda: self._open_drop_folder('front'),
                   style="Folder.TButton").pack(fill=tk.X)

        # 后段：文件行 + 按钮 + 文件夹
        f2 = ttk.LabelFrame(ff, text="后段文本", padding=5)
        f2.pack(fill=tk.X, pady=3)
        r2 = ttk.Frame(f2); r2.pack(fill=tk.X)
        self._back_drop = tk.Text(r2, height=2, relief=tk.RIDGE, bg="#ffffff", cursor="hand2")
        self._back_drop.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        self._back_drop.insert("1.0", " 拖放文件或点击选择")
        self._back_drop.configure(state=tk.DISABLED)
        self._back_drop.bind("<Button-1>", lambda e: self._pick_back())
        self._back_drop.bind('<<Drop>>', self._on_drop_back_native)
        ttk.Button(r2, text="选择", command=self._pick_back).pack(side=tk.LEFT, padx=1)
        ttk.Button(r2, text="\u2716", command=self._clear_back, width=3).pack(side=tk.LEFT, padx=1)
        fd2 = ttk.Frame(f2); fd2.pack(fill=tk.X, pady=(3, 0))
        ttk.Button(fd2, text="\U0001f4c2 后段投放文件夹", command=lambda: self._open_drop_folder('back'),
                   style="Folder.TButton").pack(fill=tk.X)

        # 角色名
        nr = ttk.Frame(f); nr.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(nr, text="角色名", width=12).pack(side=tk.LEFT)
        self._char_var = tk.StringVar()
        ttk.Entry(nr, textvariable=self._char_var, width=30).pack(side=tk.LEFT, padx=5)
        self._scan_btn = ttk.Button(nr, text="扫描角色", command=self._scan_characters)
        self._scan_btn.pack(side=tk.LEFT, padx=5)
        ttk.Label(nr, text="（手动输入或扫描识别）", foreground="gray").pack(side=tk.LEFT)

        # 开始按钮
        bt = ttk.Frame(f); bt.pack(fill=tk.X, pady=5)
        self._run_btn = ttk.Button(bt, text="▶ 开始分析", command=self._run_analysis)
        self._run_btn.pack(side=tk.LEFT, padx=(0, 10))
        self._save_btn = ttk.Button(bt, text="保存报告", command=self._save_report, state=tk.DISABLED)
        self._save_btn.pack(side=tk.LEFT, padx=(0, 10))
        self._export_btn = ttk.Button(bt, text="导出监工", command=self._export_overseer, state=tk.DISABLED)
        self._export_btn.pack(side=tk.LEFT)

    # ---- 运行标签页 ----
    def _build_run_tab(self):
        f = self._tab_run

        # 进度条
        pf = ttk.Frame(f); pf.pack(fill=tk.X, pady=(0, 5))
        self._prog_var = tk.StringVar(value="\U0001f4ab 就绪")
        ttk.Label(pf, textvariable=self._prog_var, style="Header.TLabel").pack(side=tk.LEFT)
        self._prog_bar = ttk.Progressbar(pf, mode="determinate", length=200, style="Horizontal.TProgressbar")
        self._prog_bar.pack(side=tk.RIGHT, padx=5)

        # PanedWindow：可拖拽分割结果和日志
        pw = tk.PanedWindow(f, orient=tk.VERTICAL, bg="#d0d3d4", sashwidth=4, sashrelief=tk.RAISED)
        pw.pack(fill=tk.BOTH, expand=True)

        # 上：分析结果
        sf = ttk.LabelFrame(pw, text="\U0001f4ca 分析结果", padding=5)
        self._score_text = tk.Text(sf, font=("Microsoft YaHei", 10), state=tk.DISABLED, wrap=tk.WORD,
                                   bg="#ffffff", fg="#5a5a7a", relief=tk.FLAT, padx=10, pady=5)
        self._score_text.pack(fill=tk.BOTH, expand=True)
        self._score_text.configure(state=tk.NORMAL)
        self._score_text.insert("1.0", "（分析完成后自动显示完整结果）")
        self._score_text.configure(state=tk.DISABLED)
        pw.add(sf, height=350)

        # 下：日志
        lf = ttk.LabelFrame(pw, text="\U0001f4dd 执行日志", padding=5)
        lf_top = ttk.Frame(lf); lf_top.pack(fill=tk.X)
        ttk.Label(lf_top, text="拖拽分割条调整大小", foreground="gray").pack(side=tk.LEFT)
        ttk.Button(lf_top, text="打开日志文件夹", command=self._open_log_folder).pack(side=tk.RIGHT)
        self._log_text = scrolledtext.ScrolledText(lf, wrap=tk.WORD, font=("Consolas", 9), state=tk.DISABLED)
        self._log_text.pack(fill=tk.BOTH, expand=True)
        pw.add(lf, height=120)

    # ---- 监工对话标签页 ----
    def _build_trace_tab(self):
        f = self._tab_trace
        top = ttk.Frame(f); top.pack(fill=tk.X)
        ttk.Label(top, text="Agent推理完整原文（边跑边刷新）", font=("Microsoft YaHei", 10, "bold")).pack(pady=5)
        ttk.Button(top, text="清空", command=self._clear_trace).pack(side=tk.RIGHT)
        ttk.Button(top, text="导出完整监工JSON", command=self._export_overseer).pack(side=tk.RIGHT, padx=5)

        self._trace_text = scrolledtext.ScrolledText(f, wrap=tk.WORD, font=("Consolas", 10), state=tk.DISABLED)
        self._trace_text.pack(fill=tk.BOTH, expand=True)

    # ---- 历史标签页 ----
    def _build_history_tab(self):
        f = self._tab_history
        top = ttk.Frame(f); top.pack(fill=tk.X)
        ttk.Label(top, text="分析历史记录", font=("Microsoft YaHei", 10, "bold")).pack(side=tk.LEFT, pady=5)
        ttk.Button(top, text="刷新列表", command=self._refresh_history).pack(side=tk.RIGHT)
        ttk.Button(top, text="删除选中", command=self._delete_history).pack(side=tk.RIGHT, padx=5)

        self._hist_list = tk.Listbox(f, font=("Consolas", 10))
        self._hist_list.pack(fill=tk.BOTH, expand=True, pady=5)
        self._hist_list.bind("<<ListboxSelect>>", self._on_hist_select)

        self._hist_detail = scrolledtext.ScrolledText(f, height=8, font=("Consolas", 9), state=tk.DISABLED)
        self._hist_detail.pack(fill=tk.X)
        self._hist_data = []
        self._refresh_history()

    # =================== 配置加载/保存 ===================
    def _load_cfg_to_ui(self, cfg: dict):
        if cfg.get("base_url"):
            self._url_var.set(cfg["base_url"])
        if cfg.get("api_key"):
            self._key_var.set(cfg["api_key"])
        if cfg.get("model"):
            self._model_var.set(cfg["model"])
        if cfg.get("front_path"):
            self._front_path.set(cfg["front_path"])
            self._update_drop_text(self._front_drop, cfg["front_path"], "前段")
        if cfg.get("back_path"):
            self._back_path.set(cfg["back_path"])
            self._update_drop_text(self._back_drop, cfg["back_path"], "后段")
        if cfg.get("character"):
            self._char_var.set(cfg["character"])

    def _save_cfg(self):
        d = {
            "base_url": self._url_var.get().strip(),
            "api_key": self._key_var.get().strip(),
            "model": self._model_var.get().strip(),
            "front_path": self._front_path.get(),
            "back_path": self._back_path.get(),
            "character": self._char_var.get().strip(),
        }
        save_config(d)

    def _on_close(self):
        self._save_cfg()
        clean_temp_cache()
        self.root.destroy()

    # =================== 拖放区 ===================
    def _update_drop_text(self, widget: tk.Text, path: str, label: str):
        name = os.path.basename(path) if path else ""
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        if name:
            widget.insert("1.0", f" {name}")
            widget.configure(bg="#e8ffe8")
        else:
            widget.insert("1.0", f" 点击选择 或 拖放txt到此处（{label}文）")
            widget.configure(bg="#f8f8f8")
        widget.configure(state=tk.DISABLED)

    def _pick_front(self):
        try:
            self.root.lift()
            self.root.focus_force()
            self.root.state('normal')
            self.root.update_idletasks()
            p = filedialog.askopenfilename(
                parent=self.root, title="选择前段文本",
                filetypes=[("txt", "*.txt"), ("所有文件", "*.*")])
        except:
            p = ''
        if p:
            dst = os.path.join(utils_exe_dir(), "dropbox", "前段", os.path.basename(p))
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(p, dst)
                self._front_path.set(dst)
            except:
                self._front_path.set(p)
            self._update_drop_text(self._front_drop, self._front_path.get(), "前段")

    def _pick_back(self):
        try:
            self.root.lift()
            self.root.focus_force()
            self.root.state('normal')
            self.root.update_idletasks()
            p = filedialog.askopenfilename(
                parent=self.root, title="选择后段文本",
                filetypes=[("txt", "*.txt"), ("所有文件", "*.*")])
        except:
            p = ''
        if p:
            dst = os.path.join(utils_exe_dir(), "dropbox", "后段", os.path.basename(p))
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(p, dst)
                self._back_path.set(dst)
            except:
                self._back_path.set(p)
            self._update_drop_text(self._back_drop, self._back_path.get(), "后段")

    def _clear_front(self):
        fp = self._front_path.get()
        self._front_path.set("")
        self._update_drop_text(self._front_drop, "", "前段")
        if fp and os.path.exists(fp) and "\\dropbox\\" in fp:
            try: os.remove(fp)
            except: pass

    def _clear_back(self):
        fp = self._back_path.get()
        self._back_path.set("")
        self._update_drop_text(self._back_drop, "", "后段")
        if fp and os.path.exists(fp) and "\\dropbox\\" in fp:
            try: os.remove(fp)
            except: pass

    # ---- 拖放/粘贴 ----
    def _on_drop_front_native(self, event):
        """尝试从<<Drop>>事件获取路径"""
        self._handle_drop(event.data, 'front')

    def _on_drop_back_native(self, event):
        self._handle_drop(event.data, 'back')

    def _handle_drop(self, raw: str, target: str):
        """解析tkdnd的文件路径并赋值"""
        try:
            import re
            paths = re.findall(r'\{([^}]+)\}|(\S+)', raw)
            paths = [p[0] or p[1] for p in paths if (p[0] or p[1])]
            for p in paths:
                p = p.strip()
                if os.path.exists(p) and p.endswith('.txt'):
                    if target == 'front':
                        self._front_path.set(p)
                        self._update_drop_text(self._front_drop, p, '前段')
                    else:
                        self._back_path.set(p)
                        self._update_drop_text(self._back_drop, p, '后段')
                    break
        except Exception:
            pass

    def _on_paste_path(self, event):
        """Ctrl+V 粘贴文件路径"""
        try:
            clip = self.root.clipboard_get()
            clip = clip.strip(' \n\r"\'')
            if os.path.exists(clip) and clip.endswith('.txt'):
                if not self._front_path.get() or not os.path.exists(self._front_path.get()):
                    self._front_path.set(clip)
                    self._update_drop_text(self._front_drop, clip, '前段')
                else:
                    self._back_path.set(clip)
                    self._update_drop_text(self._back_drop, clip, '后段')
        except:
            pass

    # =================== API测试 ===================
    def _test_api(self):
        if not self._key_var.get().strip():
            messagebox.showwarning("", "请填写 API Key")
            return
        self._test_btn.configure(state=tk.DISABLED, text="测试中...")
        self._test_status.set("⏳ 测试中...")
        def _t():
            try:
                from api_client import APIClient
                c = APIClient(base_url=self._url_var.get().strip(), api_key=self._key_var.get().strip())
                c.call([{"role":"user","content":"回复OK"}], model=self._model_var.get().strip(),
                       max_tokens=10, timeout=15, step="连接测试")
                self.root.after(0, lambda: (self._test_btn.configure(state=tk.NORMAL, text="测试连接"),
                                            self._test_status.set("✅ 连接成功")))
            except Exception as ex:
                s = str(ex)[:80]
                self.root.after(0, lambda: (self._test_btn.configure(state=tk.NORMAL, text="测试连接"),
                                            self._test_status.set(f"❌ {s}")))
        threading.Thread(target=_t, daemon=True).start()

    def _manual_clean(self):
        n = clean_temp_cache(silent=False)
        messagebox.showinfo("清理缓存", f"清理完成。删除旧临时文件夹：{n}个")

    # =================== 角色扫描 ===================
    def _scan_characters(self):
        fp = self._front_path.get()
        if not fp or not os.path.exists(fp):
            messagebox.showwarning("", "请先选择前段文本")
            return
        if not self._key_var.get().strip():
            messagebox.showwarning("", "请填写 API Key")
            return
        try:
            with open(fp, "r", encoding="utf-8") as f:
                ft = f.read()
        except Exception as e:
            messagebox.showerror("", f"读取失败: {e}")
            return
        self._scan_btn.configure(state=tk.DISABLED, text="扫描中...")
        def _s():
            try:
                from api_client import APIClient
                from text_analyzer import TextAnalyzer
                c = APIClient(base_url=self._url_var.get().strip(), api_key=self._key_var.get().strip())
                a = TextAnalyzer(c, self._model_var.get().strip())
                chars = a.identify_characters(ft)
                self.root.after(0, lambda: self._show_char_dialog(chars))
            except Exception as ex:
                self.root.after(0, lambda: (self._scan_btn.configure(state=tk.NORMAL, text="扫描角色"),
                                             messagebox.showerror("", f"扫描失败: {ex}")))
        threading.Thread(target=_s, daemon=True).start()

    def _show_char_dialog(self, chars: list):
        self._scan_btn.configure(state=tk.NORMAL, text="扫描角色")
        if not chars:
            messagebox.showinfo("", "未识别出角色，手动输入。")
            return
        d = tk.Toplevel(self.root); d.title("选择角色"); d.geometry("300x350")
        d.transient(self.root); d.grab_set()
        ttk.Label(d, text="选择角色：", font=("Microsoft YaHei", 11)).pack(pady=8)
        lb = tk.Listbox(d, font=("Microsoft YaHei", 10))
        lb.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        for c in chars:
            lb.insert(tk.END, c)
        def _ok():
            sel = lb.curselection()
            if sel:
                self._char_var.set(lb.get(sel[0]))
            d.destroy()
        ttk.Button(d, text="确认", command=_ok).pack(pady=8)

    # =================== 主分析 ===================
    def _run_analysis(self):
        self._nb.select(self._tab_run)  # 自动切到运行标签
        if self._running:
            return
        if not self._key_var.get().strip():
            messagebox.showwarning("", "请填写 API Key")
            return
        fp = self._front_path.get()
        bp = self._back_path.get()
        if not fp or not os.path.exists(fp):
            messagebox.showwarning("", "请选择前段文本")
            return
        if not bp or not os.path.exists(bp):
            messagebox.showwarning("", "请选择后段文本")
            return
        cn = self._char_var.get().strip()
        if not cn:
            messagebox.showwarning("", "请输入角色名")
            return
        try:
            with open(fp, "r", encoding="utf-8") as f:
                ft = f.read()
            with open(bp, "r", encoding="utf-8") as f:
                bt = f.read()
        except Exception as e:
            messagebox.showerror("", f"文件读失败: {e}")
            return

        # 内容预检
        cn_front = cn in ft if cn else False
        cn_back = cn in bt if cn else False
        if not (cn_front and cn_back):
            parts = []
            if not cn_front: parts.append("前段")
            if not cn_back: parts.append("后段")
            msg = "角色「{}」在{}中未出现。\n如果文本不是该角色的内容，继续分析会浪费 API 额度。\n是否仍要继续？".format(cn, "、".join(parts))
            ret = messagebox.askyesno("角色名出现情况", msg)
            if not ret:
                return

        # 准备界面
        self._running = True
        self._disable_buttons()
        self._prog_bar["value"] = 0
        self._prog_var.set("启动中...")
        self._clear_log()
        self._clear_score()
        self._clear_trace()
        self._export_btn.configure(state=tk.DISABLED)
        self._save_btn.configure(state=tk.DISABLED)

        # 保存配置（运行前存一次，防止强退丢配置）
        self._save_cfg()
        self._log(f"=" * 60)
        self._log(f"  开始分析  角色: {cn}  前段:{len(ft)}字  后段:{len(bt)}字")

        # 初始化分析日志文件
        log_path = start_analysis_log()
        write_analysis_log(f"角色: {cn}  前段: {len(ft)}字  后段: {len(bt)}字")
        write_analysis_log("-" * 60)

        def _run():
            try:
                p = Pipeline(
                    base_url=self._url_var.get().strip(),
                    api_key=self._key_var.get().strip(),
                    model=self._model_var.get().strip(),
                    progress_callback=self._on_prog,
                    log_callback=self._on_log,
                    step_callback=self._on_step,
                )
                r = p.run(ft, bt, cn)
            except Exception as ex:
                r = {"success": False, "error": f"意外错误: {ex}\n{traceback.format_exc()}"}
            self.root.after(0, lambda: self._on_complete(r, cn))

        threading.Thread(target=_run, daemon=True).start()

    def _disable_buttons(self):
        self._run_btn.configure(state=tk.DISABLED)
        self._test_btn.configure(state=tk.DISABLED)
        self._scan_btn.configure(state=tk.DISABLED)

    def _enable_buttons(self):
        self._run_btn.configure(state=tk.NORMAL)
        self._test_btn.configure(state=tk.NORMAL)
        self._scan_btn.configure(state=tk.NORMAL)

    # ---- 回调 ----
    def _on_prog(self, msg: str, pct: int):
        self.root.after(0, lambda: (self._prog_var.set(msg), self._prog_bar.configure(value=pct)))

    def _on_log(self, msg: str):
        write_analysis_log(msg)
        self.root.after(0, lambda: self._log(msg))

    def _on_step(self, step_name: str, status: str, full: dict, dur_ms: int):
        write_analysis_log(f"\n[STEP] {step_name} -> {status} ({dur_ms}ms)")
        if isinstance(full, dict):
            for k, v in full.items():
                sv = json.dumps(v, ensure_ascii=False)[:500] if isinstance(v, (dict, list)) else str(v)[:500]
                write_analysis_log(f"  {k}: {sv}")
        else:
            write_analysis_log(f"  {str(full)[:500]}")
        if status == "error":
            write_analysis_log(f"  <<< 步骤失败 >>>")
        write_analysis_log("-" * 40)

        def _update():
            s = f"\n{'='*50}\n  [{step_name}] {status}  {dur_ms}ms\n{'='*50}\n"
            if isinstance(full, dict):
                for k, v in full.items():
                    sv = json.dumps(v, ensure_ascii=False)[:500] if isinstance(v, (dict, list)) else str(v)[:500]
                    s += f"\n  {k}:\n  {sv}\n"
            else:
                s += f"\n  {str(full)[:500]}\n"
            self._trace_append(s)
        self.root.after(0, _update)

    def _on_complete(self, r: dict, char_name: str):
        self._running = False
        self._enable_buttons()
        self._prog_bar["value"] = 100

        if r.get("success"):
            self._prog_var.set("完成 ✅")
            self._overseer_json = r.get("overseer_json", "")
            self._report_text = r.get("report", "")
            self._scores = r
            self._update_score_display(r)
            self._log(f"  ✅ 分析完成")
            self._export_btn.configure(state=tk.NORMAL)
            self._save_btn.configure(state=tk.NORMAL)

            # 保存历史
            try:
                save_history(char_name, r, self._report_text, self._overseer_json,
                             self._front_path.get(), self._back_path.get())
                self._refresh_history()
                self._nb.select(self._tab_run)
            except Exception as e:
                log_error(f"保存历史失败: {e}")
        else:
            self._prog_var.set("失败 ❌")
            self._log(f"  ❌ 失败: {r.get('error', '未知')}")
            self._overseer_json = r.get("overseer_json", "")
            if self._overseer_json:
                self._export_btn.configure(state=tk.NORMAL)
            # 错误显示在分析结果区
            self._score_text.configure(state=tk.NORMAL)
            self._score_text.delete("1.0", tk.END)
            self._score_text.insert("1.0", f"\u274c 分析失败\n\n{r.get('error', '未知')}")
            self._score_text.configure(state=tk.DISABLED)

    # ---- UI 工具 ----
    def _log(self, msg: str):
        self._log_text.configure(state=tk.NORMAL)
        self._log_text.insert(tk.END, msg + "\n")
        self._log_text.see(tk.END)
        self._log_text.configure(state=tk.DISABLED)

    def _clear_log(self):
        self._log_text.configure(state=tk.NORMAL)
        self._log_text.delete("1.0", tk.END)
        self._log_text.configure(state=tk.DISABLED)

    def _open_log_folder(self):
        p = os.path.join(utils_exe_dir(), LOG_DIR)
        if os.path.isdir(p):
            os.startfile(p)
        else:
            messagebox.showinfo("", f"日志目录未创建: {p}")

    def _open_drop_folder(self, target='front'):
        base = os.path.join(utils_exe_dir(), "dropbox")
        fd = os.path.join(base, "前段")
        bd = os.path.join(base, "后段")
        os.makedirs(fd, exist_ok=True)
        os.makedirs(bd, exist_ok=True)
        sub = fd if target == 'front' else bd
        label = "前段" if target == 'front' else "后段"
        for f in sorted(os.listdir(sub)):
            if f.endswith('.txt'):
                self._assign_drop_file(os.path.join(sub, f), target)
        os.startfile(sub)
        self._prog_var.set(f"\U0001f4c2 {label}文件夹已打开，拖入 .txt 自动加载")
        self._start_drop_watcher()

    def _start_drop_watcher(self):
        if self._drop_watcher_running:
            return
        self._drop_watcher_running = True
        base = os.path.join(utils_exe_dir(), "dropbox")
        fd = os.path.join(base, "前段")
        bd = os.path.join(base, "后段")
        os.makedirs(fd, exist_ok=True)
        os.makedirs(bd, exist_ok=True)
        sf = set(os.listdir(fd))
        sb = set(os.listdir(bd))

        def _watch():
            while self._drop_watcher_running:
                _time.sleep(2)
                try:
                    nf = set(os.listdir(fd))
                    for f in sorted(nf - sf):
                        if f.endswith('.txt'):
                            self.root.after(0, lambda p=os.path.join(fd,f): self._assign_drop_file(p, 'front'))
                    sf.update(nf)
                    nb = set(os.listdir(bd))
                    for f in sorted(nb - sb):
                        if f.endswith('.txt'):
                            self.root.after(0, lambda p=os.path.join(bd,f): self._assign_drop_file(p, 'back'))
                    sb.update(nb)
                except:
                    pass

        threading.Thread(target=_watch, daemon=True).start()

    def _assign_drop_file(self, fp: str, target: str = 'front'):
        if not os.path.exists(fp):
            return
        name = os.path.basename(fp)
        if target == 'front':
            self._front_path.set(fp)
            self._update_drop_text(self._front_drop, fp, '前段')
            self._prog_var.set(f"✅ 已加载前段: {name}")
        else:
            self._back_path.set(fp)
            self._update_drop_text(self._back_drop, fp, '后段')
            self._prog_var.set(f"✅ 已加载后段: {name}")

    def _clear_score(self):
        self._score_text.configure(state=tk.NORMAL)
        self._score_text.delete("1.0", tk.END)
        self._score_text.configure(state=tk.DISABLED)

    def _update_score_display(self, r: dict):
        self._score_text.configure(state=tk.NORMAL)
        self._score_text.delete("1.0", tk.END)
        report = r.get('report', '')
        if report:
            self._score_text.insert("1.0", report)
        else:
            s = (f"变化指数：{r.get('change_index', '?')}\n"
                 f"可预测性：{r.get('predictability_score', '?')}\n"
                 f"合理性：  {r.get('rationality_score', '?')}\n"
                 f"变化性质：{r.get('change_nature', '?')}\n"
                 f"变化方向：{r.get('change_direction', '?')}\n"
                 f"裁判判断：{r.get('overall_verdict', '?')}")
            self._score_text.insert("1.0", s)
        self._score_text.configure(state=tk.DISABLED)

    def _trace_append(self, text: str):
        self._trace_text.configure(state=tk.NORMAL)
        self._trace_text.insert(tk.END, text)
        self._trace_text.see(tk.END)
        self._trace_text.configure(state=tk.DISABLED)

    def _clear_trace(self):
        self._trace_text.configure(state=tk.NORMAL)
        self._trace_text.delete("1.0", tk.END)
        self._trace_text.configure(state=tk.DISABLED)

    # ---- 导出/保存 ----
    def _save_report(self):
        if not self._report_text:
            return
        p = filedialog.asksaveasfilename(defaultextension=".txt",
                                          filetypes=[("txt","*.txt")])
        if p:
            try:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(self._report_text)
                messagebox.showinfo("", f"已保存: {p}")
            except Exception as e:
                messagebox.showerror("", str(e))

    def _export_overseer(self):
        if not self._overseer_json:
            return
        p = filedialog.asksaveasfilename(defaultextension=".json",
                                          filetypes=[("json","*.json")])
        if not p:
            return
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write(self._overseer_json)
            messagebox.showinfo("", f"已导出: {p}")
        except Exception as e:
            messagebox.showerror("", str(e))

    # ---- 历史 ----
    def _refresh_history(self):
        self._hist_list.delete(0, tk.END)
        self._hist_data = list_history()
        for h in self._hist_data:
            label = f"{h.get('time','')}  {h.get('character','?')}  变化:{h.get('change_index','?')}"
            self._hist_list.insert(tk.END, label)

    def _on_hist_select(self, evt):
        sel = self._hist_list.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self._hist_data):
            return
        h = self._hist_data[idx]
        folder = h.get("folder", "")
        import __main__
        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        from utils import HISTORY_DIR
        hist_dir = os.path.join(exe_dir, HISTORY_DIR, folder)
        report_path = os.path.join(hist_dir, "report.txt")
        ovr_path = os.path.join(hist_dir, "overseer.json")
        self._hist_detail.configure(state=tk.NORMAL)
        self._hist_detail.delete("1.0", tk.END)
        detail = f"角色: {h.get('character','?')}\n时间: {h.get('time','?')}\n"
        detail += f"\n变化指数: {h.get('change_index','?')}  可预测性: {h.get('predictability','?')}  合理性: {h.get('rationality','?')}"
        detail += f"\n变化性质: {h.get('change_nature','?')}"
        detail += f"\n变化方向: {h.get('change_direction','?')}\n"
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                detail += f"\n--- 分析报告摘录 ---\n{f.read()[:500]}...\n"
        detail += f"\n文件: {folder}/"
        self._hist_detail.insert("1.0", detail)
        self._hist_detail.configure(state=tk.DISABLED)

    def _delete_history(self):
        sel = self._hist_list.curselection()
        if not sel:
            return
        h = self._hist_data[sel[0]]
        if not messagebox.askyesno("确认", f"删除 {h.get('folder','')} ？"):
            return
        import __main__
        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        from utils import HISTORY_DIR
        folder = os.path.join(exe_dir, HISTORY_DIR, h.get("folder", ""))
        try:
            shutil.rmtree(folder, ignore_errors=True)
            self._refresh_history()
            self._hist_detail.configure(state=tk.NORMAL)
            self._hist_detail.delete("1.0", tk.END)
            self._hist_detail.configure(state=tk.DISABLED)
        except Exception as e:
            messagebox.showerror("", f"删除失败: {e}")

    def run(self):
        self.root.mainloop()


def main():
    app = App()
    app.run()


if __name__ == "__main__":
    main()
