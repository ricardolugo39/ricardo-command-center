import sqlite3
from pathlib import Path
from datetime import date, datetime

import pandas as pd
import streamlit as st

APP_TITLE = "Ricardo Command Center"
DB_PATH = Path(__file__).parent / "todo_app.sqlite"

AREA_SEEDS = [
    ("LITET", "🧦", "Amazon, PPC, inventory, COGS, pricing."),
    ("Lugo Hermanos", "⚙️", "THK, Thomson, Cali branch, CRM."),
    ("Job Search", "💼", "Applications, interviews, follow-ups."),
    ("Personal AI", "🤖", "Python apps, home server, automation."),
    ("Personal", "🏠", "Life admin, training, pets, travel."),
]

PROJECT_SEEDS = [
    ("LITET", "PPC Recovery", "Amazon PPC and sales recovery."),
    ("LITET", "Prime Day", "Discounts, inventory, campaign prep."),
    ("LITET", "Inventory / COGS", "COGS, POs, landed cost."),
    ("Lugo Hermanos", "THK Support", "Technical selections and customer support."),
    ("Lugo Hermanos", "Cali KPI Dashboard", "Sales, visits, CRM, opportunities."),
    ("Lugo Hermanos", "CRM Migration", "Access to SQLite migration."),
    ("Job Search", "Active Interviews", "Interview prep and follow-ups."),
    ("Personal AI", "Todo App", "Command center app."),
    ("Personal AI", "Home Server", "Dell server, Tailscale, Streamlit apps."),
    ("Personal", "Training", "Workout and endurance training."),
]

