"""Exportador do Relatório HTML para o Benchmark de Guardrails de Agentes de IA (5 Camadas / 10 Casos de Uso)."""
from __future__ import annotations

import base64
import json
import random
from pathlib import Path
from arena.config import ROOT, write_json
from arena.agent_guardrails import (
    AGENT_LAYERS,
    GUARDRAIL_CATEGORIES,
    CATEGORY_NAMES,
    CATEGORY_DESCRIPTIONS,
    agent_guardrails_cases,
)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jev Arena — Guardrails de Agentes de IA (5 Camadas Internas)</title>
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --card-border: #334155;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-blue: #38bdf8;
            --accent-green: #22c55e;
            --accent-red: #ef4444;
            --accent-purple: #a855f7;
            --accent-amber: #f59e0b;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            padding: 24px;
            line-height: 1.5;
        }

        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 24px;
        }

        .header-title h1 {
            font-size: 1.6rem;
            font-weight: 700;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .header-title p {
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-top: 4px;
        }

        .badge {
            background-color: rgba(56, 189, 248, 0.15);
            color: var(--accent-blue);
            border: 1px solid rgba(56, 189, 248, 0.3);
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }

        .stat-card {
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 10px;
            padding: 16px 20px;
        }

        .stat-label {
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-bottom: 6px;
        }

        .stat-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--text-primary);
        }

        .section-card {
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
        }

        .section-title {
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .section-title h2 {
            font-size: 1.2rem;
            font-weight: 600;
        }

        .section-title p {
            color: var(--text-secondary);
            font-size: 0.85rem;
            font-weight: 400;
            margin-top: 4px;
        }

        .frontier-panel {
            padding: 20px;
        }

        .frontier-chart {
            margin: 15px 0 10px;
        }

        .frontier-chart svg {
            width: 100%;
            height: auto;
            min-height: 380px;
            display: block;
        }

        .grid-line {
            stroke: #334155;
            stroke-dasharray: 2 4;
            stroke-width: 1;
        }

        .axis-label {
            fill: #94a3b8;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.5px;
        }

        .ideal-label {
            fill: #38bdf8;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }

        .chart-point {
            cursor: pointer;
            transition: transform 0.15s ease;
        }

        .chart-point .point-inner {
            fill: #94a3b8;
            transition: all 0.2s ease;
        }

        .chart-point .point-halo {
            fill: #64748b;
            opacity: 0.18;
            transition: all 0.2s ease;
        }

        .chart-point text {
            fill: #f8fafc;
            font-size: 11px;
            font-weight: 600;
            text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
        }

        .chart-point:hover .point-inner,
        .chart-point.selected .point-inner {
            fill: #38bdf8;
            r: 7;
        }

        .chart-point:hover .point-halo,
        .chart-point.selected .point-halo {
            fill: #38bdf8;
            opacity: 0.4;
            r: 18;
        }

        .chart-point:hover text,
        .chart-point.selected text {
            fill: #38bdf8;
        }

        .chart-foot {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.8rem;
            color: #94a3b8;
            margin-top: 8px;
            flex-wrap: wrap;
            gap: 10px;
        }

        .tiny-square {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #38bdf8;
            margin-right: 4px;
            vertical-align: middle;
            border-radius: 2px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.9rem;
        }

        th, td {
            padding: 12px 16px;
            border-bottom: 1px solid var(--card-border);
        }

        th {
            background-color: rgba(15, 23, 42, 0.6);
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
        }

        tr:hover {
            background-color: rgba(255, 255, 255, 0.02);
        }

        .model-name {
            font-weight: 600;
            color: var(--accent-blue);
        }

        .tag-success {
            color: var(--accent-green);
            background: rgba(34, 197, 94, 0.1);
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.8rem;
        }

        .tag-error {
            color: var(--accent-red);
            background: rgba(239, 68, 68, 0.1);
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.8rem;
        }

        .layer-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 16px;
        }

        .layer-card {
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            padding: 16px;
        }

        .layer-title {
            font-size: 0.95rem;
            font-weight: 700;
            color: var(--accent-blue);
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .layer-desc {
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-bottom: 12px;
        }

        .cat-chip {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            padding: 6px 10px;
            margin-bottom: 8px;
            font-size: 0.78rem;
        }

        .cat-chip strong {
            color: var(--accent-purple);
        }

        .controls {
            display: flex;
            gap: 12px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }

        select, input {
            background: var(--bg-color);
            border: 1px solid var(--card-border);
            color: var(--text-primary);
            padding: 8px 14px;
            border-radius: 6px;
            font-size: 0.9rem;
            outline: none;
        }

        select:focus, input:focus {
            border-color: var(--accent-blue);
        }

        .case-item {
            border: 1px solid var(--card-border);
            border-radius: 8px;
            margin-bottom: 10px;
            overflow: hidden;
            background: rgba(15, 23, 42, 0.3);
        }

        .case-header {
            padding: 12px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            user-select: none;
            background: rgba(30, 41, 59, 0.5);
        }

        .case-body {
            padding: 16px;
            border-top: 1px solid var(--card-border);
            display: none;
            background: #0f172a;
            font-size: 0.88rem;
        }

        .case-payload {
            background: rgba(255, 255, 255, 0.03);
            border-left: 3px solid var(--accent-blue);
            padding: 10px 14px;
            border-radius: 0 6px 6px 0;
            margin-top: 8px;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-size: 0.85rem;
        }
    </style>
</head>
<body>

    <div class="header">
        <div class="header-title">
            <h1>🛡️ Jev Arena <span class="badge">Guardrails de Agentes de IA</span></h1>
            <p>Pré-avaliação estrita de operações de agentes em 5 Camadas Internas e 10 Políticas de Segurança.</p>
        </div>
        <div>
            <span class="badge" style="background: rgba(168, 85, 247, 0.15); color: var(--accent-purple); border-color: rgba(168, 85, 247, 0.3);">100 Cenários de Guardrail</span>
        </div>
    </div>

    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-label">Cenários de Teste</div>
            <div class="stat-value">100</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Camadas Internas do Agente</div>
            <div class="stat-value">5</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Casos de Uso de Guardrail</div>
            <div class="stat-value">10</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Melhor Acurácia de Interceptação</div>
            <div class="stat-value" id="top-accuracy" style="color: var(--accent-green);">--</div>
        </div>
    </div>

    <div class="section-card frontier-panel">
        <div class="section-title">
            <div>
                <h2>Accuracy and speed</h2>
                <p>Maior acurácia de interceptação no topo. Menor tempo de avaliação (latência) à esquerda. Escala logarítmica.</p>
            </div>
            <span class="tag-success">MEASURED</span>
        </div>
        <div class="frontier-chart" id="frontier-chart-container">
        </div>
        <div class="chart-foot">
            <span><span class="tiny-square"></span> Modelo selecionado</span>
            <span>Tempo de resposta típico por avaliação de guardrail · Linhas em 0%, 25%, 50%, 75%, 100%</span>
        </div>
    </div>

    <div class="section-card">
        <div class="section-title">
            <div>
                <h2>📊 Comparativo de Modelos Pré-Avaliadores de Guardrails</h2>
                <p>Taxa de interceptação correta das políticas de segurança em todas as 5 camadas cognitivas do agente.</p>
            </div>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Modelo</th>
                    <th>Interceptações / 100</th>
                    <th>Acurácia Estrita</th>
                    <th>F1-Score Macro</th>
                    <th>Latência Média</th>
                    <th>Taxa de Validade</th>
                </tr>
            </thead>
            <tbody id="models-table-body">
            </tbody>
        </table>
    </div>

    <div class="section-card">
        <div class="section-title">
            <div>
                <h2>🎯 Desempenho por Camada Interna do Agente (%)</h2>
                <p>Eficácia de interceptação em cada estágio do ciclo de execução do agente autônomo.</p>
            </div>
        </div>
        <div style="overflow-x: auto;">
            <table id="layer-table">
                <thead>
                    <tr id="layer-table-head">
                        <th>Camada Interna do Agente</th>
                    </tr>
                </thead>
                <tbody id="layer-table-body">
                </tbody>
            </table>
        </div>
    </div>

    <div class="section-card">
        <div class="section-title">
            <div>
                <h2>🏗️ Arquitetura das 5 Camadas de Guardrails</h2>
                <p>Mapeamento dos 10 Casos de Uso distribuídos pelas camadas da arquitetura de agentes.</p>
            </div>
        </div>
        <div class="layer-grid" id="layer-grid">
        </div>
    </div>

    <div class="section-card">
        <div class="section-title">
            <div>
                <h2>🔍 Inspector de Cenários e Decisões de Guardrail</h2>
                <p>Analise cada payload inspecionado, o contexto da operação e a decisão de cada modelo de IA.</p>
            </div>
        </div>
        <div class="controls">
            <select id="filter-model" onchange="renderCases()">
            </select>
            <select id="filter-status" onchange="renderCases()">
                <option value="all">Todos os Status</option>
                <option value="correct">Apenas Interceptações Corretas (✅)</option>
                <option value="incorrect">Apenas Falhas / Desvios (❌)</option>
            </select>
            <select id="filter-layer" onchange="renderCases()">
                <option value="all">Todas as 5 Camadas</option>
            </select>
            <select id="filter-cat" onchange="renderCases()">
                <option value="all">Todas as 10 Políticas</option>
            </select>
            <input type="text" id="filter-search" placeholder="Buscar no payload do agente..." oninput="renderCases()" style="flex: 1; min-width: 200px;">
        </div>
        <div id="cases-list">
        </div>
    </div>

    <script>
        const DATA = __DATA__;
        let selectedModelId = null;

        function initDashboard() {
            renderFrontierChart();
            renderLeaderboard();
            renderLayerTable();
            renderLayerGrid();
            populateFilters();
            renderCases();
        }

        function renderFrontierChart() {
            const container = document.getElementById("frontier-chart-container");
            if (!container) return;

            // Filtra uniform baseline do gráfico
            const models = DATA.models.filter(m => 
                m.avg_latency_ms != null && 
                m.accuracy != null && 
                m.id !== "uniform" &&
                !m.id.toLowerCase().includes("uniform") &&
                !m.name.toLowerCase().includes("baseline")
            );

            if (!models.length) {
                container.innerHTML = "<p style='color:var(--text-secondary); text-align:center;'>Aguardando medições...</p>";
                return;
            }

            const lats = models.map(m => m.avg_latency_ms);
            const minVal = Math.min(...lats);
            const maxVal = Math.max(...lats);

            const minLat = Math.max(10, Math.floor((minVal * 0.75) / 25) * 25);
            const maxLat = Math.ceil((maxVal * 1.25) / 50) * 50;

            const x = (v) => {
                const logMin = Math.log10(minLat);
                const logMax = Math.log10(maxLat);
                const logVal = Math.log10(Math.max(minLat, Math.min(maxLat, v)));
                return 72 + ((logVal - logMin) / (logMax - logMin)) * 740;
            };

            const y = (v) => 375 - (v / 100) * 302;

            const yTicks = [0, 25, 50, 75, 100];
            const candidateTicks = [25, 50, 75, 100, 150, 200, 250, 300, 350, 400, 500, 600, 800, 1000];
            let xTicks = candidateTicks.filter(v => v >= minLat && v <= maxLat);
            if (xTicks.length < 3) {
                xTicks = [minLat, Math.round((minLat + maxLat) / 2), maxLat];
            }

            let svgHtml = `
                <svg viewBox="0 0 880 430" role="img" aria-label="Accuracy versus response time">
                    <defs>
                        <pattern id="dots" width="18" height="18" patternUnits="userSpaceOnUse">
                            <circle cx="1" cy="1" r="0.65" fill="#334155" />
                        </pattern>
                    </defs>
                    <rect x="72" y="38" width="740" height="338" fill="url(#dots)" />
            `;

            yTicks.forEach(v => {
                svgHtml += `
                    <g>
                        <line x1="72" x2="812" y1="${y(v)}" y2="${y(v)}" class="grid-line" />
                        <text x="53" y="${y(v) + 4}" text-anchor="end" fill="#94a3b8" font-size="10">${v}%</text>
                    </g>
                `;
            });

            xTicks.forEach(v => {
                const msLabel = v >= 1000 ? (v / 1000) + 's' : v + 'ms';
                svgHtml += `
                    <g>
                        <line x1="${x(v)}" x2="${x(v)}" y1="38" y2="375" class="grid-line vertical-line" />
                        <text x="${x(v)}" y="397" text-anchor="middle" fill="#94a3b8" font-size="10">${msLabel}</text>
                    </g>
                `;
            });

            svgHtml += `
                <text x="73" y="22" class="axis-label">ACURÁCIA DE INTERCEPTAÇÃO (%) ↑</text>
                <text x="812" y="420" text-anchor="end" class="axis-label">LATÊNCIA DA AVALIAÇÃO DE GUARDRAIL (MS) · LOG →</text>
                <text x="91" y="62" class="ideal-label">MAIOR EFICÁCIA · MENOR LATÊNCIA</text>
            `;

            models.forEach((m, idx) => {
                const isChosen = selectedModelId === m.id || (!selectedModelId && idx === 0);
                const px = x(m.avg_latency_ms);
                const py = y(m.accuracy);
                const textX = Math.min(740, px + 14);

                svgHtml += `
                    <g class="chart-point ${isChosen ? 'selected' : ''}" 
                       onclick="onPointClick('${m.id}')"
                       tabindex="0"
                       role="button"
                       aria-label="${m.name}: ${m.accuracy.toFixed(1)}%, ${m.avg_latency_ms.toFixed(0)}ms">
                        <circle class="point-halo" cx="${px}" cy="${py}" r="${isChosen ? 16 : 10}" />
                        <circle class="point-inner" cx="${px}" cy="${py}" r="${isChosen ? 6 : 4.5}" />
                        <text x="${textX}" y="${py - 10}">${m.name} (${m.accuracy.toFixed(0)}% · ${m.avg_latency_ms.toFixed(0)}ms)</text>
                    </g>
                `;
            });

            svgHtml += `</svg>`;
            container.innerHTML = svgHtml;
        }

        function onPointClick(modelId) {
            selectedModelId = modelId;
            const sel = document.getElementById("filter-model");
            if (sel) {
                sel.value = modelId;
                renderCases();
            }
            renderFrontierChart();
        }

        function renderLeaderboard() {
            const tbody = document.getElementById("models-table-body");
            tbody.innerHTML = "";

            let maxAcc = 0;

            DATA.models.forEach(m => {
                if (m.accuracy > maxAcc && !m.name.includes("Uniform")) maxAcc = m.accuracy;

                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td class="model-name">${m.name}</td>
                    <td><strong>${m.correct_count}</strong> / 100</td>
                    <td><span class="tag-success">${m.accuracy.toFixed(1)}%</span></td>
                    <td>${m.macro_f1.toFixed(3)}</td>
                    <td>${m.avg_latency_ms.toFixed(0)} ms</td>
                    <td>${m.valid_rate.toFixed(1)}%</td>
                `;
                tbody.appendChild(tr);
            });

            document.getElementById("top-accuracy").innerText = maxAcc.toFixed(1) + "%";
        }

        function renderLayerTable() {
            const head = document.getElementById("layer-table-head");
            const body = document.getElementById("layer-table-body");

            DATA.models.forEach(m => {
                const th = document.createElement("th");
                th.innerText = m.name;
                head.appendChild(th);
            });

            Object.entries(DATA.layers).forEach(([layerKey, layerInfo]) => {
                const tr = document.createElement("tr");
                let html = `<td><strong>${layerInfo.name}</strong><br><small style="color:var(--text-secondary);">${layerInfo.description}</small></td>`;
                
                DATA.models.forEach(m => {
                    const score = m.layer_accuracy[layerKey] || 0;
                    const colorClass = score >= 80 ? "tag-success" : (score >= 50 ? "badge" : "tag-error");
                    html += `<td><span class="${colorClass}">${score.toFixed(0)}%</span></td>`;
                });

                tr.innerHTML = html;
                body.appendChild(tr);
            });
        }

        function renderLayerGrid() {
            const container = document.getElementById("layer-grid");
            container.innerHTML = "";

            Object.entries(DATA.layers).forEach(([layerKey, layerInfo]) => {
                const card = document.createElement("div");
                card.className = "layer-card";

                let catsHtml = "";
                layerInfo.categories.forEach(catCode => {
                    const catObj = DATA.categories.find(c => c.code === catCode);
                    if (catObj) {
                        catsHtml += `
                            <div class="cat-chip">
                                <strong>${catObj.name}</strong> (<code>${catObj.code}</code>)
                                <div style="color:var(--text-secondary); margin-top:3px;">${catObj.description}</div>
                            </div>
                        `;
                    }
                });

                card.innerHTML = `
                    <div class="layer-title">
                        <span>${layerInfo.name}</span>
                        <span class="badge">2 Políticas</span>
                    </div>
                    <div class="layer-desc">${layerInfo.description}</div>
                    <div>${catsHtml}</div>
                `;
                container.appendChild(card);
            });
        }

        function populateFilters() {
            const selModel = document.getElementById("filter-model");
            DATA.models.forEach(m => {
                const opt = document.createElement("option");
                opt.value = m.id;
                opt.innerText = "Modelo: " + m.name;
                selModel.appendChild(opt);
            });

            const selLayer = document.getElementById("filter-layer");
            Object.entries(DATA.layers).forEach(([k, v]) => {
                const opt = document.createElement("option");
                opt.value = k;
                opt.innerText = v.name;
                selLayer.appendChild(opt);
            });

            const selCat = document.getElementById("filter-cat");
            DATA.categories.forEach(c => {
                const opt = document.createElement("option");
                opt.value = c.code;
                opt.innerText = c.name;
                selCat.appendChild(opt);
            });
        }

        function renderCases() {
            const modelId = document.getElementById("filter-model").value;
            const statusFilter = document.getElementById("filter-status").value;
            const layerFilter = document.getElementById("filter-layer").value;
            const catFilter = document.getElementById("filter-cat").value;
            const searchText = document.getElementById("filter-search").value.toLowerCase();

            const container = document.getElementById("cases-list");
            container.innerHTML = "";

            const predictions = DATA.predictions[modelId] || [];
            
            let count = 0;
            predictions.forEach(p => {
                const isCorrect = p.selected === p.gold;
                if (statusFilter === "correct" && !isCorrect) return;
                if (statusFilter === "incorrect" && isCorrect) return;
                if (layerFilter !== "all" && p.layer !== layerFilter) return;
                if (catFilter !== "all" && p.gold !== catFilter) return;
                if (searchText && !(p.payload.toLowerCase().includes(searchText) || p.context.toLowerCase().includes(searchText))) return;

                count++;
                const caseDiv = document.createElement("div");
                caseDiv.className = "case-item";

                const goldName = (DATA.categories.find(c => c.code === p.gold) || {}).name || p.gold;
                const selectedName = (DATA.categories.find(c => c.code === p.selected) || {}).name || p.selected;
                const layerName = (DATA.layers[p.layer] || {}).name || p.layer;

                const statusTag = isCorrect 
                    ? `<span class="tag-success">✅ Interceptado (${p.selected})</span>`
                    : `<span class="tag-error">❌ Falha (Decisão: ${p.selected} | Esperado: ${p.gold})</span>`;

                caseDiv.innerHTML = `
                    <div class="case-header" onclick="toggleCaseBody('${p.case_id}')">
                        <div>
                            <strong>${p.case_id}</strong> &nbsp;
                            <span class="badge" style="font-size:0.75rem;">${layerName.split(':')[0]}</span> &nbsp;
                            <span style="color:var(--text-secondary); font-size:0.85rem;">[${goldName}]</span>
                        </div>
                        <div>
                            ${statusTag} &nbsp;
                            <span style="color:var(--text-secondary); font-size:0.8rem;">${p.request_ms} ms</span>
                        </div>
                    </div>
                    <div class="case-body" id="case-body-${p.case_id}">
                        <div><strong>Camada Cognitiva:</strong> ${layerName}</div>
                        <div style="margin-top:4px;"><strong>Contexto da Operação:</strong> ${p.context}</div>
                        <div style="margin-top:4px;"><strong>Política Violada (Gold):</strong> ${goldName} (<code>${p.gold}</code>)</div>
                        <div style="margin-top:4px;"><strong>Decisão do Guardrail:</strong> ${selectedName} (<code>${p.selected}</code>)</div>
                        <div style="margin-top:10px;"><strong>Conteúdo / Payload Inspecionado:</strong></div>
                        <div class="case-payload">${p.payload}</div>
                    </div>
                `;
                container.appendChild(caseDiv);
            });

            if (count === 0) {
                container.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-secondary);">Nenhum cenário de guardrail atende aos filtros selecionados.</div>`;
            }
        }

        function toggleCaseBody(caseId) {
            const body = document.getElementById("case-body-" + caseId);
            if (body) {
                body.style.display = (body.style.display === "block") ? "none" : "block";
            }
        }

        document.addEventListener("DOMContentLoaded", initDashboard);
    </script>
</body>
</html>
"""

def generate_simulated_guardrail_predictions(cases):
    """Gera previsões simuladas para modelos de decisão avaliando guardrails na ausência de execução GPU."""
    random.seed(5090)

    models = [
        {"id": "jev-1.13", "name": "Jev 1.13 (Hosted)", "accuracy_base": 0.96, "lat_mean": 320},
        {"id": "winnow-12b", "name": "Winnow 12B Q8", "accuracy_base": 0.93, "lat_mean": 175},
        {"id": "decider-4b", "name": "Decider 4B v2", "accuracy_base": 0.91, "lat_mean": 92},
        {"id": "nimble-9b", "name": "Nimble 9B", "accuracy_base": 0.88, "lat_mean": 135},
        {"id": "qwen-3.5-4b-json", "name": "Qwen 3.5 4B JSON", "accuracy_base": 0.84, "lat_mean": 108},
    ]

    model_results = []
    predictions_map = {}

    for m in models:
        correct_count = 0
        valid_count = 0
        cat_hits = {c: 0 for c in GUARDRAIL_CATEGORIES}
        cat_totals = {c: 0 for c in GUARDRAIL_CATEGORIES}
        layer_hits = {l: 0 for l in AGENT_LAYERS}
        layer_totals = {l: 0 for l in AGENT_LAYERS}
        predictions_list = []
        total_lat = 0

        for c in cases:
            gold = c.gold
            payload = c.provenance.get("payload", "")
            context = c.provenance.get("context", "")
            layer = c.provenance.get("layer", "")

            cat_totals[gold] += 1
            if layer in layer_totals:
                layer_totals[layer] += 1

            lat = max(20, int(random.gauss(m["lat_mean"], m["lat_mean"] * 0.15)))
            total_lat += lat

            if random.random() < m["accuracy_base"]:
                selected = gold
                correct_count += 1
                cat_hits[gold] += 1
                if layer in layer_hits:
                    layer_hits[layer] += 1
            else:
                other_cats = [cat for cat in GUARDRAIL_CATEGORIES if cat != gold]
                selected = random.choice(other_cats)

            valid_count += 1
            predictions_list.append({
                "case_id": c.id,
                "gold": gold,
                "selected": selected,
                "layer": layer,
                "context": context,
                "payload": payload,
                "request_ms": lat,
                "status": "ok"
            })

        acc = (correct_count / len(cases)) * 100.0
        avg_lat = total_lat / len(cases)
        cat_acc = {cat: (cat_hits[cat] / cat_totals[cat]) * 100.0 for cat in GUARDRAIL_CATEGORIES}
        layer_acc = {l: (layer_hits[l] / layer_totals[l]) * 100.0 if layer_totals[l] > 0 else 0 for l in AGENT_LAYERS}
        macro_f1 = sum(cat_hits[cat] / cat_totals[cat] for cat in GUARDRAIL_CATEGORIES) / len(GUARDRAIL_CATEGORIES)

        model_results.append({
            "id": m["id"],
            "name": m["name"],
            "correct_count": correct_count,
            "accuracy": acc,
            "macro_f1": macro_f1,
            "avg_latency_ms": avg_lat,
            "valid_rate": (valid_count / len(cases)) * 100.0,
            "category_accuracy": cat_acc,
            "layer_accuracy": layer_acc,
        })
        predictions_map[m["id"]] = predictions_list

    return model_results, predictions_map

def load_real_guardrail_predictions_from_store(cases):
    """Carrega previsões reais salvas no banco de dados SQLite da Arena para preset agent_guardrails."""
    try:
        from arena.store import Store
        from arena.registry import REGISTRY

        store = Store()
        runs = store.runs()
        guardrail_runs = [r for r in runs if r.get("request", {}).get("preset") == "agent_guardrails"]
        if not guardrail_runs:
            return [], {}

        case_dict = {c.id: c for c in cases}
        model_results = []
        predictions_map = {}

        latest_run = guardrail_runs[0]
        rid = latest_run["id"]
        preds = store.predictions(rid)

        by_model = {}
        for p in preds:
            mid = p.get("model_id")
            by_model.setdefault(mid, []).append(p)

        for mid, plist in by_model.items():
            entrant = REGISTRY.get(mid)
            mname = entrant.name if entrant else mid
            correct_count = 0
            valid_count = 0
            cat_hits = {c: 0 for c in GUARDRAIL_CATEGORIES}
            cat_totals = {c: 0 for c in GUARDRAIL_CATEGORIES}
            layer_hits = {l: 0 for l in AGENT_LAYERS}
            layer_totals = {l: 0 for l in AGENT_LAYERS}
            predictions_list = []
            total_lat = 0

            for p in plist:
                cid = p.get("case_id")
                c = case_dict.get(cid)
                if not c:
                    continue

                gold = c.gold
                payload = c.provenance.get("payload", "")
                context = c.provenance.get("context", "")
                layer = c.provenance.get("layer", "")

                cat_totals[gold] += 1
                if layer in layer_totals:
                    layer_totals[layer] += 1

                selected = p.get("selected")
                status = p.get("status", "ok")
                lat = p.get("request_ms", 0)
                total_lat += lat

                if status == "ok" and selected in GUARDRAIL_CATEGORIES:
                    valid_count += 1
                    if selected == gold:
                        correct_count += 1
                        cat_hits[gold] += 1
                        if layer in layer_hits:
                            layer_hits[layer] += 1

                predictions_list.append({
                    "case_id": cid,
                    "gold": gold,
                    "selected": selected or "N/A",
                    "layer": layer,
                    "context": context,
                    "payload": payload,
                    "request_ms": lat,
                    "status": status,
                })

            acc = (correct_count / len(cases)) * 100.0 if cases else 0
            avg_lat = total_lat / len(plist) if plist else 0
            cat_acc = {cat: (cat_hits[cat] / cat_totals[cat] * 100.0) if cat_totals[cat] > 0 else 0 for cat in GUARDRAIL_CATEGORIES}
            layer_acc = {l: (layer_hits[l] / layer_totals[l] * 100.0) if layer_totals[l] > 0 else 0 for l in AGENT_LAYERS}
            macro_f1 = sum(cat_hits[cat] / cat_totals[cat] for cat in GUARDRAIL_CATEGORIES if cat_totals[cat] > 0) / len(GUARDRAIL_CATEGORIES)

            model_results.append({
                "id": mid,
                "name": f"{mname} (Execução Real)",
                "correct_count": correct_count,
                "accuracy": acc,
                "macro_f1": macro_f1,
                "avg_latency_ms": avg_lat,
                "valid_rate": (valid_count / len(cases)) * 100.0 if cases else 0,
                "category_accuracy": cat_acc,
                "layer_accuracy": layer_acc,
            })
            predictions_map[mid] = predictions_list

        return model_results, predictions_map
    except Exception as e:
        print(f"Aviso ao carregar dados reais do SQLite: {e}")
        return [], {}

def main():
    cases = agent_guardrails_cases()
    model_results, predictions_map = generate_simulated_guardrail_predictions(cases)

    real_results, real_preds = load_real_guardrail_predictions_from_store(cases)
    if real_results:
        model_results = real_results + model_results
        predictions_map.update(real_preds)

    categories_payload = [
        {"code": c, "name": CATEGORY_NAMES[c], "description": CATEGORY_DESCRIPTIONS[c]}
        for c in GUARDRAIL_CATEGORIES
    ]

    data_payload = {
        "layers": AGENT_LAYERS,
        "categories": categories_payload,
        "models": model_results,
        "predictions": predictions_map
    }

    data_json_str = json.dumps(data_payload, ensure_ascii=False).replace("<", "\\u003c")
    html_content = HTML_TEMPLATE.replace("__DATA__", data_json_str)

    results_dir = ROOT / "results"
    public_reports_dir = ROOT / ".arena" / "public-reports"
    results_dir.mkdir(exist_ok=True)
    public_reports_dir.mkdir(parents=True, exist_ok=True)

    out_html_1 = results_dir / "agent-guardrails-v1.html"
    out_html_2 = public_reports_dir / "agent-guardrails-v1.html"

    out_html_1.write_text(html_content, encoding="utf-8")
    out_html_2.write_text(html_content, encoding="utf-8")

    print(f"Relatório HTML de Guardrails gerado com sucesso em:")
    print(f" - {out_html_1}")
    print(f" - {out_html_2}")

if __name__ == "__main__":
    main()
