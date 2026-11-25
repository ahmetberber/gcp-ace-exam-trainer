"""Tkinter masaüstü arayüzü."""
from __future__ import annotations

import json
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, ttk

from . import __version__, ai
from .engine import PASS_PERCENT, QuizSession, build_session
from .exams import EXAMS
from .store import QuestionBank, Settings, Stats

APP_TITLE = "GCP ACE Exam Trainer — Associate Cloud Engineer Sınav Pratiği"
ALL = "Tümü"
MODES = {"Pratik (anında geri bildirim)": "pratik", "Sınav simülasyonu (süreli)": "sinav"}
FOCUS = {"Akıllı karışık (zayıflara öncelik)": "karisik",
         "Yalnızca yanlış yaptıklarım": "zayif",
         "Yalnızca hiç görmediklerim": "yeni"}
SOURCES = {"Tüm sorular": None, "Hazır sorular": ["builtin"],
           "AI ile üretilenler": ["ai"], "İçe aktarılanlar": ["ice-aktarim"]}
SOURCE_LABEL = {"builtin": "Hazır", "ai": "AI", "ice-aktarim": "İçe aktarım"}

GREEN, RED, AMBER = "#1e8e3e", "#d93025", "#f9ab00"
GREEN_BG, RED_BG = "#e6f4ea", "#fce8e6"


def fmt_time(sec: int) -> str:
    h, rem = divmod(max(0, int(sec)), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1100x760")
        self.minsize(880, 600)
        self.settings = Settings()
        self.bank = QuestionBank()
        self.stats = Stats()
        self._setup_style()
        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)
        self.screen = None
        self.show_home()

    def _setup_style(self):
        style = ttk.Style(self)
        if sys.platform not in ("win32", "darwin"):
            style.theme_use("clam")
        base = tkfont.nametofont("TkDefaultFont")
        base.configure(size=11)
        tkfont.nametofont("TkTextFont").configure(size=11)
        fam = base.actual("family")
        self.f_title = (fam, 18, "bold")
        self.f_h2 = (fam, 13, "bold")
        self.f_q = (fam, 13)
        self.f_opt = (fam, 12)
        self.f_small = (fam, 10)
        style.configure("Title.TLabel", font=self.f_title)
        style.configure("H2.TLabel", font=self.f_h2)
        style.configure("Muted.TLabel", foreground="#5f6368")
        style.configure("Big.TButton", font=(fam, 12, "bold"), padding=(14, 8))
        style.configure("Treeview", rowheight=26)

    def switch(self, frame_cls, *args):
        if self.screen is not None:
            self.screen.destroy()
        self.screen = frame_cls(self.container, self, *args)
        self.screen.pack(fill="both", expand=True)

    def show_home(self):
        self.switch(HomeScreen)

    def start_session(self, session: QuizSession):
        self.switch(QuizScreen, session)

    def show_results(self, session: QuizSession, summary: dict):
        self.switch(ResultScreen, session, summary)

    def run_bg(self, work, on_done, on_error, progress=None):
        """work(progress_cb) işini arka planda çalıştırır; sonuçları ana thread'e taşır."""
        q: queue.Queue = queue.Queue()

        def runner():
            try:
                res = work(lambda m: q.put(("progress", m)))
                q.put(("done", res))
            except Exception as e:  # noqa: BLE001 - kullanıcıya gösterilecek
                q.put(("error", e))

        threading.Thread(target=runner, daemon=True).start()

        def poll():
            try:
                while True:
                    kind, val = q.get_nowait()
                    if kind == "progress":
                        if progress:
                            progress(val)
                    elif kind == "done":
                        on_done(val)
                        return
                    else:
                        on_error(val)
                        return
            except queue.Empty:
                pass
            self.after(150, poll)

        self.after(150, poll)


