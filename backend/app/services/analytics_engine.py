"""
Analytics Engine - Motor de análisis de datos de comportamiento web.
===================================================================
Calcula los 5 insights requeridos + 3 adicionales.

INSIGHTS REQUERIDOS:
  1. Páginas/Productos Top (ranking por vistas e interacciones)
  2. Puntos Críticos de Abandono (tasa de salida por página)
  3. Flujos de Navegación (secuencias más frecuentes)
  4. Interacción Promedio por Página (clics, scroll, tiempo)
  5. Patrones de Conversión (comportamiento hacia páginas clave)

INSIGHTS ADICIONALES:
  6. Segmentación por dispositivo y país
  7. Páginas "trampa" (alto tráfico, bajo engagement)
  8. Engagement Score por hora del día
"""

import pandas as pd
import numpy as np
from typing import Optional
import re
from urllib.parse import urlparse, unquote


class AnalyticsEngine:
    """Ejecuta todos los cálculos analíticos sobre el DataFrame."""

    # Páginas consideradas de "alto interés" para conversión
    CONVERSION_PAGES = ["pricing", "contact", "signup", "demo", "precios", "contacto"]

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def _has_column(self, col: str) -> bool:
        return col in self.df.columns

    def _to_safe_records(self, df: pd.DataFrame) -> list[dict]:
        cleaned = df.replace([np.inf, -np.inf], np.nan).where(pd.notna(df), None)
        return cleaned.to_dict("records")

    def _humanize_page_name(self, page_url: str) -> str:
        """
        Convierte URLs técnicas en nombres amigables para marketing.
        
        Ejemplos:
        - '/curriculum/country-list/...' → 'Currículum - Catálogo de países'
        - '/pricing' → 'Precios'
        - '/contact' → 'Contacto'
        - '/product/python-101' → 'Product: Python 101'
        """
        if not page_url or not isinstance(page_url, str):
            return "Página desconocida"

        raw_url = page_url.strip()
        parsed = urlparse(raw_url)
        url = (parsed.path if (parsed.scheme or parsed.netloc) else raw_url).strip().lower()
        if not url:
            return "Inicio"
        if url != "/":
            url = url.rstrip("/")
        url = unquote(url)
        
        # Extraer información útil de URLs complejas
        # Si es curriculum detail, extraer el nombre del curso
        if "curriculum" in url and "detail-grade" in url:
            # Extraer el último segmento antes de números (grade/course name)
            match = re.search(r'/detail-grade/\d+/([a-z0-9\-_]+)', url)
            if match:
                course = match.group(1).replace('%20', ' ').replace('-', ' ').title()
                # Extraer país si existe
                country_match = re.search(r'/tennessee|/california|/florida|/texas|/\w+(?=/)', url)
                if country_match:
                    location = country_match.group(0).strip('/').title()
                    return f"Curso: {course} ({location})"
                return f"Curso: {course}"
        
        # URLs comunes de marketing
        mappings = {
            "/pricing": "Precios",
            "/contact": "Contacto",
            "/signup": "Registrarse",
            "/register": "Register",
            "/login": "Iniciar sesión",
            "/demo": "Demo",
            "/request-demo": "Request Demo",
            "/request_demo": "Request Demo",
            "/products": "Productos",
            "/curriculum": "Currículum",
            "/courses": "Cursos",
            "/home": "Inicio",
            "/inicio": "Inicio",
            "/downloads": "Downloads",
            "/download": "Downloads",
            "/elementary-school": "Elementary School",
            "/middle-school": "Middle School",
            "": "Inicio",
            "/": "Inicio",
            "/faq": "Preguntas frecuentes",
            "/help": "Ayuda",
        }

        if url in mappings:
            return mappings[url]

        parts = [p for p in url.split('/') if p and not p.isdigit() and p != 'detail-' and 'id' not in p]
        parts = [p for p in parts if not re.fullmatch(r"[a-f0-9]{8,}", p)]
        if parts and parts[0] in {"register", "signup"}:
            return "Register"
        if parts:
            readable = " → ".join(
                p.replace("%20", " ").replace("_", " ").replace("-", " ").title()
                for p in parts[:3]
            )
            return readable if len(readable) < 50 else readable[:47] + "..."

        return page_url[:50] + "..." if len(page_url) > 50 else page_url


    # ═══════════════════════════════════════════════════════════
    # INSIGHT 1: Páginas y Productos Top
    # ═══════════════════════════════════════════════════════════

    def get_top_pages(self, limit: int = 10) -> list[dict]:
        """
        Ranking de páginas con mayor número de vistas e interacciones.
        Retorna: [{page, page_name, views, interactions, percentage}]
        """
        if not self._has_column("page"):
            return []

        # Contar vistas por página
        page_views = self.df.groupby("page").agg(
            views=("page", "count"),
            avg_scroll=("scroll", "mean") if self._has_column("scroll") else ("page", "count"),
            avg_clicks=("clicks", "mean") if self._has_column("clicks") else ("page", "count"),
        ).reset_index()

        total = len(self.df)
        page_views["percentage"] = round(page_views["views"] / total * 100, 2)
        page_views = page_views.sort_values("views", ascending=False).head(limit)
        
        # Humanizar nombres de página para marketing
        page_views["page_name"] = page_views["page"].apply(self._humanize_page_name)

        return self._to_safe_records(page_views)

    def get_top_products(self, limit: int = 10) -> list[dict]:
        """Ranking de productos más consultados."""
        if not self._has_column("product"):
            return []

        products = self.df[self.df["product"].notna() & (self.df["product"] != "")]
        if products.empty:
            return []

        product_views = products.groupby("product").agg(
            views=("product", "count"),
        ).reset_index()

        total_sessions = self.df["session_id"].nunique() if self._has_column("session_id") else len(self.df)
        product_views["session_percentage"] = round(
            product_views["views"] / total_sessions * 100, 2
        )
        product_views = product_views.sort_values("views", ascending=False).head(limit)

        return self._to_safe_records(product_views)

    # ═══════════════════════════════════════════════════════════
    # INSIGHT 2: Puntos Críticos de Abandono
    # ═══════════════════════════════════════════════════════════

    def get_abandono(self, limit: int = 10, min_visits: int = 5) -> list[dict]:
        """
        Calcula tasa de salida por página (puntos críticos de abandono).
        
        exit_rate = (sesiones que terminan en esta página / total visitas a la página) * 100
        
        FILTRO: Solo incluye páginas con mínimo min_visits visitas para evitar ruido estadístico.
        Páginas con pocas visitas y 100% abandono NO son puntos críticos - son probablemente
        landing pages, páginas de error o destinos finales.
        """
        if not self._has_column("page"):
            return []

        total_visits = self.df.groupby("page").size().reset_index(name="total_visits")
        
        # FILTRO CRÍTICO: Eliminar páginas con muy baja visibilidad
        # Esto evita que páginas específicas de error/confirmación aparezcan como "problemas"
        total_visits = total_visits[total_visits["total_visits"] >= min_visits]
        
        if total_visits.empty:
            return []

        # Método 1: Si tenemos columna exit_page (booleana)
        if self._has_column("exit_page"):
            exits = self.df[self.df["exit_page"] == True].groupby("page").size().reset_index(name="exit_count")
        # Método 2: Inferir del flujo — última página de cada sesión
        elif self._has_column("session_id") and self._has_column("timestamp"):
            last_pages = (
                self.df.sort_values("timestamp")
                .groupby("session_id")
                .tail(1)
            )
            exits = last_pages.groupby("page").size().reset_index(name="exit_count")
        else:
            # Método 3: Sin timestamp, asumir que la última fila por sesión es la salida
            if self._has_column("session_id"):
                last_pages = self.df.groupby("session_id").tail(1)
                exits = last_pages.groupby("page").size().reset_index(name="exit_count")
            else:
                return []

        result = total_visits.merge(exits, on="page", how="left")
        result["exit_count"] = result["exit_count"].fillna(0).astype(int)
        result["exit_rate"] = round(result["exit_count"] / result["total_visits"] * 100, 2)
        
        # SEGUNDA ESTRATEGIA: Filtra valores > 90% si no hay suficiente volumen
        # Esto evita falsos positivos de abandono
        result = result[
            (result["exit_rate"] < 90) |  # Mantén rates < 90%
            (result["total_visits"] >= 20)  # O si tienes >= 20 visitas entonces sí incluye
        ]
        
        result = result.sort_values("exit_rate", ascending=False).head(limit)
        
        # Humanizar nombres de página para marketing
        result["page_name"] = result["page"].apply(self._humanize_page_name)

        return self._to_safe_records(result)

    # ═══════════════════════════════════════════════════════════
    # INSIGHT 3: Flujos de Navegación
    # ═══════════════════════════════════════════════════════════

    def get_flujos(self, limit: int = 10, sequence_length: int = 3) -> list[dict]:
        """
        Identifica las secuencias de navegación más frecuentes.
        Agrupa páginas por sesión ordenadas por timestamp y extrae n-gramas.
        """
        if not self._has_column("session_id") or not self._has_column("page"):
            return []

        # Obtener secuencia de páginas por sesión
        if self._has_column("timestamp"):
            ordered = self.df.sort_values(["session_id", "timestamp"])
        else:
            ordered = self.df

        # Solo page_views si tenemos tipo de evento
        if self._has_column("event"):
            ordered = ordered[ordered["event"].isin(["page_view", "pageview", "view"])]
            if ordered.empty:
                ordered = self.df  # Fallback: usar todo

        # Agrupar páginas por sesión
        session_pages = ordered.groupby("session_id")["page"].apply(list).reset_index()

        # Extraer secuencias (n-gramas)
        sequences = []
        for _, row in session_pages.iterrows():
            pages = row["page"]
            # Eliminar páginas consecutivas duplicadas
            deduped = [pages[0]] + [p for i, p in enumerate(pages[1:]) if p != pages[i]]
            for i in range(len(deduped) - sequence_length + 1):
                seq = tuple(deduped[i:i + sequence_length])
                sequences.append(seq)

        if not sequences:
            return []

        seq_counts = pd.Series(sequences).value_counts().head(limit)
        total_sequences = len(sequences)

        result = []
        for seq, count in seq_counts.items():
            result.append({
                "sequence": list(seq),
                "count": int(count),
                "percentage": round(count / total_sequences * 100, 2),
            })

        return result

    # ═══════════════════════════════════════════════════════════
    # INSIGHT 4: Interacción Promedio por Página
    # ═══════════════════════════════════════════════════════════

    def get_interaccion(self, limit: int = 15) -> list[dict]:
        """
        Promedio de clics, scroll y tiempo por página.
        """
        if not self._has_column("page"):
            return []

        agg_dict = {}
        if self._has_column("clicks"):
            agg_dict["avg_clicks"] = ("clicks", "mean")
        if self._has_column("scroll"):
            agg_dict["avg_scroll"] = ("scroll", "mean")
        if self._has_column("duration"):
            agg_dict["avg_duration"] = ("duration", "mean")
        if self._has_column("engagement_score"):
            agg_dict["avg_engagement"] = ("engagement_score", "mean")

        agg_dict["total_events"] = ("page", "count")

        if not agg_dict:
            return []

        result = self.df.groupby("page").agg(**agg_dict).reset_index()

        # Redondear
        for col in result.columns:
            if col.startswith("avg_"):
                result[col] = result[col].round(2)

        result = result.sort_values("total_events", ascending=False).head(limit)
        return self._to_safe_records(result)

    # ═══════════════════════════════════════════════════════════
    # INSIGHT 5: Patrones de Conversión
    # ═══════════════════════════════════════════════════════════

    def get_conversion(self) -> list[dict]:
        """
        Analiza comportamiento hacia páginas de alto interés (pricing, contacto, etc).
        - ¿Qué porcentaje de sesiones llega a estas páginas?
        - ¿De dónde vienen?
        - ¿Cuál es el engagement promedio antes de llegar?
        """
        if not self._has_column("page") or not self._has_column("session_id"):
            return []

        total_sessions = self.df["session_id"].nunique()
        results = []

        for keyword in self.CONVERSION_PAGES:
            # Sesiones que visitaron esta página clave
            matching_pages = self.df[self.df["page"].str.contains(keyword, case=False, na=False)]
            if matching_pages.empty:
                continue

            sessions_reached = matching_pages["session_id"].nunique()
            reach_rate = round(sessions_reached / total_sessions * 100, 2)

            # Páginas previas (de dónde vienen)
            conversion_sessions = matching_pages["session_id"].unique()
            session_data = self.df[self.df["session_id"].isin(conversion_sessions)]

            if self._has_column("timestamp"):
                session_data = session_data.sort_values(["session_id", "timestamp"])

            # Obtener página anterior a la de conversión
            prev_pages = []
            for sid in conversion_sessions[:100]:  # Limitar para performance
                session_flow = session_data[session_data["session_id"] == sid]["page"].tolist()
                for i, p in enumerate(session_flow):
                    if keyword in p and i > 0:
                        prev_pages.append(session_flow[i - 1])

            top_sources = {}
            for p in prev_pages:
                top_sources[p] = top_sources.get(p, 0) + 1
            top_sources = sorted(top_sources.items(), key=lambda x: x[1], reverse=True)[:5]

            avg_engagement = 0
            if self._has_column("engagement_score"):
                avg_engagement = round(session_data["engagement_score"].mean(), 2)
                if pd.isna(avg_engagement):
                    avg_engagement = 0

            results.append({
                "conversion_page": keyword,
                "sessions_reached": int(sessions_reached),
                "total_sessions": int(total_sessions),
                "reach_rate": reach_rate,
                "top_sources": [{"page": p, "count": c} for p, c in top_sources],
                "avg_engagement": avg_engagement,
            })

        return results

    # ═══════════════════════════════════════════════════════════
    # INSIGHT ADICIONAL 6: Segmentación por Dispositivo y País
    # ═══════════════════════════════════════════════════════════

    def get_segmentation(self) -> dict:
        """Distribución de sesiones por dispositivo, navegador y país."""
        result = {}

        if self._has_column("device"):
            device_counts = self.df.groupby("device")["session_id"].nunique() if self._has_column("session_id") else self.df["device"].value_counts()
            result["by_device"] = [
                {"name": k, "count": int(v)}
                for k, v in device_counts.items()
            ]

        if self._has_column("country"):
            country_counts = self.df.groupby("country")["session_id"].nunique() if self._has_column("session_id") else self.df["country"].value_counts()
            country_counts = country_counts.sort_values(ascending=False).head(10)
            result["by_country"] = [
                {"name": k, "count": int(v)}
                for k, v in country_counts.items()
            ]

        if self._has_column("browser"):
            browser_counts = self.df["browser"].value_counts().head(5)
            result["by_browser"] = [
                {"name": k, "count": int(v)}
                for k, v in browser_counts.items()
            ]

        return result

    # ═══════════════════════════════════════════════════════════
    # INSIGHT ADICIONAL 7: Páginas "Trampa" (tráfico alto, engagement bajo)
    # ═══════════════════════════════════════════════════════════

    def get_trap_pages(self, limit: int = 10) -> list[dict]:
        """
        Detecta páginas que atraen mucho tráfico pero no retienen al usuario.
        Criterio: alto número de vistas + bajo scroll + alta tasa de salida.
        """
        if not self._has_column("page"):
            return []

        agg_dict = {"views": ("page", "count")}
        if self._has_column("scroll"):
            agg_dict["avg_scroll"] = ("scroll", "mean")
        if self._has_column("duration"):
            agg_dict["avg_duration"] = ("duration", "mean")
        if self._has_column("exit_page"):
            agg_dict["exit_count"] = ("exit_page", "sum")
        if self._has_column("engagement_score"):
            agg_dict["avg_engagement"] = ("engagement_score", "mean")

        pages = self.df.groupby("page").agg(**agg_dict).reset_index()

        # Calcular un "trap score" — páginas con alto tráfico pero bajo engagement
        median_views = pages["views"].median()
        pages_high_traffic = pages[pages["views"] >= median_views].copy()

        if pages_high_traffic.empty:
            return []

        # Normalizar métricas para scoring
        if "avg_scroll" in pages_high_traffic.columns:
            max_scroll = pages_high_traffic["avg_scroll"].max()
            if max_scroll > 0:
                pages_high_traffic["scroll_score"] = 1 - (pages_high_traffic["avg_scroll"] / max_scroll)
            else:
                pages_high_traffic["scroll_score"] = 0.5
        else:
            pages_high_traffic["scroll_score"] = 0.5

        if "exit_count" in pages_high_traffic.columns:
            pages_high_traffic["exit_rate"] = pages_high_traffic["exit_count"] / pages_high_traffic["views"]
        else:
            pages_high_traffic["exit_rate"] = 0.5

        pages_high_traffic["trap_score"] = (
            pages_high_traffic["scroll_score"] * 0.5 +
            pages_high_traffic["exit_rate"] * 0.5
        ).round(3)

        result = pages_high_traffic.sort_values("trap_score", ascending=False).head(limit)

        # Redondear
        for col in result.columns:
            if result[col].dtype in ["float64", "float32"]:
                result[col] = result[col].round(2)

        return self._to_safe_records(result)

    # ═══════════════════════════════════════════════════════════
    # INSIGHT ADICIONAL 8: Engagement por Hora del Día
    # ═══════════════════════════════════════════════════════════

    def get_engagement_by_hour(self) -> list[dict]:
        """
        Muestra cómo varía el engagement a lo largo del día.
        Útil para decidir cuándo lanzar campañas.
        """
        if not self._has_column("timestamp"):
            return []

        df_temp = self.df.copy()
        df_temp["hour"] = pd.to_datetime(df_temp["timestamp"], errors="coerce").dt.hour

        agg_dict = {"sessions": ("session_id", "nunique") if self._has_column("session_id") else ("hour", "count")}
        if self._has_column("engagement_score"):
            agg_dict["avg_engagement"] = ("engagement_score", "mean")
        if self._has_column("clicks"):
            agg_dict["avg_clicks"] = ("clicks", "mean")

        hourly = df_temp.groupby("hour").agg(**agg_dict).reset_index()

        for col in hourly.columns:
            if hourly[col].dtype in ["float64", "float32"]:
                hourly[col] = hourly[col].round(2)

        return self._to_safe_records(hourly)

    # ═══════════════════════════════════════════════════════════
    # DASHBOARD - Resumen General
    # ═══════════════════════════════════════════════════════════

    def get_dashboard_summary(self) -> dict:
        """Métricas resumen para el dashboard principal."""
        total_sessions = self.df["session_id"].nunique() if self._has_column("session_id") else 0
        total_rows = len(self.df)

        summary = {
            "total_sessions": int(total_sessions),
            "total_events": int(total_rows),
            "total_pages": int(self.df["page"].nunique()) if self._has_column("page") else 0,
        }

        if self._has_column("session_id") and self._has_column("page"):
            pages_per_session = self.df.groupby("session_id")["page"].nunique().mean()
            summary["avg_pages_per_session"] = round(float(pages_per_session), 2)

        if self._has_column("duration"):
            summary["avg_session_duration"] = round(float(self.df["duration"].mean()), 2)

        if self._has_column("engagement_score"):
            summary["avg_engagement_score"] = round(float(self.df["engagement_score"].mean()), 2)

        if self._has_column("scroll"):
            summary["avg_scroll_depth"] = round(float(self.df["scroll"].mean()), 2)

        # Tasa de rebote aproximada (sesiones con 1 sola página)
        if self._has_column("session_id") and self._has_column("page"):
            pages_per_sess = self.df.groupby("session_id")["page"].nunique()
            bounces = (pages_per_sess == 1).sum()
            summary["bounce_rate"] = round(float(bounces / total_sessions * 100), 2)

        return summary

    # ═══════════════════════════════════════════════════════════
    # HELPER: Buscar datos por pregunta (para el LLM)
    # ═══════════════════════════════════════════════════════════

    def answer_question(self, question: str) -> dict:
        """
        Dada una pregunta en texto, determina qué análisis ejecutar
        y devuelve los datos relevantes + una respuesta base amigable.
        """
        q = question.lower()

        # Mapeo de keywords a funciones
        if any(w in q for w in ["más visto", "más visitada", "top página", "top pagina", "más tráfico", "ranking"]):
            data = self.get_top_pages(5)
            if data:
                top = data[0]
                return {
                    "intent": "top_pages",
                    "data": data,
                    "answer": f"La página más visitada es '{top.get('page_name', top['page'])}' con {top['views']} vistas ({top.get('percentage', 0)}% del total).",
                    "chart": {"type": "horizontal_bar", "labels": [d.get('page_name', d['page']) for d in data], "values": [d["views"] for d in data], "label": "Vistas"},
                }

        if any(w in q for w in ["producto más", "producto top", "más consultado"]):
            data = self.get_top_products(5)
            if data:
                top = data[0]
                return {
                    "intent": "top_products",
                    "data": data,
                    "answer": f"El producto más consultado es '{top['product']}' con {top['views']} vistas ({top.get('session_percentage', 0)}% de las sesiones).",
                    "chart": {"type": "bar", "labels": [d["product"] for d in data], "values": [d["views"] for d in data], "label": "Vistas"},
                }

        if any(w in q for w in ["abandono", "salida", "abandonan", "exit", "tasa de salida"]):
            data = self.get_abandono(5)
            if data:
                top = data[0]
                return {
                    "intent": "abandono",
                    "data": data,
                    "answer": f"La página con mayor tasa de abandono es '{top.get('page_name', top['page'])}' con {top['exit_rate']}% de tasa de salida ({top['exit_count']} salidas de {top['total_visits']} visitas).",
                    "chart": {"type": "bar", "labels": [d.get('page_name', d['page']) for d in data], "values": [d["exit_rate"] for d in data], "label": "Tasa de salida (%)"},
                }

        if any(w in q for w in ["flujo", "recorrido", "navegación", "secuencia", "camino"]):
            data = self.get_flujos(5)
            if data:
                top = data[0]
                return {
                    "intent": "flujos",
                    "data": data,
                    "answer": f"El flujo de navegación más frecuente es: {' → '.join(top['sequence'])} ({top['count']} veces, {top['percentage']}% del total).",
                    "chart": None,
                }

        if any(w in q for w in ["interacción", "interaccion", "engagement", "clics", "scroll", "tiempo"]):
            data = self.get_interaccion(5)
            if data:
                return {
                    "intent": "interaccion",
                    "data": data,
                    "answer": f"Las métricas de interacción muestran que '{data[0]['page']}' tiene la mayor actividad con {data[0].get('avg_clicks', 0)} clics promedio y {data[0].get('avg_scroll', 0)}% de scroll promedio.",
                    "chart": None,
                }

        if any(w in q for w in ["conversión", "conversion", "pricing", "contacto", "intención", "intencion"]):
            data = self.get_conversion()
            if data:
                return {
                    "intent": "conversion",
                    "data": data,
                    "answer": f"Análisis de conversión: " + "; ".join([
                        f"'{d['conversion_page']}' alcanzada por {d['reach_rate']}% de las sesiones"
                        for d in data
                    ]),
                    "chart": {"type": "bar", "labels": [d["conversion_page"] for d in data], "values": [d["reach_rate"] for d in data], "label": "Tasa de alcance (%)"},
                }

        if any(w in q for w in ["dispositivo", "device", "móvil", "desktop", "país", "pais"]):
            data = self.get_segmentation()
            return {
                "intent": "segmentation",
                "data": data,
                "answer": self._format_segmentation(data),
                "chart": None,
            }

        if any(w in q for w in ["trampa", "no retiene", "alto tráfico bajo", "atrae pero no"]):
            data = self.get_trap_pages(5)
            if data:
                return {
                    "intent": "trap_pages",
                    "data": data,
                    "answer": f"Páginas con alto tráfico pero bajo engagement: " + ", ".join([
                        f"'{d['page']}' (trap score: {d.get('trap_score', 0)})"
                        for d in data[:3]
                    ]),
                    "chart": None,
                }

        if any(w in q for w in ["hora", "horario", "cuándo", "cuando", "mejor momento"]):
            data = self.get_engagement_by_hour()
            if data:
                best = max(data, key=lambda x: x.get("avg_engagement", x.get("sessions", 0)))
                return {
                    "intent": "hourly",
                    "data": data,
                    "answer": f"La hora con mayor engagement es las {best['hour']}:00 con un score promedio de {best.get('avg_engagement', 'N/A')}.",
                    "chart": {"type": "line", "labels": [f"{d['hour']}:00" for d in data], "values": [d.get("avg_engagement", d.get("sessions", 0)) for d in data], "label": "Engagement"},
                }

        if any(w in q for w in ["resumen", "general", "dashboard", "overview", "cómo va"]):
            data = self.get_dashboard_summary()
            return {
                "intent": "summary",
                "data": data,
                "answer": self._format_summary(data),
                "chart": None,
            }

        # Default: dar resumen + sugerir preguntas
        return {
            "intent": "unknown",
            "data": self.get_dashboard_summary(),
            "answer": "No estoy seguro de qué análisis necesitas. Puedo ayudarte con: páginas más visitadas, puntos de abandono, flujos de navegación, interacción por página, patrones de conversión, segmentación por dispositivo/país, o engagement por hora.",
            "chart": None,
        }

    def _format_segmentation(self, data: dict) -> str:
        parts = []
        if "by_device" in data:
            devices = ", ".join([f"{d['name']}: {d['count']} sesiones" for d in data["by_device"][:3]])
            parts.append(f"Por dispositivo: {devices}")
        if "by_country" in data:
            countries = ", ".join([f"{d['name']}: {d['count']}" for d in data["by_country"][:3]])
            parts.append(f"Por país: {countries}")
        return ". ".join(parts) if parts else "No hay datos de segmentación disponibles."

    def _format_summary(self, data: dict) -> str:
        parts = [f"Resumen general: {data.get('total_sessions', 0)} sesiones totales"]
        if "avg_pages_per_session" in data:
            parts.append(f"{data['avg_pages_per_session']} páginas promedio por sesión")
        if "bounce_rate" in data:
            parts.append(f"tasa de rebote del {data['bounce_rate']}%")
        if "avg_engagement_score" in data:
            parts.append(f"engagement promedio de {data['avg_engagement_score']}/10")
        return ", ".join(parts) + "."
