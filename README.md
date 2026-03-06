# BlackRabbit LAB — 시장 분석 블로그

[STOCKER](https://blackrabbitlab.site) 미국 주식 리서치 자동화 시스템의 포지션 현황, 성과 분석, 시장 브리핑을 기록하는 Jekyll 블로그입니다.

- **블로그**: [https://blackrabbitdeveloper.github.io](https://blackrabbitdeveloper.github.io)
- **STOCKER 서비스**: [https://blackrabbitlab.site](https://blackrabbitlab.site)

> ⚠️ 모든 콘텐츠는 교육 및 정보 제공 목적이며 투자 자문이 아닙니다. 모든 투자 결정은 본인의 책임입니다.

---

## STOCKER란?

기술적 분석(RSI, MACD, 볼린저 밴드) + 재무 필터(PER, ROE, 영업이익률) + 멀티 타임프레임(월봉·주봉·일봉) + 자기학습 메커니즘을 결합한 미국 주식 리서치 자동화 플랫폼.

| 스케줄 | 주기 |
|---|---|
| 포지션 업데이트 | 평일 KST 06:30 |
| 주간 리포트 | 매주 일요일 KST 18:00 |
| 자기학습 | 월 1회 (첫째 일요일) |

---

## 기술 스택

- **Jekyll** (GitHub Pages 내장 빌드)
- **Tailwind CSS** (CDN + typography plugin)
- **Noto Sans KR · JetBrains Mono** (Google Fonts)
- Google AdSense

---

## 프로젝트 구조

```
├── _config.yml         # Jekyll 설정
├── _layouts/
│   ├── default.html    # 공통 레이아웃 (헤더/푸터)
│   ├── home.html       # 블로그 홈 (포스트 목록)
│   └── post.html       # 포스트 상세
├── _posts/             # 블로그 포스트 (Markdown)
├── index.html          # 블로그 홈
├── about.md            # 소개 (STOCKER 설명)
├── projects.html       # 프로젝트 목록
├── privacy.html        # 개인정보처리방침
├── css/styles.css      # 커스텀 스타일
├── js/main.js          # 스무스 스크롤
└── Gemfile             # GitHub Pages 의존성
```

---

## 로컬 실행

```bash
bundle install
bundle exec jekyll serve
# http://localhost:4000
```

---

## 새 포스트 작성

`_posts/YYYY-MM-DD-제목.md` 파일 생성:

```yaml
---
layout: post
title: "포스트 제목"
date: 2026-03-06
categories: [시장분석]
tags: [주식, 자동매매, BlackRabbitLAB]
---

본문 내용...
```

**카테고리 예시**: `시장분석` · `포지션현황` · `주간리포트` · `전략소개` · `자기학습`

---

## 연결된 프로젝트

| 프로젝트 | 설명 |
|---|---|
| [STOCKER](https://blackrabbitlab.site) | 미국 주식 리서치 자동화 시스템 (메인 서비스) |
| [Crypto Price Predictor](https://blackrabbitDeveloper.github.io/CryptoPricePredictor/) | 비트코인/이더리움 가격 시각화 · 참고용 |

---

## 라이선스

© BlackRabbit LAB. All rights reserved.
