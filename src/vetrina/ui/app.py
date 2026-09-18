"""The main window of Vetrina."""

from __future__ import annotations

import queue
import re
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import colorchooser, filedialog

import customtkinter as ctk
from PIL import Image, ImageTk

from .. import APP_NAME, AUTHOR, LINKS
from ..github import LoadError, fetch_repository
from ..i18n import LANGUAGES, TEXTS, system_language, translate
from ..model import LABELS, LANGUAGE_COLORS, OTHER_LANGUAGE_COLOR, PRESETS, THEMES, Card
from ..paths import ICON_FILE, LOGO_FILE
from ..rendering import render
from ..settings import load_settings, save_settings
from . import icons
from .imaging import open_image, with_shadow
from .theme import (
    ACCENT,
    BACKGROUND,
    BORDER,
    CARD_EDGE,
    ERROR,
    FIELD,
    FIELD_BORDER,
    MODIFIER,
    MUTED,
    STAGE,
    STATUS_COLORS,
    SURFACE,
    TEXT,
    TRACK,
)
from .widgets import DropZone, Field, GlassButton, Painted, Segmented, Sidebar

try:  # dropping files on the window needs the tkdnd extension, which is optional
    from tkinterdnd2 import TkinterDnD
except ImportError:
    TkinterDnD = None

#: Choices for the bottom bar, and the longest text each field takes.
BAR_LANGUAGES, BAR_SINGLE = "languages", "single"
TITLE_LIMIT, DESCRIPTION_LIMIT, FOOTER_LIMIT = 60, 200, 40

#: Icons of the formats and of the themes.
FORMAT_ICONS = {"GitHub": "brand-github", "LinkedIn": "brand-linkedin", "Open Graph": "share",
                "X / Twitter": "brand-x"}
THEME_ICONS = {"Chiaro": "sun", "Scuro": "moon"}
THEME_TEXTS = {"Chiaro": "light", "Scuro": "dark"}  # theme -> its name in i18n.py


