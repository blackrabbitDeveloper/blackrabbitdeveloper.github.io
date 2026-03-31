#!/usr/bin/env python3
"""
BlackRabbit LAB — AI Post Maker v2 (Ollama 버전)
Jekyll 블로그 포스트 생성 + 수정 + 관리 도구

사전 준비:
    1. Ollama 설치: https://ollama.com
    2. 모델 다운로드: ollama pull qwen2.5:7b
    3. Ollama 실행 (백그라운드 자동 실행됨)

실행:
    python _tools/post_maker.py
"""

import json
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Timer

PORT = 8765
OLLAMA_BASE = "http://localhost:11434"

import sys as _sys
if getattr(_sys, 'frozen', False):
    # PyInstaller exe: _tools/dist/post_maker.exe → 두 단계 위가 프로젝트 루트
    _EXE_DIR     = os.path.dirname(os.path.abspath(_sys.executable))
    PROJECT_ROOT = os.path.normpath(os.path.join(_EXE_DIR, "../.."))
    SCRIPT_DIR   = os.path.normpath(os.path.join(PROJECT_ROOT, "_tools"))
else:
    SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))

POSTS_DIR    = os.path.normpath(os.path.join(PROJECT_ROOT, "_posts"))
DRAFTS_DIR   = os.path.normpath(os.path.join(PROJECT_ROOT, "_drafts"))
HISTORY_DIR  = os.path.normpath(os.path.join(SCRIPT_DIR, ".history"))
CONFIG_FILE  = os.path.join(SCRIPT_DIR, "schedule_config.json")
LOG_FILE     = os.path.join(SCRIPT_DIR, "auto_log.json")

CATEGORIES = ["시장분석", "투자 기초", "경제 공부", "ETF·펀드", "재테크", "뉴스 해설", "기업 분석", "기타"]

# ──────────────────────────────────────────────
# System Prompts
# ──────────────────────────────────────────────

SYSTEM_PROMPT = """당신은 투자 정보·경제 교육 블로그 'BlackRabbit LAB'의 전문 작가입니다.

## 블로그 정보
- 블로그: https://blackrabbitdeveloper.github.io
- 성격: 주식·ETF·경제 개념을 초중급 투자자도 이해할 수 있도록 쉽고 정확하게 설명하는 교육 블로그
- 독자층: 투자에 관심 있는 일반인, 경제 공부를 시작한 직장인, 재테크 입문자

## 카테고리별 가이드라인
- **시장분석**: 3000~4000자, 최근 시장 동향·지수·환율·금리 등을 데이터 기반으로 분석
- **투자 기초**: 3000~4500자, PER·ROE·배당·분산투자 등 주식 투자 핵심 개념을 쉽게 설명
- **경제 공부**: 3000~4500자, 거시경제·금리·인플레이션·GDP 등 경제 원리 해설
- **ETF·펀드**: 3000~4000자, ETF 구조·종류·투자 방법 및 펀드 비교
- **재테크**: 3000~4000자, 절세·적금·복리·포트폴리오 구성 등 실용적 자산 관리 팁
- **뉴스 해설**: 3000~4000자, 최신 경제·금융 뉴스를 배경 지식과 함께 해설
- **기업 분석**: 3000~5000자, 특정 기업의 사업 모델·재무지표·경쟁력·리스크를 객관적으로 분석
- **기타**: 3000~4000자, 공지·에세이·도서 추천 등

> 모든 카테고리 공통: 본문은 반드시 3000자 이상 작성하세요.

## SEO 요건 (반드시 준수)
- **title**: 20자 이상 60자 이하. 너무 짧거나 길면 SEO 감점.
- **description**: 50자 이상 150자 이하. 포스트 내용을 요약한 한 문장.
- **categories**: 반드시 포함. 목록: [시장분석, 투자 기초, 경제 공부, ETF·펀드, 재테크, 뉴스 해설, 기업 분석, 기타]

## 금지 표현
- "주식 추천" → "참고 지표", "분석 결과", "스크리닝 조건" 등으로 대체
- "확실한 수익", "수익 보장" → "역사적 데이터 기준", "백테스트 결과" 등으로 대체
- 특정 종목 매수·매도 직접 권유 금지

## 면책 고지 (content 본문 맨 마지막에 반드시 포함)
> ⚠️ **면책 고지**: 본 포스트는 정보 제공 목적으로 작성되었으며, 투자 권유가 아닙니다. 모든 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다.

## 작성 스타일
- 전문 용어는 반드시 괄호로 쉬운 설명 추가 (예: PER(주가수익비율))
- 실제 수치·사례·비교표를 적극 활용해 이해를 도움
- 마크다운 헤더(##, ###), 표, 인용문, 번호 목록을 구조적으로 사용
- 독자가 '다음에도 읽고 싶은' 블로그가 되도록 마무리에 핵심 요약 포함

## 출력 형식 (반드시 JSON)
응답을 반드시 아래 JSON 형식으로 출력하세요. JSON 외의 텍스트는 절대 포함하지 마세요.

{
  "filename": "YYYY-MM-DD-english-slug.md",
  "title": "제목 (20~60자)",
  "date": "YYYY-MM-DD",
  "categories": ["카테고리"],
  "tags": ["태그1", "태그2", "태그3"],
  "description": "SEO 설명 (50~150자)",
  "content": "마크다운 본문 (front matter 제외, 면책 고지 포함)"
}

### filename 규칙
- 영문 소문자 + 숫자 + 하이픈만 사용 (한글·공백·특수문자 금지)
- 형식: YYYY-MM-DD-주제-요약.md (예: 2026-03-10-etf-investment-basics.md)
- 반드시 .md 로 끝날 것
- 한글 파일명은 Jekyll sitemap 파싱 오류를 유발하므로 절대 사용 금지"""

EDIT_SYSTEM_PROMPT = """당신은 투자 정보·경제 교육 블로그 'BlackRabbit LAB'의 포스트를 수정하는 편집자입니다.

## 수정 규칙
- 사용자의 수정 지시를 정확히 반영하세요.
- 지시하지 않은 부분은 원문을 최대한 유지하세요.
- 파일명(date, title slug)은 변경하지 마세요. 단, 제목이 바뀌면 title 필드만 수정하세요.

## 금지 표현 (원문에 있어도 수정)
- "주식 추천" → "참고 지표", "분석 결과", "스크리닝 조건"
- "확실한 수익", "수익 보장" → "역사적 데이터 기준", "백테스트 결과"
- 특정 종목 매수·매도 직접 권유 표현

## 면책 고지
content 본문 마지막에 항상 포함:
> ⚠️ **면책 고지**: 본 포스트는 정보 제공 목적으로 작성되었으며, 투자 권유가 아닙니다. 모든 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다.

## 출력 형식 (반드시 JSON)
응답을 반드시 아래 JSON 형식으로 출력하세요. JSON 외의 텍스트는 절대 포함하지 마세요.

{
  "filename": "원본파일명.md",
  "title": "제목",
  "date": "YYYY-MM-DD",
  "categories": ["카테고리"],
  "tags": ["태그1", "태그2"],
  "description": "SEO 설명 (50~150자)",
  "content": "수정된 마크다운 본문 (front matter 제외, 면책 고지 포함)"
}"""

PROOFREAD_PROMPT = """한국어 투자·경제 블로그 포스트를 교정합니다. 수정이 필요한 부분만 찾아서 find/replace 쌍으로 알려주세요.

교정 대상: 맞춤법·띄어쓰기, 중국어 혼입, AI 아티팩트, 잘못된 금융용어, 마크다운 문법 오류, 명백한 사실 오류.
교정 금지: 문체·어조 변경, 문단 재배치, 새 내용 추가, front matter 변경.

반드시 아래 JSON 형식만 출력하세요. 설명이나 다른 텍스트는 절대 포함하지 마세요.
{"fixes":[{"find":"원문 그대로","replace":"수정문","reason":"사유"}]}
수정할 것이 없으면: {"fixes":[]}"""

