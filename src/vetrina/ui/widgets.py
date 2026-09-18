"""The window's own widgets, drawn on Tk canvases in the style of macOS glass: buttons,
segmented choices, text fields, the side panel and the drop zone of the picture."""

from __future__ import annotations

import math
import sys
import tkinter as tk
from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageTk

from . import icons
from .imaging import rounded_picture
from .theme import (
    ACCENT,
    ACCENT_SOFT,
    ACCENT_TEXT,
    DASH,
    DROP,
    FIELD,
    FIELD_BORDER,
    GLASS_STYLES,
    MUTED,
    POINTER,
    RAISED,
    SUBTLE,
    SURFACE,
    TEXT,
    TRACK,
    TRACK_HOVER,
    WHITE,
    mix,
)

try:  # dropping files needs the tkdnd extension, which is optional
    from tkinterdnd2 import DND_FILES
except ImportError:
    DND_FILES = None


class Painted(tk.Canvas):
    """A canvas that paints itself in the colors of the current appearance, and paints again
    when the appearance changes. Round shapes are made of ovals, arcs and rectangles: Tk
    snaps the points of lines and polygons to whole points, but draws ovals and arcs smooth."""

    def __init__(self, master, width: int, height: int, surface: tuple[str, str] = SURFACE) -> None:
        super().__init__(master, width=width, height=height, highlightthickness=0, borderwidth=0)
        self.surface = surface
        ctk.AppearanceModeTracker.add(self._appearance_changed, self)

    @staticmethod
    def color(pair: str | tuple[str, str]) -> str:
        return pair[ctk.AppearanceModeTracker.appearance_mode] if isinstance(pair, tuple) else pair

    @staticmethod
    def measure(text: str, font: ctk.CTkFont, icon: str | None = None, icon_size: int = 16) -> float:
        """Width of an icon followed by a label, as content() draws them."""
        glyph = icons.text(icon) if icon else ""
        gap = 7 if glyph and text else 0
        return (icon_size if glyph else 0) + gap + (font.measure(text) if text else 0)

    def repaint(self) -> None:
        tk.Canvas.configure(self, background=self.color(self.surface))
        self.delete("all")
        self.paint()

    def paint(self) -> None:
        """Draw the widget on the empty canvas."""

    def destroy(self) -> None:
        ctk.AppearanceModeTracker.remove(self._appearance_changed)
        super().destroy()

    def _appearance_changed(self, _mode: str) -> None:
        self.repaint()

    def rounded(self, left: float, top: float, right: float, bottom: float, radius: float, fill: str) -> None:
        """A filled rectangle with corners of ``radius``; half its height makes a pill."""
        r = max(0.0, min(radius, (bottom - top) / 2, (right - left) / 2))
        d = 2 * r
        if r:
            for x, y in ((left, top), (right - d, top), (left, bottom - d), (right - d, bottom - d)):
                self.create_oval(x, y, x + d, y + d, fill=fill, outline="")
        self.create_rectangle(left + r, top, right - r, bottom, fill=fill, outline="")
        self.create_rectangle(left, top + r, right, bottom - r, fill=fill, outline="")

    def rounded_outline(self, left: float, top: float, right: float, bottom: float, radius: float, color: str,
                        width: float = 1, dash: tuple[int, int] | None = None) -> None:
        r = max(0.0, min(radius, (bottom - top) / 2, (right - left) / 2))
        d = 2 * r
        arc = {"style": "arc", "outline": color, "width": width}
        line = {"fill": color, "width": width}
        if dash:
            arc["dash"] = line["dash"] = dash
        # Tk measures angles from three o'clock, counterclockwise
        for x, y, start in ((left, top, 90), (right - d, top, 0), (right - d, bottom - d, 270), (left, bottom - d, 180)):
            self.create_arc(x, y, x + d, y + d, start=start, extent=90, **arc)
        self.create_line(left + r, top, right - r, top, **line)
        self.create_line(left + r, bottom, right - r, bottom, **line)
        self.create_line(left, top + r, left, bottom - r, **line)
        self.create_line(right, top + r, right, bottom - r, **line)

    def content(self, x: float, y: float, text: str, font: ctk.CTkFont, color: str, icon: str | None = None,
                icon_size: int = 16) -> None:
        """An icon followed by a label, centered on (x, y)."""
        glyph = icons.text(icon) if icon else ""
        left = x - self.measure(text, font, icon, icon_size) / 2
        if glyph:
            self.create_text(left + icon_size / 2, y, text=glyph, font=icons.font(icon_size), fill=color)
            left += icon_size + (7 if text else 0)
        if text:
            self.create_text(left, y, text=text, font=font, fill=color, anchor="w")


