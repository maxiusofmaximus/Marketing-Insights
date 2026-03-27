"use client";

import React from "react";

interface MarkdownRendererProps {
  text: string;
  className?: string;
}

/**
 * Renderiza markdown básico: **texto** → <strong>texto</strong>
 * y alinea interpretaciones/recomendaciones con mejor visualización
 */
export function MarkdownRenderer({ text, className = "" }: MarkdownRendererProps) {
  const parts = text.split(/(\*\*[^\*]+\*\*|\n)/g);

  return (
    <div className={className}>
      {parts.map((part, index) => {
        if (part === "\n") {
          return <br key={index} />;
        }

        if (part.startsWith("**") && part.endsWith("**")) {
          const boldText = part.slice(2, -2);
          return (
            <strong key={index} className="markdown-bold">
              {boldText}
            </strong>
          );
        }

        return <span key={index}>{part}</span>;
      })}
    </div>
  );
}

/**
 * Extrae y formatea secciones de interpretación y recomendación
 */
export function extractInterpretationSections(text: string) {
  const interpretationRegex = /\*\*Interpretación\*\*:?\s*(.+?)(?=\*\*|$)/s;
  const recommendationRegex = /\*\*Recomendación accionable\*\*:?\s*(.+?)(?=\*\*|$)/s;

  const interpretationMatch = text.match(interpretationRegex);
  const recommendationMatch = text.match(recommendationRegex);

  return {
    interpretation: interpretationMatch ? interpretationMatch[1].trim() : null,
    recommendation: recommendationMatch ? recommendationMatch[1].trim() : null,
    rawText: text,
  };
}

interface InterpretationCardProps {
  interpretation?: string | null;
  recommendation?: string | null;
  rawText: string;
}

/**
 * Card mejorada que muestra interpretación y recomendación con soporte para secciones
 */
export function InterpretationCard({
  interpretation,
  recommendation,
  rawText,
}: InterpretationCardProps) {
  // Si tenemos secciones extraídas, mostrarlas con mejor formato
  if (interpretation || recommendation) {
    return (
      <div className="interpretation-card">
        {interpretation && (
          <div className="interpretation-section">
            <div className="section-header">💡 Interpretación</div>
            <div className="section-content">
              <MarkdownRenderer text={interpretation} />
            </div>
          </div>
        )}

        {recommendation && (
          <div className="recommendation-section">
            <div className="section-header">✅ Recomendación accionable</div>
            <div className="section-content">
              <MarkdownRenderer text={recommendation} />
            </div>
          </div>
        )}

        {/* Si hay texto adicional, mostrarlo */}
        {rawText.length > ((interpretation?.length || 0) + (recommendation?.length || 0) + 100) && (
          <div className="additional-context">
            <MarkdownRenderer text={rawText} />
          </div>
        )}
      </div>
    );
  }

  // Fallback: renderizar con markdown simple
  return <MarkdownRenderer text={rawText} className="message-text" />;
}
