# 📊 Retrieval Strategy Evaluation Report

**Generated:** 2026-02-07 20:39
**Questions:** 12
**Strategies:** hybrid, iterative, agentic, graphrag_local, graphrag_global, combined

## Summary: Which Strategy Wins?

### Overall Strategy Scores

| Strategy | Avg Score | Avg Time | Best For |
|----------|-----------|----------|----------|
| **hybrid** | 0.69 | 17.1s | Cross Document Synthesis |
| **iterative** | 0.79 | 41.3s | Entity Fragmented, Multi Part Comparison |
| **agentic** | 0.77 | 33.8s | — |
| **graphrag_local** | 0.78 | 41.2s | — |
| **graphrag_global** | 0.78 | 116.0s | Relationship, Comprehensive |
| **combined** | 0.81 | 28.3s | Factual Lookup |

## Category Breakdown

### 📋 Factual Lookup
_Simple questions where the answer exists in a single chunk_

| Question | hybrid | iterative | agentic | graphrag_local | graphrag_global | combined | Winner |
|----------|-------|-------|-------|-------|-------|-------|--------|
| F1: What is the street name where Station 36 is l... | 0.80 | 0.80 | 1.00 🏆| 1.00 | 0.80 | 1.00 | **agentic** |
| F2: What is the name of Station 35?... | 0.60 | 0.80 | 0.60 | 0.80 | 1.00 🏆| 1.00 | **graphrag_global** |
| **Category Avg** | **0.70** ⭐| **0.80** ⭐| **0.80** | **0.90** ⭐| **0.90** | **1.00** ⭐| **combined** ⭐ |

### 🔗 Entity-Fragmented
_Questions where the answer spans multiple chunks that don't share keywords_

| Question | hybrid | iterative | agentic | graphrag_local | graphrag_global | combined | Winner |
|----------|-------|-------|-------|-------|-------|-------|--------|
| E1: What are the approved plans in the area of St... | 0.67 🏆| 0.67 | 0.67 | 0.67 | 0.33 | 0.67 | **hybrid** |
| E2: What are the existing land use designations a... | 0.67 | 1.00 🏆| 1.00 | 0.67 | 0.67 | 0.67 | **iterative** |
| **Category Avg** | **0.67** ⭐| **0.83** ⭐| **0.83** | **0.67** | **0.50** | **0.67** | **iterative** ⭐ |

### ⚖️ Multi-Part Comparison
_Questions that require comparing attributes across stations_

| Question | hybrid | iterative | agentic | graphrag_local | graphrag_global | combined | Winner |
|----------|-------|-------|-------|-------|-------|-------|--------|
| M1: Compare the entrances of Station 35 and Stati... | 1.00 🏆| 1.00 | 1.00 | 1.00 | 0.80 | 1.00 | **hybrid** |
| M2: What are the development plan differences bet... | 0.75 | 1.00 🏆| 1.00 | 1.00 | 1.00 | 1.00 | **iterative** |
| **Category Avg** | **0.88** ⭐| **1.00** ⭐| **1.00** | **1.00** | **0.90** | **1.00** | **iterative** ⭐ |

### 🕸️ Relationship & Impact
_Questions about connections between entities, organizations, and infrastructure_

| Question | hybrid | iterative | agentic | graphrag_local | graphrag_global | combined | Winner |
|----------|-------|-------|-------|-------|-------|-------|--------|
| R1: Which organizations are involved in planning ... | 0.33 | 0.67 | 0.33 | 0.67 | 1.00 🏆| 0.67 | **graphrag_global** |
| R2: What are the connections between Station 36 a... | 0.80 🏆| 0.80 | 0.80 | 0.80 | 0.80 | 0.80 | **hybrid** |
| **Category Avg** | **0.57** ⭐| **0.73** ⭐| **0.57** | **0.73** | **0.90** ⭐| **0.73** | **graphrag_global** ⭐ |

### 🌍 Cross-Document Synthesis
_Big-picture questions requiring aggregation across all documents_

| Question | hybrid | iterative | agentic | graphrag_local | graphrag_global | combined | Winner |
|----------|-------|-------|-------|-------|-------|-------|--------|
| S1: Give an overall summary of all M1 metro line ... | 0.14 🏆| 0.00 | 0.00 | 0.00 | 0.00 | 0.14 | **hybrid** |
| S2: What are the general planning trends across M... | 1.00 🏆| 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | **hybrid** |
| **Category Avg** | **0.57** ⭐| **0.50** | **0.50** | **0.50** | **0.50** | **0.57** | **hybrid** ⭐ |

### 🔀 Comprehensive
_Questions needing both document details AND relationship context_

| Question | hybrid | iterative | agentic | graphrag_local | graphrag_global | combined | Winner |
|----------|-------|-------|-------|-------|-------|-------|--------|
| C1: Describe Station 36 comprehensively: location... | 0.80 | 0.80 | 0.80 | 0.80 | 1.00 🏆| 0.80 | **graphrag_global** |
| C2: What is the full planning status of Beer Yaak... | 0.67 | 1.00 🏆| 1.00 | 1.00 | 1.00 | 1.00 | **iterative** |
| **Category Avg** | **0.73** ⭐| **0.90** ⭐| **0.90** | **0.90** | **1.00** ⭐| **0.90** | **graphrag_global** ⭐ |