class GlassButton(Painted):
    """A button in the style of macOS glass: a vertical gradient, light along the upper edge,
    a glow along the lower one and a soft shadow. Tk can neither blur nor see through a
    widget, so the glass is painted in solid colors mixed against the surface behind it."""

    MARGIN = 5  # room around the button for its shadow

    def __init__(self, master, text: str, command, style: str = "glass", width: int | None = None,
                 height: int = 38, icon: str | tuple[str, str] | None = None, icon_size: int = 16,
                 radius: float | None = None, font: ctk.CTkFont | None = None,
                 surface: tuple[str, str] = SURFACE) -> None:
        # ``icon`` may be a pair, like the colors: one icon in light mode, one in dark mode
        if width is None:  # as wide as its label, or round when it only has an icon
            first_icon = icon[0] if isinstance(icon, tuple) else icon
            width = round(self.measure(text, font, first_icon, icon_size) + 36) if text else height
        super().__init__(master, width + 2 * self.MARGIN, height + 2 * self.MARGIN, surface)
        self._text, self._command, self._style, self._icon = text, command, GLASS_STYLES[style], icon
        self._icon_size = icon_size
        self._size, self._font = (width, height), font
        self._radius = height / 2 if radius is None else radius
        self._state, self._hover, self._pressed = "normal", False, False
        # Handlers take the event as optional: Tk sometimes runs a binding without one
        self.bind("<Enter>", lambda _=None: self._set(hover=True))
        self.bind("<Leave>", lambda _=None: self._set(hover=False, pressed=False))
        self.bind("<ButtonPress-1>", lambda _=None: self._set(pressed=self._state == "normal"))
        self.bind("<ButtonRelease-1>", self._release)
        self.configure(state="normal")

    def configure(self, **options):
        if "command" in options:
            self._command = options.pop("command")
        redraw = "state" in options or "text" in options
        self._state = options.pop("state", self._state)
        self._text = options.pop("text", self._text)
        if redraw:
            options["cursor"] = POINTER if self._state == "normal" else ""
        result = super().configure(**options) if options else None
        if redraw:
            self.repaint()
        return result

    config = configure

    def cget(self, key: str):
        if key in ("state", "text"):
            return self._state if key == "state" else self._text
        return super().cget(key)

    def _set(self, **flags: bool) -> None:
        self._hover = flags.get("hover", self._hover)
        self._pressed = flags.get("pressed", self._pressed)
        self.repaint()

    def _release(self, event: tk.Event | None = None) -> None:
        inside = event is None or (0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height())
        clicked = self._pressed and inside
        self._set(pressed=False)
        if clicked and self._state == "normal" and self._command:
            self._command()

    def paint(self) -> None:
        style = {key: self.color(value) for key, value in self._style.items()}
        surface = self.color(self.surface)
        width, height = self._size
        left = top = self.MARGIN
        right, bottom = left + width, top + height
        r = min(self._radius, height / 2)
        upper, lower, ink = style["top"], style["bottom"], style["text"]
        normal = self._state == "normal"
        if not normal:
            upper, lower = mix(upper, surface, 0.45), mix(lower, surface, 0.45)
            ink = mix(ink, lower, 0.5)
        elif self._pressed:
            upper, lower = mix(upper, "#000000", 0.08), mix(lower, "#000000", 0.1)
        elif self._hover:
            upper, lower = mix(upper, "#ffffff", 0.14), mix(lower, "#ffffff", 0.1)

        # Soft shadow: slightly larger shapes, lower than the button, fading into the surface
        if normal and not self._pressed:
            for grow, drop, strength in ((3, 3, 0.03), (2, 2, 0.05), (1, 1, 0.08)):
                shade = mix(surface, "#000000", min(0.6, strength * style["shadow"]))
                self.rounded(left - grow, top - grow + drop, right + grow, bottom + grow + drop, r + grow, shade)

        # Body: a smooth shape in the middle color, then one row after another from the top
        # color to the bottom one; the hairline drawn over the edge hides their square ends
        self.rounded(left, top, right, bottom, r, mix(upper, lower, 0.5))
        for row in range(height):
            middle = row + 0.5
            depth = max(r - middle, middle - (height - r), 0.0)
            inset = r - math.sqrt(max(0.0, r * r - depth * depth)) if depth else 0.0
            self.create_rectangle(left + inset, top + row, right - inset, top + row + 1, outline="",
                                  fill=mix(upper, lower, row / max(1, height - 1)))
        self.rounded_outline(left, top, right, bottom, r, style["rim"])
        if normal:
            self._edge_light(left + 1, top + 1, right - 1, bottom - 1, r - 1, style["shine"], upper_edge=True)
            self._edge_light(left + 1, top + 1, right - 1, bottom - 1, r - 1, style["glow"], upper_edge=False)
        self.content((left + right) / 2, (top + bottom) / 2 + (0.5 if self._pressed else 0), self._text,
                     self._font, ink, self.color(self._icon) if self._icon else None, self._icon_size)

    def _edge_light(self, left: float, top: float, right: float, bottom: float, r: float, color: str,
                    upper_edge: bool) -> None:
        d, arc = 2 * r, {"style": "arc", "outline": color, "width": 1}
        if upper_edge:
            self.create_arc(left, top, left + d, top + d, start=100, extent=60, **arc)
            self.create_arc(right - d, top, right, top + d, start=20, extent=60, **arc)
            self.create_line(left + r, top, right - r, top, fill=color, width=1)
        else:
            self.create_arc(left, bottom - d, left + d, bottom, start=200, extent=60, **arc)
            self.create_arc(right - d, bottom - d, right, bottom, start=280, extent=60, **arc)
            self.create_line(left + r, bottom, right - r, bottom, fill=color, width=1)


