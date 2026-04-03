import os

import psycopg
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://", 1)
print("DB URL set:", bool(url))

if not url:
    raise SystemExit("DATABASE_URL is empty")

with psycopg.connect(url, connect_timeout=8) as conn:
    with conn.cursor() as cur:
        cur.execute("select to_regclass('public.streamlit_sessions')")
        row = cur.fetchone()
        print("Table:", row[0] if row else None)