## 🔬 Detailed Examples

Below are specific examples showing WHY certain strategies win for certain question types.

### Example: 📋 Factual Lookup
**Question:** מהו שם התחנה מספר 35?
**English:** _What is the name of Station 35?_

**🏆 Winner: graphrag_global** (score: 1.00)
> שם התחנה מספר 35 הוא "תחנת מטרו קפלן" או "תחנת מטרו תת"ק" (תחנת מטרו תת-קרקעית)‏ [Source 1].

**❌ Weakest: agentic** (score: 0.60)
> שם התחנה מספר 35 הוא "קפלן" [מקור 1].

---

### Example: 🔗 Entity-Fragmented
**Question:** מהם התכניות המאושרות באזור תחנה 36?
**English:** _What are the approved plans in the area of Station 36?_

**🏆 Winner: hybrid** (score: 0.67)
> התכניות המאושרות באזור תחנה 36 (שדרות הציונות) כוללות ייעודי קרקע מגוונים:  
- דרך משולבת  
- דרך מאושרת  
- שטח ציבורי פתוח  
- מגורים א׳, מגורים ב׳, מגורים ג׳  
- תעשייה  
- מסחר ותעשייה  
- מבנים ומוסדות ציבור  
- שטח המוכרז כאתר עתיקות  
בנוסף, ישנם מעברים תת-קרקעיים, כניסות לתחנה, תחנת מטרו תת״ק, חניה, גינון, מדרכות, קווי חשמל, תחנות אוטובוס ומבנים שמסומנים להריסה [מקור 1].

**❌ Weakest: graphrag_global** (score: 0.33)
> התכניות המאושרות באזור תחנה 36 בראשון לציון כוללות:

- אזורי מגורים מאושרים מסוגים שונים (א', ב', ג'), כולל שכונות חדשות המתוכננות במסגרת תכנון עירוני מקיף.
- אזורי תעסוקה ומסחר מאושרים, כגון מב"ת צפון, אזורי מסחר ותעשייה.
- פיתוח עירוני משולב הכולל מגורים, תעסוקה, שיפור הנגישות התחבורתית, דרכי גישה

---

### Example: ⚖️ Multi-Part Comparison
**Question:** מה ההבדלים בתכניות הפיתוח בין תחנה 37 לתחנה 38?
**English:** _What are the development plan differences between Station 37 and Station 38?_

**🏆 Winner: iterative** (score: 1.00)
> ההבדלים העיקריים בתכניות הפיתוח בין תחנה 37 (יוסף בורג) לתחנה 38 (הרצוג) הם:

1. **תכניות בהכנה ואופי הפיתוח**:
   - תחנה 37 (יוסף בורג): מוקפת אזור תכנון "אנ״מ צפוני - רצ/1/130" עם תכנון ל-1,500 יחידות דיור, אזור מגורים עתידי ואזור נופש מטרופוליני. הפיתוח מתמקד בעיקר במגורים, שטחים ציבוריים פתוחים, ומוסדות ציבור. התחנה ממוקמת על ציר עירוני ראשי, ויש דגש על חיבור לשכונות מגורים עתידיות ולשטחים חקלאיים קיימים [מקור 1, מקור 10].
   - תחנה 38 (הרצוג): בנוסף ל"אנ״מ צפוני - רצ/1/130", יש תכניות פיתוח

**❌ Weakest: hybrid** (score: 0.75)
> אין לי מספיק מידע כדי להשוות בין תכניות הפיתוח של תחנה 37 ותחנה 38. המידע שבידי מפרט בעיקר את תכניות הפיתוח והסביבה של תחנה 38 ("הרצוג"), אך אינו כולל פירוט דומה עבור תחנה 37.  
אם תספק מידע נוסף לגבי תחנה 37, אוכל לבצע את ההשוואה המבוקשת [Source 5].

---

### Example: 🕸️ Relationship & Impact
**Question:** אילו ארגונים מעורבים בתכנון תחנות המטרו ומה התפקיד של כל אחד?
**English:** _Which organizations are involved in planning metro stations and what is each one's role?_

**🏆 Winner: graphrag_global** (score: 1.00)
> בתכנון תחנות המטרו בישראל מעורבים מספר ארגונים מרכזיים, כאשר לכל אחד מהם תפקיד ייחודי:

1. **נת"ע (NTA)** – הגוף המרכזי האחראי על תכנון, פיתוח, ניהול והפעלת תשתיות תחבורה ציבורית המונית, כולל תכנון וביצוע תחנות וקווי מטרו, פיקוח על שלבי התכנון, הבנייה והתפעול, ותיאום בין גורמים מקצועיים [Source 1].

2. **מנספלד-קהת אדריכלים בע"מ** – אחראית על התכנון והעיצוב האדריכלי של תחנות המטרו, כולל הכנת תכניות אדריכליות, שילוב התחנות בסביבה העירונית, ותכנון סביבתי ואורבני משולב [Source 1].

3. **MIS Metro**

**❌ Weakest: agentic** (score: 0.33)
> על פי המידע במקורות, הארגונים המרכזיים המעורבים בתכנון תחנות המטרו הם:

1. **נ.ת.ע | נתיבי תחבורה עירוניים להסעת המונים בע"מ** – הגוף האחראי על תכנון, פיתוח והקמה של מערכות תחבורה עירוניות להסעת המונים, כולל תכנון תחנות המטרו עצמן ותיאום בין הגורמים השונים [מקור 3, מקור 4, מקור 6, מקור 7, מקור 9].



---

### Example: 🌍 Cross-Document Synthesis
**Question:** תן סיכום כולל של כל תחנות המטרו בקו M1 ומאפייניהן העיקריים
**English:** _Give an overall summary of all M1 metro line stations and their main characteristics_

**🏆 Winner: hybrid** (score: 0.14)
> קו המטרו M1 הוא הקו המרכזי והארוך במערכת המטרו העתידית של גוש דן, ויכלול כ-62 תחנות לאורך כ-85 ק"מ, ב-14 רשויות שונות. להלן סיכום כולל של התחנות ומאפייניהן העיקריים:

**1. פריסה גאוגרפית ומבנה הקו:**
- הקו מחבר את ערי השרון והמרכז (כפר סבא, רעננה, הרצליה, הוד השרון, רמת השרון) דרך תל אביב, חולון וראשון לציון, ועד לוד, רמלה, נס ציונה ורחובות בדרום.
- בתוך ראשון לציון הקו מתפצל לשתי זרועות: זרוע מערבית (לרחובות) וזרוע מזרחית (ללוד) [Source 4].

**2. רשימת תחנות לדוגמה (לא כל התחנות, אלא עיקריות ומ

**❌ Weakest: graphrag_global** (score: 0.00)
> קו המטרו M1 כולל רשת תחנות מגוונת, רובן תת-קרקעיות, אשר מחברות בין ערים מרכזיות במטרופולין תל אביב, גוש דן והפריפריה. התחנות מאופיינות בתכנון מתקדם, תשתיות מודרניות, ושילוב תחבורתי רב-מודלי. להלן סיכום עיקרי של התחנות ומאפייניהן:

- **תחנת יוסף בורג (ראשון לציון):** תחנה מרכזית בצפון-מזרח העיר, משול

---

### Example: 🔀 Comprehensive
**Question:** מהו המצב התכנוני המלא של אזור באר יעקב ביחס למטרו - תכניות, שכונות, קישוריות וארגונים?
**English:** _What is the full planning status of Beer Yaakov area regarding metro - plans, neighborhoods, connectivity, organizations?_

**🏆 Winner: iterative** (score: 1.00)
> המצב התכנוני של אזור באר יעקב ביחס למטרו (תחנה מס' 41) כולל את המרכיבים הבאים:

**1. תכניות בנייה ופיתוח:**
- קיימות תכניות מאושרות ופעילות בארבעה מתחמים עיקריים סביב התחנה:
  - **מתחם 1**: 3,700 יחידות דיור, מסחר, תעסוקה ומבני ציבור.
  - **מתחם 2**: 3,200 יחידות דיור, 180,000 מ"ר מסחר, תעסוקה ומבני ציבור.
  - **מתחם 3**: 2,750 יחידות דיור, 11,132 מ"ר מסחר.
  - **מתחם 6**: בתכנון מוקדם, 2,148 יחידות דיור, 115,000 מ"ר תעסוקה [Source 3][Source 5].

**2. שכונות וסביבת התחנה:**
- התחנה ממוקמת בצפון 

**❌ Weakest: hybrid** (score: 0.67)
> המצב התכנוני של אזור באר יעקב ביחס למטרו כולל את המרכיבים הבאים:

**1. תכניות בנייה ופיתוח:**
- קיימות תכניות מאושרות ומוקדמות לארבעה מתחמים עיקריים סביב תחנת המטרו:
  - **מתחם 1:** מאושר, בתכנון אלי פירשטיזם – 3,700 יחידות דיור, מסחר, תעסוקה ומבני ציבור.
  - **מתחם 2:** מאושר, בתכנון קולקר אדריכלים

---

## 💡 Key Takeaways

| Question Type | Best Strategy | Why |
|--------------|---------------|-----|
| 📋 Factual Lookup | **combined** | Direct keyword + semantic match — no need for complex retrieval |
| 🔗 Entity-Fragmented | **iterative** | Entity extraction bridges disconnected chunks (e.g., station number → street name → data) |
| ⚖️ Multi-Part Comparison | **iterative** | Decomposes comparison into per-station sub-queries |
| 🕸️ Relationship & Impact | **graphrag_global** | Knowledge graph traversal finds entity connections that text search misses |
| 🌍 Cross-Document Synthesis | **hybrid** | Community summaries aggregate information across all documents |
| 🔀 Comprehensive | **graphrag_global** | Merges document facts (AI Search) with relationship context (GraphRAG) |

---
_Report generated by strategy_eval.py — 12 questions evaluated_