class App(ctk.CTk):
    PREVIEW_PAD = 24  # room around the preview for its shadow

    def __init__(self) -> None:
        icons.register_font()  # before the window, which reads the fonts when it starts
        settings = load_settings()
        # "light" or "dark" when chosen with the button, else the system's
        appearance = settings.get("appearance") if settings.get("appearance") in ("light", "dark") else "system"
        ctk.set_appearance_mode(appearance)
        super().__init__(fg_color=BACKGROUND)
        self.settings, self.appearance = settings, appearance
        icons.check(self)
        self.can_drop = False
        if TkinterDnD is not None:
            try:
                TkinterDnD._require(self)
                self.can_drop = True
            except (RuntimeError, tk.TclError):
                pass  # without tkdnd, pictures are chosen with the button only
        chosen = self.settings.get("language")
        self.language = chosen if chosen in LANGUAGES else system_language()
        self.title(APP_NAME)
        self._style_title_bar(self)
        icon = open_image(ICON_FILE)
        if icon is not None:
            self._dock_icon = ImageTk.PhotoImage(icon)  # on macOS this becomes the Dock icon
            self.iconphoto(True, self._dock_icon)
        width, height = min(1360, self.winfo_screenwidth() - 80), min(900, self.winfo_screenheight() - 100)
        self.geometry(f"{width}x{height}")
        self.minsize(1200, 700)

        self.picture: Image.Image | None = None
        self.picture_name, self.picture_from_github = "", False
        self.languages: dict[str, int] = {}
        self.accent = "#3572A5"
        self._rendered: Image.Image | None = None
        self._pending: str | None = None
        self._fitting: str | None = None
        self._fonts: dict[tuple[int, str], ctk.CTkFont] = {}
        self._description_length = 0

        self.card_title = tk.StringVar(value="owner/repository")
        self.footer = tk.StringVar()
        self.show_stats = tk.BooleanVar(value=True)
        self.stats = [tk.StringVar(value=value) for value in ("1", "0", "0", "0")]
        self.labels = tk.StringVar(value="English")
        self.bar = tk.StringVar(value=BAR_LANGUAGES)
        self.theme = tk.StringVar(value="Chiaro")
        self.preset = tk.StringVar(value=next(iter(PRESETS)))
        self.language_choice = tk.StringVar(value=self.language)

        self._build()
        for variable in (self.card_title, self.footer, self.show_stats, *self.stats, self.labels, self.bar,
                         self.theme, self.preset):
            variable.trace_add("write", lambda *_: self.schedule())
        self.card_title.trace_add("write", lambda *_: self._update_counters())
        self.footer.trace_add("write", lambda *_: self._update_counters())
        self.show_stats.trace_add("write", lambda *_: self._update_stats_state())
        self.bind(f"<{MODIFIER}-s>", lambda _: self.save())
        self._update_counters()
        self.set_status("status_start")
        self.refresh()

    def t(self, key: str, **values: object) -> str:
        """Text ``key`` of i18n.py in the language of the window."""
        return translate(self.language, key, **values)

    # -- building blocks -------------------------------------------------------------------

    def font(self, size: int = 13, weight: str = "normal") -> ctk.CTkFont:
        if (size, weight) not in self._fonts:
            self._fonts[size, weight] = ctk.CTkFont(size=size, weight=weight)
        return self._fonts[size, weight]

    def _label(self, master, text: str = "", size: int = 13, weight: str = "normal", muted: bool = False,
               **options) -> ctk.CTkLabel:
        options = {"height": size + 8, "anchor": "w", "justify": "left", **options}
        return ctk.CTkLabel(master, text=text, font=self.font(size, weight),
                            text_color=MUTED if muted else TEXT, **options)

    def _icon(self, master, name: str, size: int = 18, color: tuple[str, str] = ACCENT) -> ctk.CTkLabel:
        return ctk.CTkLabel(master, text=icons.text(name), font=ctk.CTkFont(family=icons.FAMILY, size=size),
                            text_color=color, width=size, height=size + 4)

    @staticmethod
    def _width_for(texts: list[str], font: ctk.CTkFont, icon: str | None = None) -> int:
        """Width of a glass button that fits the longest of ``texts``, for labels that change."""
        return round(max(Painted.measure(text, font, icon) for text in texts) + 36)

    def _rule(self, row: int) -> None:
        ctk.CTkFrame(self, height=1, corner_radius=0, fg_color=BORDER).grid(row=row, column=0, sticky="ew")

    def _section(self, row: int, title: str, icon: str) -> tuple[ctk.CTkFrame, ctk.CTkFrame]:
        """A card of the side panel: returns the card, whose title row has room on the
        right, and the frame for its contents."""
        card = ctk.CTkFrame(self.form, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        card.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        card.grid_columnconfigure(1, weight=1)
        self._icon(card, icon).grid(row=0, column=0, padx=(16, 8), pady=(14, 8))
        self._label(card, title, size=15, weight="bold").grid(row=0, column=1, sticky="w", pady=(14, 8))
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.grid(row=1, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 16))
        body.grid_columnconfigure(0, weight=1)
        return card, body

    def _caption(self, master, row: int, text: str, counter: bool = False, pady=(0, 2)) -> ctk.CTkLabel | None:
        """The caption above a field, with room on the right for its character counter."""
        line = ctk.CTkFrame(master, fg_color="transparent")
        line.grid(row=row, column=0, sticky="ew", pady=pady)
        line.grid_columnconfigure(0, weight=1)
        self._label(line, text, size=12, muted=True).grid(row=0, column=0, sticky="w")
        if not counter:
            return None
        label = self._label(line, size=11, muted=True)
        label.grid(row=0, column=1, sticky="e")
        return label

    # -- layout ----------------------------------------------------------------------------

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Header: the app, the repository to load, the language and the info window
        header = ctk.CTkFrame(self, corner_radius=0, fg_color=SURFACE)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        names = ctk.CTkFrame(header, fg_color="transparent")
        names.grid(row=0, column=0, sticky="w", padx=24, pady=14)
        logo = open_image(LOGO_FILE)
        if logo is not None:
            side = 44
            image = ctk.CTkImage(logo.resize((side, side), Image.LANCZOS), size=(side, side))
            ctk.CTkLabel(names, text="", image=image, width=side, height=side).grid(
                row=0, column=0, rowspan=2, padx=(0, 12))
        self._label(names, APP_NAME, size=20, weight="bold").grid(row=0, column=1, sticky="sw")
        self._label(names, self.t("subtitle"), size=12, muted=True).grid(row=1, column=1, sticky="nw")
        self.repository = Field(header, icon="link", placeholder=self.t("repository_placeholder"), width=320,
                                height=44, font=self.font())
        self.repository.grid(row=0, column=2, padx=(0, 10))
        self.repository.entry.bind("<Return>", lambda _: self.load_repository())
        font = self.font(14, "bold")
        self.load_button = GlassButton(header, self.t("load"), self.load_repository, "accent", height=44,
                                       width=self._width_for([self.t("load"), self.t("loading")], font, "download"),
                                       icon="download", radius=12, font=font)
        self.load_button.grid(row=0, column=3, padx=(0, 4))
        self.language_button = GlassButton(header, LANGUAGES[self.language], self._show_language_menu,
                                           icon="language", height=44, font=self.font(13, "bold"))
        self.language_button.grid(row=0, column=4, padx=(0, 2))
        GlassButton(header, "", self.toggle_appearance, icon=("moon", "sun"), icon_size=20, height=44).grid(
            row=0, column=5, padx=(0, 2))
        GlassButton(header, "", self.show_info, icon="info-circle", icon_size=20, height=44).grid(
            row=0, column=6, padx=(0, 19))
        self.language_menu = tk.Menu(self, tearoff=0)
        for code, name in LANGUAGES.items():
            self.language_menu.add_radiobutton(label=name, value=code, variable=self.language_choice,
                                               command=lambda code=code: self.after_idle(self.set_language, code))
        self._rule(row=1)

        # Body: the settings on the left, the preview on the right
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew", padx=16, pady=16)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        self.form = Sidebar(body, width=356, corner_radius=0, fg_color="transparent",
                            scrollbar_button_color=TRACK, scrollbar_button_hover_color=FIELD_BORDER)
        self.form.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        self.form.grid_columnconfigure(0, weight=1)
        self._build_text(0)
        self._build_picture(1)
        self._build_stats(2)
        self._build_labels(3)
        self._build_bar(4)
        self._build_preview(body)

        # Status line
        self._rule(row=3)
        status = ctk.CTkFrame(self, corner_radius=0, fg_color=SURFACE)
        status.grid(row=4, column=0, sticky="ew")
        status.grid_columnconfigure(1, weight=1)
        self.status_icon = self._icon(status, "info-circle", size=15, color=MUTED)
        self.status_icon.grid(row=0, column=0, padx=(22, 6), pady=8)
        self.status_label = self._label(status, size=12, muted=True)
        self.status_label.grid(row=0, column=1, sticky="w")

    def _build_text(self, row: int) -> None:
        _, body = self._section(row, self.t("section_text"), "letter-t")
        self.title_counter = self._caption(body, 0, self.t("title"), counter=True)
        Field(body, textvariable=self.card_title, limit=TITLE_LIMIT, font=self.font()).grid(
            row=1, column=0, sticky="ew")
        self._caption(body, 2, self.t("description"), pady=(12, 2))
        self.description = ctk.CTkTextbox(body, height=88, corner_radius=10, border_width=1, fg_color=FIELD,
                                          border_color=FIELD_BORDER, text_color=TEXT, font=self.font(), wrap="word")
        self.description.grid(row=3, column=0, sticky="ew")
        self.description.insert("1.0", "A short description of the project.")
        self._description_length = len(self.description.get("1.0", "end-1c"))
        self.description.edit_modified(False)
        self.description.bind("<<Modified>>", self._description_changed)
        self.description.bind("<FocusIn>", lambda _: self.description.configure(border_color=ACCENT))
        self.description.bind("<FocusOut>", lambda _: self.description.configure(border_color=FIELD_BORDER))
        self.description_counter = self._label(body, size=11, muted=True)
        self.description_counter.grid(row=4, column=0, sticky="e", pady=(2, 0))
        self._caption(body, 5, self.t("footer"))
        self.footer_field = Field(body, textvariable=self.footer, limit=FOOTER_LIMIT, counter=True, font=self.font())
        self.footer_field.grid(row=6, column=0, sticky="ew")
        self._label(body, self.t("footer_hint"), size=11, muted=True).grid(row=7, column=0, sticky="w", pady=(6, 0))

    def _build_picture(self, row: int) -> None:
        _, body = self._section(row, self.t("section_picture"), "photo")
        self.drop_zone = DropZone(body, self.t, (self.font(13), self.font(12), self.font(13, "bold")), self.can_drop,
                                  self.choose_picture, self.remove_picture, self.load_picture)
        self.drop_zone.grid(row=0, column=0, sticky="ew")

    def _build_stats(self, row: int) -> None:
        card, body = self._section(row, self.t("section_stats"), "chart-bar")
        # The border takes the color of the track, so the white knob stands out on a white card
        self.stats_switch = ctk.CTkSwitch(
            card, text="", variable=self.show_stats, onvalue=True, offvalue=False, width=40, switch_width=40,
            switch_height=22, border_width=3, border_color=ACCENT, fg_color=FIELD_BORDER, progress_color=ACCENT,
            button_color=("#ffffff", "#ffffff"), button_hover_color=("#f3f4f6", "#e6e8eb"))
        self.stats_switch.grid(row=0, column=2, sticky="e", padx=16, pady=(14, 8))
        body.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="stats")
        self.stat_fields = []
        names = (self.t("contributors"), self.t("issues"), self.t("stars"), self.t("forks"))
        for column, (name, variable) in enumerate(zip(names, self.stats, strict=True)):
            gap = (0, 0 if column == 3 else 8)
            self._label(body, name, size=11, muted=True).grid(row=0, column=column, sticky="w", padx=gap)
            field = Field(body, textvariable=variable, width=40, height=34, font=self.font(),
                          accept=lambda text: text == "" or (text.isdigit() and len(text) <= 10))
            field.grid(row=1, column=column, sticky="ew", padx=gap)
            self.stat_fields.append(field)

    def _build_labels(self, row: int) -> None:
        _, body = self._section(row, self.t("section_labels"), "world")
        self.labels_choice = Segmented(body, self.labels, list(LABELS), "solid", font=self.font(13))
        self.labels_choice.grid(row=0, column=0, sticky="w")

    def _build_bar(self, row: int) -> None:
        _, body = self._section(row, self.t("section_bar"), "palette")
        texts = {BAR_LANGUAGES: self.t("bar_languages"), BAR_SINGLE: self.t("bar_single")}
        Segmented(body, self.bar, list(texts), "solid", font=self.font(13), text_of=texts).grid(
            row=0, column=0, sticky="w")
        self.legend = ctk.CTkFrame(body, fg_color="transparent")
        self.legend.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        self.legend.grid_columnconfigure((0, 1), weight=1, uniform="legend")
        color = ctk.CTkFrame(body, fg_color="transparent")
        color.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        color.grid_columnconfigure(1, weight=1)
        self.swatch = ctk.CTkButton(color, text="", width=34, height=34, corner_radius=17, border_width=1,
                                    border_color=FIELD_BORDER, fg_color=self.accent, hover_color=self.accent,
                                    command=self.choose_color)
        self.swatch.grid(row=0, column=0)
        self.accent_label = self._label(color, self.accent.upper())
        self.accent_label.grid(row=0, column=1, sticky="w", padx=10)
        GlassButton(color, self.t("change_color"), self.choose_color, icon="palette", height=36,
                    font=self.font(13, "bold")).grid(row=0, column=2)
        self._update_legend()

    def _build_preview(self, master: ctk.CTkFrame) -> None:
        panel = ctk.CTkFrame(master, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        panel.grid(row=0, column=1, sticky="nsew")
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        toolbar = ctk.CTkFrame(panel, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 12))
        toolbar.grid_columnconfigure(1, weight=1)
        Segmented(toolbar, self.preset, list(PRESETS), "tabs", height=40, font=self.font(14),
                  icon_of=FORMAT_ICONS).grid(row=0, column=0, sticky="w")
        Segmented(toolbar, self.theme, list(THEMES), "switch", height=38, font=self.font(13), icon_of=THEME_ICONS,
                  text_of={theme: self.t(key) for theme, key in THEME_TEXTS.items()}).grid(
            row=0, column=2, sticky="e")

        # The card sits in the middle of the stage, lifted by a soft shadow
        self.stage = ctk.CTkFrame(panel, fg_color=STAGE, corner_radius=14)
        self.stage.grid(row=1, column=0, sticky="nsew", padx=16)
        self.stage.bind("<Configure>", lambda _: self._schedule_fit())
        self.preview = ctk.CTkLabel(self.stage, text="")
        self.preview.place(relx=0.5, rely=0.5, anchor="center")

        footer = ctk.CTkFrame(panel, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=16, pady=(10, 12))
        footer.grid_columnconfigure(0, weight=1)
        self.size_label = self._label(footer, size=12, muted=True)
        self.size_label.grid(row=0, column=0, sticky="w")
        font = self.font(13, "bold")
        self.zoom_button = GlassButton(footer, self.t("preview_at", percent=100), self.show_full_size, icon="eye",
                                       width=self._width_for([self.t("preview_at", percent=100)], font, "eye"),
                                       height=40, font=font)
        self.zoom_button.grid(row=0, column=1, padx=(0, 8))
        GlassButton(footer, self.t("save"), self.save, "accent", height=44, icon="download", radius=12,
                    font=self.font(14, "bold")).grid(row=0, column=2)

    # -- state -----------------------------------------------------------------------------

    def card(self) -> Card:
        def number(variable: tk.StringVar) -> int:
            try:
                return max(0, int(variable.get()))
            except ValueError:
                return 0

        return Card(
            title=self.card_title.get(),
            description=self.description.get("1.0", "end").strip(),
            image=self.picture,
            show_stats=self.show_stats.get(),
            stats=tuple(number(variable) for variable in self.stats),
            languages=self.languages,
            use_language_colors=self.bar.get() == BAR_LANGUAGES,
            accent=self.accent,
            theme=self.theme.get(),
            size=PRESETS[self.preset.get()],
            labels=self.labels.get(),
            footer=self.footer.get(),
        )

    def set_status(self, key: str, kind: str = "info", **values: object) -> None:
        """Show text ``key`` of i18n.py in the status line; ``kind`` is "info", "error" or "ok"."""
        self.status_label.configure(text=self.t(key, **values), text_color=STATUS_COLORS[kind])
        self.status_icon.configure(text_color=STATUS_COLORS[kind])

    @staticmethod
    def _count(label: ctk.CTkLabel, length: int, limit: int) -> None:
        label.configure(text=f"{length}/{limit}", text_color=ERROR if length > limit else MUTED)

    def _update_counters(self) -> None:
        self._count(self.title_counter, len(self.card_title.get()), TITLE_LIMIT)
        self._count(self.description_counter, self._description_length, DESCRIPTION_LIMIT)
        self._count(self.footer_field.counter, len(self.footer.get()), FOOTER_LIMIT)

    def _description_changed(self, _event: tk.Event) -> None:
        if not self.description.edit_modified():
            return
        self.description.edit_modified(False)
        text = self.description.get("1.0", "end-1c")
        if len(text) > DESCRIPTION_LIMIT and len(text) > self._description_length:
            # Typing or pasting past the limit: keep the text as long as it was, or up to the limit
            self.description.delete(f"1.0+{max(DESCRIPTION_LIMIT, self._description_length)}c", "end")
            self.description.edit_modified(False)
            text = self.description.get("1.0", "end-1c")
        self._description_length = len(text)
        self._update_counters()
        self.schedule()

    def _update_stats_state(self) -> None:
        state = "normal" if self.show_stats.get() else "disabled"
        self.stats_switch.configure(border_color=ACCENT if state == "normal" else FIELD_BORDER)
        for field in self.stat_fields:
            field.set_state(state)
        self.labels_choice.configure(state=state)

    def _update_legend(self) -> None:
        """List the loaded languages with the color and share the bar gives them."""
        for child in self.legend.winfo_children():
            child.destroy()
        languages = sorted(((name, size) for name, size in self.languages.items() if size > 0),
                           key=lambda item: -item[1])
        if not languages:
            self.legend.grid_remove()
            return
        self.legend.grid()
        total, shown = sum(size for _, size in languages), languages[:6]
        for index, (name, size) in enumerate(shown):
            share = 100 * size / total
            chip = ctk.CTkFrame(self.legend, fg_color="transparent")
            chip.grid(row=index // 2, column=index % 2, sticky="w", pady=2)
            ctk.CTkFrame(chip, width=10, height=10, corner_radius=5,
                         fg_color=LANGUAGE_COLORS.get(name, OTHER_LANGUAGE_COLOR)).grid(row=0, column=0, padx=(0, 6))
            self._label(chip, name, size=12).grid(row=0, column=1)
            self._label(chip, f"{share:.0f}%" if share >= 1 else "<1%", size=12, muted=True).grid(
                row=0, column=2, padx=(5, 0))
        if len(languages) > len(shown):
            self._label(self.legend, self.t("and_more", count=len(languages) - len(shown)), size=12,
                        muted=True).grid(row=3, column=0, columnspan=2, sticky="w", pady=2)

    def _set_picture(self, picture: Image.Image | None, name: str = "", from_github: bool = False) -> None:
        self.picture, self.picture_name, self.picture_from_github = picture, name, from_github
        self._show_picture()
        self.schedule()

    def _show_picture(self) -> None:
        name = self.t("github_avatar") if self.picture_from_github else self.picture_name
        self.drop_zone.show(self.picture, name if self.picture is not None else "")

    def schedule(self) -> None:
        """Redraw shortly after the last change, so typing stays fluid."""
        if self._pending:
            self.after_cancel(self._pending)
        self._pending = self.after(120, self.refresh)

    def refresh(self) -> None:
        self._pending = None
        card = self.card()
        self._rendered = render(card, supersample=1)
        self.size_label.configure(text=f"{card.size[0]} × {card.size[1]} px · PNG")
        self._fit_preview()

    def _schedule_fit(self) -> None:
        if self._fitting:
            self.after_cancel(self._fitting)
        self._fitting = self.after(40, self._fit_preview)

    def _fit_preview(self) -> None:
        """Scale the last drawn card to the room on the stage, never beyond its real size."""
        self._fitting = None
        pad = self.PREVIEW_PAD
        room_width, room_height = self.stage.winfo_width() - 2 * pad - 16, self.stage.winfo_height() - 2 * pad - 16
        if self._rendered is None or room_width < 50 or room_height < 50:
            return  # the window is not on screen yet: its first <Configure> fits the card
        width, height = self._rendered.size
        scale = min(room_width / width, room_height / height, 1.0)
        card = self._rendered.resize((max(1, round(width * scale)), max(1, round(height * scale))), Image.LANCZOS)
        light, dark = (with_shadow(card, ground, edge, pad) for ground, edge in zip(STAGE, CARD_EDGE, strict=True))
        self._preview_image = ctk.CTkImage(light_image=light, dark_image=dark, size=light.size)
        self.preview.configure(image=self._preview_image)
        self.zoom_button.configure(text=self.t("preview_at", percent=round(scale * 100)))

    # -- actions ---------------------------------------------------------------------------

    def set_language(self, code: str) -> None:
        """Show the window in another language, keeping everything filled in, and remember it."""
        if code == self.language or code not in LANGUAGES:
            return
        self.language = code
        self.settings["language"] = code
        save_settings(self.settings)
        repository, description = self.repository.get(), self.description.get("1.0", "end-1c")
        for child in self.winfo_children():  # the open windows too, which speak the old language
            child.destroy()
        self._build()
        if repository:
            self.repository.entry.insert(0, repository)
        self._description_length = len(description)  # kept whole, even past the limit
        self.description.delete("1.0", "end")
        self.description.insert("1.0", description)
        self._update_counters()
        self._update_stats_state()
        self._show_picture()
        self.set_status("status_language", name=LANGUAGES[code])
        self.refresh()

    def _show_language_menu(self) -> None:
        self.language_choice.set(self.language)
        button = self.language_button
        x, y = button.winfo_rootx() + GlassButton.MARGIN, button.winfo_rooty() + button.winfo_height()
        try:
            self.language_menu.tk_popup(x, y)
        finally:
            self.language_menu.grab_release()

    def show_info(self) -> None:
        """A window about the app: who made it, and where to follow them."""
        for child in self.winfo_children():
            if getattr(child, "is_info", False):
                child.lift()
                child.focus_force()
                return
        window = ctk.CTkToplevel(self, fg_color=SURFACE)
        window.withdraw()  # built hidden: see _present()
        window.is_info = True
        window.title(self.t("info_title", app=APP_NAME))
        window.resizable(False, False)
        window.transient(self)
        content = ctk.CTkFrame(window, fg_color="transparent")
        content.pack(padx=40, pady=(30, 26))
        logo = open_image(LOGO_FILE)
        if logo is not None:
            window.logo = ctk.CTkImage(logo.resize((76, 76), Image.LANCZOS), size=(76, 76))
            ctk.CTkLabel(content, text="", image=window.logo, width=76, height=76).pack()
        self._label(content, APP_NAME, size=24, weight="bold", anchor="center").pack(pady=(12, 0))
        self._label(content, self.t("subtitle"), size=13, muted=True, anchor="center").pack()
        ctk.CTkFrame(content, height=1, width=300, fg_color=BORDER).pack(fill="x", pady=20)
        self._label(content, self.t("made_by"), size=12, muted=True, anchor="center").pack()
        self._label(content, AUTHOR, size=18, weight="bold", anchor="center").pack(pady=(2, 16))
        self._label(content, self.t("follow_me"), size=12, muted=True, anchor="center").pack(pady=(0, 6))
        links = ctk.CTkFrame(content, fg_color="transparent")
        links.pack()
        for column, (name, icon, address) in enumerate(LINKS):
            text = self.t(name) if name in TEXTS else name
            GlassButton(links, text, lambda address=address: webbrowser.open(address), icon=icon, height=40,
                        font=self.font(13, "bold")).grid(row=0, column=column, padx=2)
        self._label(content, self.t("icons_credit"), size=11, muted=True, anchor="center").pack(pady=(20, 0))
        window.bind("<Escape>", lambda _: window.destroy())
        self._present(window)

    def _present(self, window: ctk.CTkToplevel) -> None:
        """Show a window built hidden, centered on the main one and a little above its middle.
        Shown at once, macOS would first put it in a corner and then move it."""
        window.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - window.winfo_reqwidth()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - window.winfo_reqheight()) // 3
        window.geometry(f"+{max(0, x)}+{max(0, y)}")
        self._style_title_bar(window)
        window.deiconify()
        window.after(100, window.focus_force)

    def _style_title_bar(self, window: tk.Misc) -> None:
        """On macOS, give the title bar of ``window`` the chosen appearance (Tk leaves it to the system)."""
        if sys.platform == "darwin":
            style = {"light": "aqua", "dark": "darkaqua"}.get(self.appearance, "auto")
            try:
                window.tk.call("::tk::unsupported::MacWindowStyle", "appearance", window._w, style)
            except tk.TclError:
                pass  # an older Tk: the title bar follows the system

    def toggle_appearance(self) -> None:
        """Switch the window between light and dark, and remember the choice."""
        self.appearance = "light" if ctk.get_appearance_mode() == "Dark" else "dark"
        ctk.set_appearance_mode(self.appearance)  # every widget repaints itself
        self.settings["appearance"] = self.appearance
        save_settings(self.settings)
        for window in (self, *(child for child in self.winfo_children() if isinstance(child, tk.Toplevel))):
            self._style_title_bar(window)

    def load_repository(self) -> None:
        if self.load_button.cget("state") == "disabled":
            return  # a repository is already loading
        text = self.repository.get()
        if not text.strip():
            self.set_status("status_missing", "error")
            self.repository.focus_set()
            return
        self.load_button.configure(state="disabled", text=self.t("loading"))
        self.set_status("status_loading")
        results: queue.Queue = queue.Queue()

        def work() -> None:
            try:
                results.put(fetch_repository(text))
            except Exception as error:  # reported in the window, never raised in the thread
                results.put(error)

        threading.Thread(target=work, daemon=True).start()
        self._wait_for(results)

    def _wait_for(self, results: queue.Queue) -> None:
        # Tkinter is not thread-safe: the main loop polls the queue instead of being called back
        try:
            outcome = results.get_nowait()
        except queue.Empty:
            self.after(100, self._wait_for, results)
            return
        self.load_button.configure(state="normal", text=self.t("load"))
        if isinstance(outcome, LoadError):
            self.set_status(outcome.key, "error", **outcome.values)
            return
        if isinstance(outcome, Exception):
            self.set_status("error_unexpected", "error", error=outcome)
            return
        self.card_title.set(outcome["title"])
        self._description_length = len(outcome["description"])  # text from GitHub is kept whole
        self.description.delete("1.0", "end")
        self.description.insert("1.0", outcome["description"])
        for variable, value in zip(self.stats, outcome["stats"], strict=True):
            variable.set(str(value))
        self.languages = outcome["languages"]
        self._update_legend()
        self._set_picture(outcome["image"], from_github=True)
        self.bar.set(BAR_LANGUAGES)
        self.set_status("status_loaded", "ok", title=outcome["title"])

    def choose_picture(self) -> None:
        path = filedialog.askopenfilename(
            title=self.t("choose_title"),
            filetypes=[(self.t("images"), "*.png *.jpg *.jpeg *.gif *.webp *.bmp"), (self.t("all_files"), "*")])
        if path:
            self.load_picture(Path(path))

    def load_picture(self, path: Path) -> None:
        """Put the image at ``path`` on the card, chosen with the button or dropped."""
        picture = open_image(path)
        if picture is None:
            self.set_status("status_bad_image", "error", name=path.name)
            return
        self._set_picture(picture, path.name)

    def remove_picture(self) -> None:
        self._set_picture(None)

    def choose_color(self) -> None:
        _, chosen = colorchooser.askcolor(self.accent, title=self.t("color_title"))
        if chosen:
            self.accent = chosen
            self.swatch.configure(fg_color=chosen, hover_color=chosen)
            self.accent_label.configure(text=chosen.upper())
            self.bar.set(BAR_SINGLE)  # its trace redraws the card

    def show_full_size(self) -> None:
        """Open the card in a window of its own at its real size, as the saved PNG will be."""
        card = render(self.card(), supersample=2)
        room_width, room_height = self.winfo_screenwidth() - 120, self.winfo_screenheight() - 180
        scale = min(1.0, room_width / card.width, room_height / card.height)
        size = (round(card.width * scale), round(card.height * scale))
        window = ctk.CTkToplevel(self, fg_color=STAGE)
        window.withdraw()  # built hidden: see _present()
        window.title(self.t("full_size_title", app=APP_NAME, percent=round(scale * 100)))
        window.image = ctk.CTkImage(card.resize(size, Image.LANCZOS) if scale < 1 else card, size=size)
        ctk.CTkLabel(window, text="", image=window.image).pack(padx=24, pady=24)
        window.bind("<Escape>", lambda _: window.destroy())
        self._present(window)

    def save(self) -> None:
        card = self.card()
        slug = re.sub(r"[^\w\-]+", "-", card.title.rpartition("/")[2]).strip("-") or self.t("file_suffix")
        path = filedialog.asksaveasfilename(
            title=self.t("save_title"), initialdir=str(Path.home() / "Desktop"),
            initialfile=f"{slug}-{self.t('file_suffix')}.png", defaultextension=".png", filetypes=[("PNG", "*.png")])
        if not path:
            return
        try:
            render(card, supersample=2).save(path, optimize=True)
        except OSError as error:
            self.set_status("status_save_failed", "error", error=error.strerror or error)
            return
        self.set_status("status_saved", "ok", path=path)


def main() -> None:
    """Open the window of Vetrina."""
    App().mainloop()
