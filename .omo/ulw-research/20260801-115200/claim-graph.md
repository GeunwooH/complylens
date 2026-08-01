# claim-graph.md — DeepSeek V4 저비용 AI 서비스

## verified-claims (Phase 4b 게이트 통과 — 합성이 인용 가능한 유일한 리스트)

| id | claim | status | evidence |
|---|---|---|---|
| C13 | deepseek-v4-flash 공식 가격: 캐시미스 입력 $0.14, 캐시히트 입력 $0.0028, 출력 $0.28 (1M 토큰) | supported | api-docs.deepseek.com/quick_start/pricing 페치 (2026-08-01, 리드 직접) |
| C14 | deepseek-v4-pro 공식 가격: 캐시미스 입력 $0.435, 캐시히트 입력 $0.003625, 출력 $0.87 (1M 토큰) — **현재 영구 가격 (4/24 출시 리스트 $1.74/$3.48의 75% 프로모가 5/22 영구화, Azure 채널은 여전히 $1.74/$3.48)** | supported | api-docs.deepseek.com 페치 (2026-08-01) + skeptic 레인 수정 (C56) |
| C15 | V4 컨텍스트 1M 토큰, 최대 출력 384K | supported | api-docs.deepseek.com 페치 (2026-08-01) |
| C16 | 캐시 히트 할인은 98% (Flash) ~ 99.2% (Pro) — "90% 할인" 주장은 오기재 | supported | C13/C14 수치 산출 (DERIVED, 공식 기준) |
| C17 | 피크/오프피크 정책: 피크시간 9-12시, 14-18시 (베이징 UTC+8) 2배 요금, 발효일 미정 | supported | api-docs.deepseek.com 페치 (2026-08-01) |
| C18 | 동시성 제한: Flash 2500 / Pro 500; Responses API는 flash만 지원 (pro는 2026-08 초), Anthropic 포맷 지원, 모델 버전 DeepSeek-V4-Flash-0731 | supported | api-docs.deepseek.com 페치 (2026-08-01) |
| C19 | V4는 MIT 라이선스 오픈웨이트: Pro 1.6T/49B active, Flash 284B/13B active, FP4+FP8 Mixed | **verified** | HF 모델 카드 페치 (deepseek-ai/DeepSeek-V4-Pro, 2026-08-01, 공식 docs 레인) |
| C20 | 오픈웨이트 배포처는 HuggingFace/ModelScope — github.com/deepseek-ai/DeepSeek-V4는 존재하지 않음 (org 36개 repo 전체 열거로 확인) | verified | 공식 docs 레인 (2026-08-01) |
| C21 | 기술 보고서: arxiv.org/abs/2606.19348, "DeepSeek-V4: Towards Highly Efficient Million-Token Context Intelligence" | verified | HF 모델 카드 (2026-08-01) |
| C22 | deepseek-chat & deepseek-reasoner는 2026-07-24 15:59 UTC로 폐지, deepseek-v4-flash로 라우팅 | verified | 공식 뉴스 news260424 (2026-08-01) |
| C23 | 동시성 제한 초과 시 HTTP 429, 용량 확장 요청은 무료 | verified | api-docs.deepseek.com/quick_start/rate_limit (2026-08-01) |
| C24 | 무료 티어는 공식 API 문서 어디에도 기재되지 않음 ("granted balance" 메커니즘만 존재) | verified (부재 확인) | 공식 docs 전수 조사 (2026-08-01, 공식 docs 레인) |
| C25 | 벤치마크(모델 카드 자체 보고): SWE Verified(Resolved) Pro-Max 80.6 / Flash-Max 79.0, Terminal Bench 2.0 67.9, LiveCodeBench 93.5, GPQA Diamond 90.1 (Pro-Max) — "SWE-bench 80.6%"는 정확히는 SWE Verified이며 vendor-reported | verified (자체 보고 확인) | HF 모델 카드 SHA 고정 permalink + arXiv abstract 교차 (2026-08-01, repo-dive 레인) |
| C26 | 오픈웨이트 repo에는 언어 목록 미기재 — 한국어 명시 없음 (멀티링궐은 벤치마크로 간접 확인) | verified (부재 확인) | HF 카드 전수 (2026-08-01, repo-dive 레인) |
| C27 | max_output_tokens는 오픈웨이트 repo 미기재 (API 사이드 제한 384K만 공식), 자체호스팅 GPU SKU/VRAM도 공식 미기재 (MP=8 참조 가이드만) | verified (부재 확인) | HF inference/README (2026-08-01, repo-dive 레인) |
| C28 | 아키텍처 확정: CSA+HCA 하이브리드 어텐션, mHC, Muon — 1M 컨텍스트에서 V3.2 대비 27% FLOPs, 10% KV cache | verified | HF 카드 + arXiv abstract 교차 (2026-08-01) |
| C29 | **U9 해소**: NY주 감사관 2025-12-02 감사 — DCWP의 LL144 집행 "ineffective" 판정, 컴플레인 75% 분실, DCWP는 위반 1건만 발견 vs 감사관 17건 발견 | verified | osc.ny.gov/state-agencies/audits/2025/12/02 + DLA Piper 요약 + paperclipped.de (2026-08-01, 리드 직접 검색) |
| C30 | LL144 패널티: 위반 시 $500~$1,500/일 (첫날 $500, 이후 $500-1,500) | verified | osc.ny.gov PDF + aicomplianceatlas (2026-08-01) |
| C31 | 규제 패치워크 확장: Illinois HB 3773 (2026-01-01 시행), Colorado SB 25B-004 (2026-06-30), California ADMT (2027-01-01 예정) — 감사 후 DCWP 집행 강화 예고 | verified | dlapiper.com, beancount.io, paperclipped.de (2026-08-01) |
| C32 | LL144 집행 실무: 고발 중심 (proactive 스윕 없음), 컴플라이언스는 소수 관행 (Cornell-Data&Society 2023 등), 6개월 연속 위반 시 패널티 잠재 노출 $90K~270K, EU AI Act 고위험 2026-08-02 시행으로 HR 벤더 감사 지원 확대 | partial (서비스 마케팅 소스 포함) | auditll144.com (2026-08-01, 리드 페치) — osc.ny.gov 감사(C29)와 방향 일치, 정량치는 교차 필요 |
| C33 | LL144 감사 핵심 작업 = 통계 계산 (selection rate, impact ratio, median-threshold scoring) + 독립성 요건 — LLM 의존도 낮은 작업 특성 | verified (규정 구조) | auditll144.com + osc.ny.gov PDF (2026-08-01) |
| C34 | 가격 모순 완전 해소: $1.74/$3.48은 4/24 출시가, 5/22부터 75% 할인이 영구화되어 $0.435/$0.87이 현재 정가 | verified | Simon Willison (2026-04-24) + HN 48236823 (2026-05-22) + 공식 docs 교차 (2026-08-01) |
| C35 | 환각이 주요 약점: AA-Omniscience 기준 Pro 94% / Flash 96% (최악 수준), Opus 4.8 36%, GLM-5.2 28% — RAG 에이전트 사용에서는 "acceptable" 후기도 존재 | partial (독립 벤치 + 일화) | HN 47988232, 48605020, 48242773 (커뮤니티 레인) |
| C36 | SWE-bench 현실 검증: NIST CAISI 독립 측정 V4 Pro 74% vs GPT-5.5 81%, Opus 4.6 79% — 자체 보고 80.6%와 gap (harness 의존 ±6pt) | **verified (NIST 원문)** | nist.gov/news-events/news/2026/05/caisi-evaluation-deepseek-v4-pro (2026-08-01, 리드 직접 페치) — CAISI는 시스템 프롬프트/scaffolding 차이로 낮게 나옴을 명시 |
| C41 | NIST CAISI 판정: V4 Pro 능력은 프론티어 대비 약 8개월 뒤처짐 (IRT Elo 800±28 vs GPT-5.5 1260±28, Opus 4.6 999±27, GPT-5.4 mini 749±46); 비공개 오염 없는 벤치에서 큰 격차 (PortBench 44% vs 78%, ARC-AGI-2 46% vs 79%, CTF 32% vs 71%); GPQA-Diamond 90%는 자체 보고 재현 성공 | verified (1차 출처) | NIST CAISI 원문 (2026-08-01, 리드 직접) |
| C42 | 비용 효율성: 유사 능력 모델(GPT-5.4 mini) 대비 7개 벤치 중 5개에서 저렴 (53% 저렴 ~ 41% 비쌈) — NIST 평가는 출시가($1.74/$3.48) 기준이므로 75% 인하 후엔 더 유리 | verified (1차 출처, 가격은 outdated) | NIST CAISI 원문 (2026-08-01) |
| C37 | 한국어 품질: "챗GPT 못지않게 자연스럽다", "GLM보다 한국어 이해 잘함" — 단, 한국어 평가는 블로거 ~4명 수준으로 표본 작음; 간혹 한국어 오타 | partial | Naver 블로그 3건 + Clien (커뮤니티 레인, 2026-08-01) |
| C38 | 비전 없음(이미지 입력 불가), first-party ToS가 상호작용 훈련 허용(ZDR 없음), first-party 검열 존재(third-party 경유로 완화), Flash 로컬 ~14 tok/s (DGX Spark) | verified (복수 커뮤니티 소스) | HN 49124170, 48012498, 48031824, 48522459 (커뮤니티 레인) |
| C39 | 에이전트 워크로드: OpenRouter 기준 V4 점유율 9%→18%, Flash가 에이전트 토큰 70% — "V4는 에이전트 워크로드에 충분한 첫 DeepSeek 모델" (OpenRouter 자체 평가) | verified (공급자 데이터) | openrouter.ai/blog/insights/deepseek-v4-adoption (2026-06-30) |
| C40 | "2M 토큰에 30¢" (HN 실사용), 한국 기업 보도 "100배 비용 폭탄" (에이전트 토큰 볼륨) — 단가 저렴해도 볼륨 관리 필요 | partial | HN 48070245, Naver aipostkoreayhd (커뮤니티 레인) |
| C43 | **U9 최종 판정 (idea-space 레인): 집행 실적 de minimis** — 2년간(2023-07~2025-06) AEDT 컴플레인 단 2건, 문서화된 패널티/제재 0건, nyc.gov 집행 페이지 404, 311 테스트 콜 75% 오연결; 감사관은 동일 32개 기업에서 위반 17건 발견 (DCWP 1건) | verified (1차 + 부재 확인) | osc.ny.gov 감사 2024-N-6 (2025-12-02) + 부재 검색 전수 (idea-space 레인, 2026-08-01) |
| C44 | 편향감사 시장 가격 하락 중: $2,500 (ll144audit.com) → $1,500 (aedtaudits.com, 2026-08-01 실측) — 40% 하락, 7개 이상 벤더 경쟁 | verified | 두 벤더 가격 페이지 실측 (idea-space 레인) |
| C45 | 감사 1건당 LLM 원가: Flash $0.022 / Pro $0.070 (100K 입력 + 30K 출력 가정) — 납품가($1,500-2,500)의 0.001-0.005%. 모든 후보 카테고리에서 LLM 비용은 납품가의 <1% | derived (공식 가격 기준) | idea-space 레인 계산 + 공식 가격 (2026-08-01) |
| C46 | "싼 토큰은 필요조건이지 충분조건 아님" — 바인딩 제약은 유통/신뢰/규제 자격/통합 깊이/도메인 전문성. 후보 7개 중 solo 실행 가능 + 지불의사 있는 건: 편향감사(다중관할), 수직 특화 지원 에이전트, 규제 컴플라이언스 문서 (조건부) | synthesis (idea-space 레인 판단) | idea-space 레인 (2026-08-01) |
| C47 | 단위 경제: 후보 4종(감사/번역/튜터링/콘텐츠) 모두 마진 분석 생존 — API 비용은 수익의 0.001~0.6%, 마진 위협 아님; 최악 민감도(피크 2x + 캐시 -20pp)도 마진 0.1pp 미만 변동 | derived (산술 검증 완료) | unit-economics 레인 (2026-08-01, 공식 가격 × ASSUMED 토큰 프로파일) |
| C48 | **반전 발견**: 입력-집약 워크로드(튜터링 80K 입력/5K 출력)에서 Gemini 2.5 Flash-Lite($0.10/$0.40)가 V4-Flash보다 5.9% 저렴 — "DeepSeek 최저가"는 워크로드 의존 | derived (MEASURED 가격 비교) | unit-economics 레인 — Gemini 가격은 ai.google.dev 직접 페치 (2026-08-01) |
| C49 | Flash vs Pro 선택이 벤더 선택보다 10~100배 중요 (Pro는 항상 3.1x 멀티플라이어); $50/월 절약 임계: Flash vs Gemini는 94K~342K 단위/월, Flash vs Pro는 1.7K~25K 단위/월 | derived | unit-economics 레인 (2026-08-01) |
| C50 | 진짜 마진 킬러는 서포트/인력 비용(수익의 1.3~8%) — 저가 볼륨($1-5/단위) 생존의 핵심은 API 벤더가 아니라 셀프서비스 자동화; 피크 2배 정책은 한국 기준 78% 트래픽 겹침(1.78x 유효)에도 논-이벤트; Gemini 배치 티어($0.05/$0.20) 50% 저렴 (DeepSeek엔 미공지) | derived + partial | unit-economics 레인 (2026-08-01) |
| C51 | LL144 패널티 스케줄 상세 (§ 6-81): 첫 위반 $375(디폴트 $500), 2차 $1,350($1,500), 3차+ $1,500 — 일별 누적 (30일 위반 = $15K~45K/AEDT) | verified (1차 규정) | codelibrary.amlegal.com NYC 규칙 (2026-08-01, browsing 레인) |
| C52 | 2026-08-01 현재까지 LL144 공개 집행 사례 0건 확정 — NYC.gov 검색 0건, DCWP 프레스릴리스 0건, OATH/판례 0건 (검색엔진 4개 + 법률 DB 전수); "2026 stricter enforcement phase"는 법률회사 예고일 뿐 실적 아님; 감사 2024-N-6 요약에 311 75% 수치는 없음(Employsome 인용 — PDF 미확보) | verified (부재 확인, 전수 검색) | browsing 레인 — Startpage 경유 OSC 발견, Google/Bing/DDG/Brave 차단 극복 (2026-08-01) |
| C53 | **skeptic 판정 1**: "싼 API = 기회" 전제 WEAKENED — 유통/신뢰/서포트/컴플라이언스/결제는 가격과 무관; MIT 오픈웨이트라 가격 모트 제로; 기회는 유통+신뢰+규제 동력에서 오고 싼맛은 마진을 안 죽일 뿐 | red-team verdict | skeptic 레인 (2026-08-01) |
| C54 | **skeptic 판정 2a**: DCWP 집행 기반 수요 REFUTED(why-now로) — DCWP가 감사 권고 3개 중 3개 거절(컴플레인 원인 조사, proactive 식별, 17건 조사), 공식 입장 "광범위한 위반 증거 없다" + 자원 제약; "2026 강화"는 법률회사 마케팅 | red-team verdict (1차 증거 기반) | skeptic 레인 (2026-08-01) |
| C55 | **skeptic 판정 2b**: 편향감사에 LLM 불필요 REFUTED(LLM 각도) — 감사는 EEOC UGESP 통계(50년 프레임워크) + 독립 서명 + 법률 지식; 양 벤더 모두 방법론에 LLM 언급 없음; DeepSeek 연결은 근거 약함 | red-team verdict | skeptic 레인 (2026-08-01) |
| C56 | **skeptic 판정 3a**: C14 프레이밍 수정 — $1.74/$3.48은 "오기재"가 아니라 진짜 출시 리스트 가격(4/24), 75% 프로모가 5/22 영구화; Azure AI Foundry는 여전히 $1.74/$3.48 (채널 차이); 가격이 프로모 결정으로 설정됨 → 원복 가능성 (최악 $0.435→$1.74×2 = 8배) | red-team verdict (사실적 수정) | skeptic 레인 + tokenmix/aireiter/basedai (2026-08-01) |
| C57 | **skeptic 판정 4**: SWE-bench Verified는 OpenAI가 2026-02-23 퇴역 — 문제의 59.4% 결함, 프론티어 전부 오염(태스크 ID만으로 gold patch 재생산); 진짜 신호는 SWE-bench Pro (프론티어 23~58%, V4 Pro 수치 비공개); "80.6%"는 은퇴한 오염 벤치의 마케팅 숫자 | red-team verdict (5+ 2차 소스) | skeptic 레인 (2026-08-01) |
| C58 | **skeptic 판정 6**: 단위 경제 WEAKENED — 캐시 히트 낙관 (감사 워크로드는 캐시 미스 위주, 현실적 10-20%), USD 가격은 CNY 페그(~6.9)라 환율+지정학 리스크 미모델링, 피크 정책 미프라이싱; 한국 대상 서비스는 근무시간 2x | red-team verdict | skeptic 레인 (2026-08-01) |
| C59 | SWE-bench 80.6%는 DeepSeek 자체 하네스(미공개) 기준 — 공식 swebench.com 리더보드 최고 79.2%, V4는 리더보드 부재, 독립 재현 0건; 자체 하네스가 오피셜 대비 1~2pp 높게 나오는 경향 | verified (독립 리더보드 + 자체 보고) | swebench.com + HF 카드 (2026-08-01, v4-benchmarks 레인) |
| C60 | 독립 성능: AA Intelligence Index 44 (#6/101, 중앙값 25), LMArena Text Elo 1457±4 (탑10 컷오프 1486 미만), WebDev Flash-high #7 (1586) — "프론티어 미만, Sonnet급"; 강점 LiveCodeBench 93.5/Codeforces 3206 (둘 다 최고), 약점 Apex 38.3 vs 60.9, HLE 37.7, MRCR 1M 83.5 vs 92.9, 비멀티모달 | verified (독립 평가) | artificialanalysis.ai + lmarena.ai (2026-08-01, v4-benchmarks 레인) |
| C61 | **한국어 품질: 완전 미검증** — 한국어 벤치마크(KMMLU 등) 어디에도 없음, LMArena 한국어 카테고리 부재, 한국 커뮤니티 검증 데이터 없음 (JS 렌더 차단); 논문 자체 "SOTA 대비 3~6개월 뒤처짐" 인정 | verified (부재 확인) | v4-benchmarks 레인 (2026-08-01) |
| C62 | 최저가 판정: 리스트 가격 기준 V4-Flash는 Gemini 3.5 Flash-Lite($0.10/$0.40)와 근소한 동률 (3:1 입력:출력 워크로드에서 동일 $0.70/4M); OpenRouter 경유(StreamLake/DeepInfra 프로모 $0.0896/$0.1792)로는 확실한 최저가 | verified (공식 가격 페이지 실측) | competitor 레인 (2026-08-01) — ai.google.dev, openrouter.ai 등 공식/공급자 페이지 |
| C63 | **V4-Flash의 최대 구조적 이점: 추론 출력 멀티플라이어 없음** — reasoning 활성화해도 출력 $0.28/M 동일; 경쟁사 대비 7~50배 (Kimi K3 ¥100/M≈$13.89, o4-mini $4.40, gpt-5-mini extended $2.00); 캐시 히트 2% = 시장 최저 (경쟁사 10%, Groq 50%) | verified | competitor 레인 (2026-08-01) |
| C64 | Gemini 가격 모순 해소: $0.30/$2.50은 "3.5 Flash-Lite"가 아니라 2.5 Flash 가격 — Flash-Lite 공식은 $0.10/$0.40; Groq $0.037은 캐시드 가격(표준 $0.075); MiMo v2.5가 V4-Flash와 동일 가격으로 신규 진입; Zhipu GLM-4.7-Flash 완전 무료(프로모) | verified | competitor 레인 (2026-08-01) |
| C65 | **한국 시장 구조적 NO-GO (한국어 사용자 대상)**: V4 한국어 벤치마크 제로 (중국어/영어 중심), PIPA 28-8 중국 이전 별도 동의, 정부 기관 DeepSeek 차단 선례, PIPC 실태점검, 한국 리셀러/릴레이 부재 | verified (1차+법률) | kr-market 레인 (2026-08-01) — shiftee.io, lawtimes, tech42, ZDNet 등 |
| C66 | 국내 대안: K-ExaOne 2.0 (2026-07-31 출시, 750B, 한국어 99.8점, MIT 오픈소스, 정부 지원), HyperCLOVA X (2,000+ 기관, 토큰+구독), Kakao Kanana (한국어 토큰 40% 절감) — DeepSeek 원가 우위를 상쇄 | verified | kr-market 레인 (2026-08-01) |
| C67 | AI 기본법 2026-01-22 시행 (1년 계도): 투명성 의무(과태료 최대 3,000만원), 고영향 AI 사전확인/영향평가, 국내 대리인 지정(연 매출 1조/100억 또는 일일 한국 사용자 100만) — API 이용사업자 면제 조항 있으나 DeepSeek 자체 컴플라이언스 불확실 | verified (법률 분석) | lawtimes + danipent (kr-market 레인) |
| C68 | 한국 결제 관행: per-seat SaaS 죽음 확정 (Shiftee 2,000원/인/월, 정부 보조금 포함), 하이브리드 과금 95% (사용량 91.3% + 구독 71.3%), 무료 온보딩이 기본 (Naver/Kakao 5,000만 무료), AI 비용 폭발 인식 (200만→800만원/월 사례) | verified | tech42 + shiftee (kr-market 레인) |
| C69 | 한국 시장 유일 생존 경로: 자체호스팅 V4 백엔드 (비-PII, 비한국어 워크로드) — 단 K-ExaOne 2.0도 MIT 오픈소스로 경쟁; 엔터프라이즈 프로젝트는 국내 모델 필수 | synthesis (kr-market 판단) | kr-market 레인 (2026-08-01) |
| C70 | 안정성: 자체 보고 99.90% uptime (V4 API, 2026-05~08), SLA 없음 (ToS "AS IS"), 문서화된 장애 2025-01 다일/2026-03 7h13m/2026-07 검색 | verified (1차 상태 페이지 + 보도) | risks 레인 (2026-08-01) — status.deepseek.com (Jina 경유), Reuters |
| C71 | 프라이버시: PRC 서버 확정, 컨슈머는 탈식별 훈련(옵트아웃 토글), **API ToS는 훈련/보존에 침묵 — no-training 약속 없음 → DPA 필요**; 볼케이노(ByteDance) 텔레메트리 이전, PIPC 처벌 선례(2025-02), 한국 대리인 법무법인 세종 지정 | verified (1차 정책 문서) | risks 레인 — cdn.deepseek.com/policies, Open Platform ToS (2026-08-01) |
| C72 | **락인 낮음 확정**: MIT 오픈웨이트 코모디티화 — OpenRouter 10+ 호스트 (StreamLake $0.0896, DeepInfra $0.09, DigitalOcean $0.112 등 DeepSeek 직판보다 35% 저렴), Together AI가 V4 Pro 미국 호스팅, OpenAI/Anthropic 호환 = 교체 비용 낮음 | verified (OpenRouter API 실측) | risks 레인 (2026-08-01) |
| C73 | 자체호스팅: 2×H200 최소 / 4-8×H100 프로덕션 (~$1,800/월), 고이용률 시 $0.03~0.10/1M 출력 vs API $0.28 — 손익분기 수십억 토큰/월 — 비용 플레이가 아니라 데이터 주권/연속성 보험 | derived (risks 레인 추정) | risks 레인 (2026-08-01) |
| C74 | 지정학/계약: PRC 법 + 항저우 법원, 수출통제 책임은 고객, 책임 상한 = 12개월 지출, 일방적 가격/약관 변경 허용(7일 통지), 호주/한국 정부 기기 금지, 미국 금지 법안 제안(법 아님) | verified (ToS 원문 + 보도) | risks 레인 (2026-08-01) |
| C75 | **리스크 판정**: 진지한 서비스 구축 가능 — 단, "모델에 구축하되 벤더에 구축하지 마라": 멀티프로바이더 라우팅 + 규제 데이터는 비-PRC 호스트로 분리 + 자체호스팅 폴백 + 자체 레이어 SLA + 비-DeepSeek 모델 스와프 가능 | red-team verdict | risks 레인 (2026-08-01) |
| C76 | **C43/C52 갱신 (skeptic 검증 → 다중 소스 확인)**: "집행 0건" 전제는 2025 Q4 이전 스냅샷 — 최초 벌금이 2025 Q4~2026 초 부과 (regulome "First Fines Issued", paperclipped "First Real Fines Hit in 2026", nyc144euaiact), DCWP가 2026-01부터 proactive 조사 전환, NY Comptroller 감사(2025-12-02) "ineffective" 결론 + DLA Piper(2026-01) 집행 강화 경고 — 수요는 살아있으나 형태는 $49 PDF가 아닌 감사/준비도 서비스 | supported (다중 2차 소스 — OSC 본문은 403으로 미확인) | skeptic 레인 + regulome.io + paperclipped.de + nyc144euaiact.com (2026-08-01) |

## 승계 (이전 세션 20260730-204855에서 상속 — 원문은 ../20260730-204855/claim-graph.md)

| id | claim | status | 이번 세션에서 할 일 |
|---|---|---|---|
| C9 | LL144 편향감사는 $2,500/72시간 고정가 생산품으로 판매됨 | supported | 원가 구조 재평가에 사용 |
| U9 | DCWP 집행 실적(LL144 위반 과태료 실제 부과) | unresolved | **재검증 시도 — idea-space/risks 축에 위임** |
| C7 | 한국 HR SaaS는 인당 월 ~2,000원 수준 | supported | kr-market 축이 현재 가격 재확인 |
| C12 | 미국 오가닉 검색 트래픽 -2.5% YoY, 제로클릭 ~60% | partial | 유통 논리 재사용 |

## Unresolved / Refuted — 이번 세션

(웨이브 진행 중 채움)

## 거부된 클레임 (게이트 실패)

- 스코핑에서 관측된 "V4 Pro $0.435/$0.87" — 출처 간 모순, 공식 확인 전까지 **주장 금지**
- 스코핑에서 관측된 "캐시 히트 $0.003625/$0.0028" — 할인율 불일치, **주장 금지**
