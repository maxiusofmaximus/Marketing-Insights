"use client";

import { useMemo, useRef, useState } from "react";
import { type ChartData } from "@/lib/marketing-analytics";

type ChatChartProps = {
  data: ChartData;
};

type VisualType = "bar" | "line" | "pie";

type Datum = {
  label: string;
  value: number;
};

const titleize = (value: string) =>
  value
    .toLowerCase()
    .split(" ")
    .filter(Boolean)
    .map((token) => token.charAt(0).toUpperCase() + token.slice(1))
    .join(" ");

const prettifyLabel = (raw: string) => {
  let value = raw.trim();
  if (!value || value === "/") return "Inicio";
  value = value.split("?")[0].split("#")[0];
  if (value.startsWith("/")) {
    const parts = value
      .split("/")
      .filter(Boolean)
      .filter((part) => !/^\d+$/.test(part))
      .filter((part) => !/^[a-f0-9]{8,}$/i.test(part));
    if (parts.length === 0) return "Inicio";
    const first = parts[0].toLowerCase();
    if (first === "request-demo" || first === "request_demo" || first === "demo") return "Request Demo";
    if (first === "register" || first === "signup") return "Register";
    return titleize(first.replace(/[_-]+/g, " "));
  }
  return titleize(value.replace(/[_-]+/g, " "));
};

const wrapLabel = (label: string, maxChars: number, maxLines: number) => {
  const words = label.split(" ").filter(Boolean);
  const lines: string[] = [];
  let current = "";
  for (const word of words) {
    const chunk = word.length > maxChars ? word.slice(0, maxChars) : word;
    const candidate = current ? `${current} ${chunk}` : chunk;
    if (candidate.length <= maxChars) {
      current = candidate;
      continue;
    }
    if (current) lines.push(current);
    current = chunk;
    if (lines.length >= maxLines - 1) break;
  }
  if (current && lines.length < maxLines) lines.push(current);
  if (lines.length === 0) return [label.slice(0, maxChars)];
  return lines.slice(0, maxLines);
};

const sanitize = (data: ChartData): Datum[] =>
  data.labels.map((label, index) => ({
    label: prettifyLabel(String(label)),
    value: Number.isFinite(data.values[index]) ? Number(data.values[index]) : 0
  }));

const inferVisualType = (data: ChartData, rows: Datum[]): VisualType => {
  const source = data.chart_type.toLowerCase();
  if (source.includes("line")) return "line";
  if (source.includes("pie")) return "pie";
  const labelsLookTemporal = rows.every((row) => /^(\d{1,2}:\d{2}|\d{1,2})$/.test(row.label));
  if (labelsLookTemporal) return "line";
  const positives = rows.filter((row) => row.value >= 0);
  const total = positives.reduce((sum, row) => sum + row.value, 0);
  if (positives.length === rows.length && rows.length > 1 && rows.length <= 6 && total >= 95 && total <= 105) return "pie";
  return "bar";
};

const buildPiePath = (cx: number, cy: number, r: number, start: number, end: number) => {
  const x1 = cx + r * Math.cos(start);
  const y1 = cy + r * Math.sin(start);
  const x2 = cx + r * Math.cos(end);
  const y2 = cy + r * Math.sin(end);
  const largeArc = end - start > Math.PI ? 1 : 0;
  return `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z`;
};

const palette = ["#8df7d8", "#71bfff", "#ff7c94", "#f5e663", "#c89dff", "#8fd46f"];

