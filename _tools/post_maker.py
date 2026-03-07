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
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Timer

PORT = 8765
OLLAMA_BASE = "http://localhost:11434"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
POSTS_DIR = os.path.normpath(os.path.join(PROJECT_ROOT, "_posts"))
DRAFTS_DIR = os.path.normpath(os.path.join(PROJECT_ROOT, "_drafts"))
HISTORY_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, ".history"))

# ──────────────────────────────────────────────
# System Prompts
# ──────────────────────────────────────────────

SYSTEM_PROMPT = """당신은 투자 정보·경제 교육 블로그 'BlackRabbit LAB'의 전문 작가입니다.

## 블로그 정보
- 블로그: https://blackrabbitdeveloper.github.io
- 성격: 주식·ETF·경제 개념을 초중급 투자자도 이해할 수 있도록 쉽고 정확하게 설명하는 교육 블로그
- 독자층: 투자에 관심 있는 일반인, 경제 공부를 시작한 직장인, 재테크 입문자

## 카테고리별 가이드라인
- **시장분석**: 1500~2500자, 최근 시장 동향·지수·환율·금리 등을 데이터 기반으로 분석
- **투자 기초**: 2000~3500자, PER·ROE·배당·분산투자 등 주식 투자 핵심 개념을 쉽게 설명
- **경제 공부**: 2000~3500자, 거시경제·금리·인플레이션·GDP 등 경제 원리 해설
- **ETF·펀드**: 1500~2500자, ETF 구조·종류·투자 방법 및 펀드 비교
- **재테크**: 1500~2500자, 절세·적금·복리·포트폴리오 구성 등 실용적 자산 관리 팁
- **뉴스 해설**: 1000~2000자, 최신 경제·금융 뉴스를 배경 지식과 함께 해설
- **기타**: 1000~2000자, 공지·에세이·도서 추천 등

## Jekyll Front Matter 규칙
포스트 맨 앞에 반드시 아래 형식을 코드 블록(```) 없이 그대로 출력하세요.
코드 펜스(```yaml 등)로 감싸면 Jekyll이 인식하지 못합니다.

---
layout: post
title: "제목"
date: YYYY-MM-DD
categories: [카테고리]
tags: [투자, 경제, 재테크]
description: "SEO 설명 (150자 이내)"
---

## 금지 표현
- "주식 추천" → "참고 지표", "분석 결과", "스크리닝 조건" 등으로 대체
- "확실한 수익", "수익 보장" → "역사적 데이터 기준", "백테스트 결과" 등으로 대체
- 특정 종목 매수·매도 직접 권유 금지

## 면책 고지
포스트 마지막에 다음 문구를 반드시 포함:
> ⚠️ **면책 고지**: 본 포스트는 정보 제공 목적으로 작성되었으며, 투자 권유가 아닙니다. 모든 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다.

## 작성 스타일
- 전문 용어는 반드시 괄호로 쉬운 설명 추가 (예: PER(주가수익비율))
- 실제 수치·사례·비교표를 적극 활용해 이해를 도움
- 마크다운 헤더(##, ###), 표, 인용문, 번호 목록을 구조적으로 사용
- 독자가 '다음에도 읽고 싶은' 블로그가 되도록 마무리에 핵심 요약 포함

## 출력 형식 (반드시 준수)
1. --- 로 시작하는 Jekyll front matter (코드 블록 없이 그대로)
2. 포스트 본문 (마크다운)
3. 면책 고지
4. 마지막 줄: FILENAME_SUGGESTION: YYYY-MM-DD-english-slug.md (영문 소문자, 하이픈 구분)

절대 하지 말 것: front matter를 ```yaml ... ``` 로 감싸지 마세요.
파일명은 반드시 영문으로 제안하세요. 한글 파일명은 Jekyll sitemap 파싱 오류를 유발합니다."""

