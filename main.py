from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.graphics import Color, RoundedRectangle

import json
import os
from datetime import datetime, time, timedelta

try:
    from android.storage import app_storage_path
    APP_DIR = app_storage_path()
except ImportError:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.join(APP_DIR, "work_records.json")

DAY_SALARY = 4500.0
OT_RATE_PER_HOUR = 420.0
STANDARD_OFF = time(17, 0)

def load_records():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_records(records):
    with open(DATA_FILE, "w") as f:
        json.dump(records, f, indent=2)

def parse_time(s):
    s = s.strip().lower().replace(".", "")
    for fmt in ("%H%M", "%H:%M", "%I%p", "%I:%M%p", "%I:%M %p", "%I %p"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"Invalid time: {s}")

def parse_date(s):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Invalid date: {s}")

def compute_ot_hours(on_t, off_t):
    if off_t <= STANDARD_OFF:
        return 0.0
    on_dt = datetime.combine(datetime.today(), on_t)
    off_dt = datetime.combine(datetime.today(), off_t)
    ref_dt = datetime.combine(datetime.today(), STANDARD_OFF)
    if off_dt < on_dt:
        off_dt += timedelta(days=1)
    if off_dt <= ref_dt:
        return 0.0
    return round((off_dt - ref_dt).total_seconds() / 3600, 2)

def compute_record(rec):
    ot_hours = rec.get("ot_hours", 0)
    ot_pay = ot_hours * OT_RATE_PER_HOUR
    worked = rec.get("worked", True)
    gross_day = (DAY_SALARY if worked else 0) + ot_pay
    allowance = rec.get("allowance", 0)
    payment = rec.get("payment", 0)
    net_day = gross_day - allowance - payment
    return {
        "ot_pay": round(ot_pay, 2),
        "gross_day": round(gross_day, 2),
        "allowance": round(allowance, 2),
        "payment": round(payment, 2),
        "net_day": round(net_day, 2),
    }

def compute_totals(records):
    work_days = sum(1 for r in records if r.get("worked", True))
    off_days = len(records) - work_days
    total_ot_hours = round(sum(r.get("ot_hours", 0) for r in records), 2)
    total_ot_pay = round(total_ot_hours * OT_RATE_PER_HOUR, 2)
    total_day_pay = work_days * DAY_SALARY
    gross_total = round(total_day_pay + total_ot_pay, 2)
    total_allowance = round(sum(r.get("allowance", 0) for r in records), 2)
    total_payment = round(sum(r.get("payment", 0) for r in records), 2)
    net_total = round(gross_total - total_allowance - total_payment, 2)
    return {
        "work_days": work_days, "off_days": off_days,
        "total_ot_hours": total_ot_hours, "total_ot_pay": total_ot_pay,
        "total_day_pay": round(total_day_pay, 2), "gross_total": gross_total,
        "total_allowance": total_allowance, "total_payment": total_payment,
        "net_total": net_total,
    }

BG = get_color_from_hex("#0F172A")
CARD = get_color_from_hex("#1E293B")
ACCENT = get_color_from_hex("#38BDF8")
GREEN = get_color_from_hex("#22C55E")
RED = get_color_from_hex("#EF4444")
TEXT = get_color_from_hex("#F1F5F9")
MUTED = get_color_from_hex("#94A3B8")

def lbl(text, size=16, bold=False, color=TEXT, h=36):
    return Label(text=text, font_size=dp(size), bold=bold, color=color,
                 halign="left", valign="middle", size_hint_y=None, height=dp(h))

def inp(hint, text=""):
    return TextInput(text=text, hint_text=hint, multiline=False,
                     size_hint_y=None, height=dp(46), font_size=dp(15),
                     background_color=get_color_from_hex("#334155"),
                     foreground_color=TEXT, cursor_color=ACCENT,
                     padding=[dp(10), dp(10), dp(10), dp(10)])

def btn(text, color=ACCENT, cb=None, height=48):
    b = Button(text=text, size_hint_y=None, height=dp(height), font_size=dp(15),
               bold=True, background_normal="", background_color=color,
               color=get_color_from_hex("#0F172A"))
    if cb:
        b.bind(on_release=cb)
    return b

def popup(title, msg):
    Popup(title=title, content=Label(text=msg, font_size=dp(15)),
          size_hint=(0.85, 0.4)).open()

class Card(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", size_hint_y=None,
                         height=dp(94), padding=dp(8), spacing=dp(2), **kw)
        with self.canvas.before:
            Color(*CARD)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._u, size=self._u)
    def _u(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size

class MainScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        lo = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(12))
        lo.add_widget(lbl("💼  Work Record Manager", size=22, bold=True, h=44))
        self.bal = lbl("", size=20, bold=True, h=48)
        lo.add_widget(self.bal)
        for txt, cb in [
            ("➕   Add Work Record", self.go_add_work),
            ("💵   Add Payment / Advance", self.go_add_pay),
            ("📋   List Records", self.go_list),
            ("📅   Pay Sheet (Date Range)", self.go_pay),
        ]:
            lo.add_widget(btn(txt, cb=cb, height=54))
        lo.add_widget(BoxLayout())
        self.add_widget(lo)
    def on_enter(self):
        t = compute_totals(load_records())
        color = GREEN if t["net_total"] >= 0 else RED
        word = "Payable to you" if t["net_total"] >= 0 else "You owe"
        self.bal.text = f"{word}: {abs(t['net_total']):,.2f} LKR"
        self.bal.color = color
    def go_add_work(self): self.manager.current = "add_work"
    def go_add_pay(self): self.manager.current = "add_pay"
    def go_list(self):
        self.manager.current = "list"; self.manager.get_screen("list").refresh()
    def go_pay(self): self.manager.current = "paysheet"

class AddWorkScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        sv = ScrollView()
        lo = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8),
                       size_hint_y=None)
        lo.bind(minimum_height=lo.setter("height"))
        lo.add_widget(lbl("Add Work Record", size=20, bold=True, h=44))
        self.d = inp("Date (YYYY-MM-DD, blank = today)")
        self.on = inp("On time (e.g. 08:00)")
        self.off = inp("Off time (e.g. 17:30)")
        self.al = inp("Allowance (LKR)", "0")
        self.pay = inp("Payment received (LKR)", "0")
        for t, w in [("Date", self.d), ("On time", self.on), ("Off time", self.off),
                     ("Allowance", self.al), ("Payment", self.pay)]:
            lo.add_widget(lbl(t, size=12, color=MUTED, h=22))
            lo.add_widget(w)
        lo.add_widget(btn("Save Record", GREEN, self.save, 54))
        lo.add_widget(btn("← Back", get_color_from_hex("#475569"),
                          lambda *a: setattr(self.manager, "current", "main")))
        sv.add_widget(lo)
        self.add_widget(sv)
    def save(self, *a):
        try:
            d = parse_date(self.d.text) if self.d.text.strip() else datetime.today().date()
            on = parse_time(self.on.text)
            off = parse_time(self.off.text)
            al = float(self.al.text or 0)
            pay = float(self.pay.text or 0)
            recs = load_records()
            if any(r["date"] == d.isoformat() for r in recs):
                return popup("Error", f"Record for {d} exists.")
            ot = compute_ot_hours(on, off)
            rec = {"date": d.isoformat(), "worked": True,
                   "on": on.strftime("%H:%M"), "off": off.strftime("%H:%M"),
                   "ot_hours": ot, "allowance": al, "payment": pay}
            recs.append(rec); recs.sort(key=lambda r: r["date"]); save_records(recs)
            c = compute_record(rec)
            popup("✅ Saved", f"{d}\nOT: {ot}h\nNet: {c['net_day']:,.2f} LKR")
            for w in (self.d, self.on, self.off): w.text = ""
            self.al.text = "0"; self.pay.text = "0"
        except ValueError as e:
            popup("Error", str(e))

class AddPayScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        lo = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        lo.add_widget(lbl("Add Payment / Advance", size=20, bold=True, h=44))
        self.d = inp("Date (YYYY-MM-DD, blank = today)")
        self.amt = inp("Amount received (LKR)")
        self.note = inp("Note (optional)")
        for t, w in [("Date", self.d), ("Amount", self.amt), ("Note", self.note)]:
            lo.add_widget(lbl(t, size=12, color=MUTED, h=22)); lo.add_widget(w)
        lo.add_widget(btn("Save Payment", GREEN, self.save, 54))
        lo.add_widget(btn("← Back", get_color_from_hex("#475569"),
                          lambda *a: setattr(self.manager, "current", "main")))
        lo.add_widget(BoxLayout())
        self.add_widget(lo)
    def save(self, *a):
        try:
            d = parse_date(self.d.text) if self.d.text.strip() else datetime.today().date()
            amt = float(self.amt.text)
            if amt <= 0: raise ValueError("Amount must be > 0")
            note = self.note.text.strip()
            recs = load_records()
            ex = next((r for r in recs if r["date"] == d.isoformat()), None)
            if ex and ex.get("worked", True):
                return popup("Error", f"{d} is a WORK day record.")
            if ex:
                ex["payment"] = round(ex.get("payment", 0) + amt, 2)
                if note: ex["note"] = (ex.get("note", "") + " | " + note).strip(" |")
            else:
                recs.append({"date": d.isoformat(), "worked": False, "on": "-", "off": "-",
                             "ot_hours": 0, "allowance": 0, "payment": round(amt, 2),
                             "note": note})
                recs.sort(key=lambda r: r["date"])
            save_records(recs)
            popup("✅ Saved", f"{amt:,.2f} LKR for {d}")
            self.d.text = ""; self.amt.text = ""; self.note.text = ""
        except ValueError as e:
            popup("Error", str(e))

class ListScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        lo = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        top = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        top.add_widget(btn("← Back", get_color_from_hex("#475569"),
                           lambda *a: setattr(self.manager, "current", "main")))
        top.add_widget(btn("🔄 Refresh", ACCENT, lambda *a: self.refresh()))
        lo.add_widget(top)
        lo.add_widget(lbl("All Records", size=20, bold=True, h=40))
        self.scroll = ScrollView()
        self.box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        self.box.bind(minimum_height=self.box.setter("height"))
        self.scroll.add_widget(self.box); lo.add_widget(self.scroll)
        self.tot = lbl("", size=13, bold=True, h=60); lo.add_widget(self.tot)
        self.add_widget(lo)
    def refresh(self):
        self.box.clear_widgets()
        recs = load_records()
        if not recs:
            self.box.add_widget(lbl("No records yet.", color=MUTED))
        for r in recs:
            c = compute_record(r); worked = r.get("worked", True)
            card = Card()
            card.add_widget(lbl(f"{r['date']}  {'🕐' if worked else '💵'}",
                                size=14, bold=True, color=ACCENT, h=22))
            if worked:
                card.add_widget(lbl(f"On {r['on']} → Off {r['off']}  |  OT {r.get('ot_hours',0)}h",
                                    size=12, h=20))
                card.add_widget(lbl(f"Gross {c['gross_day']:,.0f}  Allow {c['allowance']:,.0f}  Paid {c['payment']:,.0f}",
                                    size=11, color=MUTED, h=18))
            else:
                card.add_widget(lbl(f"Payment: {c['payment']:,.2f} LKR", size=12, h=20))
                card.add_widget(lbl(r.get("note", ""), size=11, color=MUTED, h=18))
            nc = GREEN if c["net_day"] >= 0 else RED
            card.add_widget(lbl(f"Net: {c['net_day']:,.2f} LKR", size=12, bold=True, color=nc, h=20))
            self.box.add_widget(card)
        t = compute_totals(recs)
        color = GREEN if t["net_total"] >= 0 else RED
        self.tot.text = (f"Days {t['work_days']} | OT {t['total_ot_hours']}h | "
                         f"Gross {t['gross_total']:,.0f}\n"
                         f"Allow {t['total_allowance']:,.0f} | Paid {t['total_payment']:,.0f} | "
                         f"NET {t['net_total']:,.2f}")
        self.tot.color = color

class PaySheetScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        sv = ScrollView()
        lo = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8), size_hint_y=None)
        lo.bind(minimum_height=lo.setter("height"))
        lo.add_widget(lbl("Pay Sheet (Date Range)", size=20, bold=True, h=44))
        self.s = inp("Start date (YYYY-MM-DD)")
        self.e = inp("End date (YYYY-MM-DD)")
        lo.add_widget(lbl("Start", size=12, color=MUTED, h=22)); lo.add_widget(self.s)
        lo.add_widget(lbl("End", size=12, color=MUTED, h=22)); lo.add_widget(self.e)
        lo.add_widget(btn("Generate", ACCENT, self.gen))
        self.res = Label(text="", font_size=dp(12), color=TEXT, size_hint_y=None,
                         height=dp(500), halign="left", valign="top")
        self.res.bind(texture_size=self._r)
        lo.add_widget(self.res)
        lo.add_widget(btn("← Back", get_color_from_hex("#475569"),
                          lambda *a: setattr(self.manager, "current", "main")))
        sv.add_widget(lo); self.add_widget(sv)
    def _r(self, *a):
        self.res.height = max(dp(500), self.res.texture_size[1] + dp(20))
    def gen(self, *a):
        try:
            s = parse_date(self.s.text); e = parse_date(self.e.text)
            if e < s: raise ValueError("End must be >= start")
            recs = [r for r in load_records() if s.isoformat() <= r["date"] <= e.isoformat()]
            lines = [f"PAY SHEET {s} → {e}", "=" * 32]
            for r in recs:
                c = compute_record(r)
                if r.get("worked", True):
                    lines.append(f"{r['date']} {r['on']}-{r['off']} OT {r.get('ot_hours',0)}h")
                else:
                    lines.append(f"{r['date']} PAYMENT {c['payment']:,.0f}")
                lines.append(f"  G {c['gross_day']:,.0f} A {c['allowance']:,.0f} N {c['net_day']:,.0f}")
            t = compute_totals(recs)
            lines += ["=" * 32,
                      f"Days {t['work_days']} | OT {t['total_ot_hours']}h",
                      f"Gross {t['gross_total']:,.2f}",
                      f"Allow {t['total_allowance']:,.2f}",
                      f"Paid {t['total_payment']:,.2f}",
                      f"NET {t['net_total']:,.2f} LKR"]
            self.res.text = "\n".join(lines)
        except ValueError as ex:
            popup("Error", str(ex))

class WorkApp(App):
    def build(self):
        Window.clearcolor = BG
        self.title = "Work Record Manager"
        sm = ScreenManager()
        sm.add_widget(MainScreen(name="main"))
        sm.add_widget(AddWorkScreen(name="add_work"))
        sm.add_widget(AddPayScreen(name="add_pay"))
        sm.add_widget(ListScreen(name="list"))
        sm.add_widget(PaySheetScreen(name="paysheet"))
        return sm

if __name__ == "__main__":
    WorkApp().run()
