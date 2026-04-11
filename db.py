"""
db.py — Todas las operaciones de base de datos para Morning Commander
"""

import sqlite3
import random
from datetime import datetime

DB_PATH = "morning.db"

# 20 frases motivacionales pre-cargadas
FRASES_INICIALES = [
    ("La disciplina es el puente entre metas y logros.", "Jim Rohn"),
    ("El éxito no es definitivo, el fracaso no es fatal: lo que cuenta es el valor de continuar.", "Winston Churchill"),
    ("No cuentes los días, haz que los días cuenten.", "Muhammad Ali"),
    ("La única forma de hacer un gran trabajo es amar lo que haces.", "Steve Jobs"),
    ("El secreto de salir adelante es comenzar.", "Mark Twain"),
    ("No es lo que tienes, sino lo que haces con lo que tienes.", "Aldous Huxley"),
    ("Cada mañana tenemos dos opciones: continuar durmiendo con sueños o levantarnos y perseguirlos.", "Anónimo"),
    ("El dolor que sientes hoy será la fuerza que sentirás mañana.", "Anónimo"),
    ("Las personas que son lo suficientemente locas para pensar que pueden cambiar el mundo son quienes lo hacen.", "Steve Jobs"),
    ("Trabaja mientras ellos duermen, aprende mientras ellos descansan.", "Anónimo"),
    ("La motivación te impulsa, el hábito te mantiene.", "Jim Ryun"),
    ("No te preocupes por los fracasos, preocúpate por las oportunidades que pierdes cuando ni siquiera lo intentas.", "Jack Canfield"),
    ("Sé el cambio que deseas ver en el mundo.", "Mahatma Gandhi"),
    ("El único límite a nuestros logros del mañana son las dudas de hoy.", "Franklin D. Roosevelt"),
    ("Empieza donde estás, usa lo que tienes, haz lo que puedas.", "Arthur Ashe"),
    ("La vida es 10% lo que te sucede y 90% cómo reaccionas a ello.", "Charles R. Swindoll"),
    ("No esperes. Nunca será el momento perfecto.", "Napoleón Hill"),
    ("El que madruga, Dios le ayuda.", "Refrán"),
    ("Invierte en ti mismo. Tu carrera es el motor de tu riqueza.", "Paul Clitheroe"),
    ("Pequeños pasos diarios llevan a grandes logros anuales.", "Anónimo"),
]


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Crea las tablas si no existen y pre-carga las frases."""
    with get_conn() as conn:
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS tareas (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                texto     TEXT NOT NULL,
                creada_en TEXT NOT NULL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS completadas (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                texto         TEXT NOT NULL,
                creada_en     TEXT NOT NULL,
                completada_en TEXT NOT NULL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS frases (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                texto TEXT NOT NULL,
                autor TEXT NOT NULL,
                usada INTEGER DEFAULT 0
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS config (
                clave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            )
        """)

        conn.commit()

        # Pre-cargar frases si la tabla está vacía
        c.execute("SELECT COUNT(*) as total FROM frases")
        if c.fetchone()["total"] == 0:
            c.executemany(
                "INSERT INTO frases (texto, autor) VALUES (?, ?)",
                FRASES_INICIALES
            )
            conn.commit()


# ── TAREAS ────────────────────────────────────────────────────────────────────

def agregar_tarea(texto: str) -> int:
    with get_conn() as conn:
        c = conn.cursor()
        ahora = datetime.now().isoformat()
        c.execute(
            "INSERT INTO tareas (texto, creada_en) VALUES (?, ?)",
            (texto.strip(), ahora)
        )
        conn.commit()
        return c.lastrowid


def obtener_tareas() -> list:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id, texto, creada_en FROM tareas ORDER BY id")
        return [(row["id"], row["texto"], row["creada_en"]) for row in c.fetchall()]


def completar_tarea(tarea_id: int) -> str | None:
    """Mueve la tarea a completadas y retorna su texto. None si no existe."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT texto, creada_en FROM tareas WHERE id = ?", (tarea_id,))
        row = c.fetchone()
        if not row:
            return None
        texto, creada_en = row["texto"], row["creada_en"]
        ahora = datetime.now().isoformat()
        c.execute(
            "INSERT INTO completadas (texto, creada_en, completada_en) VALUES (?, ?, ?)",
            (texto, creada_en, ahora)
        )
        c.execute("DELETE FROM tareas WHERE id = ?", (tarea_id,))
        conn.commit()
        return texto


def borrar_tarea(tarea_id: int) -> str | None:
    """Elimina la tarea sin registrarla como completada. None si no existe."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT texto FROM tareas WHERE id = ?", (tarea_id,))
        row = c.fetchone()
        if not row:
            return None
        texto = row["texto"]
        c.execute("DELETE FROM tareas WHERE id = ?", (tarea_id,))
        conn.commit()
        return texto


# ── FRASES ────────────────────────────────────────────────────────────────────

def obtener_frase() -> tuple[str, str]:
    """Retorna (texto, autor) de una frase aleatoria no usada.
    Si se agotan todas, reinicia el ciclo.
    """
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id, texto, autor FROM frases WHERE usada = 0")
        disponibles = c.fetchall()

        if not disponibles:
            c.execute("UPDATE frases SET usada = 0")
            conn.commit()
            c.execute("SELECT id, texto, autor FROM frases")
            disponibles = c.fetchall()

        frase = random.choice(disponibles)
        c.execute("UPDATE frases SET usada = 1 WHERE id = ?", (frase["id"],))
        conn.commit()
        return frase["texto"], frase["autor"]


# ── CONFIG ────────────────────────────────────────────────────────────────────

def get_config(clave: str, default: str = None) -> str | None:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT valor FROM config WHERE clave = ?", (clave,))
        row = c.fetchone()
        return row["valor"] if row else default


def set_config(clave: str, valor: str):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO config (clave, valor) VALUES (?, ?)",
            (clave, valor)
        )
        conn.commit()
