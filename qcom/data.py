"""Download the Kaggle files, load them into Postgres as text, and run dbt."""
import csv
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import psycopg2
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT / "data" / "downloads"
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "out"
IMAGES = ROOT / "images"
DB = os.getenv("PGDATABASE", "qcom")
ENGINE = create_engine(f"postgresql+psycopg2:///{DB}")

DATASETS = [
    ("akxiit/blinkit-sales-dataset", None),
    ("thedevastator/unlock-profits-with-e-commerce-sales-data", "Amazon Sale Report.csv"),
]


def download():
    """Needs a Kaggle API token in ~/.kaggle."""
    kaggle = str(Path(sys.executable).with_name("kaggle"))
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    for ref, file in DATASETS:
        cmd = [kaggle, "datasets", "download", ref, "-p", str(DOWNLOADS)] + (["-f", file] if file else [])
        subprocess.run(cmd, check=True)


def snake(name):
    return re.sub(r"[^0-9a-zA-Z]+", "_", name.strip()).strip("_").lower() or "col"


def source_of(name):
    return "blinkit" if name.lower().startswith("blinkit") else "amazon"


def load():
    """Unzip and load every CSV into the raw schema. Columns stay text; dbt staging does the casting."""
    for z in DOWNLOADS.glob("*.zip"):
        with zipfile.ZipFile(z) as zf:
            for member in zf.namelist():
                if member.lower().endswith(".csv") and "inventory" not in member.lower():  # inventory is not used
                    target = RAW / source_of(Path(member).name) / Path(member).name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(zf.read(member))

    conn = psycopg2.connect(dbname=DB)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("create schema if not exists raw")
    for path in sorted(RAW.rglob("*.csv")):
        source = path.parent.name
        table = snake(path.stem)
        table = table if table.startswith(source) else f"{source}_{table}"
        with open(path, encoding="utf-8-sig") as f:
            header = [snake(h) for h in next(csv.reader(f))]
        cur.execute(f'drop table if exists raw."{table}"')
        cur.execute(f'create table raw."{table}" (' + ", ".join(f'"{c}" text' for c in header) + ")")
        with open(path, encoding="utf-8-sig") as f:
            cur.copy_expert(f'copy raw."{table}" from stdin with csv header', f)
        cur.execute(f'select count(*) from raw."{table}"')
        print(f"raw.{table:40} {cur.fetchone()[0]:>9,}")
    conn.close()


def dbt(*args):
    exe = str(Path(sys.executable).with_name("dbt"))
    subprocess.run([exe, *args, "--profiles-dir", "."], cwd=ROOT / "dbt", check=True)
