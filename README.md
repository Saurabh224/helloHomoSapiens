# MedFlow Clinic Prototype (V2)

A local desktop prototype for a doctor's clinic using **Python + Tkinter**.

## What's new in V2

- More professional/fancy dashboard styling with KPI cards.
- Quick filter for appointments.
- Time input now uses `HH-MM` format (dash separator), e.g. `14-30`.
- Prescription upload/open flow retained.

## Features

- Track appointments (patient, doctor, date, time, reason).
- Store data in `clinic.db` (SQLite).
- Upload prescription files into `prescriptions/`.
- Open prescription for selected appointment.
- Delete appointments.

## Run

```bash
python3 app.py