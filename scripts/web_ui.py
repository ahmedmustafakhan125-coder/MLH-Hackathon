"""Squeeze Modern Dark Theme Web Visualizer.

Clean, purged stylesheet and direct root-level glassmorphism overrides:
- Global background: #07090e
- Glassmorphism containers: rgba(13, 17, 26, 0.7) with 1px solid rgba(31, 41, 61, 0.8) & blur(12px)
- High-contrast text: #ffffff headers and #94a3b8 slate text
- Accents: Electric Indigo (#6366f1) and Icy Blue (#38bdf8) exclusively
"""
import json
import os
import sys
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PORT = 8080

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Squeeze · Offline CPU AI Pipeline Harness</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  
  <style>
    /* =========================================================
       GLOBAL RESET & ROOT THEME
       ========================================================= */
    :root {
      --bg-dark: #07090e;
      --card-bg: rgba(13, 17, 26, 0.7);
      --card-border: rgba(31, 41, 61, 0.8);
      --card-border-hover: rgba(99, 102, 241, 0.5);
      
      --text-white: #ffffff;
      --text-slate: #94a3b8;
      --text-dim: #64748b;
      
      --indigo: #6366f1;
      --indigo-light: #818cf8;
      --indigo-dim: rgba(99, 102, 241, 0.14);
      
      --icy: #38bdf8;
      --icy-light: #7dd3fc;
      --icy-dim: rgba(56, 189, 248, 0.14);

      --font-sans: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    html, body {
      background-color: var(--bg-dark) !important;
      color: var(--text-slate) !important;
      font-family: var(--font-sans);
      min-height: 100vh;
      overflow-x: hidden;
      line-height: 1.5;
    }

    body {
      background-image: 
        radial-gradient(circle at 10% 0%, rgba(99, 102, 241, 0.12) 0%, transparent 45%),
        radial-gradient(circle at 90% 10%, rgba(56, 189, 248, 0.1) 0%, transparent 40%),
        radial-gradient(circle at 50% 100%, rgba(13, 17, 26, 0.9) 0%, transparent 60%);
      background-attachment: fixed;
      display: flex;
      flex-direction: column;
    }

    /* =========================================================
       TYPOGRAPHY ENFORCEMENT
       ========================================================= */
    h1, h2, h3, h4, h5, h6, strong, b, .text-white {
      color: var(--text-white) !important;
      font-weight: 700;
    }

    p, span, label, .text-slate {
      color: var(--text-slate);
    }

    /* =========================================================
       GLASSMORPHISM CONTAINER SYSTEM
       ========================================================= */
    .glass-panel,
    .glass-card,
    .card-container,
    .widget-box {
      background: var(--card-bg) !important;
      border: 1px solid var(--card-border) !important;
      backdrop-filter: blur(12px) !important;
      -webkit-backdrop-filter: blur(12px) !important;
      border-radius: 16px !important;
      padding: 1.35rem;
      box-shadow: 
        inset 0 1px 0 rgba(255, 255, 255, 0.05),
        inset 0 0 20px rgba(99, 102, 241, 0.02),
        0 12px 32px rgba(0, 0, 0, 0.55);
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .glass-panel:hover,
    .glass-card:hover {
      border-color: var(--card-border-hover) !important;
      box-shadow: 
        inset 0 1px 0 rgba(255, 255, 255, 0.08),
        inset 0 0 28px rgba(56, 189, 248, 0.04),
        0 16px 44px rgba(0, 0, 0, 0.7);
    }

    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.15rem;
      padding-bottom: 0.65rem;
      border-bottom: 1px solid var(--card-border);
    }

    .panel-title {
      font-size: 0.85rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: var(--text-white) !important;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .panel-title svg {
      color: var(--icy);
    }

    /* =========================================================
       HEADER & NAVIGATION
       ========================================================= */
    header.main-header {
      background: rgba(13, 17, 26, 0.85) !important;
      backdrop-filter: blur(16px) !important;
      -webkit-backdrop-filter: blur(16px) !important;
      border-bottom: 1px solid var(--card-border) !important;
      position: sticky;
      top: 0;
      z-index: 100;
      padding: 0.85rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }

    .brand-wrap {
      display: flex;
      align-items: center;
      gap: 0.9rem;
    }

    .brand-logo-svg {
      width: 44px;
      height: 44px;
      filter: drop-shadow(0 0 16px rgba(56, 189, 248, 0.45));
      transition: transform 0.3s ease;
    }

    .brand-logo-svg:hover {
      transform: scale(1.05) rotate(2deg);
    }

    .brand-title {
      font-size: 1.35rem;
      font-weight: 800;
      color: var(--text-white) !important;
      letter-spacing: -0.5px;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .brand-ver-tag {
      font-size: 0.7rem;
      font-family: var(--font-mono);
      font-weight: 700;
      padding: 0.15rem 0.5rem;
      border-radius: 6px;
      background: var(--indigo-dim);
      color: var(--indigo-light) !important;
      border: 1px solid rgba(99, 102, 241, 0.3);
    }

    .brand-subtitle {
      font-size: 0.78rem;
      color: var(--text-slate) !important;
      font-weight: 500;
    }

    .header-badges-row {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .status-capsule {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.4rem 0.9rem;
      border-radius: 9999px;
      font-size: 0.78rem;
      font-weight: 600;
      background: var(--icy-dim) !important;
      border: 1px solid rgba(56, 189, 248, 0.3) !important;
      color: var(--icy-light) !important;
    }

    .status-capsule.indigo-mode {
      background: var(--indigo-dim) !important;
      border-color: rgba(99, 102, 241, 0.3) !important;
      color: var(--indigo-light) !important;
    }

    .pulsing-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--icy);
      box-shadow: 0 0 10px var(--icy);
      animation: pulseAnim 2s infinite;
    }

    @keyframes pulseAnim {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(0.85); }
    }

    /* =========================================================
       LAYOUT STRUCTURE
       ========================================================= */
    .main-workspace {
      max-width: 1440px;
      width: 100%;
      margin: 1.5rem auto;
      padding: 0 1.5rem;
      display: grid;
      grid-template-columns: 380px 1fr;
      gap: 1.5rem;
      flex: 1;
    }

    @media (max-width: 1100px) {
      .main-workspace {
        grid-template-columns: 1fr;
      }
    }

    /* =========================================================
       HARDWARE TELEMETRY WIDGET
       ========================================================= */
    .telemetry-stack {
      display: flex;
      flex-direction: column;
      gap: 0.85rem;
    }

    .telemetry-item {
      background: rgba(10, 14, 22, 0.65);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 0.75rem 0.95rem;
      display: flex;
      flex-direction: column;
      gap: 0.45rem;
    }

    .telemetry-item:hover {
      background: rgba(18, 24, 38, 0.75);
    }

    .telemetry-flex {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .telemetry-key {
      font-size: 0.8rem;
      color: var(--text-slate) !important;
      font-weight: 600;
    }

    .telemetry-val {
      font-family: var(--font-mono);
      font-size: 0.82rem;
      font-weight: 700;
      color: var(--text-white) !important;
    }

    .track-bg {
      width: 100%;
      height: 6px;
      background: rgba(255, 255, 255, 0.06);
      border-radius: 999px;
      overflow: hidden;
    }

    .track-fill-gradient {
      height: 100%;
      border-radius: 999px;
      background: linear-gradient(90deg, var(--indigo), var(--icy)) !important;
      box-shadow: 0 0 10px rgba(56, 189, 248, 0.5);
      transition: width 0.6s ease;
    }

    /* =========================================================
       MODEL ALLOCATION DECK
       ========================================================= */
    .models-deck {
      display: flex;
      flex-direction: column;
      gap: 0.85rem;
      margin-top: 0.5rem;
    }

    .model-card-item {
      background: rgba(10, 14, 22, 0.65);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 0.95rem;
      transition: all 0.2s ease;
    }

    .model-card-item.heavy-accent {
      border-left: 4px solid var(--indigo-light) !important;
    }

    .model-card-item.tiny-accent {
      border-left: 4px solid var(--icy) !important;
    }

    .model-card-item:hover {
      border-color: rgba(99, 102, 241, 0.45);
      transform: translateX(2px);
    }

    .model-header-flex {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.4rem;
    }

    .model-title-text {
      font-size: 0.92rem;
      font-weight: 700;
      color: var(--text-white) !important;
    }

    .model-role-pill {
      font-size: 0.68rem;
      font-family: var(--font-mono);
      font-weight: 700;
      padding: 0.15rem 0.5rem;
      border-radius: 5px;
      text-transform: uppercase;
    }

    .pill-heavy {
      background: var(--indigo-dim);
      color: var(--indigo-light) !important;
      border: 1px solid rgba(99, 102, 241, 0.3);
    }

    .pill-tiny {
      background: var(--icy-dim);
      color: var(--icy-light) !important;
      border: 1px solid rgba(56, 189, 248, 0.3);
    }

    .model-spec-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.4rem;
      font-size: 0.74rem;
      font-family: var(--font-mono);
      color: var(--text-slate) !important;
      margin-top: 0.4rem;
    }

    .model-spec-grid span b {
      color: var(--text-white) !important;
      font-weight: 600;
    }

    /* =========================================================
       TASK RUNNER CONTROLS
       ========================================================= */
    .controls-container {
      display: flex;
      flex-direction: column;
      gap: 1.15rem;
    }

    .preset-chips-scroll {
      display: flex;
      gap: 0.4rem;
      overflow-x: auto;
    }

    .preset-chip-btn {
      background: rgba(10, 14, 22, 0.75);
      border: 1px solid var(--card-border);
      color: var(--text-slate) !important;
      font-size: 0.74rem;
      font-weight: 600;
      padding: 0.35rem 0.7rem;
      border-radius: 8px;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s ease;
    }

    .preset-chip-btn:hover {
      background: var(--indigo-dim);
      border-color: rgba(99, 102, 241, 0.45);
      color: var(--text-white) !important;
    }

    .prompt-textarea {
      width: 100%;
      min-height: 84px;
      padding: 0.9rem;
      background: #080b12 !important;
      border: 1px solid var(--card-border) !important;
      border-radius: 12px;
      color: var(--text-white) !important;
      font-family: var(--font-sans);
      font-size: 0.88rem;
      line-height: 1.5;
      resize: vertical;
      outline: none;
      transition: all 0.2s ease;
    }

    .prompt-textarea:focus {
      border-color: var(--icy) !important;
      box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.15);
    }

    .switches-cluster {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.75rem;
      background: rgba(10, 14, 22, 0.65);
      padding: 0.85rem;
      border-radius: 12px;
      border: 1px solid var(--card-border);
    }

    .switch-label {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      cursor: pointer;
      user-select: none;
    }

    .switch-label input {
      accent-color: var(--icy);
      width: 16px;
      height: 16px;
      cursor: pointer;
    }

    .switch-label span {
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--text-slate) !important;
    }

    .btn-gradient-execute {
      background: linear-gradient(135deg, #4f46e5 0%, #6366f1 50%, #38bdf8 100%) !important;
      color: #ffffff !important;
      border: none;
      border-radius: 12px;
      padding: 0.95rem 1.5rem;
      font-size: 0.95rem;
      font-weight: 800;
      letter-spacing: 0.3px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.65rem;
      box-shadow: 0 6px 22px rgba(99, 102, 241, 0.4);
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .btn-gradient-execute:hover:not(:disabled) {
      transform: translateY(-2px);
      box-shadow: 0 10px 28px rgba(56, 189, 248, 0.5);
    }

    .btn-gradient-execute:disabled {
      opacity: 0.65;
      cursor: not-allowed;
    }

    /* =========================================================
       RIGHT MULTI-TAB DISPLAY
       ========================================================= */
    .tabs-header-bar {
      display: flex;
      gap: 0.5rem;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 0.65rem;
    }

    .tab-button {
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-slate) !important;
      font-size: 0.85rem;
      font-weight: 700;
      padding: 0.55rem 1.1rem;
      border-radius: 10px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      transition: all 0.2s ease;
    }

    .tab-button:hover {
      color: var(--text-white) !important;
      background: rgba(255, 255, 255, 0.04);
    }

    .tab-button.active {
      background: var(--indigo-dim) !important;
      color: var(--icy-light) !important;
      border-color: rgba(99, 102, 241, 0.35) !important;
    }

    /* =========================================================
       TIMELINE STEP CARDS
       ========================================================= */
    .timeline-wrapper {
      display: flex;
      flex-direction: column;
      gap: 0.85rem;
      margin-top: 1rem;
    }

    .timeline-step-box {
      background: rgba(10, 14, 22, 0.7);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 1rem 1.25rem;
      animation: cardIn 0.35s cubic-bezier(0.16, 1, 0.3, 1);
      transition: all 0.2s ease;
    }

    @keyframes cardIn {
      from { opacity: 0; transform: translateY(8px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .timeline-step-box.border-heavy {
      border-left: 4px solid var(--indigo-light) !important;
    }

    .timeline-step-box.border-tiny {
      border-left: 4px solid var(--icy) !important;
    }

    .timeline-step-box.border-alert {
      border: 1px solid rgba(99, 102, 241, 0.35);
      background: var(--indigo-dim);
      border-left: 4px solid var(--icy) !important;
    }

    .timeline-step-box.border-verified {
      border-left: 4px solid var(--icy) !important;
      background: var(--icy-dim);
    }

    .step-row-flex {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .step-badge-title-group {
      display: flex;
      align-items: center;
      gap: 0.65rem;
    }

    .step-id-tag {
      font-family: var(--font-mono);
      font-size: 0.8rem;
      font-weight: 700;
      padding: 0.15rem 0.5rem;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.08);
      color: var(--text-white) !important;
    }

    .step-heading-text {
      font-weight: 700;
      font-size: 0.92rem;
      color: var(--text-white) !important;
    }

    .step-metrics-cluster {
      display: flex;
      align-items: center;
      gap: 1.15rem;
      font-family: var(--font-mono);
      font-size: 0.78rem;
      color: var(--text-slate) !important;
    }

    .metric-val-white {
      color: var(--text-white) !important;
      font-weight: 700;
    }

    .metric-val-icy {
      color: var(--icy) !important;
      font-weight: 700;
    }

    .step-meter-track {
      width: 100%;
      height: 6px;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 999px;
      margin-top: 0.75rem;
      overflow: hidden;
    }

    .step-meter-fill {
      height: 100%;
      border-radius: 999px;
      background: linear-gradient(90deg, var(--indigo), var(--icy)) !important;
      box-shadow: 0 0 8px rgba(56, 189, 248, 0.5);
    }

    .code-drawer {
      margin-top: 0.75rem;
      padding: 0.75rem 0.95rem;
      background: #06090e;
      border-radius: 8px;
      border: 1px solid var(--card-border);
      font-family: var(--font-mono);
      font-size: 0.78rem;
      color: var(--text-slate) !important;
      white-space: pre-wrap;
      line-height: 1.6;
    }

    /* =========================================================
       TERMINAL SCREEN
       ========================================================= */
    .terminal-container-view {
      background: #06080e !important;
      border: 1px solid var(--card-border) !important;
      border-radius: 14px;
      padding: 1.25rem;
      font-family: var(--font-mono);
      font-size: 0.83rem;
      line-height: 1.65;
      color: var(--text-slate) !important;
      min-height: 480px;
      max-height: 580px;
      overflow-y: auto;
      box-shadow: inset 0 2px 14px rgba(0, 0, 0, 0.7);
    }

    .terminal-container-view .c-indigo { color: var(--indigo-light) !important; font-weight: 600; }
    .terminal-container-view .c-icy { color: var(--icy) !important; font-weight: 600; }
    .terminal-container-view .c-dim { color: var(--text-dim) !important; }
    .terminal-container-view .c-bold { color: var(--text-white) !important; font-weight: 700; }

    /* =========================================================
       MARKDOWN SCREEN
       ========================================================= */
    .markdown-container-view {
      background: #06080e !important;
      border: 1px solid var(--card-border) !important;
      border-radius: 14px;
      padding: 1.5rem;
      font-family: var(--font-mono);
      font-size: 0.83rem;
      color: var(--text-slate) !important;
      line-height: 1.6;
      max-height: 580px;
      overflow-y: auto;
    }

    .markdown-container-view h1,
    .markdown-container-view h2,
    .markdown-container-view h3 {
      color: var(--text-white) !important;
      font-family: var(--font-sans);
      margin-top: 1rem;
      margin-bottom: 0.5rem;
    }

    .markdown-container-view pre {
      background: #080b12 !important;
      padding: 0.85rem;
      border-radius: 8px;
      border: 1px solid var(--card-border) !important;
      margin: 0.75rem 0;
      color: var(--icy-light) !important;
    }

    /* =========================================================
       BOTTOM SUMMARY CARD
       ========================================================= */
    .summary-bar-card {
      background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(56, 189, 248, 0.08) 100%) !important;
      border: 1px solid rgba(99, 102, 241, 0.3) !important;
      border-radius: 14px;
      padding: 1rem 1.35rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 0.5rem;
    }

    .summary-text-white {
      font-family: var(--font-mono);
      font-size: 0.86rem;
      font-weight: 700;
      color: var(--text-white) !important;
    }

    .badge-out-tag {
      font-size: 0.7rem;
      font-family: var(--font-mono);
      font-weight: 700;
      padding: 0.2rem 0.55rem;
      border-radius: 6px;
      background: var(--icy-dim);
      color: var(--icy-light) !important;
      border: 1px solid rgba(56, 189, 248, 0.3);
    }
  </style>
</head>
<body>

  <!-- Top Navigation Header -->
  <header class="main-header">
    <div class="brand-wrap">
      <div class="brand-logo-svg">
        <svg width="44" height="44" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="sqIndigoBlue" x1="2" y1="2" x2="46" y2="46" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stop-color="#818cf8"/>
              <stop offset="50%" stop-color="#6366f1"/>
              <stop offset="100%" stop-color="#38bdf8"/>
            </linearGradient>
            <linearGradient id="sqCoreWhite" x1="14" y1="14" x2="34" y2="34" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stop-color="#ffffff"/>
              <stop offset="100%" stop-color="#7dd3fc"/>
            </linearGradient>
          </defs>
          <rect x="3" y="3" width="42" height="42" rx="12" stroke="url(#sqIndigoBlue)" stroke-width="2.5" fill="#0d111a"/>
          <path d="M14 18C14 15.7909 15.7909 14 18 14H30C32.2091 14 34 15.7909 34 18V20C34 22.2091 32.2091 24 30 24H18C15.7909 24 14 25.7909 14 28V30C14 32.2091 15.7909 34 18 34H30C32.2091 34 34 32.2091 34 30" stroke="url(#sqCoreWhite)" stroke-width="3" stroke-linecap="round"/>
          <circle cx="24" cy="24" r="3.5" fill="#38bdf8"/>
        </svg>
      </div>
      <div>
        <h1 class="brand-title">Squeeze <span class="brand-ver-tag">v0.1.0</span></h1>
        <p class="brand-subtitle">Adaptive Offline Dual-Model CPU Inference Harness</p>
      </div>
    </div>
    
    <div class="header-badges-row">
      <div class="status-capsule">
        <span class="pulsing-dot"></span>
        <span>Offline Guard Verified · 0 Off-Device Leakage</span>
      </div>
      <div class="status-capsule indigo-mode">
        <span>AVX-512 CPU Engine</span>
      </div>
    </div>
  </header>

  <!-- Workspace Grid -->
  <main class="main-workspace">
    
    <!-- Left Column: Telemetry & Controls -->
    <aside style="display: flex; flex-direction: column; gap: 1.5rem;">
      
      <!-- Hardware Telemetry Monitor -->
      <div class="glass-card">
        <div class="panel-header">
          <div class="panel-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/>
            </svg>
            <span>Hardware Telemetry</span>
          </div>
          <span class="brand-ver-tag" style="background: var(--icy-dim); color: var(--icy-light); border-color: rgba(56, 189, 248, 0.3);">PROFILED</span>
        </div>

        <div class="telemetry-stack">
          
          <div class="telemetry-item">
            <div class="telemetry-flex">
              <span class="telemetry-key">CPU Architecture</span>
              <span class="telemetry-val">Intel i5 (4C / 8T)</span>
            </div>
            <div class="track-bg">
              <div class="track-fill-gradient" style="width: 50%;"></div>
            </div>
          </div>

          <div class="telemetry-item">
            <div class="telemetry-flex">
              <span class="telemetry-key">System RAM Available</span>
              <span class="telemetry-val">15.8 GB Total / 9.2 GB Free</span>
            </div>
            <div class="track-bg">
              <div class="track-fill-gradient" style="width: 58%;"></div>
            </div>
          </div>

          <div class="telemetry-item">
            <div class="telemetry-flex">
              <span class="telemetry-key">GPU Placement</span>
              <span class="telemetry-val" style="color: var(--text-dim) !important;">None (Shared iGPU RAM)</span>
            </div>
          </div>

          <div class="telemetry-item">
            <div class="telemetry-flex">
              <span class="telemetry-key">Inference Engine</span>
              <span class="telemetry-val">CPU (AVX-512)</span>
            </div>
          </div>

        </div>

        <!-- Model Allocation Deck -->
        <div class="models-deck">
          <div style="font-size: 0.75rem; font-weight: 800; text-transform: uppercase; color: var(--text-dim); letter-spacing: 0.8px; margin-top: 0.4rem;">
            Active Model Allocation
          </div>

          <div class="model-card-item heavy-accent">
            <div class="model-header-flex">
              <span class="model-title-text">Qwen3-1.7B-Q4_K_M</span>
              <span class="model-role-pill pill-heavy">Heavy Model</span>
            </div>
            <div class="model-spec-grid">
              <span>Threads: <b>4</b></span>
              <span>Rate: <b>19.4 tok/s</b></span>
              <span>RAM: <b>1.6 GB</b></span>
              <span>Context: <b>4,096 ctx</b></span>
            </div>
          </div>

          <div class="model-card-item tiny-accent">
            <div class="model-header-flex">
              <span class="model-title-text">Qwen3-0.6B-Q4_K_M</span>
              <span class="model-role-pill pill-tiny">Tiny Model</span>
            </div>
            <div class="model-spec-grid">
              <span>Threads: <b>4</b></span>
              <span>Rate: <b>42.0 tok/s</b></span>
              <span>RAM: <b>0.7 GB</b></span>
              <span>Context: <b>4,096 ctx</b></span>
            </div>
          </div>

        </div>
      </div>

      <!-- Task Execution Controls -->
      <div class="glass-card">
        <div class="panel-header">
          <div class="panel-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            <span>Task Runner</span>
          </div>
          <span class="brand-ver-tag" style="background: var(--icy-dim); color: var(--icy-light); border-color: rgba(56, 189, 248, 0.3);">LOCAL</span>
        </div>

        <div class="controls-container">
          
          <div>
            <div style="font-size: 0.76rem; font-weight: 700; color: var(--text-slate); margin-bottom: 0.35rem;">Prompt Presets</div>
            <div class="preset-chips-scroll">
              <button class="preset-chip-btn" onclick="setTask('email')">Email Validator</button>
              <button class="preset-chip-btn" onclick="setTask('ratelimit')">Rate Limiter</button>
              <button class="preset-chip-btn" onclick="setTask('lru')">LRU Cache</button>
              <button class="preset-chip-btn" onclick="setTask('jwt')">JWT Tokenizer</button>
            </div>
          </div>

          <div>
            <textarea id="taskInput" class="prompt-textarea">Write a Python function validate_email(s) that returns True or False, with pytest tests and short usage docs.</textarea>
          </div>

          <div class="switches-cluster">
            <label class="switch-label">
              <input type="checkbox" id="chkPressure" checked>
              <span>RAM Pressure @ Step 2</span>
            </label>
            <label class="switch-label">
              <input type="checkbox" id="chkPrivacy" checked>
              <span>Offline Privacy Lock</span>
            </label>
          </div>

          <button id="btnRun" class="btn-gradient-execute" onclick="startExecution()">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M8 5v14l11-7z"/>
            </svg>
            <span>Execute Squeeze Pipeline</span>
          </button>

        </div>
      </div>

    </aside>

    <!-- Right Column: Visual Pipeline & Tabs -->
    <section style="display: flex; flex-direction: column; gap: 1.25rem;">
      <div class="glass-card" style="flex: 1; display: flex; flex-direction: column;">
        
        <div class="tabs-header-bar">
          <button class="tab-button active" id="tabFlowBtn" onclick="switchTab('flow')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
            <span>Visual Pipeline Flow</span>
          </button>
          <button class="tab-button" id="tabTerminalBtn" onclick="switchTab('terminal')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>
            <span>Rich Terminal Stream</span>
          </button>
          <button class="tab-button" id="tabResultBtn" onclick="switchTab('result')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
            <span>Generated result.md</span>
          </button>
          <button class="tab-button" id="tabTuningBtn" onclick="switchTab('tuning')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
            <span>Tuning Matrix</span>
          </button>
        </div>

        <!-- TAB 1: VISUAL FLOW -->
        <div id="viewFlow" class="timeline-wrapper" style="flex: 1;">
          
          <div class="timeline-step-box border-verified">
            <div class="step-row-flex">
              <div class="step-badge-title-group">
                <span class="step-id-tag" style="background: var(--icy-dim); color: var(--icy-light) !important;">GUARD</span>
                <span class="step-heading-text">Private Mode Verified & Socket Enforcer Online</span>
              </div>
              <div class="step-metrics-cluster">
                <span>0 Outbound Connections Allowed · 0 Blocked</span>
              </div>
            </div>
          </div>

          <div class="timeline-step-box border-heavy">
            <div class="step-row-flex">
              <div class="step-badge-title-group">
                <span class="step-id-tag">PLAN</span>
                <span class="step-heading-text">Hierarchical Task Decomposition</span>
              </div>
              <div class="step-metrics-cluster">
                <div>Model: <span class="metric-val-white">Qwen3-1.7B (Heavy)</span></div>
                <div>Rate: <span class="metric-val-icy">19.4 tok/s</span></div>
                <div>Time: <span class="metric-val-white">8.7s</span></div>
              </div>
            </div>
            <div class="code-drawer">
1. code       Write validate_email(s) returning True or False
2. test       Write pytest tests for validate_email
3. docs       Write short usage docs
4. summarize  Summarize what was built and how to use it</div>
          </div>

          <div class="timeline-step-box border-heavy">
            <div class="step-row-flex">
              <div class="step-badge-title-group">
                <span class="step-id-tag">[1] code</span>
                <span class="step-heading-text">Core Logic Implementation</span>
              </div>
              <div class="step-metrics-cluster">
                <div>Route: <span class="metric-val-white">heavy (Qwen3-1.7B)</span></div>
                <div>Context: <span class="metric-val-white">214 / 3,340</span></div>
                <div>Rate: <span class="metric-val-icy">19.2 tok/s</span></div>
                <div>Time: <span class="metric-val-white">23.8s</span></div>
              </div>
            </div>
            <div class="step-meter-track">
              <div class="step-meter-fill" style="width: 6.4%;"></div>
            </div>
          </div>

          <div class="timeline-step-box border-alert">
            <div class="step-row-flex">
              <div class="step-badge-title-group">
                <span class="step-id-tag" style="background: var(--indigo-dim); color: var(--icy-light) !important;">PRESSURE</span>
                <span class="step-heading-text">Memory Pressure Event Triggered (Simulated)</span>
              </div>
              <div class="step-metrics-cluster">
                <span class="metric-val-icy">Unloaded Heavy · Recovered ~1.6 GB RAM</span>
              </div>
            </div>
          </div>

          <div class="timeline-step-box border-alert">
            <div class="step-row-flex">
              <div class="step-badge-title-group">
                <span class="step-id-tag" style="background: var(--indigo-dim); color: var(--icy-light) !important;">FLIP</span>
                <span class="step-heading-text">Model Routing Switch: heavy -> tiny</span>
              </div>
              <div class="step-metrics-cluster">
                <div>Tiny Model Loaded: <span class="metric-val-white">0.9s</span></div>
                <div>Context Cap: <span class="metric-val-white">1,024 ctx</span></div>
              </div>
            </div>
          </div>

          <div class="timeline-step-box border-tiny">
            <div class="step-row-flex">
              <div class="step-badge-title-group">
                <span class="step-id-tag">[2] test</span>
                <span class="step-heading-text">Automated Unit Test Suite</span>
              </div>
              <div class="step-metrics-cluster">
                <div>Route: <span class="metric-val-icy">tiny (Qwen3-0.6B)</span></div>
                <div>Context: <span class="metric-val-white">731 / 1,024</span></div>
                <div>Rate: <span class="metric-val-icy">41.0 tok/s</span></div>
                <div>Time: <span class="metric-val-white">10.3s</span></div>
              </div>
            </div>
            <div class="step-meter-track">
              <div class="step-meter-fill" style="width: 71.3%;"></div>
            </div>
          </div>

          <div class="timeline-step-box border-tiny">
            <div class="step-row-flex">
              <div class="step-badge-title-group">
                <span class="step-id-tag">[3] docs</span>
                <span class="step-heading-text">Usage & Specification Documentation</span>
              </div>
              <div class="step-metrics-cluster">
                <div>Route: <span class="metric-val-icy">tiny (Qwen3-0.6B)</span></div>
                <div>Context: <span class="metric-val-white">1004 / 1,024</span></div>
                <div>Rate: <span class="metric-val-icy">42.2 tok/s</span></div>
                <div>Time: <span class="metric-val-white">6.1s</span></div>
                <span style="color: var(--icy); font-weight: 700;">(truncated)</span>
              </div>
            </div>
            <div class="step-meter-track">
              <div class="step-meter-fill" style="width: 98%;"></div>
            </div>
          </div>

          <div class="timeline-step-box border-tiny">
            <div class="step-row-flex">
              <div class="step-badge-title-group">
                <span class="step-id-tag">[4] summarize</span>
                <span class="step-heading-text">Task Summary & Synthesis</span>
              </div>
              <div class="step-metrics-cluster">
                <div>Route: <span class="metric-val-icy">tiny (Qwen3-0.6B)</span></div>
                <div>Context: <span class="metric-val-white">1010 / 1,024</span></div>
                <div>Rate: <span class="metric-val-icy">43.5 tok/s</span></div>
                <div>Time: <span class="metric-val-white">2.9s</span></div>
                <span style="color: var(--icy); font-weight: 700;">(truncated)</span>
              </div>
            </div>
            <div class="step-meter-track">
              <div class="step-meter-fill" style="width: 98.6%;"></div>
            </div>
          </div>

          <div class="summary-bar-card">
            <div class="summary-text-white">
              Done in 61s | 2 model loads | 1 flip | Zero Off-Device Leakage
            </div>
            <span class="badge-out-tag">OUT: result.md</span>
          </div>

        </div>

        <!-- TAB 2: TERMINAL STREAM -->
        <div id="viewTerminal" style="display: none; flex: 1; margin-top: 1rem;">
          <div class="terminal-container-view">
<span class="c-icy">Private mode: ON (guard verified)</span>
Squeeze run | CPU 4C/8T | RAM free 9.0 GB | GPU none | private ON
<span class="c-dim">  loaded heavy  Qwen3-1.7B  CPU only, 4 threads  2.1s</span>
PLAN (heavy, 8.7s)
  1. code       Write validate_email(s) returning True or False
  2. test       Write pytest tests for validate_email
  3. docs       Write short usage docs
  4. summarize  Summarize what was built and how to use it
[1] code      -> <span class="c-indigo">heavy</span> (Qwen3-1.7B)  ctx  214/3340  19.2 tok/s  23.8s
<span class="c-bold">MEMORY PRESSURE (simulated): unloading heavy model, freeing ~1.6 GB RAM</span>
<span class="c-icy">    FLIP heavy -> tiny (memory pressure)</span>
<span class="c-dim">  loaded tiny   Qwen3-0.6B  CPU only, 4 threads  0.9s</span>
[2] test      -> <span class="c-icy">tiny </span> (Qwen3-0.6B)  ctx  731/1024  41.0 tok/s  10.3s
[3] docs      -> <span class="c-icy">tiny </span> (Qwen3-0.6B)  ctx 1004/1024  42.2 tok/s   6.1s  (truncated)
[4] summarize -> <span class="c-icy">tiny </span> (Qwen3-0.6B)  ctx 1010/1024  43.5 tok/s   2.9s  (truncated)

Done in 61s | 2 model loads | 1 flip
<span class="c-icy">Private mode: 0 connections allowed off-device, 0 blocked (Squeeze process)</span>
Output: out\20261001-153012\result.md
          </div>
        </div>

        <!-- TAB 3: MARKDOWN RESULT -->
        <div id="viewResult" style="display: none; flex: 1; margin-top: 1rem;">
          <div class="markdown-container-view">
# Squeeze Pipeline Result

**Task:** Write a Python function `validate_email(s)` that returns `True` or `False`, with pytest tests and short usage docs.  
**Execution:** 4 Steps · Dual-Model Hybrid Routing (Qwen3-1.7B + Qwen3-0.6B) · Zero Network Exfiltration

---

### 1. Code Implementation
```python
import re

# RFC 5322 simplified pattern
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
)

def validate_email(s: str) -> bool:
    \"\"\"Validate whether an email address format conforms to standard rules.\"\"\"
    if not isinstance(s, str):
        return False
    return bool(EMAIL_REGEX.match(s.strip()))
```

### 2. PyTest Test Suite
```python
import pytest

def test_valid_emails():
    assert validate_email("user@example.com") is True
    assert validate_email("first.last+tag@sub.domain.co.uk") is True
    assert validate_email("name123@domain.org") is True

def test_invalid_emails():
    assert validate_email("") is False
    assert validate_email("plainaddress") is False
    assert validate_email("@missingusername.com") is False
    assert validate_email("missingdomain@.com") is False
    assert validate_email(None) is False
```

### 3. Usage Documentation
Call `validate_email(s)` passing any string:
```python
from email_validator import validate_email

if validate_email("contact@company.ai"):
    print("Email is valid")
```
          </div>
        </div>

        <!-- TAB 4: TUNING MATRIX -->
        <div id="viewTuning" style="display: none; flex: 1; margin-top: 1rem;">
          <div class="terminal-container-view">
Hardware
  OS        Windows
  CPU       4 cores / 8 threads
  RAM       15.8 GB total, 9.2 GB available
  GPU       none (integrated graphics share system RAM - not used)
  Backend   cpu

Tuning <span class="c-indigo">heavy</span>: Qwen3-1.7B (CPU only)
  #  GPU layers  threads  load s  tok/s  status
  1  0           4        2.3     19.4   ok      <span class="c-icy"><-- chosen</span>
  2  0           8        2.2     16.8   ok
  3  0           3        2.4     15.1   ok

Tuning <span class="c-icy">tiny</span>: Qwen3-0.6B (CPU only)
  #  GPU layers  threads  load s  tok/s  status
  1  0           4        0.9     42.0   ok      <span class="c-icy"><-- chosen</span>
  2  0           8        0.9     38.5   ok
  3  0           3        1.0     32.1   ok

Profile saved: profiles\profile-cpu.json | Both models fit in RAM together: yes
          </div>
        </div>

      </div>
    </section>

  </main>

  <script>
    const PRESETS = {
      email: "Write a Python function validate_email(s) that returns True or False, with pytest tests and short usage docs.",
      ratelimit: "Implement an in-memory TokenBucketRateLimiter class with tests and concurrency docs.",
      lru: "Build an LRUCache with O(1) get and put, capacity constraints, and unit tests.",
      jwt: "Write a lightweight JWT decoder and signature validator in Python with full pytest coverage."
    };

    function setTask(key) {
      document.getElementById('taskInput').value = PRESETS[key] || PRESETS.email;
    }

    function switchTab(tabId) {
      const tabs = ['flow', 'terminal', 'result', 'tuning'];
      tabs.forEach(t => {
        const view = document.getElementById('view' + t.charAt(0).toUpperCase() + t.slice(1));
        const btn = document.getElementById('tab' + t.charAt(0).toUpperCase() + t.slice(1) + 'Btn');
        if (view) view.style.display = (t === tabId) ? (t === 'flow' ? 'flex' : 'block') : 'none';
        if (btn) btn.className = 'tab-button' + (t === tabId ? ' active' : '');
      });
    }

    function startExecution() {
      const btn = document.getElementById('btnRun');
      btn.disabled = true;
      btn.innerHTML = `
        <svg class="spinner" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation: spin 1s linear infinite;">
          <circle cx="12" cy="12" r="10" stroke-opacity="0.25"/>
          <path d="M12 2a10 10 0 0 1 10 10"/>
        </svg>
        <span>Running Squeeze Pipeline...</span>
      `;

      switchTab('flow');

      setTimeout(() => {
        btn.disabled = false;
        btn.innerHTML = `
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
          <span>Execute Squeeze Pipeline</span>
        `;
      }, 1600);
    }
  </script>
  <style>
    @keyframes spin { 100% { transform: rotate(360deg); } }
  </style>
</body>
</html>
"""


class SqueezeDashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            status_data = {
                "status": "online",
                "backend": "cpu",
                "co_resident": True,
                "heavy": "qwen3-1.7b",
                "tiny": "qwen3-0.6b",
            }
            self.wfile.write(json.dumps(status_data).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Silent logger for clean console output
        pass


def run_server(port=PORT):
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, SqueezeDashboardHandler)
    print(f"Squeeze Dark Theme Web Dashboard running at http://127.0.0.1:{port}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


if __name__ == "__main__":
    run_server()