class Segmented(Painted):
    """Choices bound to a StringVar, in one of three looks: "tabs", separate tabs with the
    chosen one tinted by the accent; "switch", a track where the chosen item is raised on
    a white pill; "solid", a track where the chosen item is filled with the accent."""

    PAD, INSET = 14, 3

    def __init__(self, master, variable: tk.StringVar, values: list[str], look: str = "solid", height: int = 32,
                 font: ctk.CTkFont | None = None, icon_of: dict[str, str] | None = None,
                 text_of: dict[str, str] | None = None, surface: tuple[str, str] = SURFACE) -> None:
        self._variable, self._values, self._look, self._font = variable, values, look, font
        self._icon_of, self._text_of = icon_of or {}, text_of or {}
        self._gap = 8 if look == "tabs" else 0
        self._inset = 0 if look == "tabs" else self.INSET
        self._widths = [round(self.measure(self._text(value), font, self._icon_of.get(value)) + 2 * self.PAD)
                        for value in values]
        width = sum(self._widths) + self._gap * (len(values) - 1) + 2 * self._inset
        super().__init__(master, width, height, surface)
        self._width, self._height = width, height
        self._state, self._hover = "normal", None
        tk.Canvas.configure(self, cursor=POINTER)
        self.bind("<Motion>", lambda event=None: self._set_hover(self._index(event.x) if event else None))
        self.bind("<Leave>", lambda _=None: self._set_hover(None))
        self.bind("<ButtonRelease-1>", self._click)
        self._trace = variable.trace_add("write", lambda *_: self.repaint())
        self.repaint()

    def _text(self, value: str) -> str:
        return self._text_of.get(value, value)

    def destroy(self) -> None:
        self._variable.trace_remove("write", self._trace)
        super().destroy()

    def configure(self, **options):
        if "state" in options:
            self._state = options.pop("state")
            tk.Canvas.configure(self, cursor=POINTER if self._state == "normal" else "")
            self.repaint()
        return super().configure(**options) if options else None

    config = configure

    def _spans(self):
        x = self._inset
        for index, width in enumerate(self._widths):
            yield index, x, x + width
            x += width + self._gap

    def _index(self, x: float) -> int | None:
        return next((index for index, left, right in self._spans() if left <= x < right), None)

    def _set_hover(self, index: int | None) -> None:
        if index != self._hover:
            self._hover = index
            self.repaint()

    def _click(self, event: tk.Event | None = None) -> None:
        index = self._index(event.x) if event else None
        if index is not None and self._state == "normal":
            self._variable.set(self._values[index])

    def paint(self) -> None:
        c = self.color
        surface = c(self.surface)
        enabled = self._state == "normal"

        def ink(pair):
            return c(pair) if enabled else mix(c(pair), surface, 0.55)

        height, inset = self._height, self._inset
        if self._look != "tabs":
            self.rounded(0, 0, self._width, height, height / 2, ink(TRACK))
        for index, left, right in self._spans():
            value = self._values[index]
            chosen, hover = value == self._variable.get(), enabled and index == self._hover
            top, bottom = inset, height - inset
            radius = 10 if self._look == "tabs" else (bottom - top) / 2
            if self._look == "tabs":
                fill, color = (ACCENT_SOFT if chosen else TRACK_HOVER if hover else TRACK), (ACCENT_TEXT if chosen else SUBTLE)
            elif self._look == "switch":
                if chosen:
                    self.rounded(left, top + 1, right, bottom + 1, radius, mix(ink(TRACK), "#000000", 0.08))
                fill, color = (RAISED if chosen else TRACK_HOVER if hover else None), (ACCENT_TEXT if chosen else MUTED)
            else:
                fill, color = (ACCENT if chosen else TRACK_HOVER if hover else None), (WHITE if chosen else TEXT)
            if fill is not None:
                self.rounded(left, top, right, bottom, radius, ink(fill))
            self.content((left + right) / 2, height / 2, self._text(value), self._font, ink(color),
                         self._icon_of.get(value))


