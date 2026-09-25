"""CSV versionados: publicar CURRENT es la única escritura visible al lector."""
import csv
import hashlib
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .schema import TABLE_COLUMNS, VERSION, RULES_VERSION, empty_tables


def now():
    return datetime.now(timezone.utc).isoformat()


def stable_id(prefix, *parts):
    payload = json.dumps(parts, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return prefix + "_" + hashlib.sha256(payload.encode()).hexdigest()[:24]


def json_text(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("CSV sin encabezado o con columnas duplicadas")
        rows = list(reader)
        if any(None in row or any(v is None for v in row.values()) for row in rows):
            raise ValueError("CSV con número incorrecto de celdas")
        return reader.fieldnames, [{k: v if v != "" else None for k, v in row.items()} for row in rows]


def write_csv(path, columns, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


class Store:
    def __init__(self, root, mode="artificial"):
        if mode not in ("artificial", "private"):
            raise ValueError("Modo de almacén inválido")
        self.root = Path(root).resolve()
        project = Path(__file__).resolve().parents[2]
        if mode == "private" and self.root.is_relative_to(project):
            raise ValueError("El almacén privado debe estar fuera del proyecto")
        self.mode = mode

    @contextmanager
    def locked(self):
        self.root.mkdir(parents=True, exist_ok=True)
        lock = self.root / ".write.lock"
        try:
            handle = lock.open("x")
        except FileExistsError as exc:
            raise ValueError("Almacén ocupado; revisar bloqueo antes de reintentar") from exc
        try:
            with handle:
                handle.write(str(os.getpid()))
            yield
        finally:
            lock.unlink()

    def read(self, revision=None):
        pointer = self.root / "CURRENT"
        if revision is None and not pointer.exists():
            return empty_tables()
        revision = revision or pointer.read_text(encoding="utf-8").strip()
        if not revision.isalnum():
            raise ValueError("Revisión inválida")
        folder = self.root / "revisions" / revision
        metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
        if metadata["mode"] != self.mode:
            raise ValueError("No mezclar almacenes artificiales y privados")
        tables = {}
        for table, columns in TABLE_COLUMNS.items():
            actual, rows = read_csv(folder / (table + ".csv"))
            if actual != columns.split():
                raise ValueError(f"Encabezado de almacén incompatible: {table}")
            tables[table] = rows
        return tables

    def commit(self, tables):
        revision = uuid4().hex
        folder = self.root / "revisions" / revision
        folder.mkdir(parents=True)
        for table, columns in TABLE_COLUMNS.items():
            write_csv(folder / (table + ".csv"), columns.split(), tables[table])
        (folder / "metadata.json").write_text(json_text({"mode": self.mode, "recorded_at": now(), "schema_version": VERSION, "rules_version": RULES_VERSION}), encoding="utf-8")
        temporary = self.root / "CURRENT.tmp"
        temporary.write_text(revision, encoding="utf-8")
        os.replace(temporary, self.root / "CURRENT")
        return revision
