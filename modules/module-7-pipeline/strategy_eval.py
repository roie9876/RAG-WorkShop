"""
Strategy Evaluation Framework for RAG Pipeline
==============================================
Runs a diverse question set against ALL retrieval strategies,
collects answers, and grades them to show which strategy excels where.

This is designed to run overnight — it makes many API calls.

Usage:
    python strategy_eval.py                    # Run full evaluation
    python strategy_eval.py --quick            # Run only 2 questions per category (for testing)
    python strategy_eval.py --report-only      # Only generate report from existing results
"""
import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Optional

import httpx

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────
API_BASE = "http://localhost:8000"
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "eval_results")

# Strategies to test (each with their specific config)
STRATEGIES = {
    "hybrid": {
        "retrieval_strategy": "hybrid",
        "search_mode": "hybrid",
        "semantic_ranker": True,
        "top_k": 5,
        "enable_validation": True,
    },
    "iterative": {
        "retrieval_strategy": "iterative",
        "search_mode": "hybrid",
        "semantic_ranker": True,
        "top_k": 5,
        "enable_validation": True,
    },
    "agentic": {
        "retrieval_strategy": "agentic",
        "search_mode": "hybrid",
        "semantic_ranker": True,
        "top_k": 5,
        "enable_validation": True,
    },
    "graphrag_local": {
        "retrieval_strategy": "graphrag",
        "graphrag_mode": "local",
        "graphrag_community_level": 2,
        "graphrag_response_type": "Multiple Paragraphs",
        "enable_validation": True,
    },
    "graphrag_global": {
        "retrieval_strategy": "graphrag",
        "graphrag_mode": "global",
        "graphrag_community_level": 2,
        "graphrag_response_type": "Multiple Paragraphs",
        "enable_validation": True,
    },
    "combined": {
        "retrieval_strategy": "combined",
        "combined_base_strategy": "hybrid",
        "graphrag_mode": "local",
        "search_mode": "hybrid",
        "semantic_ranker": True,
        "top_k": 5,
        "enable_validation": True,
    },
}

