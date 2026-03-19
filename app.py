#!/usr/bin/env python3
"""MedFlow Clinic V2: fancy appointment tracker with prescription support."""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk


APP_TITLE = "MedFlow Clinic — Appointment Desk V2"
DB_PATH = Path("clinic.db")
UPLOADS_DIR = Path("prescriptions")
TIME_FORMAT = "%H-%M"  # HH-MM requested by user
DATE_FORMAT = "%Y-%m-%d"


@dataclass
class Appointment:
    id: int
    patient_name: str
    doctor_name: str
    appointment_date: str
    appointment_time: str
    reason: str
    prescription_path: str | None


class ClinicDB:
    def __init__(self, db_path: Path) -> None:
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_name TEXT NOT NULL,
                doctor_name TEXT NOT NULL,
                appointment_date TEXT NOT NULL,
                appointment_time TEXT NOT NULL,
                reason TEXT,
                prescription_path TEXT
            )
            """
        )
        self.conn.commit()

    def add_appointment(
        self,
        patient_name: str,
        doctor_name: str,
        appointment_date: str,
        appointment_time: str,
        reason: str,
        prescription_path: str | None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO appointments
            (patient_name, doctor_name, appointment_date, appointment_time, reason, prescription_path)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (patient_name, doctor_name, appointment_date, appointment_time, reason, prescription_path),
        )
        self.conn.commit()

    def all_appointments(self) -> list[Appointment]:
        rows = self.conn.execute(
            """
            SELECT * FROM appointments
            ORDER BY appointment_date ASC, appointment_time ASC
            """
        ).fetchall()
        return [Appointment(**dict(row)) for row in rows]

    def delete_appointment(self, appointment_id: int) -> None:
        self.conn.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
        self.conn.commit()


class StatCard(ttk.Frame):
    def __init__(self, master: tk.Widget, title: str, value: str, accent: str) -> None:
        super().__init__(master, style="Card.TFrame", padding=14)
        self.columnconfigure(0, weight=1)

        ttk.Label(self, text=title, style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        self.value_lbl = ttk.Label(self, text=value, style="KPI.TLabel")
        self.value_lbl.grid(row=1, column=0, sticky="w", pady=(8, 0))
        tk.Frame(self, bg=accent, height=4).grid(row=2, column=0, sticky="ew", pady=(10, 0))

    def update_value(self, value: str) -> None:
        self.value_lbl.config(text=value)


class ClinicApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1260x780")
        self.minsize(1120, 660)
        self.configure(bg="#EEF2F7")

        self.db = ClinicDB(DB_PATH)
        UPLOADS_DIR.mkdir(exist_ok=True)

        self.selected_upload: str | None = None

        self._setup_style()
        self._build_ui()
        self._refresh_table()

    def _setup_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("Sidebar.TFrame", background="#0F172A")
        style.configure("Main.TFrame", background="#EEF2F7")
        style.configure("Card.TFrame", background="#FFFFFF")

        style.configure("Title.TLabel", background="#EEF2F7", foreground="#0F172A", font=("Segoe UI", 23, "bold"))
        style.configure("CardTitle.TLabel", background="#FFFFFF", foreground="#0F172A", font=("Segoe UI", 12, "bold"))
        style.configure("KPI.TLabel", background="#FFFFFF", foreground="#0F172A", font=("Segoe UI", 24, "bold"))
        style.configure("Muted.TLabel", background="#FFFFFF", foreground="#64748B", font=("Segoe UI", 10))

        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 8), foreground="#FFFFFF", background="#2563EB", borderwidth=0)
        style.map("Primary.TButton", background=[("active", "#1D4ED8")])

        style.configure("Secondary.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 8), foreground="#0F172A", background="#E2E8F0", borderwidth=0)
        style.map("Secondary.TButton", background=[("active", "#CBD5E1")])

        style.configure("Danger.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 8), foreground="#FFFFFF", background="#DC2626", borderwidth=0)
        style.map("Danger.TButton", background=[("active", "#B91C1C")])

        style.configure("TEntry", font=("Segoe UI", 10), padding=6)

        style.configure(
            "Treeview",
            background="#FFFFFF",
            foreground="#0F172A",
            fieldbackground="#FFFFFF",
            rowheight=30,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Treeview.Heading",
            background="#E2E8F0",
            foreground="#0F172A",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
        )
        style.map("Treeview", background=[("selected", "#DBEAFE")], foreground=[("selected", "#1E3A8A")])

    def _build_ui(self) -> None:
        shell = ttk.Frame(self, style="Main.TFrame", padding=16)
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(0, weight=1)

        self._build_sidebar(shell)

        main = ttk.Frame(shell, style="Main.TFrame")
        main.grid(row=0, column=1, sticky="nsew", padx=(14, 0))
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=1)

        ttk.Label(main, text="Doctor's Clinic Dashboard", style="Title.TLabel").grid(row=0, column=0, sticky="w", pady=(2, 12))

        metrics = ttk.Frame(main, style="Main.TFrame")
        metrics.grid(row=1, column=0, sticky="ew")
        for col in range(3):
            metrics.columnconfigure(col, weight=1)

        self.total_card = StatCard(metrics, "Total appointments", "0", "#2563EB")
        self.total_card.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.today_card = StatCard(metrics, "Today's appointments", "0", "#16A34A")
        self.today_card.grid(row=0, column=1, sticky="ew", padx=10)

        self.rx_card = StatCard(metrics, "With prescription", "0", "#9333EA")
        self.rx_card.grid(row=0, column=2, sticky="ew", padx=(10, 0))

        self._build_form(main)
        self._build_table(main)

    def _build_sidebar(self, parent: ttk.Frame) -> None:
        sidebar = ttk.Frame(parent, style="Sidebar.TFrame", width=240)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)

        tk.Label(sidebar, text="MedFlow V2", bg="#0F172A", fg="#F8FAFC", font=("Segoe UI", 24, "bold")).pack(anchor="w", padx=18, pady=(22, 2))
        tk.Label(sidebar, text="Clinic workflow\nprototype", justify="left", bg="#0F172A", fg="#94A3B8", font=("Segoe UI", 11)).pack(anchor="w", padx=20, pady=(0, 8))
        tk.Frame(sidebar, bg="#1E293B", height=1).pack(fill="x", padx=18, pady=16)

        for label in ("Dashboard", "Appointments", "Prescriptions", "Patient Desk"):
            tk.Label(sidebar, text=f"• {label}", bg="#0F172A", fg="#E2E8F0", font=("Segoe UI", 11), anchor="w").pack(fill="x", padx=20, pady=8)

    def _build_form(self, parent: ttk.Frame) -> None:
        form_card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        form_card.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        for c in range(4):
            form_card.columnconfigure(c, weight=1)

        ttk.Label(form_card, text="New Appointment", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(form_card, text="Time format in V2 is HH-MM (example: 14-30)", style="Muted.TLabel").grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(2, 10)
        )

        self.patient_var = tk.StringVar()
        self.doctor_var = tk.StringVar()
        self.date_var = tk.StringVar()
        self.time_var = tk.StringVar()
        self.reason_var = tk.StringVar()
        self.search_var = tk.StringVar()

        self._labeled_entry(form_card, "Patient", self.patient_var, 2, 0)
        self._labeled_entry(form_card, "Doctor", self.doctor_var, 2, 1)
        self._labeled_entry(form_card, "Date (YYYY-MM-DD)", self.date_var, 2, 2)
        self._labeled_entry(form_card, "Time (HH-MM)", self.time_var, 2, 3)

        self._labeled_entry(form_card, "Reason", self.reason_var, 3, 0, colspan=2)
        self.upload_label = ttk.Label(form_card, text="No prescription selected", style="Muted.TLabel")
        self.upload_label.grid(row=4, column=2, columnspan=2, sticky="w", pady=(4, 0))

        actions = ttk.Frame(form_card, style="Card.TFrame")
        actions.grid(row=5, column=0, columnspan=4, sticky="w", pady=(14, 0))
        ttk.Button(actions, text="Upload Prescription", style="Secondary.TButton", command=self._choose_prescription).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Save Appointment", style="Primary.TButton", command=self._save_appointment).pack(side="left")

    def _build_table(self, parent: ttk.Frame) -> None:
        table_card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        table_card.grid(row=3, column=0, sticky="nsew", pady=(14, 0))
        table_card.rowconfigure(2, weight=1)
        table_card.columnconfigure(0, weight=1)

        ttk.Label(table_card, text="Upcoming Appointments", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")

        search_row = ttk.Frame(table_card, style="Card.TFrame")
        search_row.grid(row=1, column=0, sticky="ew", pady=(8, 10))
        search_row.columnconfigure(1, weight=1)
        ttk.Label(search_row, text="Quick filter:", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.grid(row=0, column=1, sticky="ew", padx=(8, 10))
        search_entry.bind("<KeyRelease>", lambda _e: self._refresh_table())

        columns = ("id", "patient", "doctor", "date", "time", "reason", "rx")
        self.table = ttk.Treeview(table_card, columns=columns, show="headings", selectmode="browse")

        headers = {
            "id": "#",
            "patient": "Patient",
            "doctor": "Doctor",
            "date": "Date",
            "time": "Time",
            "reason": "Reason",
            "rx": "Prescription",
        }
        widths = {"id": 50, "patient": 150, "doctor": 150, "date": 110, "time": 95, "reason": 280, "rx": 150}

        for col in columns:
            self.table.heading(col, text=headers[col])
            self.table.column(col, width=widths[col], anchor="w")

        self.table.grid(row=2, column=0, sticky="nsew")

        bar = ttk.Scrollbar(table_card, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=bar.set)
        bar.grid(row=2, column=1, sticky="ns")

        btns = ttk.Frame(table_card, style="Card.TFrame")
        btns.grid(row=3, column=0, sticky="w", pady=(12, 0))

        ttk.Button(btns, text="Open Prescription", style="Secondary.TButton", command=self._open_selected_prescription).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Delete Appointment", style="Danger.TButton", command=self._delete_selected).pack(side="left")

    def _labeled_entry(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.StringVar,
        row: int,
        col: int,
        colspan: int = 1,
    ) -> None:
        ttk.Label(parent, text=label, style="Muted.TLabel").grid(row=row, column=col, sticky="w", pady=(4, 2))
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row + 1, column=col, columnspan=colspan, sticky="ew", padx=(0, 12), pady=(0, 2))

    def _choose_prescription(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select prescription file",
            filetypes=[("Documents", "*.pdf *.png *.jpg *.jpeg *.doc *.docx"), ("All files", "*.*")],
        )
        if not selected:
            return

        self.selected_upload = selected
        self.upload_label.config(text=f"Selected: {Path(selected).name}")

    def _validate_inputs(self) -> bool:
        if not self.patient_var.get().strip() or not self.doctor_var.get().strip():
            messagebox.showerror("Missing fields", "Patient name and doctor are required.")
            return False

        try:
            datetime.strptime(self.date_var.get().strip(), DATE_FORMAT)
        except ValueError:
            messagebox.showerror("Invalid date", "Use date format YYYY-MM-DD.")
            return False

        try:
            datetime.strptime(self.time_var.get().strip(), TIME_FORMAT)
        except ValueError:
            messagebox.showerror("Invalid time", "Use time format HH-MM (example: 09-45).")
            return False

        return True

    def _save_appointment(self) -> None:
        if not self._validate_inputs():
            return

        stored_rx: str | None = None
        if self.selected_upload:
            src = Path(self.selected_upload)
            dst = UPLOADS_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{src.name}"
            shutil.copy2(src, dst)
            stored_rx = str(dst)

        self.db.add_appointment(
            patient_name=self.patient_var.get().strip(),
            doctor_name=self.doctor_var.get().strip(),
            appointment_date=self.date_var.get().strip(),
            appointment_time=self.time_var.get().strip(),
            reason=self.reason_var.get().strip(),
            prescription_path=stored_rx,
        )

        self.patient_var.set("")
        self.doctor_var.set("")
        self.date_var.set("")
        self.time_var.set("")
        self.reason_var.set("")
        self.selected_upload = None
        self.upload_label.config(text="No prescription selected")

        self._refresh_table()
        messagebox.showinfo("Saved", "Appointment added successfully.")

    def _refresh_table(self) -> None:
        for item in self.table.get_children():
            self.table.delete(item)

        all_items = self.db.all_appointments()
        query = self.search_var.get().strip().lower() if hasattr(self, "search_var") else ""

        filtered: list[Appointment] = []
        for appt in all_items:
            haystack = f"{appt.patient_name} {appt.doctor_name} {appt.reason} {appt.appointment_date} {appt.appointment_time}".lower()
            if not query or query in haystack:
                filtered.append(appt)

        for appt in filtered:
            rx_display = Path(appt.prescription_path).name if appt.prescription_path else "—"
            self.table.insert(
                "",
                "end",
                values=(
                    appt.id,
                    appt.patient_name,
                    appt.doctor_name,
                    appt.appointment_date,
                    appt.appointment_time,
                    appt.reason,
                    rx_display,
                ),
            )

        today = datetime.now().strftime(DATE_FORMAT)
        todays_count = sum(1 for a in all_items if a.appointment_date == today)
        rx_count = sum(1 for a in all_items if a.prescription_path)
        self.total_card.update_value(str(len(all_items)))
        self.today_card.update_value(str(todays_count))
        self.rx_card.update_value(str(rx_count))

    def _selected_appointment(self) -> Appointment | None:
        selected = self.table.selection()
        if not selected:
            messagebox.showwarning("No selection", "Select an appointment first.")
            return None

        row = self.table.item(selected[0], "values")
        selected_id = int(row[0])
        matches = [a for a in self.db.all_appointments() if a.id == selected_id]
        return matches[0] if matches else None

    def _open_selected_prescription(self) -> None:
        appt = self._selected_appointment()
        if appt is None:
            return

        if not appt.prescription_path:
            messagebox.showinfo("No file", "No prescription is attached for this appointment.")
            return

        if not os.path.exists(appt.prescription_path):
            messagebox.showerror("Missing file", "Prescription file no longer exists on disk.")
            return

        self._open_file(appt.prescription_path)

    def _open_file(self, path: str) -> None:
        try:
            if os.name == "nt":
                os.startfile(path)  # type: ignore[attr-defined]
                return

            if os.uname().sysname == "Darwin":
                subprocess.run(["open", path], check=False)
            else:
                subprocess.run(["xdg-open", path], check=False)
        except Exception as exc:  # pragma: no cover
            messagebox.showerror("Open failed", f"Could not open file: {exc}")

    def _delete_selected(self) -> None:
        appt = self._selected_appointment()
        if appt is None:
            return

        confirm = messagebox.askyesno("Confirm delete", f"Delete appointment for {appt.patient_name}?")
        if not confirm:
            return

        self.db.delete_appointment(appt.id)
        self._refresh_table()


def main() -> None:
    app = ClinicApp()
    app.mainloop()


if __name__ == "__main__":
    main()