# ──────────────────────────────────────────────
# HTML UI
# ──────────────────────────────────────────────

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BlackRabbit LAB — AI Post Maker</title>
  <script src="https://cdn.tailwindcss.com?plugins=typography"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <style>
    body { font-family: 'Noto Sans KR', sans-serif; background: #0f0f0f; color: #e5e7eb; }
    .brand { color: #3ECF8E; }
    .panel { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 8px; }
    .input-base {
      background: #111; border: 1px solid #333; border-radius: 6px;
      color: #e5e7eb; padding: 10px 14px; width: 100%; outline: none;
      transition: border-color 0.2s;
    }
    .input-base:focus { border-color: #3ECF8E; }
    textarea.input-base { resize: vertical; }
    .btn-primary {
      background: #3ECF8E; color: #0f0f0f; font-weight: 700;
      padding: 11px 24px; border-radius: 6px; border: none; cursor: pointer;
      transition: opacity 0.2s; font-size: 14px; white-space: nowrap;
      display: inline-flex; align-items: center; gap: 8px;
    }
    .btn-primary:hover { opacity: 0.85; }
    .btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }
    .btn-secondary {
      background: #2a2a2a; color: #e5e7eb; font-weight: 500;
      padding: 8px 16px; border-radius: 6px; border: 1px solid #444; cursor: pointer;
      transition: border-color 0.2s; font-size: 13px; white-space: nowrap;
    }
    .btn-secondary:hover { border-color: #3ECF8E; color: #3ECF8E; }
    .btn-secondary:disabled { opacity: 0.4; cursor: not-allowed; }
    .btn-danger {
      background: #2a0a0a; color: #ef4444; font-weight: 500;
      padding: 6px 12px; border-radius: 6px; border: 1px solid #ef444433; cursor: pointer;
      transition: border-color 0.2s; font-size: 12px; white-space: nowrap;
    }
    .btn-danger:hover { border-color: #ef4444; }
    .btn-publish {
      background: #0d2318; color: #3ECF8E; font-weight: 500;
      padding: 6px 12px; border-radius: 6px; border: 1px solid #3ECF8E33; cursor: pointer;
      transition: border-color 0.2s; font-size: 12px; white-space: nowrap;
    }
    .btn-publish:hover { border-color: #3ECF8E; }
    /* Mode tabs */
    .mode-tab {
      padding: 10px 22px; border-radius: 8px 8px 0 0; font-size: 14px; font-weight: 600;
      cursor: pointer; border: 1px solid #2a2a2a; border-bottom: none;
      background: #111; color: #555; transition: all 0.2s;
    }
    .mode-tab.active { background: #1a1a1a; color: #3ECF8E; border-color: #3ECF8E; }
    /* Preview tabs */
    .tab-btn {
      padding: 7px 18px; border-radius: 6px 6px 0 0; font-size: 13px;
      cursor: pointer; border: 1px solid #2a2a2a; border-bottom: none;
      background: #111; color: #888; transition: all 0.2s;
    }
    .tab-btn.active { background: #1a1a1a; color: #3ECF8E; border-color: #3ECF8E; }
    .preview-content {
      background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 0 8px 8px 8px;
      padding: 24px; min-height: 200px;
    }
    .preview-content-plain {
      background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 8px;
      padding: 20px; min-height: 200px;
    }
    .spinner {
      display: inline-block; width: 16px; height: 16px;
      border: 2px solid rgba(0,0,0,0.3); border-top-color: transparent;
      border-radius: 50%; animation: spin 0.8s linear infinite; flex-shrink: 0;
    }
    .spinner-brand {
      display: inline-block; width: 16px; height: 16px;
      border: 2px solid #3ECF8E33; border-top-color: #3ECF8E;
      border-radius: 50%; animation: spin 0.8s linear infinite; flex-shrink: 0;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .collapsible-header {
      cursor: pointer; user-select: none; display: flex;
      align-items: center; justify-content: space-between;
    }
    .collapsible-header:hover .collapse-label { color: #3ECF8E; }
    .filename-badge {
      background: #0d2318; border: 1px solid #3ECF8E33;
      border-radius: 6px; padding: 10px 16px;
      color: #3ECF8E; font-family: 'JetBrains Mono', monospace; font-size: 13px;
    }
    .status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
    .status-dot.ok { background: #3ECF8E; }
    .status-dot.err { background: #ef4444; }
    .status-dot.checking { background: #f59e0b; animation: pulse 1s infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
    .prose-custom { color: #d1d5db; }
    .prose-custom h1, .prose-custom h2, .prose-custom h3 { color: #f9fafb; }
    .prose-custom code { color: #3ECF8E; background: #0d2318; padding: 2px 6px; border-radius: 4px; }
    .prose-custom pre { background: #111; border: 1px solid #2a2a2a; }
    .prose-custom blockquote { border-left-color: #3ECF8E; color: #9ca3af; }
    .prose-custom a { color: #3ECF8E; }
    .prose-custom table { color: #d1d5db; }
    .prose-custom th { background: #1f1f1f; color: #f9fafb; }
    .prose-custom td, .prose-custom th { border-color: #2a2a2a; }
    .toast {
      position: fixed; bottom: 24px; right: 24px; padding: 12px 20px;
      border-radius: 8px; font-size: 14px; z-index: 9999;
      animation: toastIn 0.3s ease; max-width: 360px;
    }
    .toast-success { background: #0d2318; border: 1px solid #3ECF8E; color: #3ECF8E; }
    .toast-error { background: #2a0a0a; border: 1px solid #ef4444; color: #ef4444; }
    @keyframes toastIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    .divider { border: none; border-top: 1px solid #2a2a2a; margin: 20px 0; }
    .seo-item { display: flex; align-items: flex-start; gap: 8px; font-size: 12px; margin-bottom: 6px; }
    .manage-table { width: 100%; border-collapse: collapse; }
    .manage-table th { text-align: left; padding: 8px 12px; font-size: 11px; color: #6b7280; font-weight: 500; border-bottom: 1px solid #2a2a2a; }
    .manage-table td { padding: 8px 12px; font-size: 13px; border-bottom: 1px solid #1f1f1f; vertical-align: middle; }
    .manage-table tr:hover td { background: #1f1f1f; }
    .split-editor-wrap { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .edit-split-wrap { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .draft-badge {
      display: inline-block; font-size: 10px; padding: 2px 6px;
      background: #1a1200; border: 1px solid #f59e0b44; color: #f59e0b;
      border-radius: 4px; margin-left: 4px;
    }
  </style>
</head>
<body class="min-h-screen">
<div class="max-w-5xl mx-auto px-4 py-10">

  <!-- Header -->
  <div class="mb-8 text-center">
    <div class="text-2xl font-bold mb-1">Black<span class="brand">Rabbit</span> LAB</div>
    <div class="text-gray-500 text-sm">투자·경제 블로그 AI Post Maker v2 — Ollama 로컬 실행</div>
  </div>

  <!-- Ollama Status -->
  <div class="panel p-5 mb-6">
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center gap-2">
        <span id="statusDot" class="status-dot checking"></span>
        <span class="text-sm font-medium text-gray-300">Ollama 연결 상태</span>
        <span id="statusText" class="text-xs text-gray-500">확인 중...</span>
      </div>
      <button onclick="checkOllama()" class="btn-secondary text-xs py-1 px-3">새로고침</button>
    </div>
    <div class="flex items-center gap-3">
      <div class="flex-1">
        <label class="block text-xs text-gray-500 mb-1">모델 선택</label>
        <select id="modelSelect" class="input-base text-sm">
          <option value="">-- 모델 로딩 중 --</option>
        </select>
      </div>
      <div class="text-xs text-gray-600 pt-5">
        모델 없으면:<br>
        <span class="font-mono text-gray-500">ollama pull qwen2.5:7b</span>
      </div>
    </div>
    <div id="ollamaHelp" class="hidden mt-3 p-3 rounded" style="background:#2a0a0a;border:1px solid #ef444433;">
      <p class="text-red-400 text-xs font-medium mb-1">Ollama가 실행되지 않고 있습니다.</p>
      <ol class="text-gray-400 text-xs space-y-1 list-decimal list-inside">
        <li><a href="https://ollama.com" target="_blank" class="brand underline">ollama.com</a>에서 Ollama 설치</li>
        <li>터미널에서 <code class="brand">ollama pull qwen2.5:7b</code> 실행</li>
        <li>위 새로고침 버튼 클릭</li>
      </ol>
    </div>
  </div>

  <!-- Mode Tabs -->
  <div class="flex gap-1 mb-0 flex-wrap">
    <button class="mode-tab active" id="modeTabCreate" onclick="switchMode('create')">새 포스트 생성</button>
    <button class="mode-tab" id="modeTabEdit" onclick="switchMode('edit')">포스트 수정</button>
    <button class="mode-tab" id="modeTabManage" onclick="switchMode('manage')">포스트 관리</button>
    <button class="mode-tab" id="modeTabScheduler" onclick="switchMode('scheduler')">⏱ 자동 스케줄러</button>
  </div>

  <!-- ══════════════════ 생성 모드 ══════════════════ -->
  <div id="createPanel" class="panel p-6 mb-6" style="border-radius:0 8px 8px 8px;">
    <div class="grid grid-cols-1 gap-5 md:grid-cols-2">
      <div class="md:col-span-2">
        <label class="block text-sm text-gray-400 mb-2">주제 <span class="text-red-400">*</span></label>
        <input type="text" id="topic" class="input-base" placeholder="예: 이번 주 코스피 변동성 급등 원인과 개인 투자자 대응 전략">
      </div>
      <div>
        <label class="block text-sm text-gray-400 mb-2">카테고리 <span class="text-red-400">*</span></label>
        <select id="category" class="input-base">
          <option value="시장분석">시장분석</option>
          <option value="투자 기초">투자 기초</option>
          <option value="경제 공부">경제 공부</option>
          <option value="ETF·펀드">ETF·펀드</option>
          <option value="재테크">재테크</option>
          <option value="뉴스 해설">뉴스 해설</option>
          <option value="기업 분석">기업 분석</option>
          <option value="기타">기타</option>
        </select>
      </div>
      <div>
        <label class="block text-sm text-gray-400 mb-2">날짜</label>
        <input type="date" id="postDate" class="input-base">
      </div>
    </div>

    <div class="mt-5">
      <div class="collapsible-header mb-2" onclick="toggleCollapse('stockerPanel','stockerArrow')">
        <label class="text-sm text-gray-400 collapse-label cursor-pointer">참고 데이터 (선택)</label>
        <span id="stockerArrow" class="text-gray-500 text-xs font-mono">▼</span>
      </div>
      <div id="stockerPanel">
        <textarea id="stockerData" class="input-base font-mono text-sm" rows="5"
          placeholder="포스트에 활용할 수치·데이터·종목 정보 등을 붙여넣으세요.&#10;예: 코스피 2,650 (+1.2%), 미국 CPI 3.1%, 달러/원 1,340원, S&amp;P500 PER 21배, ..."></textarea>
      </div>
    </div>

    <div class="mt-4">
      <div class="collapsible-header mb-2" onclick="toggleCollapse('contextPanel','contextArrow')">
        <label class="text-sm text-gray-400 collapse-label cursor-pointer">추가 컨텍스트 (선택)</label>
        <span id="contextArrow" class="text-gray-500 text-xs font-mono">▼</span>
      </div>
      <div id="contextPanel">
        <textarea id="extraContext" class="input-base text-sm" rows="4"
          placeholder="참고할 뉴스, 특이사항, 강조할 내용 등"></textarea>
      </div>
    </div>

    <div class="mt-6 flex justify-end items-center gap-4">
      <label class="flex items-center gap-2 text-sm text-gray-400 cursor-pointer select-none">
        <input type="checkbox" id="asDraft" class="rounded" style="accent-color:#3ECF8E;">
        초안으로 저장
      </label>
      <button id="generateBtn" onclick="generatePost()" class="btn-primary">
        <span id="generateBtnText">AI 포스트 생성</span>
        <span id="generateSpinner" class="spinner hidden"></span>
      </button>
    </div>
  </div>

  <!-- ══════════════════ 수정 모드 ══════════════════ -->
  <div id="editPanel" class="panel p-6 mb-6 hidden" style="border-radius:0 8px 8px 8px;">

    <!-- 파일 선택 -->
    <div class="mb-5">
      <div class="flex items-center gap-2 mb-2">
        <label class="text-sm text-gray-400 font-medium">_posts/ 파일 선택</label>
        <button onclick="loadPostsList()" class="btn-secondary text-xs py-1 px-2">↺ 목록 갱신</button>
      </div>
      <div class="flex gap-2">
        <select id="postFileSelect" class="input-base text-sm font-mono flex-1">
          <option value="">-- 파일을 선택하세요 --</option>
        </select>
        <button onclick="loadSelectedFile()" class="btn-secondary">불러오기</button>
      </div>
      <p class="text-xs text-gray-600 mt-2">또는 로컬 파일을 직접 업로드:
        <label class="brand cursor-pointer underline ml-1">
          파일 선택
          <input type="file" id="fileUpload" accept=".md" class="hidden" onchange="handleFileUpload(event)">
        </label>
      </p>
    </div>

    <hr class="divider">

    <!-- 편집 영역 -->
    <div class="mb-4">
      <div class="flex items-center justify-between mb-2">
        <div class="flex items-center gap-2">
          <label class="text-sm text-gray-400 font-medium">포스트 내용</label>
          <span class="text-gray-600 text-xs">(직접 수정 가능)</span>
          <span id="editFilenameChip" class="hidden text-xs font-mono brand px-2 py-1 rounded" style="background:#0d2318;"></span>
        </div>
        <button id="splitToggleBtn" onclick="toggleEditSplit()" class="btn-secondary text-xs py-1 px-2">⊞ 스플릿 뷰</button>
      </div>
      <div id="editContentArea">
        <textarea id="editContent" class="input-base font-mono text-sm" rows="18"
          oninput="updateEditLivePreview()"
          placeholder="왼쪽에서 파일을 불러오거나 직접 마크다운을 붙여넣으세요."></textarea>
        <div id="editLivePreview" class="hidden preview-content-plain prose prose-invert prose-custom max-w-none"
          style="overflow-y:auto;max-height:450px;"></div>
      </div>
    </div>

    <hr class="divider">

    <!-- AI 수정 지시 -->
    <div class="mb-5">
      <label class="text-sm text-gray-400 font-medium mb-2 block">AI 수정 지시 <span class="text-gray-600 text-xs font-normal">(비워두면 직접 편집 저장만 가능)</span></label>
      <textarea id="editInstruction" class="input-base text-sm" rows="3"
        placeholder="예: 도입부를 더 임팩트 있게 바꿔줘&#10;예: RSI 분석 섹션을 추가해줘&#10;예: 전체적으로 문장을 더 간결하게 다듬어줘"></textarea>
    </div>

    <!-- 버튼 -->
    <div class="flex flex-wrap gap-3 justify-between items-center">
      <div class="flex gap-2 flex-wrap">
        <button id="aiEditBtn" onclick="aiEditPost()" class="btn-primary">
          <span id="aiEditBtnText">AI 수정 적용</span>
          <span id="aiEditSpinner" class="spinner hidden"></span>
        </button>
        <button id="proofreadBtn" onclick="proofreadPost()" class="btn-secondary" style="color:#f59e0b;border-color:#f59e0b55;">
          <span id="proofreadBtnText">🔍 교정 (Claude)</span>
          <span id="proofreadSpinner" class="spinner-brand hidden" style="border-color:#f59e0b33;border-top-color:#f59e0b;"></span>
        </button>
        <button onclick="applyManualEdit()" class="btn-secondary">직접 편집 확정</button>
      </div>
      <div class="flex gap-2 flex-wrap">
        <button id="saveBackBtn" onclick="saveBackToPost()" class="btn-secondary hidden" style="color:#3ECF8E;border-color:#3ECF8E33;">
          💾 저장
        </button>
        <button id="saveAsEditBtn" onclick="toggleSaveAs('edit')" class="btn-secondary hidden">✏️ 다른 이름으로 저장</button>
        <button onclick="downloadMd()" class="btn-secondary" style="color:#3ECF8E;border-color:#3ECF8E33;">⬇ .md 다운로드</button>
      </div>
    </div>

    <!-- 다른 이름으로 저장 (수정 모드) -->
    <div id="saveAsEditRow" class="hidden mt-3 p-3 rounded" style="background:#111;border:1px solid #2a2a2a;">
      <div class="flex gap-2 items-center flex-wrap">
        <span class="text-xs text-gray-400 whitespace-nowrap font-mono">_posts/</span>
        <input type="text" id="saveAsEditInput" class="input-base text-sm font-mono flex-1" style="min-width:220px;" placeholder="YYYY-MM-DD-slug.md">
        <button onclick="confirmSaveAsEdit()" class="btn-primary py-2 px-4 text-sm">저장</button>
        <button onclick="toggleSaveAs('edit')" class="btn-secondary py-2 px-3 text-sm">취소</button>
      </div>
      <p class="text-xs text-gray-600 mt-2">파일명은 영문·숫자·하이픈만 사용하세요. 예: 2026-03-07-stocker-report.md</p>
    </div>
  </div>

  <!-- ══════════════════ 결과 패널 ══════════════════ -->
  <div id="outputPanel" class="panel p-6 hidden mb-6">
    <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
      <h2 class="text-sm font-semibold text-gray-400 uppercase tracking-wider" id="outputPanelTitle">결과</h2>
      <div class="flex gap-2 flex-wrap">
        <button onclick="copyMarkdown()" class="btn-secondary">복사</button>
        <button onclick="downloadMd()" class="btn-secondary">⬇ 다운로드</button>
        <button id="proofreadOutputBtn" onclick="proofreadOutput()" class="btn-secondary" style="color:#f59e0b;border-color:#f59e0b55;">
          <span id="proofreadOutputBtnText">🔍 교정 (Claude)</span>
          <span id="proofreadOutputSpinner" class="spinner-brand hidden" style="border-color:#f59e0b33;border-top-color:#f59e0b;"></span>
        </button>
        <button id="saveDirectBtn" onclick="saveToPostsDirect()" class="btn-secondary" style="color:#3ECF8E;border-color:#3ECF8E33;">💾 _posts/ 저장</button>
        <button onclick="toggleSaveAs('output')" class="btn-secondary">✏️ 다른 이름으로 저장</button>
      </div>
    </div>

    <!-- AI 제안 파일명 -->
    <div id="filenameBox" class="filename-badge mb-3 hidden">
      <span class="text-gray-500 text-xs mr-2">AI 제안 파일명:</span>
      <span id="filenameText"></span>
    </div>

    <!-- 다른 이름으로 저장 (결과 패널) -->
    <div id="saveAsRow" class="hidden mb-4 p-3 rounded" style="background:#111;border:1px solid #2a2a2a;">
      <div class="flex gap-2 items-center flex-wrap">
        <span class="text-xs text-gray-400 whitespace-nowrap font-mono">_posts/</span>
        <input type="text" id="saveAsInput" class="input-base text-sm font-mono flex-1" style="min-width:220px;" placeholder="YYYY-MM-DD-slug.md">
        <button onclick="confirmSaveAs()" class="btn-primary py-2 px-4 text-sm">저장</button>
        <button onclick="toggleSaveAs('output')" class="btn-secondary py-2 px-3 text-sm">취소</button>
      </div>
      <p class="text-xs text-gray-600 mt-2">파일명은 영문·숫자·하이픈만 사용하세요. 예: 2026-03-07-stocker-report.md</p>
    </div>

    <!-- 뷰 모드 스위처 -->
    <div class="flex gap-1 mb-1">
      <button class="tab-btn active" id="btnTabsView" onclick="setOutputView('tabs')">탭 뷰</button>
      <button class="tab-btn" id="btnSplitView" onclick="setOutputView('split')">⊞ 스플릿 에디터</button>
    </div>

    <!-- 탭 뷰 -->
    <div id="tabsView">
      <div class="flex gap-1">
        <button class="tab-btn active" id="tabPreview" onclick="switchPreviewTab('preview')">렌더링 미리보기</button>
        <button class="tab-btn" id="tabRaw" onclick="switchPreviewTab('raw')">원본 마크다운</button>
      </div>
      <div id="previewPane" class="preview-content">
        <div id="previewContent" class="prose prose-invert prose-custom max-w-none"></div>
      </div>
      <div id="rawPane" class="preview-content hidden">
        <pre id="rawContent" class="font-mono text-sm text-gray-300 whitespace-pre-wrap break-words"></pre>
      </div>
    </div>

    <!-- 스플릿 에디터 뷰 -->
    <div id="splitView" class="hidden">
      <div class="split-editor-wrap">
        <div>
          <div class="text-xs text-gray-500 mb-1 font-medium">편집</div>
          <textarea id="splitEditor" class="input-base font-mono text-sm" rows="20"
            style="height:480px;resize:none;"
            oninput="onSplitEditorInput(this.value)"></textarea>
        </div>
        <div>
          <div class="text-xs text-gray-500 mb-1 font-medium">미리보기</div>
          <div id="splitPreview" class="preview-content-plain prose prose-invert prose-custom max-w-none"
            style="height:480px;overflow-y:auto;"></div>
        </div>
      </div>
    </div>

    <!-- SEO 분석 패널 -->
    <div id="seoPanel" class="hidden mt-5 p-4 rounded" style="background:#0a1a0a;border:1px solid #3ECF8E22;">
      <!-- renderSEO()가 채움 -->
    </div>

    <!-- Git 배포 -->
    <hr class="divider mt-5">
    <div>
      <div class="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wider">Git 배포</div>
      <div class="flex gap-2 items-center">
        <input type="text" id="gitCommitMsg" class="input-base text-sm flex-1"
          placeholder="커밋 메시지 (예: 포스트 발행: 2026-03-07-stocker-report.md)">
        <button id="gitDeployBtn" onclick="gitDeploy()" class="btn-primary" style="white-space:nowrap;">
          🚀 Git 배포
        </button>
      </div>
      <div id="gitDeployResult" class="text-xs mt-2 font-mono whitespace-pre-wrap"></div>
    </div>
  </div>

  <!-- ══════════════════ 포스트 관리 ══════════════════ -->
  <div id="managePanel" class="panel p-6 hidden mb-6" style="border-radius:0 8px 8px 8px;">

    <!-- 필터 영역 -->
    <div class="flex flex-wrap items-center gap-2 mb-5">
      <button class="tab-btn active" id="statusTabPublished" onclick="setManageStatus('published')">발행됨</button>
      <button class="tab-btn" id="statusTabDraft" onclick="setManageStatus('draft')">초안</button>
      <div class="flex-1"></div>
      <select id="manageCatFilter" class="input-base text-sm" style="width:auto;min-width:140px;" onchange="applyManageFilter()">
        <option value="">전체 카테고리</option>
        <option>시장분석</option>
        <option>투자 기초</option>
        <option>경제 공부</option>
        <option>ETF·펀드</option>
        <option>재테크</option>
        <option>뉴스 해설</option>
        <option>기업 분석</option>
        <option>기타</option>
      </select>
      <input type="text" id="manageSearch" class="input-base text-sm" style="width:180px;" placeholder="검색..." oninput="applyManageFilter()">
      <button onclick="loadManageList()" class="btn-secondary text-xs py-2 px-3">↺ 갱신</button>
      <button id="proofreadAllBtn" onclick="proofreadAll()" class="btn-secondary text-xs py-2 px-3" style="color:#f59e0b;border-color:#f59e0b55;">
        <span id="proofreadAllBtnText">🔍 전체 교정</span>
        <span id="proofreadAllSpinner" class="spinner-brand hidden" style="border-color:#f59e0b33;border-top-color:#f59e0b;width:12px;height:12px;"></span>
      </button>
    </div>

    <!-- 포스트 테이블 -->
    <div class="overflow-x-auto">
      <table class="manage-table">
        <thead>
          <tr>
            <th>날짜</th>
            <th>제목</th>
            <th>카테고리</th>
            <th>액션</th>
          </tr>
        </thead>
        <tbody id="manageTableBody">
          <tr><td colspan="4" class="text-center text-gray-600 py-8 text-sm">로딩 중...</td></tr>
        </tbody>
      </table>
    </div>

    <!-- 히스토리 섹션 -->
    <hr class="divider mt-6">
    <div>
      <div class="collapsible-header mb-3" onclick="toggleCollapse('historySection','historyArrow')">
        <div class="text-sm font-semibold text-gray-400 collapse-label">히스토리 (자동 백업)</div>
        <span id="historyArrow" class="text-gray-500 text-xs font-mono">▼</span>
      </div>
      <div id="historySection">
        <div id="historyList" class="space-y-1">
          <p class="text-xs text-gray-600 py-2">히스토리를 불러오는 중...</p>
        </div>
      </div>
    </div>
  </div>

  <!-- ══════════════════ 스케줄러 ══════════════════ -->
  <div id="schedulerPanel" class="panel p-6 hidden mb-6" style="border-radius:0 8px 8px 8px;">

    <!-- 서브 탭 -->
    <div class="flex gap-1 mb-5">
      <button class="tab-btn active" id="schTabList"    onclick="switchSchTab('list',this)">스케줄 목록</button>
      <button class="tab-btn"        id="schTabAdd"     onclick="switchSchTab('add',this)">+ 스케줄 추가</button>
      <button class="tab-btn"        id="schTabLog"     onclick="switchSchTab('log',this)">실행 로그</button>
    </div>

    <!-- 스케줄 목록 -->
    <div id="schPanelList">
      <div class="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div id="schRunnerStatus" class="text-xs font-mono text-gray-500">로딩 중...</div>
        <div class="flex gap-2 flex-wrap">
          <button onclick="runNowOpen()" class="btn-secondary text-xs">▶ 즉시 실행</button>
          <button onclick="showTaskSetup()" class="btn-secondary text-xs">🖥 작업 스케줄러 설정</button>
          <button onclick="loadSchList()" class="btn-secondary text-xs">↺ 새로고침</button>
        </div>
      </div>
      <div id="taskSetupInfo" class="text-xs font-mono mb-3 p-3 rounded-lg bg-gray-900 border border-gray-700" style="display:none;">
        <p class="text-green-400 font-semibold mb-2">🖥 Windows 작업 스케줄러 자동 등록</p>
        <p class="text-gray-400 mb-1">아래 배치 파일을 <strong class="text-white">관리자 권한</strong>으로 실행하면 매 시간 자동 포스팅이 등록됩니다.</p>
        <p class="text-yellow-400 font-mono mt-2 select-all">_tools/setup_windows_task.bat</p>
        <p class="text-gray-500 mt-2">• 실행 로그: <span class="text-gray-300">_tools/scheduler.log</span></p>
        <p class="text-gray-500">• 스케줄 설정은 이 화면에서 관리 (자동으로 저장됨)</p>
        <p class="text-gray-500">• Ollama가 PC에서 실행 중이어야 합니다</p>
        <button onclick="document.getElementById('taskSetupInfo').style.display='none'" class="mt-2 text-gray-600 hover:text-gray-400">닫기 ✕</button>
      </div>
      <div id="schList"><p class="text-xs text-gray-600 text-center py-8">로딩 중...</p></div>
    </div>

    <!-- 스케줄 추가 -->
    <div id="schPanelAdd" class="hidden">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
        <div>
          <label class="block text-xs text-gray-500 mb-1">카테고리</label>
          <select id="schAddCat" class="input-base text-sm">
            <option>시장분석</option><option>투자 기초</option><option>경제 공부</option>
            <option>ETF·펀드</option><option>재테크</option><option>뉴스 해설</option><option>기업 분석</option><option>기타</option>
          </select>
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">주기</label>
          <select id="schAddFreq" class="input-base text-sm" onchange="schUpdateFreqUI()">
            <option value="daily">매일</option>
            <option value="weekly" selected>매주</option>
            <option value="monthly">매월</option>
          </select>
        </div>
        <div id="schOptWeekly">
          <label class="block text-xs text-gray-500 mb-1">요일</label>
          <select id="schAddDow" class="input-base text-sm">
            <option value="0">월요일</option><option value="1">화요일</option>
            <option value="2" selected>수요일</option><option value="3">목요일</option>
            <option value="4">금요일</option><option value="5">토요일</option><option value="6">일요일</option>
          </select>
        </div>
        <div id="schOptMonthly" class="hidden">
          <label class="block text-xs text-gray-500 mb-1">매월 몇 일 (1~28)</label>
          <input type="number" id="schAddDom" min="1" max="28" value="1" class="input-base text-sm">
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">실행 시각</label>
          <div class="flex gap-2 items-center">
            <input type="number" id="schAddHour" min="0" max="23" value="9" class="input-base text-sm" style="width:70px;">
            <span class="text-gray-500 text-sm">시</span>
            <input type="number" id="schAddMinute" min="0" max="59" value="0" class="input-base text-sm" style="width:70px;">
            <span class="text-gray-500 text-sm">분</span>
          </div>
        </div>
        <div class="flex items-end">
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" id="schAddEnabled" checked style="accent-color:#3ECF8E;width:16px;height:16px;">
            <span class="text-sm text-gray-400">즉시 활성화</span>
          </label>
        </div>
      </div>
      <button onclick="schAddSubmit()" class="btn-primary">
        <span id="schAddSpinner" class="spinner hidden"></span>
        <span id="schAddBtnText">스케줄 등록</span>
      </button>
      <div id="schAddResult" class="text-xs mt-2 font-mono text-gray-500"></div>
    </div>

    <!-- 실행 로그 -->
    <div id="schPanelLog" class="hidden">
      <div class="flex justify-between items-center mb-3">
        <span class="text-xs text-gray-500">자동 포스팅 실행 기록</span>
        <button onclick="loadSchLog()" class="btn-secondary text-xs">↺ 새로고침</button>
      </div>
      <div id="schLog"><p class="text-xs text-gray-600 text-center py-8">로딩 중...</p></div>
    </div>


    <!-- 즉시 실행 인라인 폼 -->
    <div id="runNowInline" class="hidden mt-4 p-4 rounded" style="background:#111;border:1px solid #2a2a2a;">
      <div class="flex gap-3 items-end flex-wrap">
        <div>
          <label class="block text-xs text-gray-500 mb-1">카테고리</label>
          <select id="runNowCat" class="input-base text-sm">
            <option>시장분석</option><option>투자 기초</option><option>경제 공부</option>
            <option>ETF·펀드</option><option>재테크</option><option>뉴스 해설</option><option>기업 분석</option><option>기타</option>
          </select>
        </div>
        <button onclick="runNowExec()" class="btn-primary">
          <span id="runNowSpinner" class="spinner hidden"></span>
          <span id="runNowBtnText">실행</span>
        </button>
        <button onclick="runNowClose()" class="btn-secondary">취소</button>
      </div>
      <div id="runNowResult" class="text-xs mt-2 font-mono text-gray-500 whitespace-pre-wrap"></div>
    </div>

  </div>

  <div class="text-center text-gray-700 text-xs mt-8">
    BlackRabbit LAB AI Post Maker v2 · Powered by Ollama (완전 무료)
  </div>
</div>

<script>
  // ── State ──
  let generatedMarkdown = '';
  let suggestedFilename = '';
  let currentEditFilename = '';
  let currentEditIsDraft = false;
  let currentMode = 'create';
  let editSplitOn = false;
  let outputViewMode = 'tabs';
  let manageAllPosts = [];
  let manageStatusFilter = 'published';

  // ── Init ──
  window.onload = function() {
    document.getElementById('postDate').value = new Date().toISOString().split('T')[0];
    checkOllama();
    document.getElementById('modelSelect').addEventListener('change', function() {
      if (this.value) saveModelToConfig(this.value);
    });
  };

  function saveModelToConfig(model) {
    if (!model) return;
    fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ default_model: model })
    }).catch(function() {});
  }

  // ── Ollama 상태 ──
  async function checkOllama() {
    const dot = document.getElementById('statusDot');
    const text = document.getElementById('statusText');
    const help = document.getElementById('ollamaHelp');
    const select = document.getElementById('modelSelect');
    dot.className = 'status-dot checking';
    text.textContent = '확인 중...';
    try {
      const res = await fetch('/ollama-models');
      const data = await res.json();
      if (data.error) {
        dot.className = 'status-dot err';
        text.textContent = '연결 실패 — Ollama가 실행 중인지 확인하세요';
        help.classList.remove('hidden');
        select.innerHTML = '<option value="">모델을 불러올 수 없음</option>';
        return;
      }
      const models = data.models || [];
      help.classList.add('hidden');
      if (models.length === 0) {
        dot.className = 'status-dot err';
        text.textContent = '연결됨 — 설치된 모델 없음';
        select.innerHTML = '<option value="">모델 없음 (ollama pull qwen2.5:7b)</option>';
      } else {
        dot.className = 'status-dot ok';
        text.textContent = `연결됨 — 모델 ${models.length}개`;
        select.innerHTML = models.map(m => `<option value="${m}">${m}</option>`).join('');
        // 설정 파일의 default_model 우선, 없으면 qwen 계열 자동 선택
        const configDefault = data.default_model || '';
        const configMatch = configDefault && models.find(m => m === configDefault);
        if (configMatch) {
          select.value = configMatch;
        } else {
          const preferred = models.find(m => m.startsWith('qwen2.5') || m.startsWith('qwen'));
          if (preferred) select.value = preferred;
        }
        saveModelToConfig(select.value);
      }
    } catch(e) {
      dot.className = 'status-dot err';
      text.textContent = '연결 실패';
      help.classList.remove('hidden');
      select.innerHTML = '<option value="">모델을 불러올 수 없음</option>';
    }
  }

  // ── 모드 전환 ──
  function switchMode(mode) {
    currentMode = mode;
    ['create', 'edit', 'manage', 'scheduler'].forEach(function(m) {
      document.getElementById(m + 'Panel').classList.toggle('hidden', m !== mode);
      const tabId = 'modeTab' + m.charAt(0).toUpperCase() + m.slice(1);
      document.getElementById(tabId).classList.toggle('active', m === mode);
    });
    document.getElementById('outputPanel').classList.add('hidden');
    if (mode === 'edit') loadPostsList();
    if (mode === 'manage') loadManageList();
    if (mode === 'scheduler') loadSchList();
  }

  // ── 접기/펼치기 ──
  function toggleCollapse(panelId, arrowId) {
    const panel = document.getElementById(panelId);
    const arrow = document.getElementById(arrowId);
    const hidden = panel.style.display === 'none';
    panel.style.display = hidden ? '' : 'none';
    arrow.textContent = hidden ? '▼' : '▶';
  }

  // ── 미리보기 탭 ──
  function switchPreviewTab(tab) {
    const isPreview = tab === 'preview';
    document.getElementById('previewPane').classList.toggle('hidden', !isPreview);
    document.getElementById('rawPane').classList.toggle('hidden', isPreview);
    document.getElementById('tabPreview').classList.toggle('active', isPreview);
    document.getElementById('tabRaw').classList.toggle('active', !isPreview);
  }

  // ── 결과 뷰 모드 ──
  function setOutputView(mode) {
    outputViewMode = mode;
    document.getElementById('tabsView').classList.toggle('hidden', mode !== 'tabs');
    document.getElementById('splitView').classList.toggle('hidden', mode !== 'split');
    document.getElementById('btnTabsView').classList.toggle('active', mode === 'tabs');
    document.getElementById('btnSplitView').classList.toggle('active', mode === 'split');
    if (mode === 'split' && generatedMarkdown) {
      document.getElementById('splitEditor').value = generatedMarkdown;
      document.getElementById('splitPreview').innerHTML = marked.parse(generatedMarkdown);
    }
  }

  function onSplitEditorInput(val) {
    generatedMarkdown = val;
    document.getElementById('splitPreview').innerHTML = marked.parse(val);
    // 탭 뷰도 동기화
    document.getElementById('rawContent').textContent = val;
    document.getElementById('previewContent').innerHTML = marked.parse(val);
  }

  // ── 수정 모드 스플릿 뷰 ──
  function toggleEditSplit() {
    editSplitOn = !editSplitOn;
    const area = document.getElementById('editContentArea');
    const preview = document.getElementById('editLivePreview');
    const btn = document.getElementById('splitToggleBtn');
    if (editSplitOn) {
      area.className = 'edit-split-wrap';
      preview.classList.remove('hidden');
      updateEditLivePreview();
      btn.textContent = '⊠ 단일 뷰';
    } else {
      area.className = '';
      preview.classList.add('hidden');
      btn.textContent = '⊞ 스플릿 뷰';
    }
  }

  function updateEditLivePreview() {
    if (!editSplitOn) return;
    const content = document.getElementById('editContent').value;
    document.getElementById('editLivePreview').innerHTML = marked.parse(content);
  }

  // ── 결과 렌더링 ──
  function renderOutput(title) {
    document.getElementById('outputPanel').classList.remove('hidden');
    document.getElementById('outputPanelTitle').textContent = title || '결과';
    const fname = suggestedFilename || currentEditFilename || '';
    if (fname) {
      document.getElementById('filenameText').textContent = fname;
      document.getElementById('filenameBox').classList.remove('hidden');
    } else {
      document.getElementById('filenameBox').classList.add('hidden');
    }
    document.getElementById('saveDirectBtn').disabled = !fname;
    document.getElementById('saveAsInput').value = fname;
    document.getElementById('saveAsRow').classList.add('hidden');
    document.getElementById('previewContent').innerHTML = marked.parse(generatedMarkdown);
    document.getElementById('rawContent').textContent = generatedMarkdown;
    // 뷰 리셋
    setOutputView('tabs');
    switchPreviewTab('preview');
    // 커밋 메시지 기본값
    if (fname) {
      const existing = document.getElementById('gitCommitMsg').value;
      if (!existing || existing.startsWith('포스트 발행:') || existing.startsWith('포스트 수정:')) {
        const prefix = (title || '').includes('수정') ? '포스트 수정' : '포스트 발행';
        document.getElementById('gitCommitMsg').value = prefix + ': ' + fname;
      }
    }
    document.getElementById('outputPanel').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // ═══════════════════════════════
  // 생성 모드
  // ═══════════════════════════════
  function buildSeoFeedback(checks) {
    const lines = [];
    checks.forEach(function(c) {
      if (c.ok !== true) lines.push('- ' + c.msg + ' → 반드시 수정하세요.');
    });
    return lines.join('\n');
  }

  async function generateWithSeoRetry(params) {
    const MAX_SEO_RETRIES = 3;
    let seoFeedback = '';
    let finalScore = 0;
    let lastSeo = null;

    for (let attempt = 1; attempt <= MAX_SEO_RETRIES; attempt++) {
      const btnText = attempt > 1 ? ('SEO 개선 재생성 (' + attempt + '/' + MAX_SEO_RETRIES + ')') : null;
      setLoading('generate', true, btnText);

      const res = await fetch('/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(Object.assign({}, params, { seoFeedback }))
      });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || '생성 실패.');

      generatedMarkdown = data.markdown;
      suggestedFilename = data.filename || '';
      lastSeo = data.seo;
      finalScore = lastSeo ? lastSeo.score : 0;

      if (finalScore >= 100) break;

      if (lastSeo) {
        seoFeedback = buildSeoFeedback(lastSeo.checks);
      }
      if (attempt < MAX_SEO_RETRIES) {
        showToast('SEO ' + finalScore + '점 → 자동 재생성 중 (' + attempt + '/' + MAX_SEO_RETRIES + ')', 'warn');
      }
    }

    renderOutput('생성 결과 (SEO ' + finalScore + '점)');
    if (lastSeo) renderSEO(lastSeo.checks, lastSeo.score);
    if (finalScore < 100) {
      showToast('최대 재시도 도달. SEO ' + finalScore + '점', 'warn');
    } else {
      showToast('포스트가 생성되었습니다!', 'success');
    }
    return finalScore;
  }

  async function generatePost() {
    const model = document.getElementById('modelSelect').value;
    const topic = document.getElementById('topic').value.trim();
    const category = document.getElementById('category').value;
    const postDate = document.getElementById('postDate').value;
    const stockerData = document.getElementById('stockerData').value.trim();
    const extraContext = document.getElementById('extraContext').value.trim();
    const asDraft = document.getElementById('asDraft').checked;
    if (!model || model.includes('없음') || model.includes('불러올')) { showToast('Ollama 모델을 먼저 설치하세요.', 'error'); return; }
    if (!topic) { showToast('주제를 입력하세요.', 'error'); return; }
    document.getElementById('seoPanel').classList.add('hidden');
    try {
      await generateWithSeoRetry({ model, topic, category, postDate, stockerData, extraContext });
      // 초안 자동 저장 (최종 성공 후)
      if (asDraft && suggestedFilename) {
        const ok = await doSaveDraft(suggestedFilename, generatedMarkdown);
        if (ok) showToast('초안 저장 완료: _drafts/' + suggestedFilename, 'success');
      }
    } catch(e) {
      showToast('서버 오류: ' + e.message, 'error');
    } finally {
      setLoading('generate', false);
    }
  }

  // ═══════════════════════════════
  // SEO 렌더링 (데이터는 백엔드에서 수신)
  // ═══════════════════════════════
  function renderSEO(checks, score) {
    const panel = document.getElementById('seoPanel');
    panel.classList.remove('hidden');
    const color = score >= 80 ? '#3ECF8E' : score >= 55 ? '#f59e0b' : '#ef4444';
    const icons = { 'true': '✓', 'false': '✗', 'warn': '⚠' };
    const colors = { 'true': '#6b7280', 'false': '#ef4444', 'warn': '#f59e0b' };
    const iconColors = { 'true': '#3ECF8E', 'false': '#ef4444', 'warn': '#f59e0b' };
    let html = '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">';
    html += '<div style="font-size:12px;font-weight:600;color:#9ca3af;text-transform:uppercase;letter-spacing:0.05em;">SEO 분석</div>';
    html += '<div style="font-size:24px;font-weight:700;color:' + color + ';">' + score + '점</div>';
    html += '</div><div>';
    checks.forEach(function(c) {
      const k = String(c.ok);
      html += '<div class="seo-item">';
      html += '<span style="color:' + iconColors[k] + ';font-weight:700;flex-shrink:0;width:14px;">' + icons[k] + '</span>';
      html += '<span style="color:' + colors[k] + ';">' + c.msg + '</span>';
      html += '</div>';
    });
    html += '</div>';
    panel.innerHTML = html;
  }

  // ═══════════════════════════════
  // Git 배포
  // ═══════════════════════════════
  async function gitDeploy() {
    const msg = document.getElementById('gitCommitMsg').value.trim();
    if (!msg) { showToast('커밋 메시지를 입력하세요.', 'error'); return; }
    const btn = document.getElementById('gitDeployBtn');
    const resultEl = document.getElementById('gitDeployResult');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-brand"></span> 배포 중...';
    resultEl.textContent = '';
    try {
      const res = await fetch('/git-deploy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg })
      });
      const data = await res.json();
      if (data.error) {
        resultEl.style.color = '#ef4444';
        resultEl.textContent = '오류: ' + data.error;
        showToast('Git 배포 실패', 'error');
      } else {
        resultEl.style.color = '#3ECF8E';
        resultEl.textContent = data.output || '배포 완료';
        showToast('Git 배포 완료!', 'success');
      }
    } catch(e) {
      resultEl.style.color = '#ef4444';
      resultEl.textContent = '서버 오류: ' + e.message;
    } finally {
      btn.disabled = false;
      btn.innerHTML = '🚀 Git 배포';
    }
  }

  // ═══════════════════════════════
  // 수정 모드
  // ═══════════════════════════════

  async function loadPostsList() {
    const select = document.getElementById('postFileSelect');
    select.innerHTML = '<option value="">-- 로딩 중... --</option>';
    try {
      const res = await fetch('/posts-list');
      const data = await res.json();
      if (data.error || !data.files) {
        select.innerHTML = '<option value="">파일 목록 없음</option>';
        return;
      }
      const files = data.files;
      if (files.length === 0) {
        select.innerHTML = '<option value="">_posts/ 폴더가 비어있습니다</option>';
      } else {
        select.innerHTML = '<option value="">-- 파일을 선택하세요 --</option>' +
          files.map(function(f) { return '<option value="' + f + '">' + f + '</option>'; }).join('');
      }
    } catch(e) {
      select.innerHTML = '<option value="">목록 로드 실패</option>';
    }
  }

  async function loadSelectedFile() {
    const filename = document.getElementById('postFileSelect').value;
    if (!filename) { showToast('파일을 선택하세요.', 'error'); return; }
    try {
      const res = await fetch('/post-content?file=' + encodeURIComponent(filename) + '&draft=0');
      const data = await res.json();
      if (data.error) { showToast(data.error, 'error'); return; }
      document.getElementById('editContent').value = data.content;
      currentEditFilename = filename;
      currentEditIsDraft = false;
      generatedMarkdown = '';
      suggestedFilename = '';
      document.getElementById('outputPanel').classList.add('hidden');
      showEditFilenameChip(filename);
      document.getElementById('saveBackBtn').classList.remove('hidden');
      document.getElementById('saveAsEditBtn').classList.remove('hidden');
      showToast(filename + ' 불러왔습니다.', 'success');
    } catch(e) {
      showToast('파일 로드 실패: ' + e.message, 'error');
    }
  }

  function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function(e) {
      document.getElementById('editContent').value = e.target.result;
      currentEditFilename = file.name;
      currentEditIsDraft = false;
      generatedMarkdown = '';
      suggestedFilename = '';
      document.getElementById('outputPanel').classList.add('hidden');
      showEditFilenameChip(file.name);
      document.getElementById('saveBackBtn').classList.add('hidden');
      document.getElementById('saveAsEditBtn').classList.remove('hidden');
      showToast(file.name + ' 업로드 완료.', 'success');
    };
    reader.readAsText(file);
  }

  function showEditFilenameChip(name) {
    const chip = document.getElementById('editFilenameChip');
    chip.textContent = name;
    chip.classList.remove('hidden');
  }

  function applyManualEdit() {
    const content = document.getElementById('editContent').value.trim();
    if (!content) { showToast('내용을 입력하세요.', 'error'); return; }
    generatedMarkdown = content;
    suggestedFilename = currentEditFilename || '';
    renderOutput('수정 결과 (직접 편집)');
    showToast('편집 내용이 미리보기에 반영되었습니다.', 'success');
  }

  async function aiEditPost() {
    const model = document.getElementById('modelSelect').value;
    const content = document.getElementById('editContent').value.trim();
    const instruction = document.getElementById('editInstruction').value.trim();
    if (!model || model.includes('없음') || model.includes('불러올')) { showToast('Ollama 모델을 먼저 설치하세요.', 'error'); return; }
    if (!content) { showToast('수정할 포스트 내용을 먼저 불러오세요.', 'error'); return; }
    if (!instruction) { showToast('수정 지시 내용을 입력하세요.', 'error'); return; }
    setLoading('edit', true);
    try {
      const res = await fetch('/edit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model, content, instruction, filename: currentEditFilename })
      });
      const data = await res.json();
      if (!res.ok || data.error) { showToast(data.error || 'AI 수정 실패.', 'error'); return; }
      generatedMarkdown = data.markdown;
      suggestedFilename = data.filename || currentEditFilename || '';
      document.getElementById('editContent').value = generatedMarkdown;
      renderOutput('AI 수정 결과');
      if (data.seo) renderSEO(data.seo.checks, data.seo.score);
      showToast('AI 수정이 완료되었습니다!', 'success');
    } catch(e) {
      showToast('서버 오류: ' + e.message, 'error');
    } finally {
      setLoading('edit', false);
    }
  }

  async function saveBackToPost() {
    if (!currentEditFilename) { showToast('저장할 파일명이 없습니다.', 'error'); return; }
    const content = generatedMarkdown || document.getElementById('editContent').value;
    if (!content) { showToast('저장할 내용이 없습니다.', 'error'); return; }
    const label = currentEditIsDraft ? '_drafts/' : '_posts/';
    if (!confirm(label + currentEditFilename + ' 파일을 덮어쓰기 합니다. 계속할까요?')) return;
    if (currentEditIsDraft) {
      await doSaveDraft(currentEditFilename, content);
    } else {
      await doSavePost(currentEditFilename, content);
    }
  }

  // ─── 저장 공통 헬퍼 ───

  function validateFilename(name) {
    if (!name) return '파일명을 입력하세요.';
    if (!name.endsWith('.md')) return '파일명은 .md로 끝나야 합니다.';
    if (/[ㄱ-ㅎ가-힣]/.test(name)) return '파일명에 한글을 사용할 수 없습니다. (Jekyll sitemap 오류 방지)';
    if (/\s/.test(name)) return '파일명에 공백이 있습니다. 하이픈(-)으로 대체하세요.';
    return null;
  }

  async function doSavePost(filename, content) {
    const err = validateFilename(filename);
    if (err) { showToast(err, 'error'); return false; }
    try {
      const res = await fetch('/save-post', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename, content })
      });
      const data = await res.json();
      if (data.error) { showToast(data.error, 'error'); return false; }
      showToast('저장 완료: _posts/' + filename, 'success');
      return true;
    } catch(e) {
      showToast('저장 실패: ' + e.message, 'error');
      return false;
    }
  }

  async function doSaveDraft(filename, content) {
    const err = validateFilename(filename);
    if (err) { showToast(err + ' (초안 저장 취소)', 'error'); return false; }
    try {
      const res = await fetch('/save-draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename, content })
      });
      const data = await res.json();
      if (data.error) { showToast(data.error, 'error'); return false; }
      showToast('초안 저장: _drafts/' + filename, 'success');
      return true;
    } catch(e) {
      showToast('초안 저장 실패: ' + e.message, 'error');
      return false;
    }
  }

  async function saveToPostsDirect() {
    const fname = suggestedFilename || currentEditFilename;
    if (!fname) { showToast('저장할 파일명이 없습니다. "다른 이름으로 저장"을 사용하세요.', 'error'); return; }
    if (!generatedMarkdown) { showToast('저장할 내용이 없습니다.', 'error'); return; }
    if (!confirm('_posts/' + fname + ' 으로 저장합니다. 계속할까요?')) return;
    await doSavePost(fname, generatedMarkdown);
  }

  function toggleSaveAs(mode) {
    if (mode === 'output') {
      const row = document.getElementById('saveAsRow');
      const open = row.classList.toggle('hidden') === false;
      if (open) {
        const fname = suggestedFilename || currentEditFilename || '';
        document.getElementById('saveAsInput').value = fname;
        document.getElementById('saveAsInput').focus();
      }
    } else {
      const row = document.getElementById('saveAsEditRow');
      const open = row.classList.toggle('hidden') === false;
      if (open) {
        document.getElementById('saveAsEditInput').value = currentEditFilename || '';
        document.getElementById('saveAsEditInput').focus();
      }
    }
  }

  async function confirmSaveAs() {
    const filename = document.getElementById('saveAsInput').value.trim();
    if (!generatedMarkdown) { showToast('저장할 내용이 없습니다.', 'error'); return; }
    const ok = await doSavePost(filename, generatedMarkdown);
    if (ok) document.getElementById('saveAsRow').classList.add('hidden');
  }

  async function confirmSaveAsEdit() {
    const filename = document.getElementById('saveAsEditInput').value.trim();
    const content = generatedMarkdown || document.getElementById('editContent').value;
    if (!content) { showToast('저장할 내용이 없습니다.', 'error'); return; }
    const ok = await doSavePost(filename, content);
    if (ok) {
      document.getElementById('saveAsEditRow').classList.add('hidden');
      currentEditFilename = filename;
      currentEditIsDraft = false;
      showEditFilenameChip(filename);
    }
  }

  // ═══════════════════════════════
  // 포스트 관리
  // ═══════════════════════════════
  async function loadManageList() {
    document.getElementById('manageTableBody').innerHTML =
      '<tr><td colspan="4" class="text-center text-gray-600 py-8 text-sm">로딩 중...</td></tr>';
    try {
      const res = await fetch('/posts-info');
      const data = await res.json();
      manageAllPosts = data.posts || [];
      renderManageTable();
      loadHistory();
    } catch(e) {
      document.getElementById('manageTableBody').innerHTML =
        '<tr><td colspan="4" class="text-center text-gray-500 py-6 text-sm">로드 실패: ' + e.message + '</td></tr>';
    }
  }

  function setManageStatus(status) {
    manageStatusFilter = status;
    document.getElementById('statusTabPublished').classList.toggle('active', status === 'published');
    document.getElementById('statusTabDraft').classList.toggle('active', status === 'draft');
    renderManageTable();
  }

  function applyManageFilter() {
    renderManageTable();
  }

  function renderManageTable() {
    const cat = document.getElementById('manageCatFilter').value.toLowerCase();
    const search = document.getElementById('manageSearch').value.toLowerCase();
    const filtered = manageAllPosts.filter(function(p) {
      if (manageStatusFilter === 'published' && p.is_draft) return false;
      if (manageStatusFilter === 'draft' && !p.is_draft) return false;
      if (cat && !(p.categories || '').toLowerCase().includes(cat)) return false;
      if (search && !(p.title || '').toLowerCase().includes(search) &&
          !p.filename.toLowerCase().includes(search)) return false;
      return true;
    });

    const tbody = document.getElementById('manageTableBody');
    if (filtered.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" class="text-center text-gray-600 py-8 text-sm">포스트 없음</td></tr>';
      return;
    }

    tbody.innerHTML = filtered.map(function(p) {
      const isDraft = p.is_draft;
      const fname = p.filename.replace(/'/g, "\\'");
      const title = (p.title || p.filename).replace(/</g, '&lt;').replace(/>/g, '&gt;');
      const cats = (p.categories || '-').replace(/</g, '&lt;');
      let actions = '<button onclick="loadToEdit(\'' + fname + '\',' + isDraft + ')" class="btn-secondary py-1 px-2 mr-1" style="font-size:12px;">수정</button>';
      if (isDraft) {
        actions += '<button onclick="publishDraft(\'' + fname + '\')" class="btn-publish py-1 px-2 mr-1">발행</button>';
      }
      actions += '<button onclick="deletePost(\'' + fname + '\',' + isDraft + ')" class="btn-danger py-1 px-2">삭제</button>';
      const draftBadge = isDraft ? '<span class="draft-badge">초안</span>' : '';
      return '<tr>' +
        '<td class="font-mono text-gray-500" style="font-size:11px;white-space:nowrap;">' + (p.date || '-') + '</td>' +
        '<td class="text-gray-200 text-sm">' + title + draftBadge + '</td>' +
        '<td class="text-gray-400" style="font-size:12px;">' + cats + '</td>' +
        '<td style="white-space:nowrap;">' + actions + '</td>' +
        '</tr>';
    }).join('');
  }

  async function loadToEdit(filename, isDraft) {
    switchMode('edit');
    await new Promise(function(r) { setTimeout(r, 80); });
    try {
      const res = await fetch('/post-content?file=' + encodeURIComponent(filename) + '&draft=' + (isDraft ? '1' : '0'));
      const data = await res.json();
      if (data.error) { showToast(data.error, 'error'); return; }
      document.getElementById('editContent').value = data.content;
      currentEditFilename = filename;
      currentEditIsDraft = !!isDraft;
      const label = isDraft ? filename + ' [초안]' : filename;
      showEditFilenameChip(label);
      document.getElementById('saveBackBtn').classList.remove('hidden');
      document.getElementById('saveAsEditBtn').classList.remove('hidden');
      showToast(filename + ' 불러왔습니다.', 'success');
    } catch(e) {
      showToast('파일 로드 실패: ' + e.message, 'error');
    }
  }

  async function deletePost(filename, isDraft) {
    if (!confirm('정말 삭제합니까?\n' + filename + '\n(삭제 전 자동 백업이 생성됩니다)')) return;
    try {
      const res = await fetch('/delete-post', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename, is_draft: !!isDraft })
      });
      const data = await res.json();
      if (data.error) { showToast(data.error, 'error'); return; }
      showToast('삭제 완료: ' + filename, 'success');
      loadManageList();
    } catch(e) {
      showToast('삭제 실패: ' + e.message, 'error');
    }
  }

  async function publishDraft(filename) {
    if (!confirm('초안을 발행합니다:\n' + filename + '\n_drafts/ → _posts/ 이동')) return;
    try {
      const res = await fetch('/publish-draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename })
      });
      const data = await res.json();
      if (data.error) { showToast(data.error, 'error'); return; }
      showToast('발행 완료: ' + filename, 'success');
      loadManageList();
    } catch(e) {
      showToast('발행 실패: ' + e.message, 'error');
    }
  }

  // ═══════════════════════════════
  // 히스토리
  // ═══════════════════════════════
  async function loadHistory() {
    const container = document.getElementById('historyList');
    try {
      const res = await fetch('/history');
      const data = await res.json();
      const items = data.items || [];
      if (items.length === 0) {
        container.innerHTML = '<p class="text-xs text-gray-600 py-2">히스토리 없음 (파일 저장/삭제 시 자동 생성)</p>';
        return;
      }
      container.innerHTML = items.map(function(item) {
        const bak = item.name.replace(/'/g, "\\'");
        return '<div style="display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid #1f1f1f;">' +
          '<div>' +
          '<div style="font-size:12px;font-family:monospace;color:#d1d5db;">' + item.original + '</div>' +
          '<div style="font-size:11px;color:#6b7280;">' + item.timestamp + '</div>' +
          '</div>' +
          '<button onclick="restoreHistory(\'' + bak + '\')" class="btn-secondary py-1 px-2" style="font-size:11px;">복원</button>' +
          '</div>';
      }).join('');
    } catch(e) {
      container.innerHTML = '<p class="text-xs text-gray-600">히스토리 로드 실패</p>';
    }
  }

  async function restoreHistory(backupName) {
    if (!confirm('백업을 _posts/에 복원합니까?\n' + backupName)) return;
    try {
      const res = await fetch('/restore-history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ backup_name: backupName })
      });
      const data = await res.json();
      if (data.error) { showToast(data.error, 'error'); return; }
      showToast('복원 완료: ' + data.filename, 'success');
      loadManageList();
    } catch(e) {
      showToast('복원 실패: ' + e.message, 'error');
    }
  }

  // ═══════════════════════════════
  // 공통 유틸
  // ═══════════════════════════════
  function copyMarkdown() {
    if (!generatedMarkdown) return;
    navigator.clipboard.writeText(generatedMarkdown).then(function() { showToast('마크다운이 복사되었습니다.', 'success'); });
  }

  function downloadMd() {
    const content = generatedMarkdown || document.getElementById('editContent').value || '';
    if (!content) { showToast('다운로드할 내용이 없습니다.', 'error'); return; }
    const filename = suggestedFilename || currentEditFilename || 'post.md';
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
    showToast(filename + ' 다운로드 완료', 'success');
  }

  function setLoading(mode, loading, text) {
    if (mode === 'generate') {
      document.getElementById('generateBtn').disabled = loading;
      document.getElementById('generateBtnText').textContent = loading ? (text || '생성 중...') : 'AI 포스트 생성';
      document.getElementById('generateSpinner').classList.toggle('hidden', !loading);
    } else {
      document.getElementById('aiEditBtn').disabled = loading;
      document.getElementById('aiEditBtnText').textContent = loading ? '수정 중...' : 'AI 수정 적용';
      document.getElementById('aiEditSpinner').classList.toggle('hidden', !loading);
    }
  }

  function showToast(msg, type) {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();
    const toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(function() { toast.remove(); }, 3500);
  }

  // ═══════════════════════════════
  // 스케줄러
  // ═══════════════════════════════
  var schCurrentSubTab = 'list';

  function switchSchTab(name, btn) {
    ['list','add','log'].forEach(function(t) {
      document.getElementById('schPanel' + t.charAt(0).toUpperCase() + t.slice(1)).classList.toggle('hidden', t !== name);
      document.getElementById('schTab' + t.charAt(0).toUpperCase() + t.slice(1)).classList.toggle('active', t === name);
    });
    schCurrentSubTab = name;
    if (name === 'list') loadSchList();
    if (name === 'log')  loadSchLog();
  }

  // ── 스케줄 목록 ──
  async function loadSchList() {
    try {
    const res  = await fetch('/api/schedules');
    const data = await res.json();
    document.getElementById('schRunnerStatus').textContent =
      data.running ? '🟢 스케줄러 실행 중' : '⚪ 스케줄러 정지';

    const el = document.getElementById('schList');
    if (!data.schedules || data.schedules.length === 0) {
      el.innerHTML = '<p class="text-xs text-gray-600 text-center py-8">등록된 스케줄이 없습니다.<br>+ 스케줄 추가 탭에서 등록하세요.</p>';
      return;
    }
    const freqL = { daily:'매일', weekly:'매주', monthly:'매월' };
    const dowL  = ['월','화','수','목','금','토','일'];
    let html = '<table class="manage-table"><thead><tr><th>카테고리</th><th>주기</th><th>실행 시각</th><th>다음 실행</th><th>상태</th><th></th></tr></thead><tbody>';
    data.schedules.forEach(function(s) {
      var when = '';
      if (s.frequency === 'weekly')  when = dowL[s.day_of_week||0] + '요일 ';
      if (s.frequency === 'monthly') when = (s.day_of_month||1) + '일 ';
      when += String(s.hour||9).padStart(2,'0') + ':' + String(s.minute||0).padStart(2,'0');
      var next = s.next_run ? s.next_run.replace('T',' ').substring(0,16) : '-';
      var badge = s.enabled
        ? '<span style="font-size:11px;padding:2px 8px;border-radius:4px;background:#0d2318;color:#3ECF8E;border:1px solid #3ECF8E44;">활성</span>'
        : '<span style="font-size:11px;padding:2px 8px;border-radius:4px;background:#1a1a1a;color:#6b7280;border:1px solid #333;">정지</span>';
      html += '<tr>' +
        '<td class="text-white font-medium">' + s.category + '</td>' +
        '<td class="font-mono" style="font-size:11px;color:#6b7280;">' + (freqL[s.frequency]||s.frequency) + '</td>' +
        '<td class="font-mono" style="font-size:11px;color:#6b7280;">' + when + '</td>' +
        '<td class="font-mono" style="font-size:11px;color:#6b7280;">' + next + '</td>' +
        '<td>' + badge + '</td>' +
        '<td style="white-space:nowrap;">' +
          '<button onclick="schToggle(\'' + s.id + '\')" class="btn-secondary py-1 px-2 mr-1" style="font-size:12px;">' + (s.enabled ? '정지' : '활성화') + '</button>' +
          '<button onclick="schDelete(\'' + s.id + '\')" class="btn-danger py-1 px-2" style="font-size:12px;">삭제</button>' +
        '</td></tr>';
    });
    html += '</tbody></table>';
    el.innerHTML = html;
    } catch(e) {
      console.error('loadSchList error:', e);
      document.getElementById('schRunnerStatus').textContent = '⚪ 스케줄러 상태 확인 실패';
      document.getElementById('schList').innerHTML = '<p class="text-xs text-red-400 text-center py-8">스케줄 목록을 불러오지 못했습니다.<br>서버가 실행 중인지 확인하세요.</p>';
    }
  }

  // ── 주기 UI 업데이트 ──
  function schUpdateFreqUI() {
    var freq = document.getElementById('schAddFreq').value;
    document.getElementById('schOptWeekly').classList.toggle('hidden', freq !== 'weekly');
    document.getElementById('schOptMonthly').classList.toggle('hidden', freq !== 'monthly');
  }

  // ── 스케줄 추가 ──
  async function schAddSubmit() {
    var btn = document.getElementById('schAddBtnText');
    var spinner = document.getElementById('schAddSpinner');
    var resultEl = document.getElementById('schAddResult');
    btn.textContent = '등록 중...';
    spinner.classList.remove('hidden');
    resultEl.textContent = '';
    var payload = {
      category:     document.getElementById('schAddCat').value,
      frequency:    document.getElementById('schAddFreq').value,
      day_of_week:  parseInt(document.getElementById('schAddDow').value),
      day_of_month: parseInt(document.getElementById('schAddDom').value || 1),
      hour:         parseInt(document.getElementById('schAddHour').value),
      minute:       parseInt(document.getElementById('schAddMinute').value),
      enabled:      document.getElementById('schAddEnabled').checked,
    };
    try {
      var res  = await fetch('/api/schedules', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
      var data = await res.json();
      if (data.error) throw new Error(data.error);
      showToast('스케줄 등록 완료', 'success');
      resultEl.textContent = '✓ 등록됨 — 다음 실행: ' + (data.next_run || '').replace('T',' ').substring(0,16);
      loadSchList();
    } catch(e) {
      showToast(e.message, 'error');
      resultEl.textContent = '✗ ' + e.message;
    } finally {
      btn.textContent = '스케줄 등록';
      spinner.classList.add('hidden');
    }
  }

  async function schToggle(id) {
    var res = await fetch('/api/schedules/' + id + '/toggle', { method:'POST' });
    var data = await res.json();
    if (data.error) { showToast(data.error, 'error'); return; }
    loadSchList();
  }

  async function schDelete(id) {
    if (!confirm('스케줄을 삭제할까요?')) return;
    var res = await fetch('/api/schedules/' + id, { method:'DELETE' });
    var data = await res.json();
    if (data.error) { showToast(data.error, 'error'); return; }
    var msg = data.win_task_removed
      ? '삭제됐습니다. (Windows 작업 스케줄러 태스크도 함께 제거됨)'
      : '삭제됐습니다.';
    showToast(msg, 'success');
    loadSchList();
  }

  // ── 실행 로그 ──
  async function loadSchLog() {
    try {
    var res  = await fetch('/api/log');
    var data = await res.json();
    var el   = document.getElementById('schLog');
    if (!data.items || data.items.length === 0) {
      el.innerHTML = '<p class="text-xs text-gray-600 text-center py-8">실행 기록이 없습니다.</p>';
      return;
    }
    var html = '<table class="manage-table"><thead><tr><th>일시</th><th>카테고리</th><th>파일명</th><th>결과</th></tr></thead><tbody>';
    data.items.forEach(function(item) {
      var ts    = item.timestamp ? item.timestamp.replace('T',' ').substring(0,16) : '-';
      var badge = item.ok
        ? '<span style="font-size:11px;padding:2px 8px;border-radius:4px;background:#0d2318;color:#3ECF8E;border:1px solid #3ECF8E44;">성공</span>'
        : '<span style="font-size:11px;padding:2px 8px;border-radius:4px;background:#2a0a0a;color:#ef4444;border:1px solid #ef444444;" title="' + (item.error||'') + '">실패</span>';
      html += '<tr>' +
        '<td class="font-mono" style="font-size:11px;color:#6b7280;">' + ts + '</td>' +
        '<td class="text-white" style="font-size:13px;">' + item.category + '</td>' +
        '<td class="font-mono" style="font-size:11px;color:#9ca3af;">' + (item.filename||'-') + '</td>' +
        '<td>' + badge + '</td></tr>';
    });
    html += '</tbody></table>';
    el.innerHTML = html;
    } catch(e) {
      console.error('loadSchLog error:', e);
      document.getElementById('schLog').innerHTML = '<p class="text-xs text-red-400 text-center py-8">실행 기록을 불러오지 못했습니다.<br>서버가 실행 중인지 확인하세요.</p>';
    }
  }


  // ── Windows 작업 스케줄러 안내 ──
  function showTaskSetup() {
    var el = document.getElementById('taskSetupInfo');
    el.style.display = el.style.display === 'none' ? 'block' : 'none';
  }

  // ── 즉시 실행 ──
  function runNowOpen() {
    document.getElementById('runNowInline').classList.remove('hidden');
    document.getElementById('runNowResult').textContent = '';
  }
  function runNowClose() {
    document.getElementById('runNowInline').classList.add('hidden');
  }

  async function runNowExec() {
    var category = document.getElementById('runNowCat').value;
    var model    = document.getElementById('modelSelect').value;
    if (!model || model.includes('없음') || model.includes('불러올')) {
      showToast('상단 Ollama 패널에서 모델을 먼저 선택하세요.', 'error'); return;
    }
    var btn = document.getElementById('runNowBtnText');
    var spinner = document.getElementById('runNowSpinner');
    var resultEl = document.getElementById('runNowResult');
    btn.textContent = '생성 중...';
    spinner.classList.remove('hidden');
    resultEl.textContent = 'AI가 포스트를 생성 중입니다...\n(모델에 따라 수 분 소요)';
    try {
      var res  = await fetch('/api/run-now', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ category, model }) });
      var data = await res.json();
      if (data.error) throw new Error(data.error);
      resultEl.textContent = '✓ 완료\n파일: ' + data.filename + '\nGit: ' + (data.git && data.git.ok ? '배포 성공' : (data.git && data.git.error ? data.git.error : '실패'));
      showToast('포스팅 완료: ' + data.filename, 'success');
      loadSchLog();
    } catch(e) {
      resultEl.textContent = '✗ ' + e.message;
      showToast(e.message, 'error');
    } finally {
      btn.textContent = '실행';
      spinner.classList.add('hidden');
    }
  }

  // ── 교정 (Claude CLI) ──
  async function proofreadOutput() {
    if (!generatedMarkdown) { showToast('교정할 생성 결과가 없습니다.', 'error'); return; }
    var btn = document.getElementById('proofreadOutputBtn');
    var txt = document.getElementById('proofreadOutputBtnText');
    var spin = document.getElementById('proofreadOutputSpinner');
    btn.disabled = true; txt.textContent = '교정 중...'; spin.classList.remove('hidden');
    try {
      var res = await fetch('/proofread', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: generatedMarkdown, filename: suggestedFilename })
      });
      var data = await res.json();
      if (!res.ok || data.error) { showToast(data.error || '교정 실패', 'error'); return; }
      var changes = data.changes || [];
      if (changes.length === 0) { showToast('교정할 내용이 없습니다.', 'success'); return; }
      generatedMarkdown = data.corrected;
      renderOutput('생성 결과 (교정 ' + changes.length + '건 적용)');
      showToast('교정 완료: ' + changes.length + '건 수정\n' + changes.join('\n'), 'success');
    } catch(e) {
      showToast('서버 오류: ' + e.message, 'error');
    } finally {
      btn.disabled = false; txt.textContent = '🔍 교정 (Claude)'; spin.classList.add('hidden');
    }
  }

  async function proofreadPost() {
    const content = document.getElementById('editContent').value.trim();
    if (!content) { showToast('교정할 포스트 내용을 먼저 불러오세요.', 'error'); return; }
    const btn = document.getElementById('proofreadBtn');
    const txt = document.getElementById('proofreadBtnText');
    const spin = document.getElementById('proofreadSpinner');
    btn.disabled = true; txt.textContent = '교정 중...'; spin.classList.remove('hidden');
    try {
      const res = await fetch('/proofread', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, filename: currentEditFilename })
      });
      const data = await res.json();
      if (!res.ok || data.error) { showToast(data.error || '교정 실패', 'error'); return; }
      const changes = data.changes || [];
      if (changes.length === 0) {
        showToast('교정할 내용이 없습니다.', 'success');
        return;
      }
      document.getElementById('editContent').value = data.corrected;
      generatedMarkdown = data.corrected;
      renderOutput('교정 결과');
      showToast('교정 완료: ' + changes.length + '건 수정\n' + changes.join('\n'), 'success');
      document.getElementById('saveBackBtn').classList.remove('hidden');
      document.getElementById('saveAsEditBtn').classList.remove('hidden');
    } catch(e) {
      showToast('서버 오류: ' + e.message, 'error');
    } finally {
      btn.disabled = false; txt.textContent = '🔍 교정 (Claude)'; spin.classList.add('hidden');
    }
  }

  async function proofreadAll() {
    if (!confirm('모든 발행 포스트를 Claude로 교정합니다. 계속하시겠습니까?')) return;
    const btn = document.getElementById('proofreadAllBtn');
    const txt = document.getElementById('proofreadAllBtnText');
    const spin = document.getElementById('proofreadAllSpinner');
    btn.disabled = true; txt.textContent = '교정 중...'; spin.classList.remove('hidden');
    try {
      const res = await fetch('/proofread-all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const data = await res.json();
      if (!res.ok || data.error) { showToast(data.error || '전체 교정 실패', 'error'); return; }
      const results = data.results || [];
      const changed = results.filter(r => r.saved);
      const errors = results.filter(r => r.error);
      let msg = '전체 교정 완료: ' + results.length + '개 파일 중 ' + changed.length + '개 수정';
      if (errors.length > 0) msg += ', ' + errors.length + '개 오류';
      if (changed.length > 0) {
        msg += '\n\n수정된 파일:\n' + changed.map(r => '• ' + r.filename + ' (' + r.changes.length + '건)').join('\n');
      }
      showToast(msg, changed.length > 0 ? 'success' : 'info');
      loadManageList();
    } catch(e) {
      showToast('서버 오류: ' + e.message, 'error');
    } finally {
      btn.disabled = false; txt.textContent = '🔍 전체 교정'; spin.classList.add('hidden');
    }
  }
</script>
</body>
</html>"""


# ──────────────────────────────────────────────
# Python 백엔드 — 유틸리티
# ──────────────────────────────────────────────

def parse_frontmatter(content: str) -> dict:
    """YAML front matter에서 키-값 파싱."""
    result = {}
    m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not m:
        return result
    for line in m.group(1).split('\n'):
        kv = re.match(r'^([\w]+):\s*(.+)$', line.strip())
        if kv:
            key = kv.group(1)
            val = kv.group(2).strip().strip('"\'[]')
            result[key] = val
    return result


def backup_post(filename: str, is_draft: bool = False):
    """덮어쓰기/삭제 전 .history/파일명.YYYYMMDD_HHMMSS.bak 생성."""
    src_dir = DRAFTS_DIR if is_draft else POSTS_DIR
    src = os.path.join(src_dir, os.path.basename(filename))
    if not os.path.isfile(src):
        return None
    try:
        os.makedirs(HISTORY_DIR, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        bak_name = f"{os.path.basename(filename)}.{ts}.bak"
        bak_path = os.path.join(HISTORY_DIR, bak_name)
        with open(src, 'r', encoding='utf-8') as f:
            data = f.read()
        with open(bak_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(data)
        print(f"  백업: {bak_path}")
        return bak_name
    except Exception as e:
        print(f"  백업 실패: {e}")
        return None


def get_posts_info() -> dict:
    """_posts/ + _drafts/ 전체 메타데이터 반환."""
    posts = []
    dirs = [(POSTS_DIR, False), (DRAFTS_DIR, True)]
    for d, is_draft in dirs:
        if not os.path.isdir(d):
            continue
        for fname in sorted(os.listdir(d), reverse=True):
            if not fname.endswith('.md'):
                continue
            fpath = os.path.join(d, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read(3000)
                fm = parse_frontmatter(content)
                posts.append({
                    'filename': fname,
                    'title': fm.get('title', fname),
                    'date': fm.get('date', ''),
                    'categories': fm.get('categories', ''),
                    'is_draft': is_draft,
                })
            except Exception:
                posts.append({
                    'filename': fname, 'title': fname,
                    'date': '', 'categories': '', 'is_draft': is_draft,
                })
    return {'posts': posts}


def get_history() -> dict:
    """히스토리 목록 반환 (최신순, 최대 30개)."""
    if not os.path.isdir(HISTORY_DIR):
        return {'items': []}
    items = []
    for fname in os.listdir(HISTORY_DIR):
        if not fname.endswith('.bak'):
            continue
        m = re.match(r'^(.+\.md)\.(\d{8}_\d{6})\.bak$', fname)
        if m:
            original = m.group(1)
            ts_str = m.group(2)
            try:
                ts = datetime.strptime(ts_str, '%Y%m%d_%H%M%S')
                timestamp = ts.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                timestamp = ts_str
            items.append({'name': fname, 'original': original, 'timestamp': timestamp})
    items.sort(key=lambda x: x['name'], reverse=True)
    return {'items': items[:30]}


def restore_history(backup_name: str) -> dict:
    """백업 파일 → _posts/ 복원."""
    safe = os.path.basename(backup_name)
    bak_path = os.path.join(HISTORY_DIR, safe)
    if not os.path.isfile(bak_path):
        return {'error': f'백업 파일을 찾을 수 없습니다: {safe}'}
    m = re.match(r'^(.+\.md)\.\d{8}_\d{6}\.bak$', safe)
    if not m:
        return {'error': '올바른 백업 파일 형식이 아닙니다.'}
    original = m.group(1)
    dest = os.path.join(POSTS_DIR, original)
    try:
        os.makedirs(POSTS_DIR, exist_ok=True)
        with open(bak_path, 'r', encoding='utf-8') as f:
            content = f.read()
        with open(dest, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        print(f"  복원: {dest}")
        return {'ok': True, 'filename': original}
    except Exception as e:
        return {'error': str(e)}


def delete_post(filename: str, is_draft: bool = False) -> dict:
    """백업 후 파일 삭제."""
    src_dir = DRAFTS_DIR if is_draft else POSTS_DIR
    safe = os.path.basename(filename)
    path = os.path.join(src_dir, safe)
    if not os.path.isfile(path):
        return {'error': f'파일을 찾을 수 없습니다: {safe}'}
    backup_post(safe, is_draft)
    try:
        os.remove(path)
        print(f"  삭제: {path}")
        return {'ok': True, 'filename': safe}
    except Exception as e:
        return {'error': str(e)}


def publish_draft(filename: str) -> dict:
    """_drafts/ → _posts/ 이동."""
    safe = os.path.basename(filename)
    src = os.path.join(DRAFTS_DIR, safe)
    if not os.path.isfile(src):
        return {'error': f'초안 파일을 찾을 수 없습니다: {safe}'}
    try:
        os.makedirs(POSTS_DIR, exist_ok=True)
        dest = os.path.join(POSTS_DIR, safe)
        with open(src, 'r', encoding='utf-8') as f:
            content = f.read()
        with open(dest, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        os.remove(src)
        print(f"  발행: {src} → {dest}")
        return {'ok': True, 'filename': safe}
    except Exception as e:
        return {'error': str(e)}


def similarity_check(content: str) -> dict:
    """Jaccard 유사도 검사. 임계값 0.5 초과 시 파일명 반환."""
    def tokenize(text):
        return set(re.findall(r'[가-힣a-zA-Z0-9]+', text.lower()))

    new_tokens = tokenize(content)
    if len(new_tokens) < 15:
        return {'similar_post': None, 'similarity': 0.0}

    best_file = None
    best_sim = 0.0

    if os.path.isdir(POSTS_DIR):
        for fname in os.listdir(POSTS_DIR):
            if not fname.endswith('.md'):
                continue
            try:
                with open(os.path.join(POSTS_DIR, fname), 'r', encoding='utf-8') as f:
                    existing_tokens = tokenize(f.read())
                if len(existing_tokens) < 15:
                    continue
                inter = len(new_tokens & existing_tokens)
                union = len(new_tokens | existing_tokens)
                sim = inter / union if union > 0 else 0.0
                if sim > best_sim:
                    best_sim = sim
                    best_file = fname
            except Exception:
                pass

    if best_sim >= 0.5:
        return {'similar_post': best_file, 'similarity': round(best_sim, 3)}
    return {'similar_post': None, 'similarity': round(best_sim, 3)}


def _find_git() -> str:
    """git 실행 파일 경로 반환. PATH 우선, 없으면 Windows 기본 설치 경로 시도."""
    git = shutil.which('git')
    if git:
        return git
    # Windows 일반 설치 경로 폴백
    candidates = [
        r'C:\Program Files\Git\bin\git.exe',
        r'C:\Program Files\Git\mingw64\bin\git.exe',
        r'C:\Program Files (x86)\Git\bin\git.exe',
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return 'git'  # 마지막 시도 (오류 메시지를 위해 문자열 유지)


def git_deploy(message: str) -> dict:
    """git add _posts/ _drafts/ → commit → push."""
    git = _find_git()
    try:
        # git add (_drafts/는 폴더가 있을 때만 포함)
        add_targets = ['_posts/']
        if os.path.isdir(DRAFTS_DIR):
            add_targets.append('_drafts/')
        subprocess.run(
            [git, 'add'] + add_targets,
            cwd=PROJECT_ROOT, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        # git commit
        commit = subprocess.run(
            [git, 'commit', '-m', message],
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        c_out = (commit.stdout or b'').decode('utf-8', errors='replace').strip()
        c_err = (commit.stderr or b'').decode('utf-8', errors='replace').strip()
        if commit.returncode != 0:
            combined = c_out + c_err
            if 'nothing to commit' in combined:
                return {'error': '커밋할 변경 사항이 없습니다. 먼저 파일을 저장하세요.'}
            return {'error': c_err or c_out or 'commit 실패'}
        # git push
        push = subprocess.run(
            [git, 'push'],
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        p_out = (push.stdout or b'').decode('utf-8', errors='replace').strip()
        p_err = (push.stderr or b'').decode('utf-8', errors='replace').strip()
        if push.returncode != 0:
            return {'error': p_err or p_out or 'push 실패'}
        output = c_out
        if p_out:
            output += '\n' + p_out
        print(f"  Git 배포 완료: {message}")
        return {'ok': True, 'output': output or '배포 완료'}
    except subprocess.CalledProcessError as e:
        raw_err = e.stderr or b''
        return {'error': raw_err.decode('utf-8', errors='replace') if isinstance(raw_err, bytes) else str(raw_err)}
    except FileNotFoundError:
        return {'error': f'git을 찾을 수 없습니다. (시도: {git})\n'
                         f'해결: git을 설치하거나 시스템 PATH에 추가하세요.\n'
                         f'설치 경로: C:\\Program Files\\Git\\bin'}
    except Exception as e:
        return {'error': str(e)}


# ──────────────────────────────────────────────
# Python 백엔드 — 기존 함수
# ──────────────────────────────────────────────

def get_ollama_models() -> dict:
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            models = [m["name"] for m in data.get("models", [])]
            cfg = load_config()
            return {"models": models, "default_model": cfg.get("default_model", "")}
    except urllib.error.URLError:
        return {"error": "Ollama 서버에 연결할 수 없습니다."}
    except Exception as e:
        return {"error": str(e)}


def get_posts_list() -> dict:
    try:
        if not os.path.isdir(POSTS_DIR):
            return {"files": [], "note": f"_posts/ 디렉토리를 찾을 수 없습니다: {POSTS_DIR}"}
        files = sorted(
            [f for f in os.listdir(POSTS_DIR) if f.endswith(".md")],
            reverse=True
        )
        return {"files": files}
    except Exception as e:
        return {"error": str(e)}


def get_post_content(filename: str, is_draft: bool = False) -> dict:
    safe_name = os.path.basename(filename)
    src_dir = DRAFTS_DIR if is_draft else POSTS_DIR
    path = os.path.join(src_dir, safe_name)
    if not os.path.isfile(path):
        return {"error": f"파일을 찾을 수 없습니다: {safe_name}"}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return {"content": f.read(), "filename": safe_name, "is_draft": is_draft}
    except Exception as e:
        return {"error": str(e)}


def save_post(filename: str, content: str, is_draft: bool = False) -> dict:
    safe_name = os.path.basename(filename)
    if not safe_name.endswith(".md"):
        return {"error": "마크다운(.md) 파일만 저장할 수 있습니다."}
    if not safe_name:
        return {"error": "파일명이 비어 있습니다."}
    target_dir = DRAFTS_DIR if is_draft else POSTS_DIR
    try:
        os.makedirs(target_dir, exist_ok=True)
    except Exception as e:
        return {"error": f"디렉토리 생성 실패: {e}"}
    path = os.path.join(target_dir, safe_name)
    # 기존 파일이면 백업
    if os.path.isfile(path):
        backup_post(safe_name, is_draft)
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        dir_label = "_drafts" if is_draft else "_posts"
        print(f"  저장: {dir_label}/{safe_name}")
        # 썸네일 자동 생성 (포스트만, 드래프트 제외)
        if not is_draft:
            try:
                from generate_thumbnails import process_post as gen_thumb
                gen_thumb(safe_name)
            except Exception as e:
                print(f"  썸네일 생성 스킵: {e}")
        return {"ok": True, "path": path, "filename": safe_name, "is_draft": is_draft}
    except PermissionError:
        return {"error": f"파일 쓰기 권한이 없습니다: {path}"}
    except Exception as e:
        return {"error": f"저장 실패: {e}"}


REQUIRED_POST_FIELDS = ("title", "date", "categories", "tags", "description", "content", "filename")


def assemble_markdown(post_data: dict) -> str:
    """JSON 포스트 데이터 → Jekyll front matter + 본문 마크다운."""
    cats = post_data.get("categories", [])
    if isinstance(cats, str):
        cats = [cats]
    tags = post_data.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]
    # 썸네일 이미지 경로 생성
    stem = os.path.splitext(post_data.get("filename", ""))[0]
    image_path = f"/assets/img/posts/{stem}.png" if stem else ""
    lines = [
        "---",
        "layout: post",
        f'title: "{post_data["title"]}"',
        f'date: {post_data["date"]}',
        f'categories: [{", ".join(cats)}]',
        f'tags: [{", ".join(tags)}]',
        f'description: "{post_data["description"]}"',
    ]
    if image_path:
        lines.append(f'image: {image_path}')
    lines += [
        "---",
        "",
        post_data["content"],
    ]
    return "\n".join(lines) + "\n"


def analyze_seo(post_data: dict, similar_post: str = None) -> dict:
    """백엔드 SEO 분석. post_data는 JSON 응답 dict."""
    checks = []
    score = 0

    title = post_data.get("title", "")
    desc = post_data.get("description", "")
    cats = post_data.get("categories", [])
    tags = post_data.get("tags", [])
    content = post_data.get("content", "")
    filename = post_data.get("filename", "")

    if isinstance(cats, str):
        cats = [cats]
    if isinstance(tags, str):
        tags = [tags]

    # 제목 길이 (15점)
    tLen = len(title)
    if 20 <= tLen <= 60:
        checks.append({"ok": True, "msg": f"제목 길이 양호 ({tLen}자)"})
        score += 15
    elif tLen > 0:
        checks.append({"ok": "warn", "msg": f"제목 길이 주의 ({tLen}자, 권장 20-60자)"})
        score += 8
    else:
        checks.append({"ok": False, "msg": "제목 없음"})

    # description 길이 (15점)
    dLen = len(desc)
    if 50 <= dLen <= 150:
        checks.append({"ok": True, "msg": f"설명 길이 양호 ({dLen}자)"})
        score += 15
    elif dLen > 0:
        checks.append({"ok": "warn", "msg": f"설명 길이 주의 ({dLen}자, 권장 50-150자)"})
        score += 8
    else:
        checks.append({"ok": False, "msg": "설명(description) 없음"})

    # 카테고리 (10점)
    if cats and cats[0]:
        checks.append({"ok": True, "msg": f"카테고리 있음: [{', '.join(cats)}]"})
        score += 10
    else:
        checks.append({"ok": False, "msg": "카테고리 없음"})

    # 금지 표현 (15점)
    banned = ["주식 추천", "확실한 수익", "수익 보장", "투자 권유합니다"]
    full_text = title + " " + desc + " " + content
    found = [b for b in banned if b in full_text]
    if not found:
        checks.append({"ok": True, "msg": "금지 표현 없음"})
        score += 15
    else:
        checks.append({"ok": False, "msg": f"금지 표현 발견: {', '.join(found)}"})

    # 면책 고지 (15점)
    if "면책 고지" in content:
        checks.append({"ok": True, "msg": "면책 고지 포함"})
        score += 15
    else:
        checks.append({"ok": False, "msg": "면책 고지 없음 (포스트 하단에 추가하세요)"})

    # 파일명 영문 (10점)
    if not filename:
        checks.append({"ok": "warn", "msg": "파일명 미정"})
        score += 5
    elif re.match(r'^[a-z0-9\-_.]+$', filename, re.IGNORECASE):
        checks.append({"ok": True, "msg": f"파일명 영문 OK: {filename}"})
        score += 10
    else:
        checks.append({"ok": False, "msg": f"파일명에 한글 포함 (Jekyll sitemap 오류 위험): {filename}"})

    # tags 유무 (10점)
    if tags and tags[0]:
        checks.append({"ok": True, "msg": f"tags 있음: [{', '.join(tags)}]"})
        score += 10
    else:
        checks.append({"ok": False, "msg": "tags 없음 (SEO를 위해 관련 태그를 추가하세요)"})

    # 본문 길이 (10점)
    bodyLen = len(content)
    if bodyLen >= 3000:
        checks.append({"ok": True, "msg": f"본문 길이 양호 ({bodyLen}자)"})
        score += 10
    elif bodyLen >= 1500:
        checks.append({"ok": "warn", "msg": f"본문이 다소 짧음 ({bodyLen}자, 권장 3000자 이상)"})
        score += 5
    else:
        checks.append({"ok": False, "msg": f"본문이 너무 짧음 ({bodyLen}자, 권장 3000자 이상)"})

    # 중복 포스트
    if similar_post:
        checks.append({"ok": False, "msg": f"유사 포스트 발견: {similar_post} (내용 중복 가능성 있음)"})
    else:
        checks.append({"ok": True, "msg": "중복 포스트 없음"})

    return {"checks": checks, "score": min(100, score)}


def call_ollama(model: str, system: str, user: str) -> dict:
    """Ollama API 호출 — JSON 모드. 구조화된 post_data dict 반환."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "format": "json",
        "options": {"num_predict": -1},
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=None) as resp:
            result = json.loads(resp.read())
            raw = result.get("message", {}).get("content", "")
        if not raw:
            return {"error": "모델에서 응답이 없습니다."}

        # thinking 태그 제거 (qwen3 등)
        raw = re.sub(r'<think>[\s\S]*?</think>\s*', '', raw).strip()

        try:
            post_data = json.loads(raw)
        except json.JSONDecodeError:
            snippet = raw[:300] if raw else "(empty)"
            print(f"  [JSON 파싱 실패] 응답 미리보기: {snippet}")
            return {"error": f"AI 응답이 올바른 JSON 형식이 아닙니다.\n미리보기: {snippet[:150]}"}

        # 필수 필드 검증
        for key in REQUIRED_POST_FIELDS:
            if key not in post_data:
                return {"error": f"AI 응답에 '{key}' 필드가 누락되었습니다."}

        # categories/tags 정규화
        if isinstance(post_data["categories"], str):
            post_data["categories"] = [post_data["categories"]]
        if isinstance(post_data["tags"], str):
            post_data["tags"] = [post_data["tags"]]

        filename = post_data["filename"]
        markdown = assemble_markdown(post_data)

        return {"post": post_data, "markdown": markdown, "filename": filename}
    except urllib.error.URLError:
        return {"error": "Ollama 서버에 연결할 수 없습니다. (Ollama가 실행 중인지 확인하세요)"}
    except Exception as e:
        return {"error": f"오류: {str(e)}"}


def generate_post(data: dict) -> dict:
    model = data.get("model", "qwen2.5:7b")
    topic = data.get("topic", "")
    category = data.get("category", "시장분석")
    post_date = data.get("postDate", "")
    stocker_data = data.get("stockerData", "")
    extra_context = data.get("extraContext", "")
    seo_feedback = data.get("seoFeedback", "")

    parts = [f"**주제**: {topic}", f"**카테고리**: {category}"]
    if post_date:
        parts.append(f"**날짜**: {post_date}")
    if stocker_data:
        parts.append(f"\n**참고 데이터**:\n{stocker_data}")
    if extra_context:
        parts.append(f"\n**추가 컨텍스트**:\n{extra_context}")
    if seo_feedback:
        parts.append(f"\n**⚠ SEO 개선 필수사항 (이전 생성에서 누락)**:\n{seo_feedback}")
    parts.append("\n위 정보를 바탕으로 BlackRabbit LAB 블로그 포스트를 JSON 형식으로 작성해주세요.")

    result = call_ollama(model, SYSTEM_PROMPT, "\n".join(parts))
    if "error" in result:
        return result

    post_data = result["post"]
    markdown = result["markdown"]
    filename = result["filename"]

    # 유사도 검사
    sim = similarity_check(markdown)
    similar_post = sim.get("similar_post")

    # SEO 분석
    seo = analyze_seo(post_data, similar_post)

    return {
        "post": post_data,
        "markdown": markdown,
        "filename": filename,
        "seo": seo,
    }


def edit_post(data: dict) -> dict:
    model = data.get("model", "qwen2.5:7b")
    content = data.get("content", "")
    instruction = data.get("instruction", "")
    filename = data.get("filename", "post.md")

    user_msg = (
        f"## 원본 포스트\n\n{content}\n\n"
        f"## 수정 지시\n\n{instruction}\n\n"
        f"## 원본 파일명\n{filename}\n\n"
        "위 수정 지시에 따라 포스트를 수정해주세요. JSON 형식으로 응답하세요."
    )
    result = call_ollama(model, EDIT_SYSTEM_PROMPT, user_msg)
    if "error" in result:
        return result

    post_data = result["post"]
    markdown = result["markdown"]
    fname = result["filename"]

    # SEO 분석
    seo = analyze_seo(post_data)

    return {
        "post": post_data,
        "markdown": markdown,
        "filename": fname,
        "seo": seo,
    }


_PROOFREAD_SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "fixes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "find":    {"type": "string", "description": "원문에서 찾을 문자열 (정확히 일치)"},
                    "replace": {"type": "string", "description": "교체할 문자열"},
                    "reason":  {"type": "string", "description": "수정 사유"},
                },
                "required": ["find", "replace", "reason"],
            },
        },
    },
    "required": ["fixes"],
}, ensure_ascii=False)