# ──────────────────────────────────────────────────────────────────────────────
# Question Set — organized by category
# Each question has:
#   - question: the actual query
#   - expected_strategy: which strategy SHOULD answer best
#   - expected_keywords: keywords we expect in a good answer (for automated scoring)
#   - difficulty: easy / medium / hard
#   - category: what type of question this is
# ──────────────────────────────────────────────────────────────────────────────
QUESTIONS = [
    # ══════════════════════════════════════════════════════════════════════════
    # CATEGORY 1: Simple Factual Lookup
    # These are straightforward — the answer exists in a single chunk.
    # EXPECTED WINNER: Hybrid (fast, accurate for direct matches)
    # ══════════════════════════════════════════════════════════════════════════
    {
        "id": "F1",
        "question": "מהו שם הרחוב שבו ממוקמת תחנה 36?",
        "question_en": "What is the street name where Station 36 is located?",
        "category": "factual_lookup",
        "difficulty": "easy",
        "expected_winner": "hybrid",
        "expected_keywords": ["שדרות הציונות", "הציונות"],
        "ground_truth": "תחנה 36 ממוקמת בשדרות הציונות (Sderot HaTzionut / Zionism Boulevard)",
    },
    {
        "id": "F2",
        "question": "מהו שם התחנה מספר 35?",
        "question_en": "What is the name of Station 35?",
        "category": "factual_lookup",
        "difficulty": "easy",
        "expected_winner": "hybrid",
        "expected_keywords": ["קפלן"],
        "ground_truth": "תחנה 35 נקראת תחנת קפלן (Kaplan Station)",
    },
    {
        "id": "F3",
        "question": "מהו שם התחנה מספר 41?",
        "question_en": "What is the name of Station 41?",
        "category": "factual_lookup",
        "difficulty": "easy",
        "expected_winner": "hybrid",
        "expected_keywords": ["באר יעקב"],
        "ground_truth": "תחנה 41 נקראת תחנת באר יעקב",
    },
    {
        "id": "F4",
        "question": "מהו רדיוס השירות של תחנות המטרו?",
        "question_en": "What is the service radius of metro stations?",
        "category": "factual_lookup",
        "difficulty": "easy",
        "expected_winner": "hybrid",
        "expected_keywords": ["800", "מטר"],
        "ground_truth": "רדיוס השירות של תחנות המטרו הוא 800 מטר",
    },
    {
        "id": "F5",
        "question": "באיזה עמוד מופיעים ייעודי הקרקע של תחנה 38?",
        "question_en": "On which page do the land use designations for Station 38 appear?",
        "category": "factual_lookup",
        "difficulty": "medium",
        "expected_winner": "hybrid",
        "expected_keywords": ["הרצוג", "38"],
        "ground_truth": "ייעודי הקרקע המאושרים של תחנה 38 (הרצוג) מופיעים בתיעוד התחנה",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # CATEGORY 2: Entity-Fragmented Questions
    # The answer requires connecting info from MULTIPLE chunks that don't
    # share the same keywords. Station number is on one chunk, details on another.
    # EXPECTED WINNER: Iterative (entity extraction bridges the gap)
    # ══════════════════════════════════════════════════════════════════════════
    {
        "id": "E1",
        "question": "מהם התכניות המאושרות באזור תחנה 36?",
        "question_en": "What are the approved plans in the area of Station 36?",
        "category": "entity_fragmented",
        "difficulty": "medium",
        "expected_winner": "iterative",
        "expected_keywords": ["שדרות הציונות", "מאושר", "תכנית"],
        "ground_truth": "תחנה 36 (שדרות הציונות) - יש תכניות מאושרות באזור הכוללות ייעודי קרקע שונים",
    },
    {
        "id": "E2",
        "question": "מהם ייעודי הקרקע הקיימים בסביבת תחנת קפלן?",
        "question_en": "What are the existing land use designations around Kaplan Station?",
        "category": "entity_fragmented",
        "difficulty": "medium",
        "expected_winner": "iterative",
        "expected_keywords": ["35", "קפלן", "קרקע"],
        "ground_truth": "תחנת קפלן (35) - אזור מגורים, תעסוקה ומסחר",
    },
    {
        "id": "E3",
        "question": "מהם השכונות הסמוכות לתחנה שנמצאת ליד בית החולים אסף הרופא?",
        "question_en": "What neighborhoods are near the station by Assaf HaRofeh hospital?",
        "category": "entity_fragmented",
        "difficulty": "hard",
        "expected_winner": "iterative",
        "expected_keywords": ["39", "אסף הרופא", "צריפין"],
        "ground_truth": "תחנה 39 (אסף הרופא) - ממוקמת ליד מרכז רפואי אסף הרופא, בסמוך לצריפין",
    },
    {
        "id": "E4",
        "question": "כמה תחנות מטרו יש בראשון לציון?",
        "question_en": "How many metro stations are in Rishon LeZion?",
        "category": "entity_fragmented",
        "difficulty": "medium",
        "expected_winner": "iterative",
        "expected_keywords": ["35", "36", "37", "38"],
        "ground_truth": "מספר תחנות מטרו בראשון לציון (תחנות 35-41 הן חלק מקו M1)",
    },
    {
        "id": "E5",
        "question": "מה שם הרחוב של התחנה שיש לה הכי הרבה תמונות במסמך?",
        "question_en": "What is the street of the station with the most figures in its document?",
        "category": "entity_fragmented",
        "difficulty": "hard",
        "expected_winner": "iterative",
        "expected_keywords": ["36", "שדרות הציונות"],
        "ground_truth": "תחנה 36 (שדרות הציונות) - metro-s36.pdf has 20 figures, the most",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # CATEGORY 3: Multi-Part Comparison Questions
    # Require looking at multiple stations and comparing attributes.
    # EXPECTED WINNER: Agentic (decomposes into sub-queries per station)
    # ══════════════════════════════════════════════════════════════════════════
    {
        "id": "M1",
        "question": "השווה בין כניסות תחנה 35 ותחנה 36 - מה ההבדלים העיקריים?",
        "question_en": "Compare the entrances of Station 35 and Station 36 - what are the main differences?",
        "category": "multi_part_comparison",
        "difficulty": "hard",
        "expected_winner": "agentic",
        "expected_keywords": ["35", "36", "קפלן", "שדרות הציונות", "כניסה"],
        "ground_truth": "השוואה בין כניסות תחנות 35 (קפלן) ו-36 (שדרות הציונות)",
    },
    {
        "id": "M2",
        "question": "מה ההבדלים בתכניות הפיתוח בין תחנה 37 לתחנה 38?",
        "question_en": "What are the development plan differences between Station 37 and Station 38?",
        "category": "multi_part_comparison",
        "difficulty": "hard",
        "expected_winner": "agentic",
        "expected_keywords": ["37", "38", "יוסף בורג", "הרצוג"],
        "ground_truth": "תחנה 37 (יוסף בורג) vs תחנה 38 (הרצוג) - differences in land use and development plans",
    },
    {
        "id": "M3",
        "question": "באילו תחנות יש שבילי אופניים קיימים ובאילו מתוכננים?",
        "question_en": "Which stations have existing bike paths and which have planned ones?",
        "category": "multi_part_comparison",
        "difficulty": "hard",
        "expected_winner": "agentic",
        "expected_keywords": ["אופניים", "קיים", "מתוכנן"],
        "ground_truth": "סקירה של תשתיות אופניים קיימות ומתוכננות ליד תחנות שונות",
    },
    {
        "id": "M4",
        "question": "השווה את ייעודי הקרקע המאושרים של תחנה 39 ותחנה 40",
        "question_en": "Compare the approved land use designations of Station 39 and Station 40",
        "category": "multi_part_comparison",
        "difficulty": "hard",
        "expected_winner": "agentic",
        "expected_keywords": ["39", "40", "אסף הרופא", "צריפין"],
        "ground_truth": "תחנה 39 (אסף הרופא) vs תחנה 40 (צריפין) - approved land use designations",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # CATEGORY 4: Relationship / Impact Questions
    # These ask about connections BETWEEN entities — which organization plans
    # which station, what connects to what, dependencies, etc.
    # EXPECTED WINNER: GraphRAG (knowledge graph traversal)
    # ══════════════════════════════════════════════════════════════════════════
    {
        "id": "R1",
        "question": "אילו ארגונים מעורבים בתכנון תחנות המטרו ומה התפקיד של כל אחד?",
        "question_en": "Which organizations are involved in planning metro stations and what is each one's role?",
        "category": "relationship",
        "difficulty": "hard",
        "expected_winner": "graphrag_local",
        "expected_keywords": ["נת\"ע", "מנספלד", "MIS"],
        "ground_truth": "נת\"ע (תכנון מטרו), מנספלד-קהת אדריכלים (תכנון אדריכלי), MIS (ניהול)",
    },
    {
        "id": "R2",
        "question": "מהם הקשרים בין תחנה 36 לתשתיות הסביבתיות שלה?",
        "question_en": "What are the connections between Station 36 and its surrounding infrastructure?",
        "category": "relationship",
        "difficulty": "hard",
        "expected_winner": "graphrag_local",
        "expected_keywords": ["36", "שדרות הציונות", "תשתית", "אופניים", "הולכי רגל"],
        "ground_truth": "תחנה 36 מחוברת לשבילי אופניים, צירי הולכי רגל, צירי ביקוש עירוניים ותחבורה ציבורית",
    },
    {
        "id": "R3",
        "question": "כיצד קו החום מחבר בין הערים והשכונות השונות?",
        "question_en": "How does the Brown Line connect different cities and neighborhoods?",
        "category": "relationship",
        "difficulty": "hard",
        "expected_winner": "graphrag_local",
        "expected_keywords": ["קו החום", "ראשון לציון", "באר יעקב", "לוד"],
        "ground_truth": "קו החום (M1) מחבר בין ראשון לציון, באר יעקב, ולוד דרך תחנות 35-41",
    },
    {
        "id": "R4",
        "question": "איזה בתי חולים ומרכזים רפואיים נמצאים בסמוך לתחנות המטרו?",
        "question_en": "Which hospitals and medical centers are near metro stations?",
        "category": "relationship",
        "difficulty": "hard",
        "expected_winner": "graphrag_local",
        "expected_keywords": ["אסף הרופא", "39"],
        "ground_truth": "בית חולים אסף הרופא נמצא בסמוך לתחנה 39",
    },
    {
        "id": "R5",
        "question": "מהי ההשפעה של מערכת המטרו על תכנון ייעודי הקרקע בערים השונות?",
        "question_en": "What is the metro system's impact on land use planning in different cities?",
        "category": "relationship",
        "difficulty": "hard",
        "expected_winner": "graphrag_global",
        "expected_keywords": ["מגורים", "תעסוקה", "פיתוח"],
        "ground_truth": "מערכת המטרו משפיעה על ייעודי קרקע - הגדלת צפיפות מגורים ותעסוקה סביב התחנות",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # CATEGORY 5: Cross-Document Synthesis / Big Picture
    # Require aggregating information across ALL documents.
    # EXPECTED WINNER: GraphRAG Global (community summaries)
    # ══════════════════════════════════════════════════════════════════════════
    {
        "id": "S1",
        "question": "תן סיכום כולל של כל תחנות המטרו בקו M1 ומאפייניהן העיקריים",
        "question_en": "Give an overall summary of all M1 metro line stations and their main characteristics",
        "category": "cross_document_synthesis",
        "difficulty": "hard",
        "expected_winner": "graphrag_global",
        "expected_keywords": ["35", "36", "37", "38", "39", "40", "41"],
        "ground_truth": "סקירה של תחנות 35-41 בקו M1: קפלן, שדרות הציונות, יוסף בורג, הרצוג, אסף הרופא, צריפין, באר יעקב",
    },
    {
        "id": "S2",
        "question": "מה המגמות הכלליות בתכנון תחנות המטרו לאורך קו M1?",
        "question_en": "What are the general planning trends across M1 metro line stations?",
        "category": "cross_document_synthesis",
        "difficulty": "hard",
        "expected_winner": "graphrag_global",
        "expected_keywords": ["תכנון", "פיתוח", "נגישות"],
        "ground_truth": "מגמות: שילוב תחבורה ציבורית, הגדלת צפיפות, פיתוח מרחב ציבורי, נגישות",
    },
    {
        "id": "S3",
        "question": "מהם האתגרים המשותפים לכל תחנות המטרו בפרויקט?",
        "question_en": "What are the common challenges across all metro stations in the project?",
        "category": "cross_document_synthesis",
        "difficulty": "hard",
        "expected_winner": "graphrag_global",
        "expected_keywords": ["אתגר", "תכנון", "פיתוח"],
        "ground_truth": "אתגרים משותפים בתכנון תחנות מטרו: קישוריות, ייעודי קרקע, שילוב סביבתי",
    },
    {
        "id": "S4",
        "question": "איך השכונות השונות שמסביב לתחנות צפויות להשתנות בעקבות הקמת המטרו?",
        "question_en": "How are neighborhoods around stations expected to change due to metro construction?",
        "category": "cross_document_synthesis",
        "difficulty": "hard",
        "expected_winner": "graphrag_global",
        "expected_keywords": ["פיתוח", "מגורים", "תעסוקה", "שינוי"],
        "ground_truth": "שכונות צפויות לפיתוח: מגורים, תעסוקה, מסחר - סביב כל תחנות המטרו",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # CATEGORY 6: Combined / Comprehensive Questions
    # Need BOTH document details AND relationship context.
    # EXPECTED WINNER: Combined (merges AI Search facts + GraphRAG relationships)
    # ══════════════════════════════════════════════════════════════════════════
    {
        "id": "C1",
        "question": "תאר את תחנה 36 באופן מקיף: מיקום, תשתיות מחוברות, ייעודי קרקע, וארגונים מתכננים",
        "question_en": "Describe Station 36 comprehensively: location, connected infrastructure, land use, and planning organizations",
        "category": "comprehensive",
        "difficulty": "hard",
        "expected_winner": "combined",
        "expected_keywords": ["36", "שדרות הציונות", "נת\"ע", "אופניים", "קרקע"],
        "ground_truth": "תחנה 36 (שדרות הציונות): מיקום, תשתיות סביבתיות, ייעודי קרקע, ארגונים מתכננים",
    },
    {
        "id": "C2",
        "question": "מהו המצב התכנוני המלא של אזור באר יעקב ביחס למטרו - תכניות, שכונות, קישוריות וארגונים?",
        "question_en": "What is the full planning status of Beer Yaakov area regarding metro - plans, neighborhoods, connectivity, organizations?",
        "category": "comprehensive",
        "difficulty": "hard",
        "expected_winner": "combined",
        "expected_keywords": ["41", "באר יעקב", "צריפין"],
        "ground_truth": "באר יעקב (תחנה 41): תכניות מפורטות, קישוריות, ייעודי קרקע, ארגונים מעורבים",
    },
    {
        "id": "C3",
        "question": "כיצד תחנת אסף הרופא משתלבת במערך הבריאותי והתחבורתי של האזור?",
        "question_en": "How does Assaf HaRofeh station integrate with the health and transportation infrastructure of the area?",
        "category": "comprehensive",
        "difficulty": "hard",
        "expected_winner": "combined",
        "expected_keywords": ["39", "אסף הרופא", "בית חולים", "תחבורה"],
        "ground_truth": "תחנה 39 (אסף הרופא) - שילוב במערך בריאותי ותחבורתי: בית חולים, קישוריות, פיתוח",
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# Evaluation Logic
# ──────────────────────────────────────────────────────────────────────────────

async def query_api(client: httpx.AsyncClient, question: str, strategy_config: dict) -> dict:
    """Send a query to the API and return the full response."""
    payload = {
        "question": question,
        "min_score": 0,
        **strategy_config,
    }

    start = time.time()
    try:
        resp = await client.post(
            f"{API_BASE}/api/query",
            json=payload,
            timeout=180.0,  # some strategies are slow
        )
        elapsed = time.time() - start

        if resp.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                "time_ms": int(elapsed * 1000),
            }

        data = resp.json()
        return {
            "success": True,
            "answer": data.get("answer", ""),
            "sources_count": len(data.get("sources", [])),
            "sources": [
                {
                    "id": s.get("id", ""),
                    "content_type": s.get("content_type", ""),
                    "relevance_score": s.get("relevance_score", 0),
                    "source_document": s.get("source_document", ""),
                    "page_numbers": s.get("page_numbers", []),
                }
                for s in data.get("sources", [])[:10]  # limit stored sources
            ],
            "validation": data.get("validation"),
            "metadata": data.get("metadata"),
            "combined_results": data.get("combined_results"),
            "time_ms": int(elapsed * 1000),
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "success": False,
            "error": str(e),
            "time_ms": int(elapsed * 1000),
        }


def score_answer(answer: str, expected_keywords: list[str]) -> dict:
    """
    Score an answer based on keyword coverage.
    Returns a dict with score details.
    """
    if not answer:
        return {"keyword_score": 0.0, "found": [], "missing": expected_keywords}

    answer_lower = answer.lower()
    found = []
    missing = []

    for kw in expected_keywords:
        if kw.lower() in answer_lower:
            found.append(kw)
        else:
            missing.append(kw)

    keyword_score = len(found) / len(expected_keywords) if expected_keywords else 1.0

    # Penalize very short answers (likely "I don't have enough information")
    length_penalty = 1.0
    if len(answer) < 30:
        length_penalty = 0.3
    elif len(answer) < 50:
        length_penalty = 0.6
    elif len(answer) < 80:
        length_penalty = 0.8

    # Check for "don't have information" type answers
    no_info_phrases = [
        "אין לי מספיק מידע",
        "I don't have enough",
        "no information available",
        "לא נמצא מידע",
        "I cannot find",
        "אין מידע",
    ]
    has_no_info = any(phrase.lower() in answer_lower for phrase in no_info_phrases)

    final_score = keyword_score * length_penalty
    if has_no_info and keyword_score < 0.5:
        final_score *= 0.5  # heavy penalty for "no info" with low keyword match

    return {
        "keyword_score": round(keyword_score, 3),
        "length_penalty": round(length_penalty, 3),
        "final_score": round(final_score, 3),
        "found_keywords": found,
        "missing_keywords": missing,
        "answer_length": len(answer),
        "has_no_info": has_no_info,
    }


async def run_evaluation(questions: list[dict], strategies: dict[str, dict], quick: bool = False) -> dict:
    """Run all questions against all strategies and collect results."""
    os.makedirs(RESULTS_DIR, exist_ok=True)

    results = {
        "meta": {
            "started": datetime.now().isoformat(),
            "total_questions": len(questions),
            "strategies": list(strategies.keys()),
            "quick_mode": quick,
        },
        "evaluations": [],
    }

    total_runs = len(questions) * len(strategies)
    completed = 0

    async with httpx.AsyncClient() as client:
        # Check API health first
        try:
            health = await client.get(f"{API_BASE}/api/health", timeout=10)
            print(f"✅ API is healthy: {health.status_code}")
        except Exception as e:
            print(f"❌ API is not reachable: {e}")
            print("   Make sure the backend is running on port 8000")
            return results

        for q in questions:
            q_result = {
                "id": q["id"],
                "question": q["question"],
                "question_en": q.get("question_en", ""),
                "category": q["category"],
                "difficulty": q["difficulty"],
                "expected_winner": q["expected_winner"],
                "ground_truth": q["ground_truth"],
                "strategy_results": {},
            }

            print(f"\n{'━'*80}")
            print(f"📝 [{q['id']}] {q['question_en']}")
            print(f"   Category: {q['category']} | Expected: {q['expected_winner']}")
            print(f"{'━'*80}")

            for strat_name, strat_config in strategies.items():
                completed += 1
                pct = int(completed / total_runs * 100)
                print(f"  [{pct:3d}%] Testing {strat_name:20s}...", end="", flush=True)

                api_result = await query_api(client, q["question"], strat_config)

                if api_result["success"]:
                    scoring = score_answer(api_result["answer"], q["expected_keywords"])
                    print(
                        f" ✅ {api_result['time_ms']:5d}ms | "
                        f"score={scoring['final_score']:.2f} | "
                        f"sources={api_result['sources_count']} | "
                        f"len={scoring['answer_length']}"
                    )
                else:
                    scoring = {"final_score": 0.0, "keyword_score": 0.0}
                    print(f" ❌ {api_result.get('error', 'unknown')[:60]}")

                q_result["strategy_results"][strat_name] = {
                    **api_result,
                    "scoring": scoring,
                }

                # Rate limit — don't hammer the API
                await asyncio.sleep(1)

            # Determine actual winner
            scores = {
                name: r["scoring"]["final_score"]
                for name, r in q_result["strategy_results"].items()
                if r.get("success", False)
            }
            if scores:
                actual_winner = max(scores, key=scores.get)
                q_result["actual_winner"] = actual_winner
                q_result["expected_correct"] = (
                    actual_winner == q["expected_winner"]
                    or (q["expected_winner"].startswith("graphrag") and actual_winner.startswith("graphrag"))
                )
            else:
                q_result["actual_winner"] = "none"
                q_result["expected_correct"] = False

            winner_emoji = "✅" if q_result["expected_correct"] else "🔄"
            print(f"\n  {winner_emoji} Winner: {q_result['actual_winner']} (expected: {q['expected_winner']})")
            print(f"     Scores: {json.dumps(scores, indent=None)}")

            results["evaluations"].append(q_result)

            # Save intermediate results after each question
            save_results(results)

    results["meta"]["finished"] = datetime.now().isoformat()
    save_results(results)
    return results


def save_results(results: dict):
    """Save results to JSON file."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    filepath = os.path.join(RESULTS_DIR, "eval_results.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def load_results() -> Optional[dict]:
    """Load existing results."""
    filepath = os.path.join(RESULTS_DIR, "eval_results.json")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def generate_report(results: dict) -> str:
    """Generate a comprehensive markdown report from evaluation results."""
    lines = []
    lines.append("# 📊 Retrieval Strategy Evaluation Report")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Questions:** {results['meta']['total_questions']}")
    lines.append(f"**Strategies:** {', '.join(results['meta']['strategies'])}")
    lines.append("")

    # ── Overall Summary ──
    lines.append("## Summary: Which Strategy Wins?")
    lines.append("")

    # Count wins per strategy per category
    category_winners = {}
    strategy_scores = {s: [] for s in results["meta"]["strategies"]}
    strategy_times = {s: [] for s in results["meta"]["strategies"]}

    for ev in results["evaluations"]:
        cat = ev["category"]
        if cat not in category_winners:
            category_winners[cat] = {}

        for strat_name, strat_result in ev["strategy_results"].items():
            score = strat_result.get("scoring", {}).get("final_score", 0.0)
            time_ms = strat_result.get("time_ms", 0)
            strategy_scores[strat_name].append(score)
            strategy_times[strat_name].append(time_ms)

            if strat_name not in category_winners[cat]:
                category_winners[cat][strat_name] = []
            category_winners[cat][strat_name].append(score)

    # Strategy leaderboard
    lines.append("### Overall Strategy Scores")
    lines.append("")
    lines.append("| Strategy | Avg Score | Avg Time | Best For |")
    lines.append("|----------|-----------|----------|----------|")

    strategy_avgs = {}
    for strat in results["meta"]["strategies"]:
        scores = strategy_scores[strat]
        times = strategy_times[strat]
        avg_score = sum(scores) / len(scores) if scores else 0
        avg_time = sum(times) / len(times) if times else 0
        strategy_avgs[strat] = avg_score

        # Find which categories this strategy does best in
        best_cats = []
        for cat, strat_scores in category_winners.items():
            cat_avgs = {s: sum(sc) / len(sc) for s, sc in strat_scores.items() if sc}
            if cat_avgs and max(cat_avgs, key=cat_avgs.get) == strat:
                cat_label = cat.replace("_", " ").title()
                best_cats.append(cat_label)

        best_str = ", ".join(best_cats) if best_cats else "—"
        lines.append(f"| **{strat}** | {avg_score:.2f} | {avg_time/1000:.1f}s | {best_str} |")

    lines.append("")

    # ── Category Breakdown ──
    lines.append("## Category Breakdown")
    lines.append("")

    category_labels = {
        "factual_lookup": ("📋 Factual Lookup", "Simple questions where the answer exists in a single chunk"),
        "entity_fragmented": ("🔗 Entity-Fragmented", "Questions where the answer spans multiple chunks that don't share keywords"),
        "multi_part_comparison": ("⚖️ Multi-Part Comparison", "Questions that require comparing attributes across stations"),
        "relationship": ("🕸️ Relationship & Impact", "Questions about connections between entities, organizations, and infrastructure"),
        "cross_document_synthesis": ("🌍 Cross-Document Synthesis", "Big-picture questions requiring aggregation across all documents"),
        "comprehensive": ("🔀 Comprehensive", "Questions needing both document details AND relationship context"),
    }

    for cat, (label, description) in category_labels.items():
        cat_evals = [e for e in results["evaluations"] if e["category"] == cat]
        if not cat_evals:
            continue

        lines.append(f"### {label}")
        lines.append(f"_{description}_")
        lines.append("")

        # Category scores per strategy
        lines.append("| Question | " + " | ".join(results["meta"]["strategies"]) + " | Winner |")
        lines.append("|----------|" + "|".join(["-------" for _ in results["meta"]["strategies"]]) + "|--------|")

        for ev in cat_evals:
            row = f"| {ev['id']}: {ev['question_en'][:45]}... "
            scores = {}
            for strat in results["meta"]["strategies"]:
                sr = ev["strategy_results"].get(strat, {})
                score = sr.get("scoring", {}).get("final_score", 0.0)
                time_ms = sr.get("time_ms", 0)
                scores[strat] = score
                emoji = "🏆" if strat == ev.get("actual_winner") else ""
                row += f"| {score:.2f} {emoji}"
            row += f"| **{ev.get('actual_winner', '?')}** |"
            lines.append(row)

        # Category averages
        avg_row = "| **Category Avg** "
        cat_avgs = {}
        for strat in results["meta"]["strategies"]:
            strat_scores_cat = category_winners.get(cat, {}).get(strat, [])
            avg = sum(strat_scores_cat) / len(strat_scores_cat) if strat_scores_cat else 0
            cat_avgs[strat] = avg
            best = "⭐" if cat_avgs and strat == max(cat_avgs, key=cat_avgs.get) else ""
            avg_row += f"| **{avg:.2f}** {best}"
        cat_winner = max(cat_avgs, key=cat_avgs.get) if cat_avgs else "?"
        avg_row += f"| **{cat_winner}** ⭐ |"
        lines.append(avg_row)
        lines.append("")

    # ── Detailed Examples ──
    lines.append("## 🔬 Detailed Examples")
    lines.append("")
    lines.append("Below are specific examples showing WHY certain strategies win for certain question types.")
    lines.append("")

    # Pick the best example from each category
    for cat, (label, _) in category_labels.items():
        cat_evals = [e for e in results["evaluations"] if e["category"] == cat]
        if not cat_evals:
            continue

        # Find the evaluation where the score gap is largest (most dramatic difference)
        best_example = None
        best_gap = 0
        for ev in cat_evals:
            scores = {
                s: ev["strategy_results"].get(s, {}).get("scoring", {}).get("final_score", 0)
                for s in results["meta"]["strategies"]
            }
            if scores:
                max_score = max(scores.values())
                min_score = min(scores.values())
                gap = max_score - min_score
                if gap > best_gap:
                    best_gap = gap
                    best_example = ev

        if not best_example:
            continue

        lines.append(f"### Example: {label}")
        lines.append(f"**Question:** {best_example['question']}")
        lines.append(f"**English:** _{best_example['question_en']}_")
        lines.append("")

        # Show top 2 vs bottom 2 strategies
        all_scores = {
            s: best_example["strategy_results"].get(s, {}).get("scoring", {}).get("final_score", 0)
            for s in results["meta"]["strategies"]
        }
        sorted_strats = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)

        # Winner answer
        winner_name = sorted_strats[0][0]
        winner_result = best_example["strategy_results"].get(winner_name, {})
        winner_answer = winner_result.get("answer", "N/A")[:500]

        lines.append(f"**🏆 Winner: {winner_name}** (score: {sorted_strats[0][1]:.2f})")
        lines.append(f"> {winner_answer}")
        lines.append("")

        # Loser answer (for contrast)
        loser_name = sorted_strats[-1][0]
        loser_result = best_example["strategy_results"].get(loser_name, {})
        loser_answer = loser_result.get("answer", "N/A")[:300]

        lines.append(f"**❌ Weakest: {loser_name}** (score: {sorted_strats[-1][1]:.2f})")
        lines.append(f"> {loser_answer}")
        lines.append("")
        lines.append("---")
        lines.append("")

    # ── Key Takeaways ──
    lines.append("## 💡 Key Takeaways")
    lines.append("")
    lines.append("| Question Type | Best Strategy | Why |")
    lines.append("|--------------|---------------|-----|")

    takeaway_reasons = {
        "factual_lookup": "Direct keyword + semantic match — no need for complex retrieval",
        "entity_fragmented": "Entity extraction bridges disconnected chunks (e.g., station number → street name → data)",
        "multi_part_comparison": "Decomposes comparison into per-station sub-queries",
        "relationship": "Knowledge graph traversal finds entity connections that text search misses",
        "cross_document_synthesis": "Community summaries aggregate information across all documents",
        "comprehensive": "Merges document facts (AI Search) with relationship context (GraphRAG)",
    }

    for cat, (label, _) in category_labels.items():
        cat_avgs = {}
        for strat in results["meta"]["strategies"]:
            sc = category_winners.get(cat, {}).get(strat, [])
            cat_avgs[strat] = sum(sc) / len(sc) if sc else 0
        if cat_avgs:
            best = max(cat_avgs, key=cat_avgs.get)
            reason = takeaway_reasons.get(cat, "—")
            lines.append(f"| {label} | **{best}** | {reason} |")

    lines.append("")
    lines.append("---")
    lines.append(f"_Report generated by strategy_eval.py — {len(results['evaluations'])} questions evaluated_")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
async def main():
    parser = argparse.ArgumentParser(description="RAG Strategy Evaluation Framework")
    parser.add_argument("--quick", action="store_true", help="Run only 2 questions per category")
    parser.add_argument("--report-only", action="store_true", help="Generate report from existing results")
    parser.add_argument("--category", type=str, help="Only run questions from this category")
    args = parser.parse_args()

    if args.report_only:
        results = load_results()
        if not results:
            print("❌ No results found. Run evaluation first.")
            return
        report = generate_report(results)
        report_path = os.path.join(RESULTS_DIR, "eval_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"📊 Report saved to: {report_path}")
        return

    questions = QUESTIONS

    if args.category:
        questions = [q for q in questions if q["category"] == args.category]
        print(f"Filtered to {len(questions)} questions in category: {args.category}")

    if args.quick:
        # Take 2 questions per category
        from itertools import groupby
        quick_qs = []
        seen_cats = {}
        for q in questions:
            cat = q["category"]
            seen_cats[cat] = seen_cats.get(cat, 0) + 1
            if seen_cats[cat] <= 2:
                quick_qs.append(q)
        questions = quick_qs
        print(f"Quick mode: {len(questions)} questions")

    print(f"\n{'='*80}")
    print(f"  RAG STRATEGY EVALUATION")
    print(f"  {len(questions)} questions × {len(STRATEGIES)} strategies = {len(questions) * len(STRATEGIES)} API calls")
    print(f"  Estimated time: {len(questions) * len(STRATEGIES) * 15 // 60} - {len(questions) * len(STRATEGIES) * 30 // 60} minutes")
    print(f"{'='*80}\n")

    results = await run_evaluation(questions, STRATEGIES, quick=args.quick)

    # Generate report
    report = generate_report(results)
    report_path = os.path.join(RESULTS_DIR, "eval_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n{'='*80}")
    print(f"  ✅ EVALUATION COMPLETE")
    print(f"  Results: {os.path.join(RESULTS_DIR, 'eval_results.json')}")
    print(f"  Report:  {report_path}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
