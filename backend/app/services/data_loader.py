"""
Data Loader - Carga, limpieza y normalización del dataset de Microsoft Clarity.
===============================================================================
Este módulo es ADAPTABLE. Cuando reciban el dataset real, solo hay que ajustar
los nombres de columnas en COLUMN_MAP.
"""

import pandas as pd
import numpy as np
import os
import glob
from urllib.parse import urlparse


# ─── Mapeo de columnas ─────────────────────────────────────────
# CLAVE: nombre que usamos internamente
# VALOR: posibles nombres que puede tener en el CSV real
# Cuando reciban el dataset, ajusten estos mappings

COLUMN_MAP = {
    "session_id": ["session_id", "sessionid", "id_sesion", "id_usuario_clarity", "userid", "user_id"],
    "timestamp": ["timestamp", "fecha_hora", "datetime", "time"],
    "page": ["page", "pagina", "url", "direccion_url_entrada", "url", "Url"],
    "event": ["event", "evento", "tipo_evento", "metricName"],
    "product": ["product", "producto", "nombre_producto"],
    "exit_page": ["exit_page", "pagina_salida", "abandono", "abandono_rapido", "quickbacktotop"],
    "scroll": ["scroll", "scroll_depth", "porcentaje_scroll", "averagescrolldepth", "averageScrollDepth"],
    "clicks": ["clicks", "clics", "clics_sesion", "clicks_por_pagina", "interaction_total"],
    "duration": ["duration", "duracion", "duracion_sesion", "duracion_sesion_segundos", "tiempo_por_pagina", "totaltime", "activetime"],
    "device": ["device", "dispositivo", "Device"],
    "browser": ["browser", "navegador", "explorador"],
    "os": ["os", "sistema_operativo", "OS"],
    "country": ["country", "pais"],
    "referrer": ["referrer", "referente", "fuente"],
    "pages_count": ["pages_count", "recuento_paginas"],
    "engagement_score": ["engagement_score", "standarized_engagement_score"],
    "is_home_entry": ["is_home_entry", "entrada_es_home"],
    "is_external": ["is_external", "trafico_externo"],
    "interaction_total": ["interaction_total", "interaccion_total"],
    "possible_frustration": ["possible_frustration", "posible_frustracion"],
}