export function ChatChart({ data }: ChatChartProps) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const rows = useMemo(() => sanitize(data), [data]);
  const visualType = useMemo(() => inferVisualType(data, rows), [data, rows]);
  const maxValue = Math.max(...rows.map((row) => row.value), 1);
  const total = rows.reduce((sum, row) => sum + row.value, 0);

  const triggerDownload = (content: Blob, name: string) => {
    const url = URL.createObjectURL(content);
    const link = document.createElement("a");
    link.href = url;
    link.download = name;
    link.click();
    URL.revokeObjectURL(url);
  };

  const exportCsv = () => {
    const head = "label,value\n";
    const body = rows.map((row) => `"${row.label.replace(/"/g, '""')}",${row.value}`).join("\n");
    triggerDownload(new Blob([head + body], { type: "text/csv;charset=utf-8" }), "grafico-chat.csv");
  };

  const exportSvg = () => {
    if (!svgRef.current) return;
    const serialized = new XMLSerializer().serializeToString(svgRef.current);
    triggerDownload(new Blob([serialized], { type: "image/svg+xml;charset=utf-8" }), "grafico-chat.svg");
  };

  const exportPng = () => {
    if (!svgRef.current || isExporting) return;
    setIsExporting(true);
    const serialized = new XMLSerializer().serializeToString(svgRef.current);
    const svgBlob = new Blob([serialized], { type: "image/svg+xml;charset=utf-8" });
    const svgUrl = URL.createObjectURL(svgBlob);
    const image = new Image();
    image.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = 560;
      canvas.height = 280;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        URL.revokeObjectURL(svgUrl);
        setIsExporting(false);
        exportSvg();
        return;
      }
      ctx.fillStyle = "#05070f";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
      canvas.toBlob((blob) => {
        if (blob) {
          triggerDownload(blob, "grafico-chat.png");
        } else {
          exportSvg();
        }
        URL.revokeObjectURL(svgUrl);
        setIsExporting(false);
      }, "image/png");
    };
    image.onerror = () => {
      URL.revokeObjectURL(svgUrl);
      setIsExporting(false);
      exportSvg();
    };
    image.src = svgUrl;
  };

  return (
    <div className="chat-chart">
      <div className="chat-chart-header">
        <p>{data.label || "Visualización de datos"}</p>
        <div className="chat-chart-actions">
          <button type="button" className="button" onClick={exportCsv}>CSV</button>
          <button type="button" className="button" onClick={exportPng} disabled={isExporting}>
            {isExporting ? "Exportando..." : "PNG"}
          </button>
        </div>
      </div>

      <svg ref={svgRef} viewBox="0 0 560 280" role="img" aria-label={`Gráfico ${visualType}`} className="chat-chart-svg">
        <rect x="0" y="0" width="560" height="280" fill="#05070f" />
        {visualType === "bar" && rows.map((row, index) => {
          const left = 70;
          const top = 30;
          const chartWidth = 460;
          const chartHeight = 200;
          const gap = 8;
          const barWidth = (chartWidth - gap * (rows.length - 1)) / Math.max(rows.length, 1);
          const barHeight = Math.max((row.value / maxValue) * chartHeight, 2);
          const x = left + index * (barWidth + gap);
          const y = top + chartHeight - barHeight;
          const labelLines = wrapLabel(row.label, 14, 2);
          return (
            <g key={`${row.label}-${index}`}>
              <rect x={x} y={y} width={barWidth} height={barHeight} fill="#71bfff" rx="4" />
              <text x={x + barWidth / 2} y={top + chartHeight + 16} textAnchor="middle" fill="#b0bfd7" fontSize="10">
                {labelLines.map((line, lineIndex) => (
                  <tspan key={`${row.label}-${line}-${lineIndex}`} x={x + barWidth / 2} dy={lineIndex === 0 ? 0 : 10}>
                    {line}
                  </tspan>
                ))}
              </text>
              <text x={x + barWidth / 2} y={y - 6} textAnchor="middle" fill="#8df7d8" fontSize="10">
                {row.value.toFixed(1).replace(/\.0$/, "")}
              </text>
            </g>
          );
        })}

        {visualType === "line" && (() => {
          const left = 60;
          const top = 30;
          const chartWidth = 470;
          const chartHeight = 190;
          const step = rows.length > 1 ? chartWidth / (rows.length - 1) : 0;
          const points = rows.map((row, index) => {
            const x = left + index * step;
            const y = top + chartHeight - (row.value / maxValue) * chartHeight;
            return { x, y, row, labelLines: wrapLabel(row.label, 12, 2) };
          });
          return (
            <g>
              <polyline
                points={points.map((point) => `${point.x},${point.y}`).join(" ")}
                fill="none"
                stroke="#71bfff"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              {points.map((point, index) => (
                <g key={`${point.row.label}-${index}`}>
                  <circle cx={point.x} cy={point.y} r="4" fill="#8df7d8" />
                  <text x={point.x} y={top + chartHeight + 16} textAnchor="middle" fill="#b0bfd7" fontSize="10">
                    {point.labelLines.map((line, lineIndex) => (
                      <tspan key={`${point.row.label}-${line}-${lineIndex}`} x={point.x} dy={lineIndex === 0 ? 0 : 10}>
                        {line}
                      </tspan>
                    ))}
                  </text>
                </g>
              ))}
            </g>
          );
        })()}

        {visualType === "pie" && (() => {
          let start = -Math.PI / 2;
          return (
            <g>
              {rows.map((row, index) => {
                const ratio = total > 0 ? row.value / total : 0;
                const end = start + ratio * Math.PI * 2;
                const d = buildPiePath(190, 140, 90, start, end);
                const mid = start + (end - start) / 2;
                const tx = 190 + 60 * Math.cos(mid);
                const ty = 140 + 60 * Math.sin(mid);
                const output = (
                  <g key={`${row.label}-${index}`}>
                    <path d={d} fill={palette[index % palette.length]} stroke="#05070f" strokeWidth="2" />
                    <text x={tx} y={ty} fill="#05070f" fontSize="10" textAnchor="middle">
                      {(ratio * 100).toFixed(0)}%
                    </text>
                  </g>
                );
                start = end;
                return output;
              })}
              {rows.map((row, index) => (
                <g key={`legend-${row.label}-${index}`}>
                  <rect x="330" y={50 + index * 28} width="12" height="12" fill={palette[index % palette.length]} />
                  <text x="350" y={60 + index * 28} fill="#b0bfd7" fontSize="11">
                    {row.label.slice(0, 22)} ({((row.value / Math.max(total, 1)) * 100).toFixed(1).replace(/\.0$/, "")}%)
                  </text>
                </g>
              ))}
            </g>
          );
        })()}
      </svg>
    </div>
  );
}
