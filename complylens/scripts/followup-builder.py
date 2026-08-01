#!/usr/bin/env python3
"""팔로업 아웃리치 빌더 — 1차 발송 2-3일 후 사용.

사용법: python3 followup-builder.py [대상 인덱스|all]
출력: Gmail compose URL (Safari에서 열기 + Cmd+Enter로 발송)
"""
import sys
import urllib.parse

FOLLOWUPS = [
    ("vedvyas@aedtaudits.com", "[Listing] ComplyLens — quick follow-up",
     "Hello,\n\nJust following up on my message from August 1 about listing ComplyLens (automated LL144/AEDT analysis, 72h delivery, $299-$1,500) on your directory.\n\nWe'd be glad to supply a description, reciprocal link, or sample report. If now isn't a good time, happy to check back later in the quarter.\n\nBest,\nComplyLens (https://html.npopo.com)"),
    ("support@ll144audit.com", "[Listing] Add ComplyLens — quick follow-up",
     "Hello,\n\nFollowing up on my August 1 message about listing ComplyLens on your vendor comparison page. We can provide a short description and reciprocal link to make evaluation easy.\n\nBest,\nComplyLens (https://html.npopo.com)"),
    ("advisory@lexaraadvisory.com", "[Partnership] Bias audit referral — quick follow-up",
     "Hello,\n\nFollowing up on my August 1 referral-cooperation proposal (10-15% fee on completed engagements). We regularly receive inquiries from employers needing independent auditor sign-off.\n\nBest,\nComplyLens (https://html.npopo.com)"),
    ("support@phenompeople.com", "[Partnership] Bias audit for Phenom customers — follow-up",
     "Hello,\n\nFollowing up on my August 1 message about offering your customers a preferred-rate LL144 analysis with a referral arrangement. Happy to share a sample report.\n\nBest,\nComplyLens (https://html.npopo.com)"),
    ("lets.talk@idiro.com", "[Partnership] Bias audit referral — quick follow-up",
     "Hello,\n\nFollowing up on my August 1 referral-cooperation proposal (10-15% fee). We'd also welcome cross-listing on vendor comparison content.\n\nBest,\nComplyLens (https://html.npopo.com)"),
]


def build_url(to: str, subject: str, body: str) -> str:
    return (
        "https://mail.google.com/mail/?view=cm&fs=1"
        f"&to={urllib.parse.quote(to)}"
        f"&su={urllib.parse.quote(subject)}"
        f"&body={urllib.parse.quote(body)}"
    )


def main() -> None:
    targets = sys.argv[1:] or ["all"]
    for i, (to, subj, body) in enumerate(FOLLOWUPS):
        if "all" in targets or str(i + 1) in targets:
            print(f"=== {i+1}. {to} ===")
            print(build_url(to, subj, body))
            print()


if __name__ == "__main__":
    main()