# ----------------------------------------------------------------------------- Ana ekran
class HomeScreen(ttk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent, padding=20)
        self.app = app
        exam_code = app.settings["last_exam"] if app.settings["last_exam"] in EXAMS else "ACE"

        head = ttk.Frame(self)
        head.pack(fill="x")
        titles = ttk.Frame(head)
        titles.pack(side="left")
        ttk.Label(titles, text="GCP ACE Exam Trainer", style="Title.TLabel").pack(anchor="w")
        ttk.Label(titles, text=f"Associate Cloud Engineer sınav pratiği • v{__version__}",
                  style="Muted.TLabel").pack(anchor="w")
        for txt, cmd in (("Ayarlar", self.open_settings), ("JSON içe aktar", self.import_json),
                         ("Soru bankası", self.open_bank)):
            ttk.Button(head, text=txt, command=cmd).pack(side="right", padx=4)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=(16, 0))
        body.columnconfigure(0, weight=3, uniform="c")
        body.columnconfigure(1, weight=2, uniform="c")
        body.rowconfigure(0, weight=1)

        # --- Sol: oturum kurulumu
        left = ttk.LabelFrame(body, text="Yeni oturum", padding=14)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.columnconfigure(1, weight=1)

        self.v_exam = tk.StringVar(value=self._exam_label(exam_code))
        self.v_mode = tk.StringVar(value=list(MODES)[0])
        self.v_count = tk.IntVar(value=20)
        self.v_domain = tk.StringVar(value=ALL)
        self.v_topic = tk.StringVar(value=ALL)
        self.v_focus = tk.StringVar(value=list(FOCUS)[0])
        self.v_source = tk.StringVar(value=list(SOURCES)[0])
        self.v_timed = tk.BooleanVar(value=False)

        r = 0

        def row(label, widget):
            nonlocal r
            ttk.Label(left, text=label).grid(row=r, column=0, sticky="w", pady=5, padx=(0, 10))
            widget.grid(row=r, column=1, sticky="ew", pady=5)
            r += 1

        self.cb_exam = ttk.Combobox(left, textvariable=self.v_exam, state="readonly",
                                    values=[self._exam_label(c) for c in EXAMS])
        self.cb_exam.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        row("Sınav", self.cb_exam)
        row("Mod", ttk.Combobox(left, textvariable=self.v_mode, state="readonly", values=list(MODES)))
        cnt = ttk.Frame(left)
        ttk.Spinbox(cnt, from_=5, to=200, increment=5, textvariable=self.v_count, width=6).pack(side="left")
        for n in (10, 20, 50):
            ttk.Button(cnt, text=str(n), width=4, command=lambda n=n: self.v_count.set(n)).pack(side="left", padx=2)
        ttk.Checkbutton(cnt, text="Pratikte de süre tut", variable=self.v_timed).pack(side="left", padx=10)
        row("Soru sayısı", cnt)
        self.cb_domain = ttk.Combobox(left, textvariable=self.v_domain, state="readonly")
        row("Alan (domain)", self.cb_domain)
        self.cb_topic = ttk.Combobox(left, textvariable=self.v_topic, state="readonly")
        row("Konu", self.cb_topic)
        row("Odak", ttk.Combobox(left, textvariable=self.v_focus, state="readonly", values=list(FOCUS)))
        row("Kaynak", ttk.Combobox(left, textvariable=self.v_source, state="readonly", values=list(SOURCES)))

        self.lbl_bank = ttk.Label(left, style="Muted.TLabel", wraplength=520, justify="left")
        self.lbl_bank.grid(row=r, column=0, columnspan=2, sticky="w", pady=(10, 4))
        r += 1
        btns = ttk.Frame(left)
        btns.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        ttk.Button(btns, text="▶  Başla", style="Big.TButton", command=self.start).pack(side="left")
        ttk.Button(btns, text="✨ AI ile güncel soru üret", style="Big.TButton",
                   command=self.open_generate).pack(side="left", padx=10)
        r += 1
        tip = ("İpucu: Pratik modunda 1-5 tuşlarıyla seçenek seçip Enter ile kontrol edebilir, "
               "← → ile sorular arasında gezebilirsiniz.")
        ttk.Label(left, text=tip, style="Muted.TLabel", wraplength=520, justify="left").grid(
            row=r, column=0, columnspan=2, sticky="w", pady=(16, 0))

        # --- Sağ: ilerleme
        right = ttk.LabelFrame(body, text="İlerlemeniz", padding=14)
        right.grid(row=0, column=1, sticky="nsew")
        self.lbl_overall = ttk.Label(right, font=self.app.f_h2, justify="left")
        self.lbl_overall.pack(anchor="w")
        ttk.Label(right, text="Alan bazında başarı", style="Muted.TLabel").pack(anchor="w", pady=(12, 2))
        self.dom_frame = ttk.Frame(right)
        self.dom_frame.pack(fill="x")
        ttk.Label(right, text="Son oturumlar", style="Muted.TLabel").pack(anchor="w", pady=(14, 2))
        self.tv_hist = ttk.Treeview(right, columns=("t", "m", "s"), show="headings", height=8)
        for c, t, w in (("t", "Tarih", 130), ("m", "Mod", 70), ("s", "Puan", 90)):
            self.tv_hist.heading(c, text=t)
            self.tv_hist.column(c, width=w, anchor="w")
        self.tv_hist.pack(fill="both", expand=True)

        if app.bank.load_errors:
            messagebox.showwarning("Soru bankası", "Bazı sorular yüklenemedi:\n" +
                                   "\n".join(app.bank.load_errors[:10]))
        self.refresh()

    # yardımcılar
    @staticmethod
    def _exam_label(code):
        e = EXAMS[code]
        return f"{e.code} — {e.name}"

    def exam_code(self):
        return self.v_exam.get().split(" — ")[0]

    def refresh(self):
        code = self.exam_code()
        exam = EXAMS[code]
        self.app.settings["last_exam"] = code
        self.app.settings.save()
        self.cb_domain["values"] = [ALL] + [f"{k}. {v[0]}" for k, v in exam.domains.items()]
        if self.v_domain.get() not in self.cb_domain["values"]:
            self.v_domain.set(ALL)
        topics = sorted({q["topic"] for q in self.app.bank.for_exam(code) if q["topic"]})
        self.cb_topic["values"] = [ALL] + topics
        if self.v_topic.get() not in self.cb_topic["values"]:
            self.v_topic.set(ALL)
        c = self.app.bank.count(code)
        qs = self.app.bank.for_exam(code)
        seen = sum(1 for q in qs if self.app.stats.get(q["id"])["seen"])
        weak = len(self.app.stats.weak_ids(q["id"] for q in qs))
        if c["toplam"]:
            txt = (f"Bankada {c['toplam']} soru var ({c['hazir']} hazır, {c['eklenen']} eklenen). "
                   f"Gördüğünüz: {seen} • Tekrar etmeniz gereken: {weak}. "
                   f"Gerçek sınav: ~{exam.question_count} soru / {exam.minutes} dk.")
        else:
            txt = (f"{exam.code} için henüz soru yok. '✨ AI ile güncel soru üret' ile soru "
                   f"üretebilir veya JSON içe aktarabilirsiniz.")
        self.lbl_bank["text"] = txt

        # ilerleme paneli
        tot = sum(self.app.stats.get(q["id"])["seen"] for q in qs)
        cor = sum(self.app.stats.get(q["id"])["correct"] for q in qs)
        acc = f"%{round(100 * cor / tot)}" if tot else "—"
        self.lbl_overall["text"] = f"{tot} cevap • Başarı {acc}"
        for w in self.dom_frame.winfo_children():
            w.destroy()
        for k, (name, _w) in exam.domains.items():
            dq = [q for q in qs if q["domain"] == k]
            t = sum(self.app.stats.get(q["id"])["seen"] for q in dq)
            cc = sum(self.app.stats.get(q["id"])["correct"] for q in dq)
            pct = round(100 * cc / t) if t else 0
            fr = ttk.Frame(self.dom_frame)
            fr.pack(fill="x", pady=2)
            ttk.Label(fr, text=f"{k}. {name}", wraplength=260, justify="left").pack(anchor="w")
            bar = ttk.Frame(fr)
            bar.pack(fill="x")
            pb = ttk.Progressbar(bar, maximum=100, value=pct)
            pb.pack(side="left", fill="x", expand=True)
            ttk.Label(bar, text=f"%{pct} ({t})" if t else "—", width=10).pack(side="left", padx=4)
        self.tv_hist.delete(*self.tv_hist.get_children())
        for s in reversed([s for s in self.app.stats.sessions if s["exam"] == code][-30:]):
            mark = "✓" if s["passed"] else "✗"
            self.tv_hist.insert("", "end", values=(s["date"], s["mode"],
                                                   f"{mark} %{s['percent']} ({s['correct']}/{s['total']})"))

    def start(self):
        code = self.exam_code()
        dom = self.v_domain.get()
        domains = None if dom == ALL else [int(dom.split(".")[0])]
        topics = None if self.v_topic.get() == ALL else [self.v_topic.get()]
        mode = MODES[self.v_mode.get()]
        try:
            n = max(1, int(self.v_count.get()))
        except (tk.TclError, ValueError):
            n = 20
        try:
            sess = build_session(self.app.bank, self.app.stats, code, n, mode, domains,
                                 FOCUS[self.v_focus.get()], SOURCES[self.v_source.get()],
                                 timed=True if self.v_timed.get() or mode == "sinav" else False,
                                 topics=topics)
        except ValueError as e:
            messagebox.showinfo("Soru yok", str(e))
            return
        self.app.start_session(sess)

    def open_settings(self):
        SettingsDialog(self.app, on_close=self.refresh)

    def open_bank(self):
        BankWindow(self.app, self.exam_code(), on_close=self.refresh)

    def open_generate(self):
        GenerateDialog(self.app, self.exam_code(), on_close=self.refresh)

    def import_json(self):
        path = filedialog.askopenfilename(title="Soru dosyası seç", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            messagebox.showerror("İçe aktarma", f"Dosya okunamadı:\n{e}")
            return
        if isinstance(data, dict):
            data = data.get("questions", [])
        if not isinstance(data, list):
            messagebox.showerror("İçe aktarma", "Dosya bir soru listesi içermeli.")
            return
        added, errors = self.app.bank.add_user_questions(data, self.exam_code())
        msg = f"{added} soru eklendi."
        if errors:
            msg += f"\n{len(errors)} soru atlandı:\n" + "\n".join(errors[:12])
        messagebox.showinfo("İçe aktarma", msg)
        self.refresh()


# ----------------------------------------------------------------------------- Soru ekranı
class QuizScreen(ttk.Frame):
    def __init__(self, parent, app: App, session: QuizSession):
        super().__init__(parent, padding=(20, 14))
        self.app, self.s = app, session
        self.idx = 0
        self.checked: set[int] = set()  # pratik modunda kontrol edilen sorular
        self.exam = EXAMS[session.exam_code]

        top = ttk.Frame(self)
        top.pack(fill="x")
        self.lbl_pos = ttk.Label(top, style="H2.TLabel")
        self.lbl_pos.pack(side="left")
        self.lbl_timer = ttk.Label(top, style="H2.TLabel")
        self.lbl_timer.pack(side="right")
        self.lbl_score = ttk.Label(top, style="Muted.TLabel")
        self.lbl_score.pack(side="right", padx=16)
        self.progress = ttk.Progressbar(self, maximum=len(session.items))
        self.progress.pack(fill="x", pady=(6, 4))
        self.lbl_meta = ttk.Label(self, style="Muted.TLabel")
        self.lbl_meta.pack(anchor="w")

        # kaydırılabilir içerik
        mid = ttk.Frame(self)
        mid.pack(fill="both", expand=True, pady=(8, 8))
        self.canvas = tk.Canvas(mid, highlightthickness=0, bg=self._bg())
        sb = ttk.Scrollbar(mid, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=self._bg())
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.canvas.bind("<Configure>", self._on_resize)
        self.bind_all("<MouseWheel>", self._on_wheel)
        self.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-2, "units"))
        self.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(2, "units"))

        self.lbl_q = tk.Label(self.inner, font=app.f_q, justify="left", anchor="w", bg=self._bg())
        self.lbl_q.pack(fill="x", pady=(0, 12))
        self.opt_frame = tk.Frame(self.inner, bg=self._bg())
        self.opt_frame.pack(fill="x")
        self.feedback = tk.Label(self.inner, font=app.f_opt, justify="left", anchor="w",
                                 bg=self._bg(), padx=12, pady=10)
        self.btn_ask = ttk.Button(self.inner, text="🤖 Claude'a sor (ayrıntılı açıklama)", command=self.ask_claude)

        # alt düğmeler
        bot = ttk.Frame(self)
        bot.pack(fill="x")
        ttk.Button(bot, text="⟵ Önceki", command=lambda: self.go(-1)).pack(side="left")
        self.btn_flag = ttk.Button(bot, text="⚑ İşaretle", command=self.toggle_flag)
        self.btn_flag.pack(side="left", padx=6)
        self.btn_nav = ttk.Button(bot, text="☰ Soru listesi", command=self.open_navigator)
        self.btn_nav.pack(side="left")
        ttk.Button(bot, text="Bitir", command=self.finish).pack(side="right")
        self.btn_next = ttk.Button(bot, text="Sonraki ⟶", style="Big.TButton", command=self.primary)
        self.btn_next.pack(side="right", padx=6)

        self.vars: list = []
        self.radio_var = tk.IntVar(value=-1)
        self.opt_widgets: list[tk.Widget] = []

        for k in range(1, 9):
            self.app.bind(str(k), lambda e, k=k: self.key_select(k - 1))
        self.app.bind("<Return>", lambda e: self.primary())
        self.app.bind("<Right>", lambda e: self.go(1))
        self.app.bind("<Left>", lambda e: self.go(-1))
        self.render()
        self.tick()

    def destroy(self):
        for k in list(range(1, 9)):
            self.app.unbind(str(k))
        for seq in ("<Return>", "<Right>", "<Left>"):
            self.app.unbind(seq)
        self.unbind_all("<MouseWheel>")
        self.unbind_all("<Button-4>")
        self.unbind_all("<Button-5>")
        super().destroy()

    def _bg(self):
        return ttk.Style(self).lookup("TFrame", "background") or "#f0f0f0"

    def _on_resize(self, e):
        self.canvas.itemconfigure(self.win, width=e.width)
        wrap = max(300, e.width - 60)
        self.lbl_q.configure(wraplength=wrap)
        self.feedback.configure(wraplength=wrap - 30)
        for w in self.opt_widgets:
            w.configure(wraplength=wrap - 40)

    def _on_wheel(self, e):
        self.canvas.yview_scroll(int(-e.delta / 120) if sys.platform != "darwin" else -e.delta, "units")

    # ---- çizim
    @property
    def practice(self):
        return self.s.mode == "pratik"

    def render(self):
        it = self.s.items[self.idx]
        q = it.q
        n = len(self.s.items)
        self.lbl_pos["text"] = f"Soru {self.idx + 1} / {n}"
        self.progress["value"] = len(self.s.answers)
        meta = f"Alan {q['domain']}: {self.exam.domain_name(q['domain'])}"
        if q.get("topic"):
            meta += f"  •  Konu: {q['topic']}"
        meta += f"  •  Zorluk: {q['difficulty']}  •  Kaynak: {SOURCE_LABEL.get(q['source'], q['source'])}"
        if self.idx in self.s.flagged:
            meta += "  •  ⚑ işaretli"
        self.lbl_meta["text"] = meta
        if self.practice:
            done = [i for i in self.checked]
            ok = sum(self.s.is_correct(i) for i in done)
            self.lbl_score["text"] = f"Doğru: {ok} / {len(done)}"
        else:
            self.lbl_score["text"] = f"Cevaplanan: {len(self.s.answers)} / {n} • İşaretli: {len(self.s.flagged)}"

        text = q["question"]
        low = text.lower()
        if it.multi and "seçin" not in low and "choose" not in low and "select" not in low:
            text += f"\n\n({len(q['correct'])} seçenek seçin)"
        self.lbl_q["text"] = text

        for w in self.opt_frame.winfo_children():
            w.destroy()
        self.opt_widgets = []
        prev = self.s.answers.get(self.idx, set())
        wrap = max(300, self.canvas.winfo_width() - 100)
        locked = self.practice and self.idx in self.checked
        if it.multi:
            self.vars = [tk.BooleanVar(value=(i in prev)) for i in range(len(it.options))]
        else:
            self.radio_var = tk.IntVar(value=next(iter(prev)) if prev else -1)
        for i, opt in enumerate(it.options):
            label = f"{chr(65 + i)}.  {opt}"
            common = dict(text=label, font=self.app.f_opt, justify="left", anchor="w",
                          wraplength=wrap, padx=8, pady=8, bg=self._bg(), activebackground=self._bg(),
                          highlightthickness=0, bd=0, command=self.on_select)
            if it.multi:
                w = tk.Checkbutton(self.opt_frame, variable=self.vars[i], **common)
            else:
                w = tk.Radiobutton(self.opt_frame, variable=self.radio_var, value=i, **common)
            if locked:
                w.configure(state="disabled", disabledforeground="#202124")
            w.pack(fill="x", anchor="w", pady=2)
            self.opt_widgets.append(w)

        self.feedback.pack_forget()
        self.btn_ask.pack_forget()
        if locked:
            self.show_feedback()
        self.btn_flag["text"] = "⚑ İşareti kaldır" if self.idx in self.s.flagged else "⚑ İşaretle"
        self._update_primary()
        self.canvas.yview_moveto(0)

    def _update_primary(self):
        last = self.idx == len(self.s.items) - 1
        if self.practice and self.idx not in self.checked:
            self.btn_next["text"] = "Kontrol et ✓"
        elif last:
            self.btn_next["text"] = "Bitir ⏹"
        else:
            self.btn_next["text"] = "Sonraki ⟶"

    def selection(self) -> set[int]:
        it = self.s.items[self.idx]
        if it.multi:
            return {i for i, v in enumerate(self.vars) if v.get()}
        v = self.radio_var.get()
        return {v} if v >= 0 else set()

    def on_select(self):
        if self.practice and self.idx in self.checked:
            return
        sel = self.selection()
        if sel:
            self.s.answers[self.idx] = sel
        else:
            self.s.answers.pop(self.idx, None)
        self.progress["value"] = len(self.s.answers)
        if not self.practice:
            n = len(self.s.items)
            self.lbl_score["text"] = f"Cevaplanan: {len(self.s.answers)} / {n} • İşaretli: {len(self.s.flagged)}"

    def key_select(self, i):
        it = self.s.items[self.idx]
        if i >= len(it.options) or (self.practice and self.idx in self.checked):
            return
        if it.multi:
            self.vars[i].set(not self.vars[i].get())
        else:
            self.radio_var.set(i)
        self.on_select()

    def primary(self):
        if self.practice and self.idx not in self.checked:
            self.check()
        elif self.idx == len(self.s.items) - 1:
            self.finish()
        else:
            self.go(1)

    def check(self):
        sel = self.selection()
        it = self.s.items[self.idx]
        if not sel:
            messagebox.showinfo("Cevap", "Lütfen bir seçenek seçin.")
            return
        if it.multi and len(sel) != len(it.correct):
            if not messagebox.askyesno("Cevap", f"Bu soru {len(it.correct)} seçenek istiyor; "
                                                f"siz {len(sel)} seçtiniz. Yine de kontrol edilsin mi?"):
                return
        self.s.answer(self.idx, sel)
        self.checked.add(self.idx)
        self.render()

    def show_feedback(self):
        it = self.s.items[self.idx]
        sel = self.s.answers.get(self.idx, set())
        for i, w in enumerate(self.opt_widgets):
            if i in it.correct:
                w.configure(bg=GREEN_BG, disabledforeground=GREEN)
            elif i in sel:
                w.configure(bg=RED_BG, disabledforeground=RED)
        ok = self.s.is_correct(self.idx)
        right = ", ".join(chr(65 + i) for i in sorted(it.correct))
        head = "✓ Doğru!" if ok else f"✗ Yanlış. Doğru cevap: {right}"
        body = it.q["explanation"] or "(Açıklama yok)"
        if it.q.get("source_url"):
            body += f"\n\nKaynak: {it.q['source_url']}"
        self.feedback.configure(text=f"{head}\n\n{body}", bg=GREEN_BG if ok else RED_BG,
                                fg="#202124")
        self.feedback.pack(fill="x", pady=(14, 6))
        self.btn_ask.pack(anchor="w", pady=(0, 10))

    def go(self, d):
        new = self.idx + d
        if 0 <= new < len(self.s.items):
            self.idx = new
            self.render()

    def toggle_flag(self):
        self.s.flagged.symmetric_difference_update({self.idx})
        self.render()

    def open_navigator(self):
        win = tk.Toplevel(self)
        win.title("Soru listesi")
        win.transient(self.app)
        ttk.Label(win, text="Bir soruya gitmek için tıklayın.  ● cevaplandı  ⚑ işaretli",
                  padding=8).pack()
        grid = ttk.Frame(win, padding=8)
        grid.pack()
        for i in range(len(self.s.items)):
            mark = ""
            if self.practice and i in self.checked:
                mark = "✓" if self.s.is_correct(i) else "✗"
            elif i in self.s.answers:
                mark = "●"
            if i in self.s.flagged:
                mark += "⚑"
            b = ttk.Button(grid, text=f"{i + 1} {mark}", width=6,
                           command=lambda i=i: (setattr(self, "idx", i), self.render(), win.destroy()))
            b.grid(row=i // 10, column=i % 10, padx=2, pady=2)

    def tick(self):
        if not self.winfo_exists():
            return
        rem = self.s.remaining()
        if rem is None:
            self.lbl_timer["text"] = "⏱ " + fmt_time(int(__import__("time").time() - self.s.started))
        else:
            self.lbl_timer["text"] = "⏳ " + fmt_time(rem)
            self.lbl_timer.configure(foreground=RED if rem < 300 else "")
            if rem == 0:
                messagebox.showinfo("Süre doldu", "Süre doldu! Sonuçlar gösteriliyor.")
                self.finish(force=True)
                return
        self.after(1000, self.tick)

    def finish(self, force=False):
        if not force:
            unanswered = len(self.s.items) - len(self.s.answers)
            if self.practice:
                unanswered = len(self.s.items) - len(self.checked)
            msg = "Oturumu bitirmek istiyor musunuz?"
            if unanswered:
                msg = f"{unanswered} soru cevaplanmadı. Yine de bitirilsin mi?"
            if not messagebox.askyesno("Bitir", msg):
                return
        if self.practice:
            # pratikte yalnızca kontrol edilen cevaplar sayılır
            for i in list(self.s.answers):
                if i not in self.checked:
                    self.s.answers.pop(i)
        summary = self.s.finish(self.app.stats)
        self.app.show_results(self.s, summary)

    def ask_claude(self):
        it = self.s.items[self.idx]
        chosen = [it.options[i] for i in sorted(self.s.answers.get(self.idx, set()))]
        ExplainWindow(self.app, it.q, chosen)


# ----------------------------------------------------------------------------- Sonuç ekranı
class ResultScreen(ttk.Frame):
    def __init__(self, parent, app: App, session: QuizSession, summary: dict):
        super().__init__(parent, padding=20)
        self.app, self.s, self.sum = app, session, summary
        ok = summary["passed"]
        ttk.Label(self, text="Sonuçlar", style="Title.TLabel").pack(anchor="w")
        color = GREEN if ok else RED
        verdict = "GEÇTİNİZ 🎉" if ok else "Hedefin altında"
        tk.Label(self, text=f"%{summary['percent']}  —  {verdict}", font=(app.f_title[0], 26, "bold"),
                 fg=color, bg=ttk.Style(self).lookup("TFrame", "background")).pack(anchor="w", pady=(6, 0))
        ttk.Label(self, text=(f"{summary['correct']} / {summary['total']} doğru • "
                              f"Süre {fmt_time(summary['seconds'])} • Hedef: %{PASS_PERCENT} "
                              "(Google resmi geçme notunu açıklamaz; %70+ güvenli kabul edilir)"),
                  style="Muted.TLabel").pack(anchor="w", pady=(2, 12))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=2, uniform="r")
        body.columnconfigure(1, weight=3, uniform="r")
        body.rowconfigure(0, weight=1)

        dom = ttk.LabelFrame(body, text="Alan bazında", padding=10)
        dom.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        for name, (c, t) in summary["domains"].items():
            pct = round(100 * c / t) if t else 0
            ttk.Label(dom, text=name, wraplength=320, justify="left").pack(anchor="w", pady=(6, 0))
            fr = ttk.Frame(dom)
            fr.pack(fill="x")
            ttk.Progressbar(fr, maximum=100, value=pct).pack(side="left", fill="x", expand=True)
            ttk.Label(fr, text=f"{c}/{t}  %{pct}", width=11).pack(side="left", padx=4)

        lst = ttk.LabelFrame(body, text="Sorular (incelemek için çift tıklayın)", padding=10)
        lst.grid(row=0, column=1, sticky="nsew")
        self.tv = ttk.Treeview(lst, columns=("n", "r", "q"), show="headings")
        for c, t, w, st in (("n", "#", 40, False), ("r", "Sonuç", 70, False), ("q", "Soru", 500, True)):
            self.tv.heading(c, text=t)
            self.tv.column(c, width=w, stretch=st, anchor="w")
        sb = ttk.Scrollbar(lst, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        self.tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tv.tag_configure("ok", foreground=GREEN)
        self.tv.tag_configure("bad", foreground=RED)
        self.tv.tag_configure("skip", foreground="#80868b")
        for i, it in enumerate(session.items):
            if i not in session.answers:
                r, tag = "— boş", "skip"
            elif session.is_correct(i):
                r, tag = "✓", "ok"
            else:
                r, tag = "✗", "bad"
            self.tv.insert("", "end", iid=str(i), values=(i + 1, r, it.q["question"][:140]), tags=(tag,))
        self.tv.bind("<Double-1>", self.review)

        bot = ttk.Frame(self)
        bot.pack(fill="x", pady=(12, 0))
        ttk.Button(bot, text="⌂ Ana sayfa", style="Big.TButton", command=app.show_home).pack(side="left")
        wrong = [i for i in range(len(session.items)) if not session.is_correct(i)]
        b = ttk.Button(bot, text=f"↻ Yanlış/boş soruları tekrar çöz ({len(wrong)})", style="Big.TButton",
                       command=lambda: self.retry(wrong))
        b.pack(side="left", padx=10)
        if not wrong:
            b.state(["disabled"])

    def review(self, _e=None):
        sel = self.tv.selection()
        if sel:
            ReviewWindow(self.app, self.s, int(sel[0]))

    def retry(self, idxs):
        import random
        from .engine import Item
        items = []
        for i in idxs:
            q = self.s.items[i].q
            order = list(range(len(q["options"])))
            random.shuffle(order)
            items.append(Item(q, order))
        random.shuffle(items)
        self.app.start_session(QuizSession(self.s.exam_code, "pratik", items))


class ReviewWindow(tk.Toplevel):
    def __init__(self, app: App, session: QuizSession, idx: int):
        super().__init__(app)
        self.app = app
        self.title(f"Soru {idx + 1} — inceleme")
        self.geometry("820x620")
        it = session.items[idx]
        sel = session.answers.get(idx, set())
        txt = tk.Text(self, wrap="word", font=app.f_opt, padx=14, pady=12, relief="flat")
        txt.pack(fill="both", expand=True)
        txt.tag_configure("q", font=app.f_q, spacing3=10)
        txt.tag_configure("ok", foreground=GREEN, background=GREEN_BG)
        txt.tag_configure("bad", foreground=RED, background=RED_BG)
        txt.tag_configure("h", font=app.f_h2, spacing1=12)
        txt.insert("end", it.q["question"] + "\n", "q")
        for i, o in enumerate(it.options):
            tag = "ok" if i in it.correct else ("bad" if i in sel else "")
            mark = "  ← sizin cevabınız" if i in sel else ""
            txt.insert("end", f"{chr(65 + i)}. {o}{mark}\n", tag)
        txt.insert("end", "\nAçıklama\n", "h")
        txt.insert("end", it.q["explanation"] or "(Açıklama yok)")
        if it.q.get("source_url"):
            txt.insert("end", f"\n\nKaynak: {it.q['source_url']}")
        txt.configure(state="disabled")
        bar = ttk.Frame(self, padding=8)
        bar.pack(fill="x")
        ttk.Button(bar, text="🤖 Claude'a sor",
                   command=lambda: ExplainWindow(app, it.q, [it.options[i] for i in sorted(sel)])).pack(side="left")
        ttk.Button(bar, text="Kapat", command=self.destroy).pack(side="right")


# ----------------------------------------------------------------------------- Claude'a sor
class ExplainWindow(tk.Toplevel):
    def __init__(self, app: App, q: dict, chosen: list[str]):
        super().__init__(app)
        self.app, self.q, self.chosen = app, q, chosen
        self.title("Claude'a sor")
        self.geometry("780x600")
        self.txt = tk.Text(self, wrap="word", font=app.f_opt, padx=14, pady=12, relief="flat")
        self.txt.pack(fill="both", expand=True)
        bar = ttk.Frame(self, padding=8)
        bar.pack(fill="x")
        self.entry = ttk.Entry(bar)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda e: self.ask(self.entry.get()))
        self.btn = ttk.Button(bar, text="Ek soru sor", command=lambda: self.ask(self.entry.get()))
        self.btn.pack(side="left", padx=6)
        self.ask("")

    def ask(self, follow_up: str):
        self.btn.state(["disabled"])
        self._append(("\n\n❓ " + follow_up + "\n") if follow_up else "", "")
        self._append("Claude düşünüyor…\n", "")
        self.entry.delete(0, "end")

        def done(text):
            if self.winfo_exists():
                self._append(text + "\n", "")
                self.btn.state(["!disabled"])

        def err(e):
            if self.winfo_exists():
                self._append(f"\nHata: {e}\n", "")
                self.btn.state(["!disabled"])

        self.app.run_bg(lambda p: ai.explain(self.app.settings, self.q, self.chosen, follow_up), done, err)

    def _append(self, s, _tag):
        self.txt.configure(state="normal")
        self.txt.insert("end", s)
        self.txt.see("end")
        self.txt.configure(state="disabled")