def proofread_post(content: str, filename: str = "") -> dict:
    """claude CLI를 이용한 포스트 교정. find/replace 쌍을 받아 적용."""
    claude_bin = shutil.which("claude")
    if not claude_bin:
        return {"error": "claude CLI를 찾을 수 없습니다. 'claude'가 PATH에 있는지 확인하세요."}

    user_msg = "아래 포스트를 교정해주세요.\n\n" + content

    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    raw = ""
    try:
        proc = subprocess.run(
            [claude_bin, "-p", "-",
             "--system-prompt", PROOFREAD_PROMPT,
             "--output-format", "json",
             "--max-turns", "1",
             "--json-schema", _PROOFREAD_SCHEMA],
            input=user_msg.encode("utf-8"),
            capture_output=True, timeout=180, env=env,
        )
        stdout = proc.stdout.decode("utf-8", errors="replace") if proc.stdout else ""
        stderr = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""
        if proc.returncode != 0:
            err_msg = stderr.strip() or f"claude CLI 종료 코드: {proc.returncode}"
            return {"error": err_msg}

        raw = stdout.strip()
        if not raw:
            return {"error": "claude CLI가 빈 응답을 반환했습니다."}

        # --output-format json → {"result":"...", ...} 래퍼 파싱
        result_text = raw
        try:
            outer = json.loads(raw)
            if isinstance(outer, dict) and "result" in outer:
                result_text = outer["result"]
            elif isinstance(outer, dict) and "fixes" in outer:
                result_text = outer
        except json.JSONDecodeError:
            pass

        # result_text → fixes 배열 추출
        fixes = _extract_fixes(result_text)

        if not fixes:
            return {"corrected": content, "changes": [], "filename": filename}

        corrected = content
        changes = []
        for fix in fixes:
            find_str = fix.get("find", "")
            replace_str = fix.get("replace", "")
            reason = fix.get("reason", "")
            if find_str and find_str in corrected:
                corrected = corrected.replace(find_str, replace_str, 1)
                changes.append(f"{find_str} → {replace_str}" + (f" ({reason})" if reason else ""))

        return {"corrected": corrected, "changes": changes, "filename": filename}

    except FileNotFoundError:
        return {"error": "claude CLI를 찾을 수 없습니다. 'claude'가 설치되어 있는지 확인하세요."}
    except subprocess.TimeoutExpired:
        return {"error": "claude CLI 응답 시간 초과 (180초)"}
    except (json.JSONDecodeError, ValueError) as e:
        snippet = raw[:300] if raw else "(empty)"
        return {"error": f"claude 응답 파싱 실패: {e}\n응답 미리보기: {snippet}"}
    except Exception as e:
        return {"error": f"교정 중 오류: {e}"}


