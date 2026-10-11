import json
import os
from datetime import datetime

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.utils import get_color_from_hex

Window.size = (500, 820)

COLORS = {
    "primary": "#3498db",
    "secondary": "#2ecc71",
    "danger": "#e74c3c",
    "warning": "#f39c12",
    "text": "#2c3e50",
    "muted": "#7f8c8d",
}


class Section:
    def __init__(self, section_id, name=""):
        self.id = section_id
        self.name = name or f"قسمت {section_id}"
        self.time_per_piece = 0.0
        self.pieces = 0
        self.minutes = 0.0

    def calculate_pieces(self):
        if self.minutes > 0 and self.time_per_piece > 0:
            self.pieces = int((self.minutes * 60) / self.time_per_piece)
        return self.pieces

    def calculate_time(self):
        if self.pieces > 0 and self.time_per_piece > 0:
            return (self.pieces * self.time_per_piece) / 60
        return 0.0

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "time_per_piece": self.time_per_piece,
            "pieces": self.pieces,
            "minutes": self.minutes,
        }

    @classmethod
    def from_dict(cls, data):
        s = cls(data["id"], data.get("name", ""))
        s.time_per_piece = float(data.get("time_per_piece", 0))
        s.pieces = int(data.get("pieces", 0))
        s.minutes = float(data.get("minutes", 0))
        return s


class ProductionStatsApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sections = []
        self.work_hours = 400
        self.data_file = "calculator_data.json"
        self.load_data()

    def build(self):
        self.title = "ماشین حساب آمار تولید"
        root = BoxLayout(orientation="vertical", padding=12, spacing=10)

        header = Label(
            text="📊 ماشین حساب آمار تولید\nمحاسبه قطعات و زمان کاری",
            size_hint_y=0.10,
            bold=True,
            font_size="18sp",
            color=get_color_from_hex(COLORS["text"]),
        )
        root.add_widget(header)

        work_section = self.build_work_hours_section()
        root.add_widget(work_section)

        scroll = ScrollView(size_hint_y=0.52)
        self.sections_container = GridLayout(cols=1, spacing=10, size_hint_y=None, padding=10)
        self.sections_container.bind(minimum_height=self.sections_container.setter("height"))
        scroll.add_widget(self.sections_container)
        root.add_widget(scroll)

        add_btn = Button(
            text="+ افزودن قسمت جدید",
            size_hint_y=0.08,
            background_color=get_color_from_hex(COLORS["secondary"]),
        )
        add_btn.bind(on_press=self.add_section)
        root.add_widget(add_btn)

        summary = self.build_summary()
        root.add_widget(summary)

        actions = GridLayout(cols=3, size_hint_y=0.12, spacing=8)

        calc_btn = Button(
            text="🔢 محاسبه",
            background_color=get_color_from_hex(COLORS["primary"]),
        )
        calc_btn.bind(on_press=self.calculate_all)
        actions.add_widget(calc_btn)

        clear_btn = Button(
            text="🗑️ پاک کردن",
            background_color=get_color_from_hex(COLORS["danger"]),
        )
        clear_btn.bind(on_press=self.clear_all)
        actions.add_widget(clear_btn)

        export_btn = Button(
            text="📥 دانلود",
            background_color=get_color_from_hex(COLORS["warning"]),
        )
        export_btn.bind(on_press=self.export_data)
        actions.add_widget(export_btn)

        root.add_widget(actions)

        self.render_sections()
        return root

    def build_work_hours_section(self):
        layout = BoxLayout(orientation="vertical", size_hint_y=0.12, spacing=5)
        title = Label(
            text="⏰ ساعت کاری",
            bold=True,
            color=get_color_from_hex(COLORS["primary"]),
            size_hint_y=0.35,
        )
        layout.add_widget(title)

        row = BoxLayout(spacing=8)
        self.work_spinner = Spinner(
            text="400 (8 ساعت)",
            values=("400 (8 ساعت)", "625 (12 ساعت)", "سفارشی"),
            size_hint_x=0.7,
        )
        self.work_spinner.bind(text=self.on_work_hours_change)
        row.add_widget(self.work_spinner)

        self.custom_input = TextInput(
            multiline=False,
            input_filter="int",
            hint_text="دقیقه",
            disabled=True,
            size_hint_x=0.3,
        )
        self.custom_input.bind(text=self.on_custom_hours_input)
        row.add_widget(self.custom_input)

        layout.add_widget(row)
        return layout

    def build_summary(self):
        layout = BoxLayout(orientation="vertical", spacing=5, size_hint_y=0.18)
        title = Label(
            text="📈 خلاصه",
            bold=True,
            color=get_color_from_hex(COLORS["primary"]),
            size_hint_y=0.2,
        )
        layout.add_widget(title)

        grid = GridLayout(cols=4, spacing=6)
        self.total_pieces_label = Label(text="کل: 0\nقطعه", color=get_color_from_hex(COLORS["primary"]))
        self.total_time_label = Label(text="کل: 0\nدقیقه", color=get_color_from_hex(COLORS["primary"]))
        self.work_label = Label(text="ساعت: 400\nدقیقه", color=get_color_from_hex(COLORS["primary"]))
        self.achievement_label = Label(text="درصد: 0%", color=get_color_from_hex(COLORS["primary"]))
        grid.add_widget(self.total_pieces_label)
        grid.add_widget(self.total_time_label)
        grid.add_widget(self.work_label)
        grid.add_widget(self.achievement_label)
        layout.add_widget(grid)

        self.progress_bar = ProgressBar(max=100, value=0)
        layout.add_widget(self.progress_bar)
        return layout

    def on_work_hours_change(self, spinner, text):
        if text == "سفارشی":
            self.custom_input.disabled = False
            self.custom_input.focus = True
        else:
            self.custom_input.disabled = True
            mapping = {"400 (8 ساعت)": 400, "625 (12 ساعت)": 625}
            self.work_hours = mapping.get(text, 400)
            self.calculate_all()

    def on_custom_hours_input(self, instance, value):
        if value and value.isdigit():
            self.work_hours = int(value)
            self.calculate_all()

    def add_section(self, instance):
        section_id = int(datetime.now().timestamp() * 1000)
        section = Section(section_id, f"قسمت {len(self.sections) + 1}")
        self.sections.append(section)
        self.save_data()
        self.render_sections()

    def remove_section(self, section_id):
        self.sections = [s for s in self.sections if s.id != section_id]
        self.save_data()
        self.render_sections()

    def update_section(self, section_id, field, value):
        section = next((s for s in self.sections if s.id == section_id), None)
        if not section:
            return

        if field == "name":
            section.name = value
        else:
            try:
                val = 0 if value == "" else float(value)
                setattr(section, field, val)
            except ValueError:
                return

        if field == "minutes":
            section.calculate_pieces()

        self.save_data()
        self.render_sections()

    def render_sections(self):
        self.sections_container.clear_widgets()

        if not self.sections:
            empty = Label(
                text="هنوز قسمتی افزوده نشده است",
                color=get_color_from_hex(COLORS["muted"]),
                size_hint_y=None,
                height=40,
            )
            self.sections_container.add_widget(empty)
            self.calculate_all()
            return

        for section in self.sections:
            self.sections_container.add_widget(self.create_section_widget(section))

        self.calculate_all()

    def create_section_widget(self, section):
        card = BoxLayout(orientation="vertical", spacing=6, size_hint_y=None, height=260)

        name_input = TextInput(text=section.name, multiline=False)
        name_input.bind(text=lambda instance, val, sid=section.id: self.update_section(sid, "name", val))
        card.add_widget(name_input)

        grid = GridLayout(cols=2, spacing=6)
        time_label = Label(text="تایم هر قطعه (ثانیه)", font_size="10sp")
        time_input = TextInput(
            text=str(section.time_per_piece) if section.time_per_piece else "",
            multiline=False,
            input_filter="float",
        )
        time_input.bind(text=lambda instance, val, sid=section.id: self.update_section(sid, "time_per_piece", val))
        grid.add_widget(time_label)
        grid.add_widget(time_input)

        pieces_label = Label(text="تعداد قطعات", font_size="10sp")
        pieces_input = TextInput(
            text=str(section.pieces) if section.pieces else "",
            multiline=False,
            input_filter="float",
        )
        pieces_input.bind(text=lambda instance, val, sid=section.id: self.update_section(sid, "pieces", val))
        grid.add_widget(pieces_label)
        grid.add_widget(pieces_input)
        card.add_widget(grid)

        row = BoxLayout(spacing=6)
        minutes_label = Label(text="دقیقه", font_size="10sp", size_hint_x=0.4)
        minutes_input = TextInput(
            text=str(section.minutes) if section.minutes else "",
            multiline=False,
            input_filter="float",
        )
        minutes_input.bind(text=lambda instance, val, sid=section.id: self.update_section(sid, "minutes", val))
        row.add_widget(minutes_label)
        row.add_widget(minutes_input)
        card.add_widget(row)

        time_needed = section.calculate_time()
        result_text = f"{time_needed:.2f} دقیقه" if section.pieces and section.time_per_piece else "لطفا اطلاعات را کامل کنید"
        result_label = Label(text=result_text, color=get_color_from_hex(COLORS["primary"]), font_size="10sp")
        card.add_widget(result_label)

        remove_btn = Button(
            text="🗑️ حذف قسمت",
            background_color=get_color_from_hex(COLORS["danger"]),
        )
        remove_btn.bind(on_press=lambda instance, sid=section.id: self.remove_section(sid))
        card.add_widget(remove_btn)

        return card

    def calculate_all(self, instance=None):
        total_pieces = 0
        total_time = 0

        for section in self.sections:
            if section.time_per_piece > 0:
                if section.pieces > 0:
                    total_pieces += int(section.pieces)
                    total_time += section.calculate_time()
                elif section.minutes > 0:
                    pieces = section.calculate_pieces()
                    total_pieces += pieces
                    total_time += section.minutes

        self.total_pieces_label.text = f"کل: {total_pieces}\nقطعه"
        self.total_time_label.text = f"کل: {total_time:.2f}\nدقیقه"
        self.work_label.text = f"ساعت: {self.work_hours}\nدقیقه"

        achievement = (total_time / self.work_hours * 100) if self.work_hours > 0 else 0
        self.achievement_label.text = f"درصد: {achievement:.1f}%"
        self.progress_bar.value = min(achievement, 100)

    def clear_all(self, instance):
        self.sections = []
        self.save_data()
        self.render_sections()

    def export_data(self, instance):
        csv_content = "گزارش آمار تولید\n\n"
        csv_content += f"ساعت کاری: {self.work_hours} دقیقه\n"
        csv_content += f"تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        csv_content += "نام قسمت,تایم هر قطعه (ثانیه),تعداد قطعات,زمان (دقیقه)\n"

        total_pieces = 0
        total_time = 0

        for section in self.sections:
            t = section.calculate_time()
            csv_content += f"{section.name},{section.time_per_piece},{section.pieces},{t:.2f}\n"
            total_pieces += int(section.pieces)
            total_time += t

        csv_content += f"\nکل قطعات,{total_pieces}\n"
        csv_content += f"کل زمان,{total_time:.2f} دقیقه\n"
        csv_content += f"درصد تحقق,{(total_time / self.work_hours * 100):.1f}%\n"

        filename = f"گزارش-آمار-{datetime.now().strftime('%Y-%m-%d')}.csv"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(csv_content)

    def save_data(self):
        payload = {
            "sections": [s.to_dict() for s in self.sections],
            "work_hours": self.work_hours,
        }
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.sections = [Section.from_dict(s) for s in data.get("sections", [])]
                self.work_hours = data.get("work_hours", 400)
            except Exception:
                self.sections = []
                self.work_hours = 400


if __name__ == "__main__":
    ProductionStatsApp().run()