class DataLoader:
    """
    Carga el dataset CSV, lo limpia y normaliza para que el motor
    analítico trabaje con nombres de columna consistentes.
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.df: pd.DataFrame = pd.DataFrame()
        self.df_metrics: pd.DataFrame = pd.DataFrame()  # Tabla de métricas si existe
        self.is_loaded: bool = False
        self._raw_columns: list[str] = []

    def load_data(self, filepath: str = None):
        """
        Carga el CSV. Si no se da filepath, busca cualquier .csv en /data.
        """
        if filepath is None:
            filepath = self._find_csv()

        if filepath is None:
            print("No se encontró dataset CSV. Generando datos de ejemplo...")
            self._generate_sample_data()
            self.is_loaded = True
            return

        print(f"Cargando: {filepath}")

        # Intentar diferentes encodings comunes en datasets latinos
        for encoding in ["utf-8", "latin-1", "cp1252", "iso-8859-1"]:
            try:
                df = pd.read_csv(filepath, encoding=encoding)
                break
            except (UnicodeDecodeError, Exception):
                continue
        else:
            raise ValueError(f"No se pudo leer el archivo {filepath}")

        self._raw_columns = list(df.columns)
        print(f"   Columnas originales: {self._raw_columns}")

        # Limpiar nombres de columnas
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

        # Normalizar columnas al esquema interno
        df = self._normalize_columns(df)
        df = self._combine_timestamp_columns(df)

        # Limpieza de datos
        df = self._clean_data(df)

        self.df = df
        self.is_loaded = True

        # Intentar cargar tabla de métricas si existe
        self._try_load_metrics()
        self._enrich_from_metrics()

    def _find_csv(self) -> str | None:
        """Busca archivos CSV en el directorio de datos."""
        patterns = [
            os.path.join(self.data_dir, "*.csv"),
            os.path.join(self.data_dir, "**", "*.csv"),
        ]
        for pattern in patterns:
            files = glob.glob(pattern, recursive=True)
            if files:
                # Si hay múltiples CSVs, tomar el más grande (probablemente recordings)
                return max(files, key=os.path.getsize)
        return None

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        alias_lookup = {
            internal_name: {name.lower().replace(" ", "_") for name in possible_names}
            for internal_name, possible_names in COLUMN_MAP.items()
        }

        for internal_name, possible_names in COLUMN_MAP.items():
            normalized_aliases = alias_lookup[internal_name]
            candidates = [col for col in df.columns if col in normalized_aliases]
            if not candidates:
                continue

            if internal_name not in df.columns:
                if len(candidates) == 1:
                    df[internal_name] = df[candidates[0]]
                else:
                    merged = df[candidates[0]]
                    for col in candidates[1:]:
                        left_valid = merged.notna() & (merged.astype(str).str.strip() != "")
                        merged = merged.where(left_valid, df[col])
                    df[internal_name] = merged

            for col in candidates:
                if col != internal_name and col in df.columns:
                    df = df.drop(columns=[col])

        return df

    def _combine_timestamp_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        if "timestamp" in df.columns:
            return df

        fecha_col = "fecha" if "fecha" in df.columns else None
        hora_col = "hora" if "hora" in df.columns else None

        if fecha_col and hora_col:
            combined = df[fecha_col].astype(str).str.strip() + " " + df[hora_col].astype(str).str.strip()
            df["timestamp"] = pd.to_datetime(combined, errors="coerce", dayfirst=True)
        elif fecha_col:
            df["timestamp"] = pd.to_datetime(df[fecha_col], errors="coerce", dayfirst=True)
        elif hora_col:
            df["timestamp"] = pd.to_datetime(df[hora_col], errors="coerce")

        return df

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpieza y validación de tipos."""

        # Si no hay session_id, crear uno basado en índice
        if "session_id" not in df.columns:
            df["session_id"] = range(len(df))

        # Parsear timestamps si existen
        if "timestamp" in df.columns:
            try:
                df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
            except Exception:
                pass

        # Asegurar que scroll sea numérico
        if "scroll" in df.columns:
            df["scroll"] = pd.to_numeric(df["scroll"], errors="coerce").fillna(0)

        # Asegurar que clicks sea numérico
        if "clicks" in df.columns:
            df["clicks"] = pd.to_numeric(df["clicks"], errors="coerce").fillna(0)

        # Asegurar que duration sea numérico
        if "duration" in df.columns:
            df["duration"] = pd.to_numeric(df["duration"], errors="coerce").fillna(0)

        # Engagement score numérico
        if "engagement_score" in df.columns:
            df["engagement_score"] = pd.to_numeric(
                df["engagement_score"], errors="coerce"
            ).fillna(0)

        # Limpiar páginas: quitar espacios, normalizar
        if "page" in df.columns:
            df["page"] = df["page"].astype(str).str.strip().apply(self._normalize_page_value)
            # Quitar filas donde page es 'nan' o vacío
            df = df[df["page"].notna() & (df["page"] != "nan") & (df["page"] != "")]

        # Booleanos
        for col in ["exit_page", "is_home_entry", "is_external", "possible_frustration"]:
            if col in df.columns:
                df[col] = df[col].map(
                    {True: True, False: False, "True": True, "False": False,
                     "true": True, "false": False, "Si": True, "No": False,
                     "TRUE": True, "FALSE": False, "Yes": True, 1: True, 0: False}
                ).fillna(False)

        return df

    def _try_load_metrics(self):
        """Intenta cargar una segunda tabla de métricas si existe."""
        files = glob.glob(os.path.join(self.data_dir, "*.csv"))
        if len(files) > 1:
            # El archivo más pequeño probablemente es la tabla de métricas
            metrics_file = min(files, key=os.path.getsize)
            if metrics_file != self._find_csv():
                for encoding in ["utf-8", "latin-1", "cp1252", "iso-8859-1"]:
                    try:
                        self.df_metrics = pd.read_csv(metrics_file, encoding=encoding)
                        self.df_metrics.columns = (
                            self.df_metrics.columns.str.strip().str.lower().str.replace(" ", "_")
                        )
                        self.df_metrics = self._normalize_columns(self.df_metrics)
                        print(f"Tabla de métricas cargada: {metrics_file}")
                        break
                    except Exception:
                        continue

    def _normalize_page_value(self, value: str) -> str:
        raw = str(value).strip()
        if not raw:
            return raw
        parsed = urlparse(raw)
        if parsed.scheme and parsed.netloc:
            path = parsed.path or "/"
            return path.strip().lower()
        return raw.lower()

    def _enrich_from_metrics(self):
        if self.df.empty or self.df_metrics.empty or "page" not in self.df.columns:
            return

        metrics = self.df_metrics.copy()
        if "page" not in metrics.columns:
            return

        metrics["page"] = metrics["page"].astype(str).str.strip().apply(self._normalize_page_value)

        if "scroll" in metrics.columns:
            metrics["scroll"] = pd.to_numeric(metrics["scroll"], errors="coerce")
        if "clicks" in metrics.columns:
            metrics["clicks"] = pd.to_numeric(metrics["clicks"], errors="coerce")
        if "duration" in metrics.columns:
            metrics["duration"] = pd.to_numeric(metrics["duration"], errors="coerce")
        if "engagement_score" in metrics.columns:
            metrics["engagement_score"] = pd.to_numeric(metrics["engagement_score"], errors="coerce")

        agg_ops = {}
        for metric_col in ["scroll", "clicks", "duration", "engagement_score"]:
            if metric_col in metrics.columns:
                agg_ops[metric_col] = (metric_col, "mean")

        if not agg_ops:
            return

        metrics_page = metrics.groupby("page").agg(**agg_ops).reset_index()

        merged = self.df.merge(metrics_page, on="page", how="left", suffixes=("", "_metrics"))
        for metric_col in agg_ops.keys():
            metrics_col = f"{metric_col}_metrics"
            if metrics_col in merged.columns and metric_col in merged.columns:
                merged[metric_col] = pd.to_numeric(merged[metric_col], errors="coerce").fillna(merged[metrics_col])
                merged = merged.drop(columns=[metrics_col])
            elif metrics_col in merged.columns:
                merged[metric_col] = merged[metrics_col]
                merged = merged.drop(columns=[metrics_col])

        self.df = merged

    def _generate_sample_data(self):
        """
        Genera datos de ejemplo para desarrollo y testing.
        Simula un dataset de Clarity realista.
        """
        np.random.seed(42)
        n_sessions = 500
        n_events = 3000

        pages = [
            "/home", "/pricing", "/products", "/products/cloudlabs-fisica",
            "/products/cloudlabs-quimica", "/products/cloudlabs-matematicas",
            "/about", "/contact", "/blog", "/blog/stem-education",
            "/demo", "/signup", "/resources", "/faq",
        ]
        devices = ["Desktop", "Mobile", "Tablet"]
        browsers = ["Chrome", "Firefox", "Safari", "Edge"]
        countries = ["Colombia", "Mexico", "USA", "Spain", "Argentina", "Chile", "Peru"]
        events = ["page_view", "click", "scroll"]

        sessions = [f"SES-{i:04d}" for i in range(n_sessions)]

        data = []
        for _ in range(n_events):
            session = np.random.choice(sessions)
            page = np.random.choice(pages, p=[
                0.18, 0.12, 0.10, 0.08, 0.07, 0.06,
                0.05, 0.06, 0.05, 0.04, 0.07, 0.04, 0.04, 0.04
            ])
            data.append({
                "session_id": session,
                "timestamp": pd.Timestamp("2026-03-27") + pd.Timedelta(
                    hours=np.random.randint(0, 24),
                    minutes=np.random.randint(0, 60),
                    seconds=np.random.randint(0, 60),
                ),
                "page": page,
                "event": np.random.choice(events, p=[0.5, 0.3, 0.2]),
                "product": page.split("/")[-1] if "products" in page else None,
                "exit_page": np.random.random() < 0.15,
                "scroll": round(np.random.uniform(0, 100), 1),
                "clicks": np.random.randint(0, 10),
                "duration": round(np.random.uniform(5, 300), 1),
                "device": np.random.choice(devices, p=[0.55, 0.35, 0.10]),
                "browser": np.random.choice(browsers),
                "os": np.random.choice(["Windows", "MacOS", "Android", "iOS"]),
                "country": np.random.choice(countries, p=[0.30, 0.20, 0.15, 0.10, 0.10, 0.08, 0.07]),
                "engagement_score": round(np.random.uniform(1, 10), 1),
                "is_home_entry": page == "/home",
                "is_external": np.random.random() < 0.3,
            })

        self.df = pd.DataFrame(data)
        print(f"Datos de ejemplo: {len(self.df)} registros, {n_sessions} sesiones")

    # ─── Helpers rápidos ───────────────────────────────────────

    def total_sessions(self) -> int:
        if "session_id" in self.df.columns:
            return self.df["session_id"].nunique()
        return len(self.df)

    def total_rows(self) -> int:
        return len(self.df)

    def get_columns(self) -> list[str]:
        return list(self.df.columns)
