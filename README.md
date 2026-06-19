
# Ricardo Command Center

A Streamlit-based personal operating dashboard for tasks, routines, notes, ideas, and project visibility.

## Install

```bash
cd ricardo_command_center
python -m venv .venv
source .venv/bin/activate   # Mac/Linux
# .venv\Scripts\activate    # Windows

pip install -r requirements.txt
streamlit run app.py
```

## What it includes

- Today dashboard
- Daily routines
- Quick capture
- Project snapshot
- Inbox
- Project expanders
- Notes and ideas
- Completed task history
- SQLite storage

The app creates `todo_app.sqlite` automatically the first time it runs.
