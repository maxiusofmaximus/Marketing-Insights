"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  askCopilot,
  getDashboardSnapshot,
  getDatasetInfo,
  uploadDataset,
  type AnalyticsSnapshot,
  type ChartData,
  type DatasetInfo
} from "@/lib/marketing-analytics";
import { MarkdownRenderer, InterpretationCard, extractInterpretationSections } from "@/components/markdown-renderer";
import { ChatChart } from "@/components/chat-chart";

type ChatMessage = {
  role: "user" | "copilot";
  text: string;
  chartData?: ChartData | null;
};

const suggestedQuestions = [
  "¿Cuál es la página con mayor abandono?",
  "¿Cuál fue el producto más consultado?",
  "¿Qué flujo de navegación es más frecuente?",
  "¿Qué tan fuerte es la intención de conversión?"
];

const formatPercent = (value: number) => `${value.toFixed(1).replace(/\.0$/, "")}%`;

const emptyAnalytics: AnalyticsSnapshot = {
  totalEvents: 0,
  totalSessions: 0,
  topPages: [],
  topProducts: [],
  abandonment: [],
  commonFlows: [],
  pageEngagement: [],
  intentRate: 0,
  additionalInsights: []
};

export function MarketingCopilot() {
  const [analytics, setAnalytics] = useState<AnalyticsSnapshot>(emptyAnalytics);
  const [input, setInput] = useState("");
  const [recordingsFile, setRecordingsFile] = useState<File | null>(null);
  const [metricsFile, setMetricsFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [chat, setChat] = useState<ChatMessage[]>([
    {
      role: "copilot",
      text: "Soy tu Marketing Copilot. Ya estoy conectado al backend con el dataset cargado y listo para responder."
    }
  ]);
  const [datasetLabel, setDatasetLabel] = useState("Cargando dataset...");
  const [error, setError] = useState("");

  const hasData = analytics.totalEvents > 0;
  const canAsk = input.trim().length > 0 && hasData && !isAsking;

  const kpis = useMemo(
    () => [
      { title: "Sesiones analizadas", value: String(analytics.totalSessions) },
      { title: "Eventos procesados", value: String(analytics.totalEvents) },
      { title: "Intención de conversión", value: formatPercent(analytics.intentRate) },
      {
        title: "Punto crítico de abandono",
        value: analytics.abandonment[0]
          ? formatPercent(analytics.abandonment[0].percentage)
          : "Sin datos"
      }
    ],
    [analytics]
  );

  const syncDashboard = async (info?: DatasetInfo) => {
    const [datasetInfo, snapshot] = await Promise.all([info ? Promise.resolve(info) : getDatasetInfo(), getDashboardSnapshot()]);
    setAnalytics(snapshot);
    setDatasetLabel(
      datasetInfo.is_loaded
        ? `Dataset activo (${datasetInfo.total_rows} registros, ${datasetInfo.total_sessions} sesiones)`
        : "Sin dataset cargado"
    );
  };

  useEffect(() => {
    const bootstrap = async () => {
      try {
        await syncDashboard();
        setError("");
      } catch (err) {
        setError(err instanceof Error ? err.message : "No se pudo conectar con el backend.");
      } finally {
        setIsLoading(false);
      }
    };
    void bootstrap();
  }, []);

  const onAsk = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canAsk) return;
    const question = input.trim();
    setIsAsking(true);
    setChat((prev) => [...prev, { role: "user", text: question }]);
    setInput("");
    try {
      const response = await askCopilot(question);
      setChat((prev) => [
        ...prev,
        { role: "copilot", text: response.interpretation || response.answer, chartData: response.chart_data }
      ]);
    } catch (err) {
      setChat((prev) => [...prev, { role: "copilot", text: "No pude consultar el backend en este momento." }]);
      setError(err instanceof Error ? err.message : "Error al consultar el backend.");
    } finally {
      setIsAsking(false);
    }
  };

  const runSuggestedQuestion = async (question: string) => {
    if (!hasData) return;
    setIsAsking(true);
    setChat((prev) => [...prev, { role: "user", text: question }]);
    try {
      const response = await askCopilot(question);
      setChat((prev) => [
        ...prev,
        { role: "copilot", text: response.interpretation || response.answer, chartData: response.chart_data }
      ]);
    } catch (err) {
      setChat((prev) => [...prev, { role: "copilot", text: "No pude consultar el backend en este momento." }]);
      setError(err instanceof Error ? err.message : "Error al consultar el backend.");
    } finally {
      setIsAsking(false);
    }
  };

  const onUpload = async () => {
    if (!recordingsFile) return;
    setIsUploading(true);
    try {
      const info = await uploadDataset(recordingsFile, metricsFile ?? undefined);
      await syncDashboard(info);
      setError("");
      setRecordingsFile(null);
      setMetricsFile(null);
      setChat((prev) => [
        ...prev,
        {
          role: "copilot",
          text: `Dataset actualizado. Ahora tengo ${info.total_sessions} sesiones y ${info.total_rows} registros listos para análisis sin reentrenar el modelo.`
        }
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error cargando el dataset.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <main className="copilot-page">
      <header className="copilot-header">
        <div>
          <p className="eyebrow">Reto 1 · CloudLabs</p>
          <h1>Marketing Copilot basado en comportamiento web</h1>
          <p className="subtitle">
            Carga datos de eventos, calcula métricas de navegación/abandono y consulta insights en
            lenguaje natural.
          </p>
        </div>
        <div className="dataset-card">
          <p className="dataset-title">Dataset activo</p>
          <p className="dataset-value">{datasetLabel}</p>
          <div className="dataset-actions">
            <label className="button" htmlFor="recordings-file">
              CSV sesiones
            </label>
            <input
              id="recordings-file"
              className="hidden-input"
              type="file"
              accept=".csv,text/csv"
              onInput={(event) => {
                const file = event.currentTarget.files?.[0] ?? null;
                setRecordingsFile(file);
              }}
            />
            <label className="button" htmlFor="metrics-file">
              CSV métricas
            </label>
            <input
              id="metrics-file"
              className="hidden-input"
              type="file"
              accept=".csv,text/csv"
              onInput={(event) => {
                const file = event.currentTarget.files?.[0] ?? null;
                setMetricsFile(file);
              }}
            />
            <button className="button button-primary" type="button" onClick={onUpload} disabled={!recordingsFile || isUploading}>
              {isUploading ? "Cargando..." : "Actualizar dataset"}
            </button>
          </div>
          <p className="small">
            {recordingsFile ? `Sesiones: ${recordingsFile.name}` : "Selecciona CSV de sesiones para actualizar."}
          </p>
          <p className="small">
            {metricsFile ? `Métricas: ${metricsFile.name}` : "CSV de métricas es opcional."}
          </p>
          <p className="small">
            El modelo no se reentrena al cambiar CSV: solo se recargan datos para análisis.
          </p>
        </div>
      </header>

      {error ? <p className="error-banner">{error}</p> : null}
      {isLoading ? <p className="error-banner">Cargando datos del backend...</p> : null}

      <section className="kpi-grid">
        {kpis.map((kpi) => (
          <article key={kpi.title} className="kpi-card">
            <p>{kpi.title}</p>
            <h3>{kpi.value}</h3>
          </article>
        ))}
      </section>

      <section className="layout-grid">
        <article className="panel">
          <div className="panel-head">
            <h2>Interfaz conversacional</h2>
            <p>Respuestas automáticas con foco de negocio.</p>
          </div>

          <div className="suggestions">
            {suggestedQuestions.map((question) => (
              <button
                key={question}
                type="button"
                className="chip"
                onClick={() => runSuggestedQuestion(question)}
                disabled={!hasData}
              >
                {question}
              </button>
            ))}
          </div>

          <div className="chat-box">
            {chat.map((message, index) => {
              const sections = extractInterpretationSections(message.text);
              return (
                <article
                  key={`${message.role}-${index}`}
                  className={`message ${message.role === "user" ? "message-user" : "message-copilot"}`}
                >
                  {message.role === "copilot" ? (
                    <>
                      <InterpretationCard
                        interpretation={sections.interpretation}
                        recommendation={sections.recommendation}
                        rawText={message.text}
                      />
                      {message.chartData ? <ChatChart data={message.chartData} /> : null}
                    </>
                  ) : (
                    <MarkdownRenderer text={message.text} />
                  )}
                </article>
              );
            })}
          </div>

          <form className="ask-form" onSubmit={onAsk}>
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder={hasData ? "Pregunta algo del comportamiento web..." : "Primero carga un dataset"}
            />
            <button className="button button-primary" type="submit" disabled={!canAsk}>
              {isAsking ? "Consultando..." : "Consultar"}
            </button>
          </form>
        </article>

        <article className="panel">
          <div className="panel-head">
            <h2>Motor analítico</h2>
            <p>Métricas mínimas + insights adicionales.</p>
          </div>

          <div className="metric-block">
            <h3>Top páginas</h3>
            {analytics.topPages.slice(0, 5).map((item) => (
              <p key={item.name} className="metric-row">
                <span>{item.name}</span>
                <strong>
                  {item.value} · {formatPercent(item.percentage)}
                </strong>
              </p>
            ))}
          </div>

          <div className="metric-block">
            <h3>Top productos</h3>
            {analytics.topProducts.length === 0 ? (
              <p className="metric-empty">Sin productos registrados.</p>
            ) : (
              analytics.topProducts.slice(0, 5).map((item) => (
                <p key={item.name} className="metric-row">
                  <span>{item.name}</span>
                  <strong>
                    {item.value} · {formatPercent(item.percentage)}
                  </strong>
                </p>
              ))
            )}
          </div>

          <div className="metric-block">
            <h3>Flujos más frecuentes</h3>
            {analytics.commonFlows.slice(0, 3).map((flow) => (
              <p key={flow.flow} className="metric-row">
                <span>{flow.flow}</span>
                <strong>
                  {flow.count} sesiones · {formatPercent(flow.percentage)}
                </strong>
              </p>
            ))}
          </div>

          <div className="metric-block">
            <h3>Insights adicionales propuestos</h3>
            {analytics.additionalInsights.map((insight) => (
              <p key={insight} className="metric-empty">{insight}</p>
            ))}
          </div>
        </article>
      </section>
    </main>
  );
}
