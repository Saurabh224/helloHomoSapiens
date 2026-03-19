import sqlite3
from pathlib import Path
from datetime import datetime
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

DB = "clinic.db"
UPLOADS = Path("prescriptions")
UPLOADS.mkdir(exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient TEXT NOT NULL,
        doctor TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        reason TEXT,
        prescription TEXT
    )
    """)
    conn.commit()
    conn.close()

def add_appt(patient, doctor, date, time, reason, prescription):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "INSERT INTO appointments (patient, doctor, date, time, reason, prescription) VALUES (?, ?, ?, ?, ?, ?)",
        (patient, doctor, date, time, reason, prescription),
    )
    conn.commit()
    conn.close()

def get_appts():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, patient, doctor, date, time, reason, prescription FROM appointments ORDER BY date, time")
    rows = c.fetchall()
    conn.close()
    return rows

def delete_appt(appt_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM appointments WHERE id = ?", (appt_id,))
    conn.commit()
    conn.close()

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Clinic Appointment Manager")
        self.geometry("1000x620")
        self.configure(bg="#eef2f7")
        self.rx_file = None

        self.setup_ui()
        self.refresh()

    def setup_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        top = ttk.Frame(self, padding=16)
        top.pack(fill="x")

        ttk.Label(top, text="Doctor Clinic Appointment Manager", font=("Segoe UI", 18, "bold")).pack(anchor="w")

        form = ttk.LabelFrame(self, text="New Appointment", padding=12)
        form.pack(fill="x", padx=16, pady=8)

        self.patient = tk.StringVar()
        self.doctor = tk.StringVar()
        self.date = tk.StringVar()
        self.time = tk.StringVar()
        self.reason = tk.StringVar()

        ttk.Label(form, text="Patient").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.patient, width=25).grid(row=1, column=0, padx=5, pady=4)

        ttk.Label(form, text="Doctor").grid(row=0, column=1, sticky="w")
        ttk.Entry(form, textvariable=self.doctor, width=25).grid(row=1, column=1, padx=5, pady=4)

        ttk.Label(form, text="Date (YYYY-MM-DD)").grid(row=0, column=2, sticky="w")
        ttk.Entry(form, textvariable=self.date, width=18).grid(row=1, column=2, padx=5, pady=4)

        ttk.Label(form, text="Time (HH:MM)").grid(row=0, column=3, sticky="w")
        ttk.Entry(form, textvariable=self.time, width=12).grid(row=1, column=3, padx=5, pady=4)

        ttk.Label(form, text="Reason").grid(row=2, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.reason, width=55).grid(row=3, column=0, columnspan=2, padx=5, pady=4, sticky="we")

        self.rx_label = ttk.Label(form, text="No prescription selected")
        self.rx_label.grid(row=3, column=2, columnspan=2, sticky="w")

        ttk.Button(form, text="Upload Prescription", command=self.pick_file).grid(row=4, column=0, pady=8, sticky="w")
        ttk.Button(form, text="Save Appointment", command=self.save).grid(row=4, column=1, pady=8, sticky="w")

        table_frame = ttk.LabelFrame(self, text="Appointments", padding=12)
        table_frame.pack(fill="both", expand=True, padx=16, pady=8)

        cols = ("id", "patient", "doctor", "date", "time", "reason", "rx")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=12)
        for col, txt, w in [
            ("id", "#", 40), ("patient", "Patient", 140), ("doctor", "Doctor", 140),
            ("date", "Date", 100), ("time", "Time", 80), ("reason", "Reason", 260), ("rx", "Prescription", 160)
        ]:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True)

        btns = ttk.Frame(self, padding=8)
        btns.pack(fill="x")
        ttk.Button(btns, text="Delete Selected", command=self.delete_selected).pack(side="left")

    def pick_file(self):
        f = filedialog.askopenfilename(
            title="Select prescription",
            filetypes=[("Documents", "*.pdf *.png *.jpg *.jpeg *.doc *.docx"), ("All files", "*.*")]
        )
        if f:
            self.rx_file = f
            self.rx_label.config(text=Path(f).name)

    def save(self):
        patient = self.patient.get().strip()
        doctor = self.doctor.get().strip()
        date = self.date.get().strip()
        time = self.time.get().strip()
        reason = self.reason.get().strip()

        if not patient or not doctor:
            messagebox.showerror("Error", "Patient and doctor are required.")
            return

        try:
            datetime.strptime(date, "%Y-%m-%d")
            datetime.strptime(time, "%H:%M")
        except ValueError:
            messagebox.showerror("Error", "Invalid date/time format.")
            return

        rx_path = None
        if self.rx_file:
            src = Path(self.rx_file)
            dst = UPLOADS / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{src.name}"
            shutil.copy2(src, dst)
            rx_path = str(dst)

        add_appt(patient, doctor, date, time, reason, rx_path)

        self.patient.set("")
        self.doctor.set("")
        self.date.set("")
        self.time.set("")
        self.reason.set("")
        self.rx_file = None
        self.rx_label.config(text="No prescription selected")

        self.refresh()
        messagebox.showinfo("Saved", "Appointment saved.")

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in get_appts():
            rx_name = Path(r[6]).name if r[6] else "-"
            self.tree.insert("", "end", values=(r[0], r[1], r[2], r[3], r[4], r[5], rx_name))

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "Select an appointment first.")
            return
        row = self.tree.item(sel[0], "values")
        delete_appt(int(row[0]))
        self.refresh()

if __name__ == "__main__":
    init_db()
    app = App()
    app.mainloop()