class Sidebar(ctk.CTkScrollableFrame):
    """The scrolling side panel. On macOS, CTk scrolls it once per wheel or trackpad event,
    and every scroll redraws the whole window, preview included: the events come faster
    than the redraws, so the panel lags behind the fingers. Here the events are added up
    and applied together, at most once per frame, and each one goes twice as far."""

    SPEED, FRAME = 2, 16  # units per unit of wheel movement; milliseconds between two scrolls

    def __init__(self, *args, **options) -> None:
        super().__init__(*args, **options)
        self._scroll_amount, self._scroll_job = 0, None

    def _mouse_wheel_all(self, event: tk.Event) -> None:
        if sys.platform != "darwin" or self._shift_pressed:
            return super()._mouse_wheel_all(event)
        if not self._check_if_valid_scroll(event.widget):
            return None
        self._scroll_amount -= event.delta * self.SPEED
        if self._scroll_job is None:
            self._scroll_job = self.after(self.FRAME, self._scroll)
        return None

    def _scroll(self) -> None:
        self._scroll_job = None
        amount, self._scroll_amount = self._scroll_amount, 0
        if amount and self._parent_canvas.yview() != (0.0, 1.0):
            self._parent_canvas.yview_scroll(amount, "units")


class Field(ctk.CTkFrame):
    """A one-line text field: a rounded border that takes the accent while the field has the
    focus, an optional icon on its left and an optional character counter on its right.
    With a ``limit``, typing stops at that many characters (deleting always works)."""

    def __init__(self, master, textvariable: tk.StringVar | None = None, icon: str | None = None,
                 placeholder: str | None = None, limit: int | None = None, counter: bool = False,
                 accept=None, width: int = 200, height: int = 38, font: ctk.CTkFont | None = None) -> None:
        super().__init__(master, corner_radius=10, border_width=1, fg_color=FIELD, border_color=FIELD_BORDER)
        self.grid_columnconfigure(1, weight=1)
        if icon and icons.available:
            ctk.CTkLabel(self, text=icons.text(icon), font=ctk.CTkFont(family=icons.FAMILY, size=16),
                         text_color=MUTED, width=16, height=16).grid(row=0, column=0, padx=(12, 0))

        def allowed(proposed: str, current: str, action: str, index: str, inserted: str) -> bool:
            if action == "-1":
                # The variable was set by the program (a load from GitHub): refusing it would
                # make Tk switch validation off for good
                return True
            if accept is not None and not accept(proposed):
                return False
            if limit is None or len(proposed) <= limit or len(proposed) < len(current):
                return True
            room = limit - len(current)
            if action == "1" and room > 0:  # a paste too long: keep what fits, as web forms do
                self.after_idle(self.entry.insert, int(index), inserted[:room])
            return False

        options = {} if textvariable is None else {"textvariable": textvariable}
        if placeholder:
            options["placeholder_text"] = placeholder
        self.entry = ctk.CTkEntry(self, width=width, height=height - 4, border_width=0, corner_radius=8,
                                  fg_color=FIELD, text_color=TEXT, placeholder_text_color=MUTED, font=font,
                                  validate="key", **options)
        self.entry.configure(validatecommand=(self.register(allowed), "%P", "%s", "%d", "%i", "%S"))
        self.entry.grid(row=0, column=1, sticky="ew", padx=6, pady=2)
        self.counter = None
        if counter:
            self.counter = ctk.CTkLabel(self, text="", text_color=MUTED, height=20, font=ctk.CTkFont(size=11))
            self.counter.grid(row=0, column=2, padx=(0, 12))
        self.entry.bind("<FocusIn>", lambda _: self.configure(border_color=ACCENT))
        self.entry.bind("<FocusOut>", lambda _: self.configure(border_color=FIELD_BORDER))

    def get(self) -> str:
        return self.entry.get()

    def focus_set(self) -> None:
        self.entry.focus_set()

    def set_state(self, state: str) -> None:
        self.entry.configure(state=state, text_color=TEXT if state == "normal" else MUTED)


