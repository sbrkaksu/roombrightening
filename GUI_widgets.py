#GUI components for the main application window, including tables, buttons, and pop-up windows.

import customtkinter as ctk
import numpy as np
from CTkTable import CTkTable

from Formatter import FormatPrinter


def all_children(widget, children=None):
    children = children or []
    for child in widget.winfo_children():
        children.append(child)
        all_children(child, children)
    return children


superscript_map = {
    "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
    "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
    "+": "⁺", "-": "⁻",
}
superscript_trans = str.maketrans(
    "".join(superscript_map.keys()),
    "".join(superscript_map.values()),
)


def pprint_scientific(value):
    base, exponent = np.format_float_scientific(
        value,
        precision=2,
        min_digits=2,
        exp_digits=1,
    ).split("e", 1)
    return "{} ⋅10{}".format(base, exponent.translate(superscript_trans))


table_printer = FormatPrinter({float: pprint_scientific, str: "{}"})


class ClickableTable(ctk.CTkFrame):
    def __init__(self, *args, header_labels, row_num, callback=None, **kwargs):
        super().__init__(*args, **kwargs, fg_color="transparent")
        self.row_num = row_num
        self.col_num = len(header_labels)
        self.selected_row = None
        self.column_widths = [max(85, len(label) * 8 + 20) for label in header_labels]

        self.table_header = CTkTable(self, row=1, column=self.col_num, header_color="white", corner_radius=0, height=10, width=85)
        self.table_header.grid(row=0, column=0, padx=5, pady=1, sticky="n")
        self.table_header.update_values([header_labels])
        self.header_dict = dict(zip(header_labels, range(len(header_labels))))

        self.table = CTkTable(self, row=self.row_num, column=self.col_num, corner_radius=0, height=10, width=85, hover_color="#92d5e0")
        self.table.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="n")
        self.apply_column_widths()
        if callback is not None:
            self.set_callback(callback)

    def apply_column_widths(self):
        for column, width in enumerate(self.column_widths):
            self.table_header.frame[0, column].configure(width=width, require_redraw=True)
            for row in range(self.table.rows):
                self.table.frame[row, column].configure(width=width, require_redraw=True)

    def set_callback(self, callback):
        for row in range(self.table.rows):
            self.table.edit_row(row=row, command=lambda row=row: callback(row))

    def deselect_row(self):
        if self.selected_row is not None:
            self.table.deselect_row(self.selected_row)

    def select_row(self, row_idx):
        self.deselect_row()
        self.selected_row = row_idx
        self.table.select_row(self.selected_row)

    def update_table(self, values):
        for row in range(self.table.rows):
            for column in range(self.table.columns):
                try:
                    value = values[row][column]
                    if value is None:
                        value = " "
                except IndexError:
                    value = " "
                self.table.frame[row, column].configure(text=str(table_printer.pformat(value)), require_redraw=True)

    def update_cell(self, value, column, row_idx=None):
        if row_idx is None:
            row_idx = self.selected_row
        if isinstance(column, str):
            column = self.header_dict[column]
        self.table.insert(row_idx, column, str(table_printer.pformat(value)))

    def update_row(self, values, row_idx):
        for column, value in enumerate(values):
            if value is None:
                value = " "
            self.table.frame[row_idx, column].configure(text=str(table_printer.pformat(value)), require_redraw=True)


class CheckWindow(ctk.CTkToplevel):
    def __init__(self, parent, title, label, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.transient(parent)
        self.grab_set()
        parent.update_idletasks()
        self.geometry(f"300x200+{parent.winfo_rootx() + 20}+{parent.winfo_rooty() + 20}")
        self.title(title)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.confirm_button = ctk.CTkButton(self, text=label, command=self.destroy)
        self.confirm_button.grid(row=0, column=0, padx=20, pady=30, sticky="nsew")


class ReminderWindow(ctk.CTkToplevel):
    def __init__(self, parent, title, message, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.transient(parent)
        parent.update_idletasks()
        self.geometry(f"320x160+{parent.winfo_rootx() + 20}+{parent.winfo_rooty() + 20}")
        self.title(title)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.message_label = ctk.CTkLabel(self, text=message)
        self.message_label.grid(row=0, column=0, padx=20, pady=(25, 10), sticky="nsew")
        self.close_button = ctk.CTkButton(self, text="Close", command=self.destroy)
        self.close_button.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")


class ResultsWindow(ctk.CTkToplevel):
    def __init__(self, parent, title, text, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.transient(parent)
        parent.update_idletasks()
        self.geometry(f"420x520+{parent.winfo_rootx() + 20}+{parent.winfo_rooty() + 20}")
        self.title(title)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.textbox = ctk.CTkTextbox(self, wrap="word")
        self.textbox.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")
        self.textbox.insert("1.0", text)
        self.textbox.configure(state="disabled")
        self.close_button = ctk.CTkButton(self, text="Close", command=self.destroy)
        self.close_button.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="ew")


class SwitchButton(ctk.CTkButton):
    button_groups = {}

    def __init__(self, *args, on_color, group=None, command=None, **kwargs):
        super().__init__(*args, command=self.on_click, hover=False, **kwargs)
        self.on_color = on_color
        self.off_color = self.cget("fg_color")
        self.border_color = self.cget("border_color")
        self.border_width = self.cget("border_width")
        self.selected = False
        self.command = command
        self.group = group
        self.on_enter_id = None
        self.on_leave_id = None
        if group is not None:
            self.button_groups.setdefault(group, []).append(self)
        if self.cget("state") == "disabled":
            self.enabled = True
            self.disable()
        else:
            self.enabled = False
            self.enable()

    def on_enter(self, _event):
        self.configure(border_color="white")

    def on_leave(self, _event):
        self.configure(border_color=self.border_color)

    def add_enter_leave_interaction(self):
        if self.on_enter_id is None and self.on_leave_id is None:
            self.on_enter_id = self.bind("<Enter>", self.on_enter, add="+")
            self.on_leave_id = self.bind("<Leave>", self.on_leave, add="+")

    def remove_enter_leave_interaction(self):
        self.unbind("<Enter>")
        self.unbind("<Leave>")
        self.on_enter_id, self.on_leave_id = None, None

    def on_click(self):
        if not self.selected:
            self.select()
            if self.group is not None:
                for switch_button in self.button_groups[self.group]:
                    if switch_button is not self:
                        switch_button.deselect()
            if self.command is not None:
                self.command()

    def turn_on(self):
        self.configure(fg_color=self.on_color)

    def enable(self):
        if not self.enabled:
            self.configure(state="normal", border_color=self.border_color)
            self.add_enter_leave_interaction()
            self.enabled = True

    def enable_children(self):
        if self.enabled:
            for child in all_children(self):
                if isinstance(child, ctk.CTkButton):
                    child.configure(state="normal")

    def disable(self):
        if self.enabled:
            self.configure(state="disabled", border_color="gray")
            self.remove_enter_leave_interaction()
            self.enabled = False
            self.disable_children()

    def disable_children(self):
        for child in all_children(self):
            if isinstance(child, ctk.CTkButton):
                child.configure(state="disabled")

    def select(self):
        if self.enabled and not self.selected:
            self.selected = True
            self.remove_enter_leave_interaction()
            self.configure(border_color="white", border_width=self.border_width * 2)
            self.enable_children()

    def deselect(self):
        if self.enabled and self.selected:
            self.selected = False
            self.add_enter_leave_interaction()
            self.configure(border_color=self.border_color, border_width=self.border_width)
            self.disable_children()

    def set_command(self, command):
        self.command = command
