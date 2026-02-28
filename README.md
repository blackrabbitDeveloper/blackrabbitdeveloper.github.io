# BlackRabbit LAB

개인 개발 프로젝트와 참고 자료를 공유하는 웹 사이트입니다.  
주식 알림 봇, 암호화폐 예측 등 **투자 참고용** 도구를 GitHub Pages에서 무료로 제공합니다.

- **사이트**: [https://blackrabbitdeveloper.github.io](https://blackrabbitdeveloper.github.io)

---

## 기술 스택

- **HTML** · **Tailwind CSS** (CDN) · **Vanilla JavaScript**
- Google Fonts (Inter), Supabase 스타일 다크 테마
- Google AdSense 적용

---

## 프로젝트 구조

```
├── index.html          # 메인 (소개, 프로젝트, 참고 자료)
├── privacy.html        # 개인정보처리방침
├── ads.txt             # AdSense 인증
├── css/
│   └── styles.css      # 커스텀 스타일 (스킵 링크 등)
├── js/
│   └── main.js         # 앵커 스무스 스크롤
├── src/
│   └── input.css       # Tailwind 소스 (선택적 빌드용)
├── tailwind.config.js  # Tailwind 설정
├── package.json        # npm 스크립트 (build 등)
└── README.md
```

---

## 로컬에서 보기

1. 저장소 클론 후 `index.html`을 브라우저에서 열거나  
2. 로컬 서버 사용 예: `npx serve .` 또는 `python -m http.server`

Tailwind는 CDN으로 로드되므로 별도 빌드 없이 동작합니다.

### CSS 빌드 (선택)

Node.js가 있다면 Tailwind로 CSS를 직접 빌드할 수 있습니다.

```bash
npm install
npm run build
```

생성된 `css/styles.css`를 사용하려면 HTML에서 Tailwind CDN 스크립트를 제거하면 됩니다.

---

## 링크된 프로젝트

| 프로젝트 | 설명 |
|----------|------|
| [Stock Notify](https://blackrabbitdeveloper.github.io/stock-notify/) | 주식 추천 봇 · 조건별 종목 목록, 참고용 |
| [Crypto Price Predictor](https://blackrabbitDeveloper.github.io/CryptoPricePredictor/) | 비트코인/이더리움 예측 봇 · 가격 시각화, 참고용 |

모든 도구는 **참고 목적**이며, 투자 결정은 사용자 책임입니다.

---

## 라이선스

© BlackRabbit LAB. All rights reserved.
