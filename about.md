---
layout: default
title: 소개
description: BlackRabbit LAB 소개 - STOCKER 미국 주식 리서치 자동화 시스템과 시장 분석 블로그
---

<div class="mx-auto max-w-3xl px-4 sm:px-6 pt-10 pb-20">

  <h1 class="text-3xl font-bold tracking-tight text-white sm:text-4xl mb-2">소개</h1>
  <p class="font-mono text-xs text-zinc-600 mb-10">BlackRabbit LAB · blackrabbitlab.site</p>

  <!-- What is -->
  <div class="rounded-xl border border-white/8 bg-[#111111] p-6 sm:p-8 mb-5">
    <h2 class="text-base font-semibold text-white mb-3">BlackRabbit LAB이란?</h2>
    <p class="text-sm leading-relaxed text-zinc-400">
      BlackRabbit LAB는 미국 주식 리서치 자동화 시스템 <strong class="text-zinc-200">STOCKER</strong>를 개발·운영하는 개인 개발 프로젝트입니다.
      이 블로그는 STOCKER의 포지션 현황, 누적 성과, 시장 분석 브리핑을 기록하고 공유하는 공간입니다.
    </p>
    <p class="mt-3 text-sm leading-relaxed text-zinc-400">
      모든 콘텐츠는 교육 및 정보 제공 목적이며, 투자 자문이 아닙니다.
    </p>
  </div>

  <!-- STOCKER 4대 기능 -->
  <div class="rounded-xl border border-brand/20 bg-brand/4 p-6 sm:p-8 mb-5">
    <div class="mb-4 flex items-center gap-2">
      <span class="relative flex h-1.5 w-1.5">
        <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand opacity-75"></span>
        <span class="relative inline-flex h-1.5 w-1.5 rounded-full bg-brand"></span>
      </span>
      <h2 class="font-mono text-xs font-medium text-brand">STOCKER — 4대 분석 축</h2>
    </div>

    <div class="grid gap-3 sm:grid-cols-2">
      <div class="rounded-lg bg-white/4 p-4">
        <p class="font-mono text-xs text-brand mb-2">01 · 재무 분석</p>
        <p class="text-xs leading-relaxed text-zinc-400">PER, ROE, 영업이익률 필터로 펀더멘털이 검증된 종목만 선별합니다.</p>
      </div>
      <div class="rounded-lg bg-white/4 p-4">
        <p class="font-mono text-xs text-brand mb-2">02 · 기술적 분석</p>
        <p class="text-xs leading-relaxed text-zinc-400">RSI, MACD, 볼린저 밴드를 활용해 매수·매도 신호를 감지합니다.</p>
      </div>
      <div class="rounded-lg bg-white/4 p-4">
        <p class="font-mono text-xs text-brand mb-2">03 · 멀티 타임프레임</p>
        <p class="text-xs leading-relaxed text-zinc-400">월봉·주봉·일봉 복합 분석으로 단기 노이즈를 걸러내고 추세를 파악합니다.</p>
      </div>
      <div class="rounded-lg bg-white/4 p-4">
        <p class="font-mono text-xs text-brand mb-2">04 · 자기학습</p>
        <p class="text-xs leading-relaxed text-zinc-400">시장 레짐을 감지하고, 백테스트로 파라미터를 자동 최적화합니다. 5% 이상 개선 시에만 채택해 과적합을 방지합니다.</p>
      </div>
    </div>
  </div>

  <!-- 리스크 관리 -->
  <div class="rounded-xl border border-white/8 bg-[#111111] p-6 sm:p-8 mb-5">
    <h2 class="text-base font-semibold text-white mb-4">리스크 관리 시스템</h2>
    <ul class="space-y-2.5">
      <li class="flex items-start gap-3">
        <span class="font-mono text-xs text-brand mt-0.5 flex-shrink-0">손절</span>
        <p class="text-xs text-zinc-400 leading-relaxed">ATR 기반 동적 Stop Loss 설정</p>
      </li>
      <li class="flex items-start gap-3">
        <span class="font-mono text-xs text-brand mt-0.5 flex-shrink-0">익절</span>
        <p class="text-xs text-zinc-400 leading-relaxed">50% 트레일링 / 100% 부분 청산 혼합 전략</p>
      </li>
      <li class="flex items-start gap-3">
        <span class="font-mono text-xs text-brand mt-0.5 flex-shrink-0">트레일</span>
        <p class="text-xs text-zinc-400 leading-relaxed">수익 발생 시 손절선 자동 상향 (트레일링 스탑)</p>
      </li>
      <li class="flex items-start gap-3">
        <span class="font-mono text-xs text-brand mt-0.5 flex-shrink-0">기간</span>
        <p class="text-xs text-zinc-400 leading-relaxed">최대 보유 기간 초과 시 자동 청산</p>
      </li>
    </ul>
  </div>

  <!-- 자동화 스케줄 -->
  <div class="rounded-xl border border-white/8 bg-[#111111] p-6 sm:p-8 mb-5">
    <h2 class="text-base font-semibold text-white mb-4">자동화 스케줄</h2>
    <div class="space-y-2.5">
      <div class="flex items-center justify-between rounded-lg bg-white/3 px-4 py-2.5">
        <span class="text-xs text-zinc-400">포지션 업데이트</span>
        <span class="font-mono text-xs text-brand">평일 KST 06:30</span>
      </div>
      <div class="flex items-center justify-between rounded-lg bg-white/3 px-4 py-2.5">
        <span class="text-xs text-zinc-400">주간 리포트</span>
        <span class="font-mono text-xs text-brand">매주 일요일 KST 18:00</span>
      </div>
      <div class="flex items-center justify-between rounded-lg bg-white/3 px-4 py-2.5">
        <span class="text-xs text-zinc-400">자기학습 실행</span>
        <span class="font-mono text-xs text-brand">월 1회 (첫째 일요일)</span>
      </div>
    </div>
  </div>

  <!-- 블로그 카테고리 -->
  <div class="rounded-xl border border-white/8 bg-[#111111] p-6 sm:p-8 mb-5">
    <h2 class="text-base font-semibold text-white mb-4">블로그 주제</h2>
    <div class="flex flex-wrap gap-2">
      <span class="rounded-sm bg-brand/10 px-2.5 py-1 font-mono text-xs text-brand">시장분석</span>
      <span class="rounded-sm bg-brand/10 px-2.5 py-1 font-mono text-xs text-brand">포지션현황</span>
      <span class="rounded-sm bg-brand/10 px-2.5 py-1 font-mono text-xs text-brand">주간리포트</span>
      <span class="rounded-sm bg-brand/10 px-2.5 py-1 font-mono text-xs text-brand">전략소개</span>
      <span class="rounded-sm bg-brand/10 px-2.5 py-1 font-mono text-xs text-brand">자기학습</span>
    </div>
  </div>

  <!-- Disclaimer -->
  <div class="rounded-xl border border-white/8 bg-[#111111] p-5 mb-8">
    <p class="font-mono text-xs leading-relaxed text-zinc-600">
      ⚠️ 이 사이트의 모든 콘텐츠는 교육 및 정보 제공 목적으로만 작성됩니다. 투자 자문이 아니며, 모든 투자 결정은 본인의 판단과 책임 하에 진행하시기 바랍니다. STOCKER가 제공하는 데이터 및 신호는 과거 데이터에 기반하며, 미래 수익을 보장하지 않습니다.
    </p>
  </div>

  <!-- CTA -->
  <div class="flex gap-3">
    <a href="https://blackrabbitlab.site" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-2 rounded-lg bg-brand px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-brand/90">
      STOCKER 바로가기 ↗
    </a>
    <a href="/" class="inline-flex items-center gap-2 rounded-lg border border-white/10 px-4 py-2.5 text-sm font-medium text-zinc-300 transition hover:border-white/20 hover:text-white">
      블로그 보기
    </a>
  </div>

</div>