def _extract_fixes(result_text) -> list:
    """Claude 응답에서 fixes 배열을 안전하게 추출."""
    # dict인 경우 (정상: {"fixes":[...]})
    if isinstance(result_text, dict):
        return result_text.get("fixes", [])

    # list인 경우 (Claude가 배열을 직접 반환)
    if isinstance(result_text, list):
        return result_text

    if not isinstance(result_text, str):
        return []

    text = result_text.strip()

    # ```json ... ``` 블록 제거
    m = re.search(r'```(?:json)?\s*\n(.*?)\n\s*```', text, re.DOTALL)
    if m:
        text = m.group(1).strip()

    # JSON 파싱 시도
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed.get("fixes", [])
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    # 개별 JSON 객체들을 하나씩 추출 (배열 래핑 없이 나열된 경우)
    fixes = []
    for m in re.finditer(r'\{[^{}]*\}', text):
        try:
            obj = json.loads(m.group(0))
            if "find" in obj and "replace" in obj:
                fixes.append(obj)
        except json.JSONDecodeError:
            continue
    return fixes


# ──────────────────────────────────────────────
# 스케줄러 — 설정 / 로그
# ──────────────────────────────────────────────

def load_config() -> dict:
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"schedules": [], "default_model": "qwen2.5:7b"}