ROUTINE_SEEDS = [
]


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS areas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        emoji TEXT DEFAULT '📁',
        description TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        area_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        status TEXT DEFAULT 'Active',
        health TEXT DEFAULT 'Green',
        description TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(area_id, name),
        FOREIGN KEY(area_id) REFERENCES areas(id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        area_id INTEGER,
        project_id INTEGER,
        title TEXT NOT NULL,
        status TEXT DEFAULT 'open',
        priority TEXT DEFAULT 'Medium',
        task_type TEXT DEFAULT 'Task',
        effort TEXT DEFAULT '30 min',
        due_date TEXT,
        is_next_action INTEGER DEFAULT 0,
        waiting_on TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT,
        FOREIGN KEY(area_id) REFERENCES areas(id) ON DELETE SET NULL,
        FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        area_id INTEGER,
        project_id INTEGER,
        title TEXT NOT NULL,
        body TEXT DEFAULT '',
        note_type TEXT DEFAULT 'Note',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(area_id) REFERENCES areas(id) ON DELETE SET NULL,
        FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ideas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        area_id INTEGER,
        project_id INTEGER,
        title TEXT NOT NULL,
        body TEXT DEFAULT '',
        status TEXT DEFAULT 'new',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(area_id) REFERENCES areas(id) ON DELETE SET NULL,
        FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS routines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        frequency TEXT DEFAULT 'daily',
        area_id INTEGER,
        project_id INTEGER,
        active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(area_id) REFERENCES areas(id) ON DELETE SET NULL,
        FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS task_tags (
        task_id INTEGER NOT NULL,
        tag_id INTEGER NOT NULL,
        PRIMARY KEY(task_id, tag_id),
        FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE,
        FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS routine_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        routine_id INTEGER NOT NULL,
        log_date TEXT NOT NULL,
        done INTEGER DEFAULT 0,
        UNIQUE(routine_id, log_date),
        FOREIGN KEY(routine_id) REFERENCES routines(id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()

    seed_data()


def seed_data():
    conn = connect()
    cur = conn.cursor()

    # ---------- Areas ----------

    for name, emoji, description in AREA_SEEDS:
        cur.execute("""
            INSERT OR IGNORE INTO areas (
                name,
                emoji,
                description
            )
            VALUES (?, ?, ?)
        """, (name, emoji, description))

    conn.commit()

    # ---------- Projects ----------

    for area_name, project_name, description in PROJECT_SEEDS:

        area_id = get_area_id(conn, area_name)

        if area_id:
            cur.execute("""
                INSERT OR IGNORE INTO projects (
                    area_id,
                    name,
                    description
                )
                VALUES (?, ?, ?)
            """, (
                area_id,
                project_name,
                description
            ))

    
    conn.commit()
    conn.close()


def get_area_id(conn, area_name):
    if not area_name:
        return None
    row = conn.execute("SELECT id FROM areas WHERE name = ?", (area_name,)).fetchone()
    return row["id"] if row else None


def get_project_id(conn, area_id, project_name):
    if not area_id or not project_name:
        return None
    row = conn.execute(
        "SELECT id FROM projects WHERE area_id = ? AND name = ?",
        (area_id, project_name),
    ).fetchone()
    return row["id"] if row else None


def df_query(query, params=()):
    conn = connect()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def execute(query, params=()):
    conn = connect()
    conn.execute(query, params)
    conn.commit()
    conn.close()


def fetch_areas():
    return df_query("SELECT * FROM areas ORDER BY name")


def fetch_projects(area_id=None):
    if area_id:
        return df_query("""
            SELECT p.*, a.name AS area, a.emoji AS area_emoji
            FROM projects p
            LEFT JOIN areas a ON a.id = p.area_id
            WHERE p.area_id = ?
            ORDER BY p.status, p.name
        """, (area_id,))

    return df_query("""
        SELECT p.*, a.name AS area, a.emoji AS area_emoji
        FROM projects p
        LEFT JOIN areas a ON a.id = p.area_id
        ORDER BY a.name, p.status, p.name
    """)


def fetch_open_tasks():
    return df_query("""
        SELECT 
            t.*,
            a.name AS area,
            a.emoji AS area_emoji,
            p.name AS project
        FROM tasks t
        LEFT JOIN areas a ON a.id = t.area_id
        LEFT JOIN projects p ON p.id = t.project_id
        WHERE t.status = 'open'
        ORDER BY
          CASE t.priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
          CASE WHEN t.due_date IS NULL OR t.due_date = '' THEN 1 ELSE 0 END,
          t.due_date ASC,
          t.created_at DESC
    """)


def fetch_tasks_by_status(status="open"):
    return df_query("""
        SELECT 
            t.*,
            a.name AS area,
            a.emoji AS area_emoji,
            p.name AS project
        FROM tasks t
        LEFT JOIN areas a ON a.id = t.area_id
        LEFT JOIN projects p ON p.id = t.project_id
        WHERE t.status = ?
        ORDER BY t.created_at DESC
    """, (status,))


def area_options():
    areas = fetch_areas()
    labels = ["Inbox / No Area"] + [
        f"{row['emoji']} {row['name']}" for _, row in areas.iterrows()
    ]
    mapping = {"Inbox / No Area": None}

    for _, row in areas.iterrows():
        mapping[f"{row['emoji']} {row['name']}"] = int(row["id"])

    return labels, mapping


def project_options(area_id=None):
    projects = fetch_projects(area_id)

    labels = ["No Project"]
    mapping = {"No Project": None}

    for _, row in projects.iterrows():
        label = f"{row['area_emoji']} {row['area']} / {row['name']}"
        labels.append(label)
        mapping[label] = int(row["id"])

    return labels, mapping


def add_task(title, area_id, project_id, priority, task_type, effort, due_date, waiting_on, notes, is_next_action=0):
    due = due_date.isoformat() if due_date else None

    if project_id and not area_id:
        row = df_query("SELECT area_id FROM projects WHERE id = ?", (project_id,))
        if not row.empty:
            area_id = int(row.iloc[0]["area_id"])

    execute("""
        INSERT INTO tasks (
            title, area_id, project_id, priority, task_type, effort,
            due_date, waiting_on, notes, is_next_action
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        title, area_id, project_id, priority, task_type, effort,
        due, waiting_on, notes, is_next_action
    ))


def complete_task(task_id):
    execute(
        "UPDATE tasks SET status='done', completed_at=? WHERE id=?",
        (datetime.now().isoformat(timespec="seconds"), task_id),
    )


def reopen_task(task_id):
    execute("UPDATE tasks SET status='open', completed_at=NULL WHERE id=?", (task_id,))


def delete_task(task_id):
    execute("DELETE FROM tasks WHERE id=?", (task_id,))


def add_note(area_id, project_id, title, body, note_type="Note"):
    execute("""
        INSERT INTO notes (area_id, project_id, title, body, note_type)
        VALUES (?, ?, ?, ?, ?)
    """, (area_id, project_id, title, body, note_type))


def add_idea(area_id, project_id, title, body, status="new"):
    execute("""
        INSERT INTO ideas (area_id, project_id, title, body, status)
        VALUES (?, ?, ?, ?, ?)
    """, (area_id, project_id, title, body, status))


def add_area(name, emoji, description):
    execute("""
        INSERT OR IGNORE INTO areas (name, emoji, description)
        VALUES (?, ?, ?)
    """, (name, emoji or "📁", description))


def add_project(area_id, name, description, status="Active", health="Green"):
    execute("""
        INSERT OR IGNORE INTO projects (area_id, name, status, health, description)
        VALUES (?, ?, ?, ?, ?)
    """, (area_id, name, status, health, description))


def add_routine(title, frequency, area_id, project_id):
    execute("""
        INSERT INTO routines (title, frequency, area_id, project_id, active)
        VALUES (?, ?, ?, ?, 1)
    """, (title, frequency, area_id, project_id))


def routine_is_due(freq):
    today = date.today()

    if freq == "daily":
        return True
    if freq == "weekdays":
        return today.weekday() < 5
    if freq == "weekly":
        return today.weekday() == 0

    return True


def fetch_due_routines():
    routines = df_query("""
        SELECT 
            r.*,
            a.name AS area,
            a.emoji AS area_emoji,
            p.name AS project,
            COALESCE(l.done, 0) AS done
        FROM routines r
        LEFT JOIN areas a ON a.id = r.area_id
        LEFT JOIN projects p ON p.id = r.project_id
        LEFT JOIN routine_log l ON l.routine_id = r.id AND l.log_date = ?
        WHERE r.active = 1
        ORDER BY r.created_at ASC
    """, (date.today().isoformat(),))

    if routines.empty:
        return routines

    return routines[routines["frequency"].apply(routine_is_due)]


def set_routine_done(routine_id, done):
    conn = connect()
    conn.execute("""
        INSERT INTO routine_log (routine_id, log_date, done)
        VALUES (?, ?, ?)
        ON CONFLICT(routine_id, log_date)
        DO UPDATE SET done = excluded.done
    """, (routine_id, date.today().isoformat(), 1 if done else 0))
    conn.commit()
    conn.close()


def inject_css():
    st.markdown("""
    <style>
      .block-container {
        padding-top: 1.5rem;
        max-width: 1280px;
      }
      .project-card {
        border: 1px solid rgba(255,255,255,.12);
        border-radius: 18px;
        padding: 16px;
        min-height: 145px;
        background: rgba(127,127,127,.08);
      }
      .task-card {
        border: 1px solid rgba(255,255,255,.12);
        border-radius: 16px;
        padding: 14px 16px;
        margin-bottom: 10px;
        background: rgba(127,127,127,.06);
      }
      .muted {
        color: #8b949e;
        font-size: 0.9rem;
      }
      .high {
        color: #ff6b6b;
        font-weight: 700;
      }
      .medium {
        color: #f7b955;
        font-weight: 700;
      }
      .low {
        color: #48c78e;
        font-weight: 700;
      }
    </style>
    """, unsafe_allow_html=True)


def render_quick_capture(location="main"):
    area_labels, area_map = area_options()

    with st.form(f"quick_capture_{location}", clear_on_submit=True):
        title = st.text_input("Add task, follow-up, waiting item, note, or idea")

        c1, c2 = st.columns(2)
        area_label = c1.selectbox("Area", area_labels)
        area_id = area_map[area_label]

        project_labels, project_map = project_options(area_id)
        project_label = c2.selectbox("Project", project_labels)
        project_id = project_map[project_label]

        c3, c4, c5 = st.columns(3)
        item_type = c3.selectbox("Type", ["Task", "Follow-up", "Waiting On", "Note", "Idea"])
        priority = c4.selectbox("Priority", ["Medium", "High", "Low"])
        effort = c5.selectbox("Effort", ["5 min", "15 min", "30 min", "1 hour", "2+ hours"])

        c6, c7 = st.columns([1, 2])
        due = c6.date_input("Due date", value=None)
        waiting_on = c7.text_input("Waiting on")

        notes = st.text_area("Notes / details")
        is_next = st.checkbox("Mark as next action")

        submitted = st.form_submit_button("Add")

        if submitted and title.strip():
            if item_type == "Note":
                add_note(area_id, project_id, title.strip(), notes.strip(), "Note")
            elif item_type == "Idea":
                add_idea(area_id, project_id, title.strip(), notes.strip())
            else:
                add_task(
                    title.strip(),
                    area_id,
                    project_id,
                    priority,
                    item_type,
                    effort,
                    due,
                    waiting_on.strip(),
                    notes.strip(),
                    1 if is_next else 0,
                )

            st.success("Added.")
            st.rerun()


def task_location(row):
    location = f"{row['area_emoji'] or '📥'} {row['area'] or 'Inbox'}"
    if row["project"]:
        location += f" / {row['project']}"
    return location


def page_today():
    st.title("Ricardo Command Center")
    st.caption("Area → Project → Task / Note / Idea")

    routines = fetch_due_routines()
    open_tasks = fetch_open_tasks()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Open tasks", len(open_tasks))
    c2.metric("High priority", int((open_tasks["priority"] == "High").sum()) if not open_tasks.empty else 0)
    c3.metric("Due today", int((open_tasks["due_date"] == date.today().isoformat()).sum()) if not open_tasks.empty else 0)
    c4.metric("Routines", f"{int(routines['done'].sum()) if not routines.empty else 0}/{len(routines)}")

    left, right = st.columns([0.9, 1.7])

    with left:
        st.subheader("Daily Routines")

        if routines.empty:
            st.info("No routines due today.")
        else:
            for _, r in routines.iterrows():
                label = r["title"]
                if r["area"]:
                    label += f" · {r['area_emoji']} {r['area']}"

                checked = st.checkbox(label, value=bool(r["done"]), key=f"routine_{r['id']}")

                if checked != bool(r["done"]):
                    set_routine_done(int(r["id"]), checked)
                    st.rerun()

        st.divider()
        st.subheader("Quick Capture")
        render_quick_capture("today")

    with right:
        st.subheader("Focus Today")

        if open_tasks.empty:
            st.success("No open tasks.")
        else:
            today = date.today().isoformat()

            focus = open_tasks[
                (open_tasks["priority"] == "High")
                | (open_tasks["due_date"].notna() & (open_tasks["due_date"] <= today))
                | (open_tasks["is_next_action"] == 1)
            ].head(10)

            if focus.empty:
                focus = open_tasks.head(5)

            for _, t in focus.iterrows():
                priority_class = str(t["priority"]).lower()

                st.markdown(f"""
                <div class="task-card">
                  <b>{t['title']}</b>
                  <span class="{priority_class}"> · {t['priority']}</span>
                  <div class="muted">
                    {task_location(t)} · {t['task_type']} · {t['effort']} · Due: {t['due_date'] or 'No date'}
                  </div>
                </div>
                """, unsafe_allow_html=True)

                b1, b2 = st.columns([1, 6])
                if b1.button("Done", key=f"done_focus_{t['id']}"):
                    complete_task(int(t["id"]))
                    st.rerun()

                if b2.button("Delete", key=f"del_focus_{t['id']}"):
                    delete_task(int(t["id"]))
                    st.rerun()

    st.divider()

    st.subheader("Waiting On")
    waiting = open_tasks[
        (open_tasks["task_type"] == "Waiting On") | (open_tasks["waiting_on"].fillna("") != "")
    ] if not open_tasks.empty else pd.DataFrame()

    if waiting.empty:
        st.info("Nothing waiting.")
    else:
        for _, t in waiting.iterrows():
            st.write(f"**{t['title']}** — waiting on: {t['waiting_on'] or 'Not specified'}")
            st.caption(task_location(t))

    st.divider()

    st.subheader("Area Snapshot")
    areas = fetch_areas()
    cols = st.columns(3)

    for i, (_, a) in enumerate(areas.iterrows()):
        area_tasks = open_tasks[open_tasks["area_id"] == a["id"]] if not open_tasks.empty else pd.DataFrame()
        due_today = int((area_tasks["due_date"] == date.today().isoformat()).sum()) if not area_tasks.empty else 0
        next_task = area_tasks.iloc[0]["title"] if not area_tasks.empty else "No open tasks"

        with cols[i % 3]:
            st.markdown(f"""
            <div class="project-card">
              <h3>{a['emoji']} {a['name']}</h3>
              <div class="muted">{len(area_tasks)} open · {due_today} due today</div>
              <br>
              <b>Next:</b><br>{next_task}
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    st.subheader("Next Actions by Area / Project")

    if open_tasks.empty:
        st.info("No open tasks.")
    else:
        next_actions = open_tasks[open_tasks["is_next_action"] == 1]

        if next_actions.empty:
            next_actions = open_tasks.groupby(["area", "project"], dropna=False).head(1)

        for _, t in next_actions.iterrows():
            st.write(f"**{task_location(t)}:** {t['title']}")


def page_areas_projects():
    st.title("Areas & Projects")
    st.caption("Areas are big buckets. Projects live inside areas.")

    tab_area, tab_project = st.tabs(["Create Area", "Create Project"])

    with tab_area:
        with st.form("create_area", clear_on_submit=True):
            c1, c2 = st.columns([2, 1])
            name = c1.text_input("Area name")
            emoji = c2.text_input("Emoji", value="📁")
            desc = st.text_area("Description")

            if st.form_submit_button("Create Area") and name.strip():
                add_area(name.strip(), emoji.strip(), desc.strip())
                st.success("Area created.")
                st.rerun()

    with tab_project:
        area_labels, area_map = area_options()
        valid_area_labels = [x for x in area_labels if x != "Inbox / No Area"]

        with st.form("create_project", clear_on_submit=True):
            area_label = st.selectbox("Area", valid_area_labels)
            name = st.text_input("Project name")
            desc = st.text_area("Description")
            c1, c2 = st.columns(2)
            status = c1.selectbox("Status", ["Active", "Waiting", "Someday", "Completed"])
            health = c2.selectbox("Health", ["Green", "Yellow", "Red"])

            if st.form_submit_button("Create Project") and name.strip():
                add_project(area_map[area_label], name.strip(), desc.strip(), status, health)
                st.success("Project created.")
                st.rerun()

    st.divider()

    areas = fetch_areas()
    projects = fetch_projects()
    open_tasks = fetch_open_tasks()

    notes = df_query("""
        SELECT 
            n.*,
            a.name AS area,
            a.emoji AS area_emoji,
            p.name AS project
        FROM notes n
        LEFT JOIN areas a ON a.id = n.area_id
        LEFT JOIN projects p ON p.id = n.project_id
        ORDER BY n.created_at DESC
    """)

    ideas = df_query("""
        SELECT 
            i.*,
            a.name AS area,
            a.emoji AS area_emoji,
            p.name AS project
        FROM ideas i
        LEFT JOIN areas a ON a.id = i.area_id
        LEFT JOIN projects p ON p.id = i.project_id
        ORDER BY i.created_at DESC
    """)

    for _, a in areas.iterrows():
        area_projects = projects[projects["area_id"] == a["id"]]
        area_tasks = open_tasks[open_tasks["area_id"] == a["id"]] if not open_tasks.empty else pd.DataFrame()

        with st.expander(f"{a['emoji']} {a['name']} · {len(area_projects)} projects · {len(area_tasks)} open tasks", expanded=False):
            st.write(a["description"] or "No description yet.")

                        # Tasks assigned to this area but not to any project
            area_level_tasks = area_tasks[
                area_tasks["project_id"].isna()
            ] if not area_tasks.empty else pd.DataFrame()

            if not area_level_tasks.empty:
                st.markdown("### Quick Capture / No Project")

                for _, t in area_level_tasks.iterrows():
                    c1, c2, c3 = st.columns([5, 1, 1])

                    c1.write(
                        f"**{t['title']}**  \n"
                        f"{t['priority']} · {t['task_type']} · {t['effort']} · Due: {t['due_date'] or 'No date'}"
                    )

                    if c2.button("Done", key=f"area_done_{t['id']}"):
                        complete_task(int(t["id"]))
                        st.rerun()

                    if c3.button("Delete", key=f"area_del_{t['id']}"):
                        delete_task(int(t["id"]))
                        st.rerun()

                st.divider()

            for _, p in area_projects.iterrows():
                p_tasks = open_tasks[open_tasks["project_id"] == p["id"]] if not open_tasks.empty else pd.DataFrame()
                p_notes = notes[notes["project_id"] == p["id"]] if not notes.empty else pd.DataFrame()
                p_ideas = ideas[ideas["project_id"] == p["id"]] if not ideas.empty else pd.DataFrame()

                c_title, c_complete, c_delete = st.columns([5, 1, 1])

                with c_title:
                    st.markdown(f"### {p['name']}")
                    st.caption(f"Status: {p['status']} · Health: {p['health']}")

                with c_complete:
                    if p["status"] != "Completed":
                        if st.button("Complete", key=f"complete_project_{p['id']}"):
                            complete_project(int(p["id"]))
                            st.success("Project completed.")
                            st.rerun()

                with c_delete:
                    if p["status"] == "Completed":
                        if st.button("Delete", key=f"delete_project_{p['id']}"):
                            delete_project(int(p["id"]))
                            st.success("Project deleted.")
                            st.rerun()

                t1, t2, t3, t4 = st.tabs([
                    f"Tasks ({len(p_tasks)})",
                    f"Notes ({len(p_notes)})",
                    f"Ideas ({len(p_ideas)})",
                    "Add",
                ])

                with t1:
                    if p_tasks.empty:
                        st.info("No open tasks.")
                    else:
                        for _, t in p_tasks.iterrows():
                            c1, c2, c3 = st.columns([5, 1, 1])
                            c1.write(
                                f"**{t['title']}**  \n"
                                f"{t['priority']} · {t['task_type']} · {t['effort']} · Due: {t['due_date'] or 'No date'}"
                            )

                            if c2.button("Done", key=f"proj_done_{t['id']}"):
                                complete_task(int(t["id"]))
                                st.rerun()

                            if c3.button("Delete", key=f"proj_del_{t['id']}"):
                                delete_task(int(t["id"]))
                                st.rerun()

                with t2:
                    if p_notes.empty:
                        st.info("No notes yet.")
                    else:
                        for _, n in p_notes.iterrows():
                            st.markdown(f"**{n['note_type']}: {n['title']}**")
                            st.write(n["body"])
                            st.caption(n["created_at"])
                            st.divider()

                with t3:
                    if p_ideas.empty:
                        st.info("No ideas yet.")
                    else:
                        for _, idea in p_ideas.iterrows():
                            st.markdown(f"**{idea['title']}**")
                            st.write(idea["body"])
                            st.caption(f"Status: {idea['status']} · {idea['created_at']}")
                            st.divider()

                with t4:
                    with st.form(f"add_project_item_{p['id']}", clear_on_submit=True):
                        title = st.text_input("Title")
                        item_type = st.selectbox("Add as", ["Task", "Follow-up", "Waiting On", "Note", "Idea"])
                        body = st.text_area("Details")

                        c1, c2, c3 = st.columns(3)
                        priority = c1.selectbox("Priority", ["Medium", "High", "Low"])
                        effort = c2.selectbox("Effort", ["5 min", "15 min", "30 min", "1 hour", "2+ hours"])
                        due = c3.date_input("Due date", value=None)

                        waiting_on = st.text_input("Waiting on")
                        is_next = st.checkbox("Mark as next action")

                        if st.form_submit_button("Add") and title.strip():
                            if item_type == "Note":
                                add_note(int(a["id"]), int(p["id"]), title.strip(), body.strip(), "Note")
                            elif item_type == "Idea":
                                add_idea(int(a["id"]), int(p["id"]), title.strip(), body.strip())
                            else:
                                add_task(
                                    title.strip(),
                                    int(a["id"]),
                                    int(p["id"]),
                                    priority,
                                    item_type,
                                    effort,
                                    due,
                                    waiting_on.strip(),
                                    body.strip(),
                                    1 if is_next else 0,
                                )

                            st.success("Added.")
                            st.rerun()


def page_inbox():
    st.title("Inbox")
    st.caption("Unprocessed items with no assigned area.")

    render_quick_capture("inbox")

    inbox = df_query("""
        SELECT 
            t.*,
            a.name AS area,
            a.emoji AS area_emoji,
            p.name AS project
        FROM tasks t
        LEFT JOIN areas a ON a.id = t.area_id
        LEFT JOIN projects p ON p.id = t.project_id
        WHERE t.status='open' AND t.area_id IS NULL
        ORDER BY t.created_at DESC
    """)

    st.subheader("Unprocessed Tasks")

    if inbox.empty:
        st.success("Inbox is clear.")
    else:
        for _, t in inbox.iterrows():
            c1, c2, c3 = st.columns([5, 1, 1])
            c1.write(f"**{t['title']}**  \n{t['priority']} · {t['task_type']} · Due: {t['due_date'] or 'No date'}")

            if c2.button("Done", key=f"inbox_done_{t['id']}"):
                complete_task(int(t["id"]))
                st.rerun()

            if c3.button("Delete", key=f"inbox_del_{t['id']}"):
                delete_task(int(t["id"]))
                st.rerun()


def page_notes_ideas():
    st.title("Notes & Ideas")

    area_labels, area_map = area_options()

    with st.form("add_note_idea", clear_on_submit=True):
        c1, c2 = st.columns([2, 1])
        title = c1.text_input("Title")
        item_type = c2.selectbox("Type", ["Note", "Idea"])

        area_label = st.selectbox("Area", area_labels)
        area_id = area_map[area_label]

        project_labels, project_map = project_options(area_id)
        project_label = st.selectbox("Project", project_labels)
        project_id = project_map[project_label]

        body = st.text_area("Body")

        if st.form_submit_button("Save") and title.strip():
            if item_type == "Note":
                add_note(area_id, project_id, title.strip(), body.strip(), "Note")
            else:
                add_idea(area_id, project_id, title.strip(), body.strip())

            st.success("Saved.")
            st.rerun()

    notes = df_query("""
        SELECT 
            n.*,
            a.name AS area,
            a.emoji AS area_emoji,
            p.name AS project
        FROM notes n
        LEFT JOIN areas a ON a.id = n.area_id
        LEFT JOIN projects p ON p.id = n.project_id
        ORDER BY n.created_at DESC
    """)

    ideas = df_query("""
        SELECT 
            i.*,
            a.name AS area,
            a.emoji AS area_emoji,
            p.name AS project
        FROM ideas i
        LEFT JOIN areas a ON a.id = i.area_id
        LEFT JOIN projects p ON p.id = i.project_id
        ORDER BY i.created_at DESC
    """)

    tab_notes, tab_ideas = st.tabs(["Notes", "Ideas"])

    with tab_notes:
        if notes.empty:
            st.info("No notes yet.")
        else:
            for _, n in notes.iterrows():
                st.markdown(f"### {n['title']}")
                st.caption(task_location(n))
                st.write(n["body"])
                st.divider()

    with tab_ideas:
        if ideas.empty:
            st.info("No ideas yet.")
        else:
            for _, i in ideas.iterrows():
                st.markdown(f"### {i['title']}")
                st.caption(task_location(i))
                st.write(i["body"])
                st.divider()


def page_routines():
    st.title("Routines")
    st.caption("Fixed things that appear on your Today dashboard.")

    area_labels, area_map = area_options()

    with st.form("add_routine", clear_on_submit=True):
        title = st.text_input("Routine")

        c1, c2, c3 = st.columns(3)
        freq = c1.selectbox("Frequency", ["daily", "weekdays", "weekly"])
        area_label = c2.selectbox("Area", area_labels)
        area_id = area_map[area_label]

        project_labels, project_map = project_options(area_id)
        project_label = c3.selectbox("Project", project_labels)
        project_id = project_map[project_label]

        if st.form_submit_button("Add routine") and title.strip():
            add_routine(title.strip(), freq, area_id, project_id)
            st.success("Routine added.")
            st.rerun()

    routines = df_query("""
        SELECT 
            r.*,
            a.name AS area,
            a.emoji AS area_emoji,
            p.name AS project
        FROM routines r
        LEFT JOIN areas a ON a.id = r.area_id
        LEFT JOIN projects p ON p.id = r.project_id
        ORDER BY r.active DESC, r.created_at ASC
    """)

    if routines.empty:
        st.info("No routines.")
    else:
        for _, r in routines.iterrows():
            location = f"{r['area_emoji'] or '📥'} {r['area'] or 'Inbox'}"
            if r["project"]:
                location += f" / {r['project']}"

            c1, c2 = st.columns([5, 1])
            c1.write(f"**{r['title']}**  \n{r['frequency']} · {location} · {'Active' if r['active'] else 'Inactive'}")

            if c2.button("Delete", key=f"routine_del_{int(r['id'])}"):
                execute("DELETE FROM routine_log WHERE routine_id = ?", (int(r["id"]),))
                execute("DELETE FROM routines WHERE id = ?", (int(r["id"]),))
                st.success("Routine deleted.")
                st.rerun()

def delete_project(project_id):
    execute("UPDATE tasks SET project_id = NULL WHERE project_id = ?", (project_id,))
    execute("UPDATE notes SET project_id = NULL WHERE project_id = ?", (project_id,))
    execute("UPDATE ideas SET project_id = NULL WHERE project_id = ?", (project_id,))
    execute("UPDATE routines SET project_id = NULL WHERE project_id = ?", (project_id,))
    execute("DELETE FROM projects WHERE id = ?", (project_id,))

def complete_project(project_id):
    execute("UPDATE projects SET status = 'Completed' WHERE id = ?", (project_id,))

def page_completed():
    st.title("Completed")

    done = fetch_tasks_by_status("done")

    if done.empty:
        st.info("No completed tasks yet.")
    else:
        for _, t in done.iterrows():
            c1, c2 = st.columns([5, 1])
            c1.write(f"**{t['title']}**  \n{task_location(t)} · Completed: {t['completed_at']}")

            if c2.button("Reopen", key=f"reopen_{t['id']}"):
                reopen_task(int(t["id"]))
                st.rerun()


def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="✅", layout="wide")

    init_db()
    inject_css()

    page = st.sidebar.radio(
        "Navigate",
        ["Today", "Areas & Projects", "Inbox", "Notes & Ideas", "Routines", "Completed"],
        index=0,
    )

    if page == "Today":
        page_today()
    elif page == "Areas & Projects":
        page_areas_projects()
    elif page == "Inbox":
        page_inbox()
    elif page == "Notes & Ideas":
        page_notes_ideas()
    elif page == "Routines":
        page_routines()
    elif page == "Completed":
        page_completed()


if __name__ == "__main__":
    main()