EDIT_SYSTEM_PROMPT = """당신은 투자 정보·경제 교육 블로그 'BlackRabbit LAB'의 포스트를 수정하는 편집자입니다.

## 수정 규칙
- 사용자의 수정 지시를 정확히 반영하세요.
- 지시하지 않은 부분은 원문을 최대한 유지하세요.
- Jekyll front matter(---)는 코드 블록(```) 없이 그대로 출력하세요.
- 파일명(date, title slug)은 변경하지 마세요. 단, 제목이 바뀌면 title 필드만 수정하세요.

## 금지 표현 (원문에 있어도 수정)
- "주식 추천" → "참고 지표", "분석 결과", "스크리닝 조건"
- "확실한 수익", "수익 보장" → "역사적 데이터 기준", "백테스트 결과"
- 특정 종목 매수·매도 직접 권유 표현

## 면책 고지
포스트 마지막에 항상 포함:
> ⚠️ **면책 고지**: 본 포스트는 정보 제공 목적으로 작성되었으며, 투자 권유가 아닙니다. 모든 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다.

## 출력 형식
수정된 포스트 전체를 출력하세요 (front matter 포함).
마지막 줄에 원본 파일명을 그대로: `FILENAME_SUGGESTION: 원본파일명.md`"""

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
    <div class="text-2xl font-bold mb-1"><span class="brand">BlackRabbit</span> LAB</div>
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
  <div class="flex gap-1 mb-0">
    <button class="mode-tab active" id="modeTabCreate" onclick="switchMode('create')">새 포스트 생성</button>
    <button class="mode-tab" id="modeTabEdit" onclick="switchMode('edit')">포스트 수정</button>
    <button class="mode-tab" id="modeTabManage" onclick="switchMode('manage')">포스트 관리</button>
  </div>

  <!-- ══════════════════ 생성 모드 ══════════════════ -->
  <div id="createPanel" class="panel p-6 mb-6" style="border-radius:0 8px 8px 8px;">
    <div class="grid grid-cols-1 gap-5 md:grid-cols-2">
      <div class="md:col-span-2">
        <label class="block text-sm text-gray-400 mb-2">주제 <span class="text-red-400">*</span></label>
        <input type="text" id="topic" class="input-base" placeholder="예: 이번 주 코스피 변동성 급등과 STOCKER의 대응 전략">
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
        <option>기타</option>
      </select>
      <input type="text" id="manageSearch" class="input-base text-sm" style="width:180px;" placeholder="검색..." oninput="applyManageFilter()">
      <button onclick="loadManageList()" class="btn-secondary text-xs py-2 px-3">↺ 갱신</button>
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
  };

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
        const preferred = models.find(m => m.startsWith('qwen2.5') || m.startsWith('qwen'));
        if (preferred) select.value = preferred;
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
    ['create', 'edit', 'manage'].forEach(function(m) {
      document.getElementById(m + 'Panel').classList.toggle('hidden', m !== mode);
      const tabId = 'modeTab' + m.charAt(0).toUpperCase() + m.slice(1);
      document.getElementById(tabId).classList.toggle('active', m === mode);
    });
    document.getElementById('outputPanel').classList.add('hidden');
    if (mode === 'edit') loadPostsList();
    if (mode === 'manage') loadManageList();
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
    setLoading('generate', true);
    document.getElementById('seoPanel').classList.add('hidden');
    try {
      const res = await fetch('/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model, topic, category, postDate, stockerData, extraContext })
      });
      const data = await res.json();
      if (!res.ok || data.error) { showToast(data.error || '생성 실패.', 'error'); return; }
      generatedMarkdown = data.content;
      suggestedFilename = data.filename || '';
      renderOutput('생성 결과');
      showToast('포스트가 생성되었습니다!', 'success');
      // 초안 자동 저장
      if (asDraft && suggestedFilename) {
        const ok = await doSaveDraft(suggestedFilename, generatedMarkdown);
        if (ok) showToast('초안 저장 완료: _drafts/' + suggestedFilename, 'success');
      }
      // 유사도 검사 + SEO 분석 자동 실행
      runSeoAndSimilarity(generatedMarkdown, suggestedFilename);
    } catch(e) {
      showToast('서버 오류: ' + e.message, 'error');
    } finally {
      setLoading('generate', false);
    }
  }

  async function runSeoAndSimilarity(content, filename) {
    let similarPost = null;
    try {
      const res = await fetch('/similarity-check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content })
      });
      const data = await res.json();
      similarPost = data.similar_post || null;
    } catch(e) { /* 무시 */ }
    const result = analyzeSEO(content, filename, similarPost);
    renderSEO(result.checks, result.score);
  }

  // ═══════════════════════════════
  // SEO 분석
  // ═══════════════════════════════
  function analyzeSEO(content, filename, similarPost) {
    const checks = [];
    let score = 0;

    // Front matter 파싱
    const titleM = content.match(/^title:\s*["']?(.+?)["']?\s*$/m);
    const descM = content.match(/^description:\s*["']?(.+?)["']?\s*$/m);
    const catM = content.match(/^categories:\s*\[(.+?)\]/m);

    const title = titleM ? titleM[1].trim() : '';
    const desc = descM ? descM[1].trim() : '';
    const cats = catM ? catM[1].trim() : '';

    // 제목 길이
    const tLen = title.length;
    if (tLen >= 20 && tLen <= 60) { checks.push({ ok: true, msg: '제목 길이 양호 (' + tLen + '자)' }); score += 20; }
    else if (tLen > 0) { checks.push({ ok: 'warn', msg: '제목 길이 주의 (' + tLen + '자, 권장 20-60자)' }); score += 10; }
    else { checks.push({ ok: false, msg: '제목 없음 (front matter title 필드 확인)' }); }

    // description 길이
    const dLen = desc.length;
    if (dLen >= 50 && dLen <= 150) { checks.push({ ok: true, msg: '설명 길이 양호 (' + dLen + '자)' }); score += 20; }
    else if (dLen > 0) { checks.push({ ok: 'warn', msg: '설명 길이 주의 (' + dLen + '자, 권장 50-150자)' }); score += 10; }
    else { checks.push({ ok: false, msg: '설명(description) 없음' }); }

    // 카테고리
    if (cats) { checks.push({ ok: true, msg: '카테고리 있음: [' + cats + ']' }); score += 15; }
    else { checks.push({ ok: false, msg: '카테고리 없음' }); }

    // 금지 표현
    const banned = ['주식 추천', '확실한 수익', '수익 보장', '투자 권유합니다'];
    const found = banned.filter(function(b) { return content.includes(b); });
    if (found.length === 0) { checks.push({ ok: true, msg: '금지 표현 없음' }); score += 15; }
    else { checks.push({ ok: false, msg: '금지 표현 발견: ' + found.join(', ') }); }

    // 면책 고지
    if (content.includes('면책 고지')) { checks.push({ ok: true, msg: '면책 고지 포함' }); score += 15; }
    else { checks.push({ ok: false, msg: '면책 고지 없음 (포스트 하단에 추가하세요)' }); }

    // 파일명 영문
    if (!filename) { checks.push({ ok: 'warn', msg: '파일명 미정' }); score += 5; }
    else if (/^[a-z0-9\-_.]+$/i.test(filename)) { checks.push({ ok: true, msg: '파일명 영문 OK: ' + filename }); score += 15; }
    else { checks.push({ ok: false, msg: '파일명에 한글 포함 (Jekyll sitemap 오류 위험): ' + filename }); }

    // 중복
    if (similarPost) {
      checks.push({ ok: false, msg: '유사 포스트 발견: ' + similarPost + ' (내용 중복 가능성 있음)' });
    } else {
      checks.push({ ok: true, msg: '중복 포스트 없음' });
    }

    return { checks, score: Math.min(100, score) };
  }

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
      generatedMarkdown = data.content;
      suggestedFilename = data.filename || currentEditFilename || '';
      document.getElementById('editContent').value = generatedMarkdown;
      renderOutput('AI 수정 결과');
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
    if (ok) document.getElementById('saveAsEditRow').classList.add('hidden');
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

  function setLoading(mode, loading) {
    if (mode === 'generate') {
      document.getElementById('generateBtn').disabled = loading;
      document.getElementById('generateBtnText').textContent = loading ? '생성 중...' : 'AI 포스트 생성';
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
            cwd=PROJECT_ROOT, check=True, capture_output=True, text=True
        )
        # git commit
        commit = subprocess.run(
            [git, 'commit', '-m', message],
            cwd=PROJECT_ROOT, capture_output=True, text=True
        )
        commit_out = commit.stdout.strip()
        if commit.returncode != 0:
            if 'nothing to commit' in commit_out or 'nothing to commit' in commit.stderr:
                return {'error': '커밋할 변경 사항이 없습니다. 먼저 파일을 저장하세요.'}
            return {'error': commit.stderr or commit_out or 'commit 실패'}
        # git push
        push = subprocess.run(
            [git, 'push'],
            cwd=PROJECT_ROOT, capture_output=True, text=True
        )
        if push.returncode != 0:
            return {'error': push.stderr or push.stdout or 'push 실패'}
        output = commit_out
        if push.stdout.strip():
            output += '\n' + push.stdout.strip()
        print(f"  Git 배포 완료: {message}")
        return {'ok': True, 'output': output or '배포 완료'}
    except subprocess.CalledProcessError as e:
        return {'error': e.stderr or str(e)}
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
            return {"models": models}
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
        return {"ok": True, "path": path, "filename": safe_name, "is_draft": is_draft}
    except PermissionError:
        return {"error": f"파일 쓰기 권한이 없습니다: {path}"}
    except Exception as e:
        return {"error": f"저장 실패: {e}"}


def clean_frontmatter(content: str) -> str:
    """AI가 front matter 앞뒤에 붙이는 ```yaml 코드펜스를 제거합니다."""
    content = content.strip()
    content = re.sub(r'^```(?:yaml|yml)?\s*\n(---)', r'\1', content)
    content = re.sub(r'(\n---\n)\s*```\s*\n', r'\1\n', content)
    content = re.sub(r'^```\s*\n(---)', r'\1', content)
    return content


def call_ollama(model: str, system: str, user: str) -> dict:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"num_predict": 4096},
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read())
            content = result.get("message", {}).get("content", "")
        if not content:
            return {"error": "모델에서 응답이 없습니다."}
        content = clean_frontmatter(content)
        filename = ""
        lines = content.strip().split("\n")
        for i, line in enumerate(lines):
            if line.strip().startswith("FILENAME_SUGGESTION:"):
                filename = line.replace("FILENAME_SUGGESTION:", "").strip()
                lines = [l for j, l in enumerate(lines) if j != i]
                content = "\n".join(lines).rstrip()
                break
        return {"content": content, "filename": filename}
    except urllib.error.URLError:
        return {"error": "Ollama 서버에 연결할 수 없습니다."}
    except Exception as e:
        return {"error": f"오류: {str(e)}"}


def generate_post(data: dict) -> dict:
    model = data.get("model", "qwen2.5:7b")
    topic = data.get("topic", "")
    category = data.get("category", "시장분석")
    post_date = data.get("postDate", "")
    stocker_data = data.get("stockerData", "")
    extra_context = data.get("extraContext", "")

    parts = [f"**주제**: {topic}", f"**카테고리**: {category}"]
    if post_date:
        parts.append(f"**날짜**: {post_date}")
    if stocker_data:
        parts.append(f"\n**STOCKER 데이터**:\n{stocker_data}")
    if extra_context:
        parts.append(f"\n**추가 컨텍스트**:\n{extra_context}")
    parts.append("\n위 정보를 바탕으로 BlackRabbit LAB 블로그 포스트를 작성해주세요.")

    return call_ollama(model, SYSTEM_PROMPT, "\n".join(parts))


def edit_post(data: dict) -> dict:
    model = data.get("model", "qwen2.5:7b")
    content = data.get("content", "")
    instruction = data.get("instruction", "")
    filename = data.get("filename", "post.md")

    user_msg = (
        f"## 원본 포스트\n\n{content}\n\n"
        f"## 수정 지시\n\n{instruction}\n\n"
        f"## 원본 파일명\n{filename}\n\n"
        "위 수정 지시에 따라 포스트를 수정해주세요. "
        "수정된 포스트 전체를 출력하고, 마지막 줄에 FILENAME_SUGGESTION을 포함하세요."
    )
    return call_ollama(model, EDIT_SYSTEM_PROMPT, user_msg)


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

    def do_GET(self):
        path = self.path.split("?")[0]
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

        else:
            self.send_response(404)
            self.end_headers()

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

        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


# ──────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────

def main():
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
        print("\n  서버를 종료합니다.")
        server.shutdown()


if __name__ == "__main__":
    main()