def save_config(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def load_log() -> list:
    if os.path.isfile(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def append_log(entry: dict):
    logs = load_log()
    logs.insert(0, entry)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs[:200], f, ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────
# 스케줄러 — next_run 계산
# ──────────────────────────────────────────────

def calc_next_run(schedule: dict, after: datetime = None) -> str:
    now    = after or datetime.now()
    freq   = schedule.get("frequency", "weekly")
    hour   = int(schedule.get("hour", 9))
    minute = int(schedule.get("minute", 0))
    dow    = int(schedule.get("day_of_week", 0))   # 0=월 ~ 6=일
    dom    = int(schedule.get("day_of_month", 1))  # 1~28

    if freq == "daily":
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate.isoformat()

    elif freq == "weekly":
        days_ahead = (dow - now.weekday()) % 7
        candidate = (now + timedelta(days=days_ahead)).replace(
            hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(weeks=1)
        return candidate.isoformat()

    else:  # monthly
        dom = min(dom, 28)
        candidate = now.replace(day=dom, hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            m = now.month + 1 if now.month < 12 else 1
            y = now.year + 1 if now.month == 12 else now.year
            candidate = candidate.replace(year=y, month=m)
        return candidate.isoformat()


# ──────────────────────────────────────────────
# 스케줄러 — 자동 포스팅 실행
# ──────────────────────────────────────────────

def get_recent_titles(limit: int = 20) -> list:
    titles = []
    if not os.path.isdir(POSTS_DIR):
        return titles
    files = sorted(
        [f for f in os.listdir(POSTS_DIR) if f.endswith(".md")], reverse=True
    )[:limit]
    for fname in files:
        try:
            with open(os.path.join(POSTS_DIR, fname), "r", encoding="utf-8") as f:
                for line in f:
                    m = re.match(r'^title:\s*["\']?(.+?)["\']?\s*$', line)
                    if m:
                        titles.append(m.group(1).strip())
                        break
        except Exception:
            titles.append(fname)
    return titles


def _build_seo_feedback(checks: list) -> str:
    """SEO 실패 항목 → 피드백 문자열."""
    lines = []
    for c in checks:
        if c.get("ok") is not True:
            lines.append(f"- {c['msg']} → 반드시 수정하세요.")
    return "\n".join(lines)


def run_auto_post(schedule_id: str, category: str, model: str) -> dict:
    """카테고리 기반 주제 자동 선정 → 포스트 생성 (SEO 검증 포함) → 저장 → git 배포."""
    now      = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    recent   = get_recent_titles(20)
    recent_text = "\n".join(f"- {t}" for t in recent) if recent else "없음"

    print(f"  [Auto] 실행: {category} ({date_str})")

    user_msg = (
        f"**카테고리**: {category}\n"
        f"**오늘 날짜**: {date_str}\n\n"
        f"아래는 이미 발행된 포스트 제목입니다. 중복되지 않는 새로운 주제를 선택해 포스트를 JSON 형식으로 작성하세요:\n"
        f"{recent_text}\n\n"
        f"독자에게 실질적으로 도움이 되는 풍부한 예시와 데이터를 포함하세요."
    )

    MAX_SEO_RETRIES = 3
    seo_feedback = ""
    seo_score = 0

    for attempt in range(1, MAX_SEO_RETRIES + 1):
        full_msg = user_msg
        if seo_feedback:
            full_msg += f"\n\n**⚠ SEO 개선 필수사항 (이전 생성에서 누락)**:\n{seo_feedback}"

        result = call_ollama(model, SYSTEM_PROMPT, full_msg)
        if "error" in result:
            append_log({"id": str(uuid.uuid4())[:8], "schedule_id": schedule_id,
                        "category": category, "filename": None,
                        "timestamp": now.isoformat(), "ok": False, "error": result["error"]})
            return {"ok": False, "error": result["error"]}

        post_data = result["post"]
        markdown = result["markdown"]
        filename = result["filename"] or f"{date_str}-auto-{str(uuid.uuid4())[:6]}.md"
        if not re.match(r'^\d{4}-\d{2}-\d{2}-', filename):
            filename = f"{date_str}-{filename}"

        # SEO 검증
        seo = analyze_seo(post_data)
        seo_score = seo["score"]
        print(f"  [Auto] SEO 점수: {seo_score}점 (시도 {attempt}/{MAX_SEO_RETRIES})")

        if seo_score >= 100:
            break
        if attempt < MAX_SEO_RETRIES:
            seo_feedback = _build_seo_feedback(seo["checks"])
            print(f"  [Auto] SEO 미달 → 재생성 중...")

    # 교정 단계 (claude CLI)
    proofread_ok = False
    try:
        print(f"  [Auto] 교정 중 (Claude)...")
        pr = proofread_post(markdown, filename)
        if "error" not in pr and pr.get("changes"):
            markdown = pr["corrected"]
            proofread_ok = True
            print(f"  [Auto] 교정 완료: {len(pr['changes'])}건 수정")
        elif "error" in pr:
            print(f"  [Auto] 교정 건너뜀: {pr['error']}")
        else:
            proofread_ok = True
            print(f"  [Auto] 교정 완료: 수정 사항 없음")
    except Exception as e:
        print(f"  [Auto] 교정 건너뜀: {e}")

    os.makedirs(POSTS_DIR, exist_ok=True)
    dest = os.path.join(POSTS_DIR, filename)
    with open(dest, "w", encoding="utf-8", newline="\n") as f:
        f.write(markdown)
    print(f"  [Auto] 저장: {filename} (SEO: {seo_score}점)")

    git_result = git_deploy(f"[자동] {category} 포스트: {filename}")
    if git_result.get("ok"):
        print(f"  [Auto] Git 완료: {git_result.get('output','')}")
    else:
        print(f"  [Auto] Git 오류: {git_result.get('error','')}")

    log_entry = {
        "id": str(uuid.uuid4())[:8], "schedule_id": schedule_id,
        "category": category, "filename": filename,
        "timestamp": now.isoformat(),
        "ok": git_result.get("ok", False),
        "error": git_result.get("error", ""),
        "seo_score": seo_score,
        "proofread": proofread_ok,
    }
    append_log(log_entry)
    return {"ok": True, "filename": filename, "git": git_result}


# ──────────────────────────────────────────────
# 스케줄러 — 백그라운드 루프
# ──────────────────────────────────────────────

_scheduler_running = False


def _scheduler_loop():
    print("  [Scheduler] 시작")
    while _scheduler_running:
        now = datetime.now()
        cfg = load_config()
        changed = False
        for sch in cfg.get("schedules", []):
            if not sch.get("enabled", True):
                continue
            try:
                next_run = datetime.fromisoformat(sch.get("next_run", ""))
            except Exception:
                continue
            if now >= next_run:
                model = cfg.get("default_model", "qwen2.5:7b")
                threading.Thread(
                    target=run_auto_post,
                    args=(sch["id"], sch["category"], model),
                    daemon=True,
                ).start()
                sch["last_run"] = now.isoformat()
                sch["next_run"] = calc_next_run(sch, now)
                changed = True
                print(f"  [Scheduler] 실행: {sch['category']} → 다음: {sch['next_run']}")
        if changed:
            save_config(cfg)
        time.sleep(30)
    print("  [Scheduler] 종료")


def start_scheduler():
    global _scheduler_running
    if _scheduler_running:
        return
    _scheduler_running = True
    threading.Thread(target=_scheduler_loop, daemon=True).start()


def stop_scheduler():
    global _scheduler_running
    _scheduler_running = False


# ──────────────────────────────────────────────
# HTTP Handler
# ──────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        if args and len(args) >= 2 and not str(args[1]).startswith("2"):
            print(f"  [{args[1]}] {args[0]}")

    def send_json(self, status: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length))
        except Exception as e:
            self.send_json(400, {"error": f"요청 파싱 실패: {e}"})
            return

        if self.path == "/generate":
            print(f"  [생성] [{data.get('category','?')}] {data.get('topic','?')[:40]} ({data.get('model','?')})")
            result = generate_post(data)
            status = 400 if "error" in result else 200
            if "error" in result:
                print(f"  오류: {result['error']}")
            else:
                print(f"  완료: {result.get('filename','(파일명 없음)')}")
            self.send_json(status, result)

        elif self.path == "/edit":
            print(f"  [수정] {data.get('filename','?')} — {data.get('instruction','')[:40]} ({data.get('model','?')})")
            result = edit_post(data)
            status = 400 if "error" in result else 200
            if "error" in result:
                print(f"  오류: {result['error']}")
            else:
                print(f"  완료: {result.get('filename','')}")
            self.send_json(status, result)

        elif self.path == "/proofread":
            content = data.get("content", "")
            filename = data.get("filename", "")
            if not content:
                self.send_json(400, {"error": "content가 필요합니다."})
                return
            print(f"  [교정] {filename or '(내용)'}")
            result = proofread_post(content, filename)
            if "error" in result:
                print(f"  교정 오류: {result['error']}")
                self.send_json(400, result)
            else:
                n = len(result.get("changes", []))
                print(f"  교정 완료: {n}건 수정")
                self.send_json(200, result)

        elif self.path == "/proofread-all":
            print("  [전체 교정] 시작")
            results = []
            if not os.path.isdir(POSTS_DIR):
                self.send_json(200, {"results": []})
                return
            md_files = sorted(f for f in os.listdir(POSTS_DIR) if f.endswith(".md"))
            for i, fname in enumerate(md_files, 1):
                fpath = os.path.join(POSTS_DIR, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    original = f.read()
                print(f"  [{i}/{len(md_files)}] {fname}")
                pr = proofread_post(original, fname)
                if "error" in pr:
                    results.append({"filename": fname, "changes": [], "saved": False, "error": pr["error"]})
                    continue
                changes = pr.get("changes", [])
                corrected = pr.get("corrected", "")
                if changes and corrected and corrected.strip() != original.strip():
                    with open(fpath, "w", encoding="utf-8", newline="\n") as f:
                        f.write(corrected)
                    results.append({"filename": fname, "changes": changes, "saved": True})
                    print(f"    → {len(changes)}건 교정 저장")
                else:
                    results.append({"filename": fname, "changes": [], "saved": False})
            total_changed = sum(1 for r in results if r.get("saved"))
            print(f"  [전체 교정] 완료: {total_changed}/{len(md_files)}개 파일 수정")
            self.send_json(200, {"results": results})

        elif self.path == "/save-post":
            filename = data.get("filename", "")
            content = data.get("content", "")
            if not filename or not content:
                self.send_json(400, {"error": "filename과 content가 필요합니다."})
                return
            result = save_post(filename, content, is_draft=False)
            if "error" in result:
                print(f"  오류: {result['error']}")
                self.send_json(400, result)
            else:
                self.send_json(200, result)

        elif self.path == "/save-draft":
            filename = data.get("filename", "")
            content = data.get("content", "")
            if not filename or not content:
                self.send_json(400, {"error": "filename과 content가 필요합니다."})
                return
            result = save_post(filename, content, is_draft=True)
            if "error" in result:
                print(f"  오류: {result['error']}")
                self.send_json(400, result)
            else:
                self.send_json(200, result)

        elif self.path == "/publish-draft":
            filename = data.get("filename", "")
            if not filename:
                self.send_json(400, {"error": "filename이 필요합니다."})
                return
            print(f"  [발행] {filename}")
            result = publish_draft(filename)
            if "error" in result:
                self.send_json(400, result)
            else:
                self.send_json(200, result)

        elif self.path == "/delete-post":
            filename = data.get("filename", "")
            is_draft = bool(data.get("is_draft", False))
            if not filename:
                self.send_json(400, {"error": "filename이 필요합니다."})
                return
            print(f"  [삭제] {'_drafts' if is_draft else '_posts'}/{filename}")
            result = delete_post(filename, is_draft)
            if "error" in result:
                self.send_json(400, result)
            else:
                self.send_json(200, result)

        elif self.path == "/restore-history":
            backup_name = data.get("backup_name", "")
            if not backup_name:
                self.send_json(400, {"error": "backup_name이 필요합니다."})
                return
            print(f"  [복원] {backup_name}")
            result = restore_history(backup_name)
            if "error" in result:
                self.send_json(400, result)
            else:
                self.send_json(200, result)

        elif self.path == "/similarity-check":
            content = data.get("content", "")
            result = similarity_check(content)
            if result.get("similar_post"):
                print(f"  [유사도] {result['similar_post']} ({result['similarity']})")
            self.send_json(200, result)

        elif self.path == "/git-deploy":
            message = data.get("message", "").strip()
            if not message:
                self.send_json(400, {"error": "message가 필요합니다."})
                return
            print(f"  [Git] 배포: {message}")
            result = git_deploy(message)
            if "error" in result:
                print(f"  오류: {result['error']}")
                self.send_json(400, result)
            else:
                self.send_json(200, result)

        # ── 스케줄러 API ──
        elif self.path == "/api/schedules":
            cfg = load_config()
            sch = {
                "id":           str(uuid.uuid4())[:8],
                "category":     data.get("category", "투자 기초"),
                "frequency":    data.get("frequency", "weekly"),
                "day_of_week":  int(data.get("day_of_week", 0)),
                "day_of_month": int(data.get("day_of_month", 1)),
                "hour":         int(data.get("hour", 9)),
                "minute":       int(data.get("minute", 0)),
                "enabled":      bool(data.get("enabled", True)),
                "last_run":     None,
                "next_run":     None,
            }
            sch["next_run"] = calc_next_run(sch)
            cfg.setdefault("schedules", []).append(sch)
            save_config(cfg)
            print(f"  [Scheduler] 스케줄 추가: {sch['category']} / {sch['frequency']} → {sch['next_run']}")
            self.send_json(200, {"ok": True, "id": sch["id"], "next_run": sch["next_run"]})

        elif re.match(r'^/api/schedules/[^/]+/toggle$', self.path):
            sch_id = self.path.split("/")[3]
            cfg    = load_config()
            for s in cfg.get("schedules", []):
                if s["id"] == sch_id:
                    s["enabled"] = not s["enabled"]
                    if s["enabled"] and not s.get("next_run"):
                        s["next_run"] = calc_next_run(s)
                    save_config(cfg)
                    self.send_json(200, {"ok": True, "enabled": s["enabled"]})
                    return
            self.send_json(404, {"error": "스케줄을 찾을 수 없습니다."})

        elif self.path == "/api/run-now":
            category = data.get("category", "투자 기초")
            cfg      = load_config()
            model    = data.get("model") or cfg.get("default_model", "qwen2.5:7b")
            print(f"  [Scheduler] 즉시 실행: {category}")
            result   = run_auto_post("manual", category, model)
            self.send_json(200 if result.get("ok") else 400, result)

        elif self.path == "/api/config":
            cfg = load_config()
            if "default_model" in data:
                cfg["default_model"] = data["default_model"]
            save_config(cfg)
            self.send_json(200, {"ok": True})

        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        path  = self.path.split("?")[0]
        query = self.path[len(path) + 1:] if "?" in self.path else ""

        if path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))

        elif path == "/ollama-models":
            self.send_json(200, get_ollama_models())

        elif path == "/posts-list":
            self.send_json(200, get_posts_list())

        elif path == "/posts-info":
            self.send_json(200, get_posts_info())

        elif path == "/post-content":
            params = urllib.parse.parse_qs(query)
            filename = params.get("file", [""])[0]
            is_draft = params.get("draft", ["0"])[0] == "1"
            if not filename:
                self.send_json(400, {"error": "file 파라미터가 필요합니다."})
            else:
                self.send_json(200, get_post_content(filename, is_draft))

        elif path == "/history":
            self.send_json(200, get_history())

        # ── 스케줄러 GET ──
        elif path == "/api/schedules":
            cfg = load_config()
            self.send_json(200, {"schedules": cfg.get("schedules", []), "running": _scheduler_running})

        elif path == "/api/log":
            self.send_json(200, {"items": load_log()})

        elif path == "/api/config":
            cfg = load_config()
            self.send_json(200, {"default_model": cfg.get("default_model", "qwen2.5:7b")})

        else:
            self.send_response(404)
            self.end_headers()

    def do_DELETE(self):
        m = re.match(r'^/api/schedules/([^/]+)$', self.path.split("?")[0])
        if m:
            sch_id = m.group(1)
            cfg    = load_config()
            before = len(cfg.get("schedules", []))
            cfg["schedules"] = [s for s in cfg.get("schedules", []) if s["id"] != sch_id]
            if len(cfg["schedules"]) < before:
                save_config(cfg)
                win_task_removed = False
                if not cfg["schedules"]:
                    r = subprocess.run(
                        ["schtasks", "/delete", "/tn", "BlackRabbitLAB_AutoPost", "/f"],
                        capture_output=True
                    )
                    win_task_removed = r.returncode == 0
                    if win_task_removed:
                        print("  [Scheduler] Windows 작업 스케줄러 태스크 제거 완료")
                self.send_json(200, {"ok": True, "win_task_removed": win_task_removed})
            else:
                self.send_json(404, {"error": "스케줄을 찾을 수 없습니다."})
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


# ──────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────

def main():
    # 스케줄 next_run 재계산 (앱 재시작 후 만료된 항목 정리)
    cfg = load_config()
    changed = False
    for s in cfg.get("schedules", []):
        if s.get("enabled") and not s.get("next_run"):
            s["next_run"] = calc_next_run(s)
            changed = True
    if changed:
        save_config(cfg)

    start_scheduler()

    server = HTTPServer(("localhost", PORT), Handler)
    print(f"\n  BlackRabbit LAB — AI Post Maker v2 (Ollama)")
    print(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    posts_status = "✓ 존재" if os.path.isdir(POSTS_DIR) else "✗ 없음 (저장 시 자동 생성)"
    drafts_status = "✓ 존재" if os.path.isdir(DRAFTS_DIR) else "✗ 없음 (저장 시 자동 생성)"
    print(f"  서버 주소: http://localhost:{PORT}")
    print(f"  Ollama:   {OLLAMA_BASE}")
    print(f"  _posts/:  {POSTS_DIR}  [{posts_status}]")
    print(f"  _drafts/: {DRAFTS_DIR}  [{drafts_status}]")
    print(f"  .history: {HISTORY_DIR}")
    print(f"  종료: Ctrl+C\n")
    Timer(1.0, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        stop_scheduler()
        print("\n  서버를 종료합니다.")
        server.shutdown()


if __name__ == "__main__":
    main()