class DropZone(Painted):
    """The dashed area of the picture: the picture or a sign, a line of text and the buttons
    to choose or remove it. With tkdnd, an image file dropped on it is loaded as well."""

    HEIGHT = 150

    def __init__(self, master, t: Callable[[str], str], fonts: tuple[ctk.CTkFont, ctk.CTkFont, ctk.CTkFont],
                 can_drop: bool, on_choose: Callable[[], None], on_remove: Callable[[], None],
                 on_drop: Callable[[Path], None]) -> None:
        """``t`` gives each text in the window's language; ``fonts`` are those of the line of
        text, of the hint under it and of the buttons; ``on_drop`` gets a dropped file."""
        super().__init__(master, 320, self.HEIGHT, SURFACE)
        self._t, self._can_drop, self._on_drop = t, can_drop and DND_FILES is not None, on_drop
        self._text_font, self._hint_font, button_font = fonts
        self._photo, self._name, self._over = None, "", False
        self.choose = GlassButton(self, t("choose_file"), on_choose, icon="upload", height=36, font=button_font,
                                  surface=DROP)
        self.remove = GlassButton(self, t("remove"), on_remove, icon="trash", height=36, font=button_font,
                                  surface=DROP)
        self.bind("<Configure>", lambda _=None: self.repaint())
        if self._can_drop:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<DropEnter>>", lambda event: self._hover(event, True))
            self.dnd_bind("<<DropLeave>>", lambda event: self._hover(event, False))
            self.dnd_bind("<<Drop>>", self._drop)
        self.show(None)

    def show(self, picture: Image.Image | None, name: str = "") -> None:
        self._photo = None if picture is None else ImageTk.PhotoImage(rounded_picture(picture, 44, radius=10))
        self._name = name if len(name) <= 34 else name[:33] + "…"
        self.remove.configure(state="normal" if picture is not None else "disabled")
        self.repaint()

    def _hover(self, event, over: bool) -> str:
        self._over = over
        self.repaint()
        return event.action

    def _drop(self, event) -> str:
        self._over = False
        self.repaint()
        paths = self.tk.splitlist(event.data)
        if paths:
            self._on_drop(Path(paths[0]))
        return event.action

    def paint(self) -> None:
        c = self.color
        width = self.winfo_width() if self.winfo_width() > 1 else int(self.cget("width"))
        height, middle = self.HEIGHT, width / 2
        self.rounded(1, 1, width - 1, height - 1, 12, c(ACCENT_SOFT if self._over else DROP))
        self.rounded_outline(1, 1, width - 1, height - 1, 12, c(ACCENT if self._over else DASH), dash=(4, 4))
        if self._photo is not None:
            self.create_image(middle, 32, image=self._photo)
        else:
            self.create_text(middle, 32, text=icons.text("photo"), font=icons.font(26), fill=c(MUTED))
        can_drop, t = self._can_drop, self._t
        if self._name:
            first, second = self._name, t("drop_replace") if can_drop else ""
        else:
            first, second = (t("drop_here"), t("or")) if can_drop else (t("no_picture"), "")
        self.create_text(middle, 66, text=first, font=self._text_font, fill=c(TEXT))
        if second:
            self.create_text(middle, 84, text=second, font=self._hint_font, fill=c(MUTED))
        self.create_window(middle - 2, height - 30, window=self.choose, anchor="e")
        self.create_window(middle + 2, height - 30, window=self.remove, anchor="w")