# ----------------------------------------------------------------------------- AI soru üretme
class GenerateDialog(tk.Toplevel):
    def __init__(self, app: App, exam_code: str, on_close=None):
        super().__init__(app)
        self.app, self.on_close = app, on_close
        self.title("AI ile güncel soru üret")
        self.geometry("900x640")
        self.transient(app)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.generated: list[dict] = []

        frm = ttk.Frame(self, padding=14)
        frm.pack(fill="x")
        frm.columnconfigure(1, weight=1)
        self.v_exam = tk.StringVar(value=exam_code)
        self.v_n = tk.IntVar(value=10)
        self.v_dom = tk.StringVar(value=ALL)
        self.v_topic = tk.StringVar(value=ALL)
        self.v_diff = tk.StringVar(value="karışık")
        r = 0
        for label, w in (
            ("Sınav", ttk.Combobox(frm, textvariable=self.v_exam, values=list(EXAMS), state="readonly", width=10)),
            ("Soru sayısı", ttk.Spinbox(frm, from_=1, to=25, textvariable=self.v_n, width=6)),
            ("Alan", ttk.Combobox(frm, textvariable=self.v_dom, state="readonly")),
            ("Konu", ttk.Combobox(frm, textvariable=self.v_topic, state="readonly")),
            ("Zorluk", ttk.Combobox(frm, textvariable=self.v_diff, state="readonly",
                                    values=["karışık", "kolay", "orta", "zor"], width=10)),
        ):
            ttk.Label(frm, text=label).grid(row=r, column=0, sticky="w", pady=4, padx=(0, 10))
            w.grid(row=r, column=1, sticky="w" if label in ("Sınav", "Soru sayısı", "Zorluk") else "ew", pady=4)
            if label == "Sınav":
                w.bind("<<ComboboxSelected>>", lambda e: self._fill())
            elif label == "Alan":
                self.cb_dom = w
            elif label == "Konu":
                self.cb_topic = w
            r += 1
        info = (f"Model: {ai.MODELS.get(app.settings['model'], app.settings['model'])} • "
                f"Web araması: {'açık (cloud.google.com)' if app.settings['web_search'] else 'kapalı'} • "
                "Ayarlar'dan değiştirilebilir. 10 soru genellikle 1-3 dakika sürer.")
        ttk.Label(frm, text=info, style="Muted.TLabel", wraplength=820).grid(row=r, column=0, columnspan=2,
                                                                           sticky="w", pady=(6, 0))
        bar = ttk.Frame(self, padding=(14, 0))
        bar.pack(fill="x")
        self.btn_gen = ttk.Button(bar, text="✨ Üret", style="Big.TButton", command=self.generate)
        self.btn_gen.pack(side="left")
        self.pb = ttk.Progressbar(bar, mode="indeterminate", length=180)
        self.pb.pack(side="left", padx=10)
        self.lbl_status = ttk.Label(bar, style="Muted.TLabel")
        self.lbl_status.pack(side="left")

        lst = ttk.LabelFrame(self, text="Önizleme (kaydetmeden önce çift tıklayıp inceleyebilirsiniz)", padding=8)
        lst.pack(fill="both", expand=True, padx=14, pady=10)
        self.tv = ttk.Treeview(lst, columns=("d", "t", "z", "q"), show="headings")
        for c, t, w, st in (("d", "Alan", 50, False), ("t", "Konu", 180, False), ("z", "Zorluk", 60, False),
                            ("q", "Soru", 500, True)):
            self.tv.heading(c, text=t)
            self.tv.column(c, width=w, stretch=st, anchor="w")
        self.tv.pack(fill="both", expand=True)
        self.tv.bind("<Double-1>", self.preview)
        bot = ttk.Frame(self, padding=(14, 0, 14, 12))
        bot.pack(fill="x")
        self.btn_save = ttk.Button(bot, text="💾 Seçilenleri kaydet", command=self.save)
        self.btn_save.pack(side="right")
        self.btn_save.state(["disabled"])
        ttk.Button(bot, text="Seçilenleri çıkar", command=self.remove_selected).pack(side="right", padx=6)
        self._fill()

    def _fill(self):
        exam = EXAMS[self.v_exam.get()]
        self.cb_dom["values"] = [ALL] + [f"{k}. {v[0]}" for k, v in exam.domains.items()]
        self.v_dom.set(ALL)
        self.cb_topic["values"] = [ALL] + list(exam.topics)
        self.v_topic.set(ALL)

    def generate(self):
        code = self.v_exam.get()
        dom = None if self.v_dom.get() == ALL else int(self.v_dom.get().split(".")[0])
        topic = None if self.v_topic.get() == ALL else self.v_topic.get()
        diff = None if self.v_diff.get() == "karışık" else self.v_diff.get()
        try:
            n = max(1, min(25, int(self.v_n.get())))
        except (tk.TclError, ValueError):
            n = 10
        existing = self.app.bank.for_exam(code, [dom] if dom else None)
        self.btn_gen.state(["disabled"])
        self.pb.start(12)

        def work(progress):
            return ai.generate_questions(self.app.settings, code, n, dom, topic, diff, existing, progress)

        def done(qs):
            if not self.winfo_exists():
                return
            self.pb.stop()
            self.btn_gen.state(["!disabled"])
            fresh = [q for q in qs if not self.app.bank.is_duplicate(q)]
            self.generated += fresh
            self._redraw()
            self.lbl_status["text"] = f"{len(fresh)} yeni soru üretildi. İnceleyip kaydedin."

        def err(e):
            if not self.winfo_exists():
                return
            self.pb.stop()
            self.btn_gen.state(["!disabled"])
            self.lbl_status["text"] = "Hata"
            messagebox.showerror("Soru üretilemedi", str(e), parent=self)

        self.app.run_bg(work, done, err, progress=lambda m: self.winfo_exists() and
                        self.lbl_status.configure(text=m))

    def _redraw(self):
        self.tv.delete(*self.tv.get_children())
        for i, q in enumerate(self.generated):
            self.tv.insert("", "end", iid=str(i), values=(q["domain"], q.get("topic", ""), q["difficulty"],
                                                         q["question"][:160]))
        self.tv.selection_set(self.tv.get_children())
        if self.generated:
            self.btn_save.state(["!disabled"])
        else:
            self.btn_save.state(["disabled"])

    def preview(self, _e=None):
        sel = self.tv.selection()
        if sel:
            QuestionView(self, self.app, self.generated[int(sel[0])])

    def remove_selected(self):
        drop = {int(i) for i in self.tv.selection()}
        self.generated = [q for i, q in enumerate(self.generated) if i not in drop]
        self._redraw()

    def save(self):
        chosen = [self.generated[int(i)] for i in self.tv.selection()]
        if not chosen:
            messagebox.showinfo("Kaydet", "Önce kaydedilecek soruları seçin.", parent=self)
            return
        added, errors = self.app.bank.add_user_questions(chosen, self.v_exam.get(), source="ai")
        msg = f"{added} soru bankaya eklendi."
        if errors:
            msg += "\n" + "\n".join(errors[:8])
        messagebox.showinfo("Kaydet", msg, parent=self)
        keep = {int(i) for i in self.tv.selection()}
        self.generated = [q for i, q in enumerate(self.generated) if i not in keep]
        self._redraw()

    def close(self):
        if self.generated and not messagebox.askyesno(
                "Kapat", "Kaydedilmemiş sorular var. Yine de kapatılsın mı?", parent=self):
            return
        self.destroy()
        if self.on_close:
            self.on_close()


class QuestionView(tk.Toplevel):
    def __init__(self, parent, app: App, q: dict):
        super().__init__(parent)
        self.title(q.get("id") or "Soru")
        self.geometry("780x560")
        txt = tk.Text(self, wrap="word", font=app.f_opt, padx=14, pady=12, relief="flat")
        txt.pack(fill="both", expand=True)
        txt.tag_configure("q", font=app.f_q, spacing3=10)
        txt.tag_configure("ok", foreground=GREEN, background=GREEN_BG)
        txt.tag_configure("h", font=app.f_h2, spacing1=12)
        exam = EXAMS[q["exam"]]
        txt.insert("end", f"{exam.code} • Alan {q['domain']}: {exam.domain_name(q['domain'])} • "
                          f"{q.get('topic', '')} • {q['difficulty']}\n\n")
        txt.insert("end", q["question"] + "\n", "q")
        for i, o in enumerate(q["options"]):
            txt.insert("end", f"{chr(65 + i)}. {o}\n", "ok" if i in q["correct"] else "")
        txt.insert("end", "\nAçıklama\n", "h")
        txt.insert("end", q["explanation"])
        if q.get("source_url"):
            txt.insert("end", f"\n\nKaynak: {q['source_url']}")
        txt.configure(state="disabled")


# ----------------------------------------------------------------------------- Soru bankası
class BankWindow(tk.Toplevel):
    def __init__(self, app: App, exam_code: str, on_close=None):
        super().__init__(app)
        self.app, self.on_close = app, on_close
        self.title("Soru bankası")
        self.geometry("1000x620")
        self.protocol("WM_DELETE_WINDOW", self.close)
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")
        self.v_exam = tk.StringVar(value=exam_code)
        self.v_search = tk.StringVar()
        ttk.Label(top, text="Sınav").pack(side="left")
        cb = ttk.Combobox(top, textvariable=self.v_exam, values=list(EXAMS), state="readonly", width=8)
        cb.pack(side="left", padx=6)
        cb.bind("<<ComboboxSelected>>", lambda e: self.fill())
        ttk.Label(top, text="Ara").pack(side="left", padx=(12, 0))
        ent = ttk.Entry(top, textvariable=self.v_search, width=40)
        ent.pack(side="left", padx=6)
        self.v_search.trace_add("write", lambda *a: self.fill())
        self.lbl = ttk.Label(top, style="Muted.TLabel")
        self.lbl.pack(side="left", padx=10)
        ttk.Button(top, text="JSON olarak dışa aktar", command=self.export).pack(side="right")

        frm = ttk.Frame(self, padding=(10, 0))
        frm.pack(fill="both", expand=True)
        cols = (("id", "ID", 120, False), ("d", "Alan", 45, False), ("t", "Konu", 190, False),
                ("z", "Zorluk", 60, False), ("s", "Kaynak", 80, False), ("b", "Başarı", 80, False),
                ("q", "Soru", 400, True))
        self.tv = ttk.Treeview(frm, columns=[c[0] for c in cols], show="headings")
        for c, t, w, st in cols:
            self.tv.heading(c, text=t)
            self.tv.column(c, width=w, stretch=st, anchor="w")
        sb = ttk.Scrollbar(frm, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        self.tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tv.bind("<Double-1>", self.view)
        bot = ttk.Frame(self, padding=10)
        bot.pack(fill="x")
        ttk.Label(bot, text="Çift tıklayarak soruyu görüntüleyin. Yalnızca eklenen (AI/içe aktarılan) sorular silinebilir.",
                  style="Muted.TLabel").pack(side="left")
        ttk.Button(bot, text="Seçileni sil", command=self.delete).pack(side="right")
        self.fill()

    def rows(self):
        term = self.v_search.get().lower().strip()
        qs = self.app.bank.for_exam(self.v_exam.get())
        if term:
            qs = [q for q in qs if term in q["question"].lower() or term in q.get("topic", "").lower()
                  or any(term in o.lower() for o in q["options"])]
        return sorted(qs, key=lambda q: (q["domain"], q["id"]))

    def fill(self):
        self.tv.delete(*self.tv.get_children())
        qs = self.rows()
        for q in qs:
            s = self.app.stats.get(q["id"])
            b = f"{s['correct']}/{s['seen']}" if s["seen"] else "—"
            self.tv.insert("", "end", iid=q["id"], values=(q["id"], q["domain"], q.get("topic", ""),
                                                          q["difficulty"], SOURCE_LABEL.get(q["source"], q["source"]),
                                                          b, q["question"][:150]))
        self.lbl["text"] = f"{len(qs)} soru"

    def view(self, _e=None):
        sel = self.tv.selection()
        if sel:
            QuestionView(self, self.app, self.app.bank.questions[sel[0]])

    def delete(self):
        sel = self.tv.selection()
        if not sel:
            return
        q = self.app.bank.questions[sel[0]]
        if q["source"] == "builtin":
            messagebox.showinfo("Sil", "Hazır sorular silinemez.", parent=self)
            return
        if messagebox.askyesno("Sil", "Bu soru kalıcı olarak silinsin mi?", parent=self):
            self.app.bank.delete_user_question(q["id"])
            self.fill()

    def export(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".json",
                                            initialfile=f"{self.v_exam.get().lower()}_sorular.json",
                                            filetypes=[("JSON", "*.json")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.rows(), f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Dışa aktar", f"{len(self.rows())} soru kaydedildi.", parent=self)

    def close(self):
        self.destroy()
        if self.on_close:
            self.on_close()


# ----------------------------------------------------------------------------- Ayarlar
class SettingsDialog(tk.Toplevel):
    def __init__(self, app: App, on_close=None):
        super().__init__(app)
        self.app, self.on_close = app, on_close
        self.title("Ayarlar")
        self.transient(app)
        self.resizable(False, False)
        s = app.settings
        frm = ttk.Frame(self, padding=16)
        frm.pack(fill="both", expand=True)
        self.v_key = tk.StringVar(value=s["api_key"])
        self.v_model = tk.StringVar(value=ai.MODELS.get(s["model"], s["model"]))
        self.v_effort = tk.StringVar(value=s["effort"])
        self.v_web = tk.BooleanVar(value=s["web_search"])
        self.v_lang = tk.StringVar(value="Türkçe" if s["language"] == "tr" else "English")

        ttk.Label(frm, text="Claude API (AI soru üretimi ve 'Claude'a sor' için)", style="H2.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(frm, text="API anahtarı").grid(row=1, column=0, sticky="w", pady=6)
        ent = ttk.Entry(frm, textvariable=self.v_key, show="•", width=48)
        ent.grid(row=1, column=1, sticky="ew", pady=6)
        ttk.Label(frm, text=("Boş bırakılırsa ANTHROPIC_API_KEY ortam değişkeni kullanılır. Anahtar bu "
                             "bilgisayarda data/settings.json dosyasında düz metin olarak saklanır."),
                  style="Muted.TLabel", wraplength=460).grid(row=2, column=0, columnspan=2, sticky="w")
        ttk.Label(frm, text="Model").grid(row=3, column=0, sticky="w", pady=6)
        ttk.Combobox(frm, textvariable=self.v_model, values=list(ai.MODELS.values()),
                     state="readonly").grid(row=3, column=1, sticky="ew", pady=6)
        ttk.Label(frm, text="Efor (effort)").grid(row=4, column=0, sticky="w", pady=6)
        ttk.Combobox(frm, textvariable=self.v_effort, values=ai.EFFORTS, state="readonly",
                     width=10).grid(row=4, column=1, sticky="w", pady=6)
        ttk.Checkbutton(frm, text="Güncel bilgi için web araması yap (cloud.google.com)",
                        variable=self.v_web).grid(row=5, column=0, columnspan=2, sticky="w", pady=6)
        ttk.Label(frm, text="Üretilen soruların dili").grid(row=6, column=0, sticky="w", pady=6)
        ttk.Combobox(frm, textvariable=self.v_lang, values=["Türkçe", "English"], state="readonly",
                     width=10).grid(row=6, column=1, sticky="w", pady=6)

        ttk.Separator(frm).grid(row=7, column=0, columnspan=2, sticky="ew", pady=12)
        ttk.Button(frm, text="İstatistikleri sıfırla", command=self.reset_stats).grid(row=8, column=0, sticky="w")
        bar = ttk.Frame(frm)
        bar.grid(row=9, column=0, columnspan=2, sticky="e", pady=(16, 0))
        ttk.Button(bar, text="İptal", command=self.destroy).pack(side="right")
        ttk.Button(bar, text="Kaydet", command=self.save).pack(side="right", padx=6)

    def save(self):
        s = self.app.settings
        s["api_key"] = self.v_key.get().strip()
        inv = {v: k for k, v in ai.MODELS.items()}
        s["model"] = inv.get(self.v_model.get(), self.v_model.get())
        s["effort"] = self.v_effort.get()
        s["web_search"] = bool(self.v_web.get())
        s["language"] = "tr" if self.v_lang.get() == "Türkçe" else "en"
        s.save()
        self.destroy()
        if self.on_close:
            self.on_close()

    def reset_stats(self):
        if messagebox.askyesno("Sıfırla", "Tüm ilerleme ve oturum geçmişi silinsin mi?", parent=self):
            self.app.stats.reset()
            if self.on_close:
                self.on_close()


def main():
    app = App()
    app.mainloop()
