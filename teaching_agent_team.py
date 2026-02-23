import streamlit as st
from gemini_llm import GeminiLLM
from pdf_helper import create_pdf
from io import BytesIO
import base64
import zipfile
import pdfplumber
import docx
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image
import hashlib
import time
import re

# ================== HELPERS ==================

def img_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def is_quota_exhausted(text: str) -> bool:
    return text.startswith("QUOTA_EXHAUSTED")

def extract_syllabus_text(uploaded_file):
    try:
        file_type = uploaded_file.name.split(".")[-1].lower()

        if file_type == "pdf":
            text = ""
            pdf_bytes = uploaded_file.read()
            pdf_stream = BytesIO(pdf_bytes)
            
            # Try normal text extraction first
            try:
                with pdfplumber.open(pdf_stream) as pdf:
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t:
                            text += t + "\n"
                
                if text.strip():
                    return text.strip()
            except Exception as e:
                st.warning(f"⚠️ Text extraction failed: {str(e)[:80]}")
            
            # If text extraction failed or returned empty, try OCR
            st.info("🔄 Attempting OCR on PDF (scanned document)...")
            try:
                images = convert_from_bytes(pdf_bytes, first_page=1, last_page=10)
                for img in images:
                    ocr_text = pytesseract.image_to_string(img)
                    if ocr_text:
                        text += ocr_text + "\n"
                
                if text.strip():
                    st.success("✅ OCR extraction successful")
                    return text.strip()
                else:
                    raise ValueError("OCR returned no text")
            except Exception as e:
                st.warning(f"⚠️ OCR failed: {str(e)[:80]} (Tesseract not installed?)")
                raise ValueError("PDF appears to be empty or corrupted. Please ensure it contains readable text or images.")

        elif file_type == "docx":
            try:
                doc = docx.Document(uploaded_file)
                text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
                if text.strip():
                    return text
                raise ValueError("No text found in DOCX")
            except Exception as e:
                raise ValueError(f"DOCX error: {str(e)[:80]}")

        elif file_type == "txt":
            try:
                text = uploaded_file.read().decode("utf-8", errors="ignore")
                if text.strip():
                    return text
                raise ValueError("TXT file is empty")
            except Exception as e:
                raise ValueError(f"TXT error: {str(e)[:80]}")

        else:
            raise ValueError(f"Unsupported file type: .{file_type} (supported: pdf, docx, txt)")
    
    except Exception as e:
        st.error(f"❌ Error extracting text: {str(e)}")
        return None

# ================== PAGE CONFIG ==================

st.set_page_config(
    page_title="Mentorix",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ================== LOAD CUSTOM CSS ==================

try:
    with open("new.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass  # CSS file optional

# ================== SESSION STATE ==================

if "gemini_api_key" not in st.session_state:
    st.session_state["gemini_api_key"] = ""
if "question_patterns" not in st.session_state:
    st.session_state["question_patterns"] = [{"count": 4, "marks": 2}]
if "bloom_taxonomy" not in st.session_state:
    st.session_state["bloom_taxonomy"] = []
if "custom_questions" not in st.session_state:
    st.session_state["custom_questions"] = []
if "pdfs" not in st.session_state:
    st.session_state["pdfs"] = {}
if "sections" not in st.session_state:
    st.session_state["sections"] = {}
if "generation_id" not in st.session_state:
    st.session_state["generation_id"] = ""

# ⚠️ TEMP (REMOVE BEFORE DEPLOYMENT)
st.session_state["gemini_api_key"] =st.secrets["GEMINI_API_KEY"]
if not st.session_state["gemini_api_key"]:
    st.error("Gemini API key missing.")
    st.stop()

# ================== INIT GEMINI ==================

gemini = GeminiLLM(api_key=st.session_state["gemini_api_key"])

# ================== HEADER ==================

logo = img_to_base64("logo.png")

st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:center;">
    <img src="data:image/png;base64,{logo}" style="width:60px;margin-right:-12px;">
    <span style="margin-left: 15px;   font-size:54px;font-weight:800;color:#ffffff;">Mentorix</span>
</div>
<p style="text-align:center;color:#555;font-size:18px;">
Your AI-powered academic mentor
</p>
""", unsafe_allow_html=True)

st.divider()

# ================== INPUT MODE ==================

mode = st.radio(
    "Input Mode",
    ["Enter Topic", "Upload Syllabus"],
    horizontal=True,
    label_visibility="collapsed"
)

topic = ""
syllabus_text = ""

if mode == "Enter Topic":
    topic = st.text_input("Topic", placeholder="DBMS, ML, CN...")
else:
    file = st.file_uploader("Upload Syllabus", type=["pdf", "docx", "txt"])
    if file:
        with st.spinner("Extracting text from syllabus..."):
            syllabus_text = extract_syllabus_text(file)
        if syllabus_text:
            st.success("✅ Syllabus extracted successfully")
        else:
            st.stop()

# ================== EXTRA PROMPT ==================

extra_prompt = st.text_area(
    "Additional Instructions (Optional)",
    placeholder="Explain only Module 1 & 2, exam-oriented..."
)

# ================== INPUT VALIDATION ==================

input_ready = (mode == "Enter Topic" and bool(topic.strip())) or (mode == "Upload Syllabus" and bool(syllabus_text.strip()))

# Define BLOOM_LEVELS globally (needed for validation even when controls are hidden)
BLOOM_LEVELS = [
    "Remembering",
    "Understanding",
    "Applying",
    "Analyzing",
    "Evaluating",
    "Creating"
]

# Initialize defaults
active_custom_questions = []
generated_questions_count = 0
custom_questions_count = 0
total_questions = 0

if input_ready:
    # ================== QUESTION BUILDER ==================
    
    st.markdown("## 🧠 Question Pattern Builder")
    
    for i, qp in enumerate(st.session_state["question_patterns"]):
        c1, c2, c3, c4 = st.columns([3, 3, 0.6, 0.6])

        with c1:
            qp["count"] = st.number_input(
                "Questions",
                min_value=0,
                value=qp["count"],
                key=f"qc{i}"
            )

        with c2:
            qp["marks"] = st.number_input(
                "Marks per question",
                min_value=1,
                value=qp["marks"],
                key=f"qm{i}"
            )

        with c3:
            st.markdown("<div style='padding-top: 1.85rem;'></div>", unsafe_allow_html=True)
            if st.button("➕", key=f"add{i}", use_container_width=True):
                st.session_state["question_patterns"].append(
                    {"count": 2, "marks": 5}
                )
                st.rerun()

        with c4:
            st.markdown("<div style='padding-top: 1.85rem;'></div>", unsafe_allow_html=True)
            if st.button("➖", key=f"remove{i}", use_container_width=True):
                if len(st.session_state["question_patterns"]) > 1:
                    st.session_state["question_patterns"].pop(i)
                    st.rerun()
    
    # Calculate generated questions from pattern menu
    generated_questions_count = sum(qp["count"] for qp in st.session_state["question_patterns"])
    
    # ================== CUSTOM QUESTIONS BUILDER ==================
    
    st.markdown("## ✍️ Custom Questions (Optional)")
    st.markdown("Add teacher-framed questions to include along with generated questions.")
    
    BLOOM_KEYWORDS = {
        "Remembering": ["define", "list", "name", "state", "identify", "recall", "what is", "mention"],
        "Understanding": ["explain", "summarize", "describe", "differentiate", "classify", "interpret", "outline"],
        "Applying": ["apply", "solve", "use", "demonstrate", "calculate", "implement", "show how"],
        "Analyzing": ["analyze", "compare", "contrast", "examine", "categorize", "investigate", "why"],
        "Evaluating": ["evaluate", "justify", "critique", "assess", "argue", "recommend", "validate"],
        "Creating": ["design", "create", "develop", "construct", "propose", "formulate", "build"],
    }
    
    def detect_bloom_level(question_text: str) -> str:
        text = (question_text or "").strip().lower()
        if not text:
            return "Not detected"
    
        scores = {level: 0 for level in BLOOM_KEYWORDS.keys()}
        for level, keywords in BLOOM_KEYWORDS.items():
            for keyword in keywords:
                if text.startswith(keyword):
                    scores[level] += 3
                elif keyword in text:
                    scores[level] += 1
    
        best_level = max(scores, key=scores.get)
        return best_level if scores[best_level] > 0 else "Understanding"
    
    for i, cq in enumerate(st.session_state["custom_questions"]):
        c1, c2, c3, c4, c5 = st.columns([5, 1.2, 2.4, 0.7, 0.7])
    
        with c1:
            cq["text"] = st.text_input(
                "Custom Question",
                value=cq.get("text", ""),
                key=f"custom_q_{i}",
                placeholder="e.g., Explain normalization with suitable examples."
            )
    
        with c2:
            cq["marks"] = st.number_input(
                "Marks",
                min_value=1,
                value=int(cq.get("marks", 2)),
                key=f"custom_marks_{i}"
            )
    
        with c3:
            detected_level = detect_bloom_level(cq.get("text", ""))
            cq["bloom_level"] = detected_level
            st.markdown("<div style='padding-top: 1.85rem;'></div>", unsafe_allow_html=True)
            st.caption(f"Detected level: **{detected_level.lower()}**")
    
        with c4:
            st.markdown("<div style='padding-top: 1.85rem;'></div>", unsafe_allow_html=True)
            if st.button("➕", key=f"add_custom_{i}", use_container_width=True):
                st.session_state["custom_questions"].append({"text": "", "marks": 2, "bloom_level": "Understanding"})
                st.rerun()
    
        with c5:
            st.markdown("<div style='padding-top: 1.85rem;'></div>", unsafe_allow_html=True)
            if st.button("➖", key=f"remove_custom_{i}", use_container_width=True):
                st.session_state["custom_questions"].pop(i)
                st.rerun()
    
    if len(st.session_state["custom_questions"]) == 0:
        if st.button("➕ Add Custom Question", use_container_width=True):
            st.session_state["custom_questions"].append({"text": "", "marks": 2, "bloom_level": "Understanding"})
            st.rerun()
    
    active_custom_questions = [
    {
        "text": q.get("text", "").strip(),
        "marks": int(q.get("marks", 1)),
        "bloom_level": q.get("bloom_level") if q.get("bloom_level") in BLOOM_LEVELS else "Understanding"
    }
    for q in st.session_state["custom_questions"]
    if q.get("text", "").strip()
]

    custom_questions_count = len(active_custom_questions)
    total_questions = generated_questions_count + custom_questions_count
    
    st.info(
        f"📊 **Total Questions: {total_questions}**  |  Pattern Menu: {generated_questions_count}  |  Custom: {custom_questions_count}"
    )
    
    if active_custom_questions:
        st.success(f"✅ Custom questions added: {len(active_custom_questions)}")
    
    # ================== BLOOM'S TAXONOMY BUILDER ==================
    
    st.markdown("## 🎯 Bloom's Taxonomy Distribution (Optional)")
    st.markdown("Distribute **Pattern Menu Questions** across cognitive levels according to Bloom's Taxonomy")
    st.info("ℹ️ This applies only to Pattern Menu questions. Custom questions use their auto-detected levels.")

    for i, taxonomy in enumerate(st.session_state["bloom_taxonomy"]):
        c1, c2, c3, c4 = st.columns([3, 3, 0.6, 0.6])
        
        with c1:
            taxonomy["level"] = st.selectbox(
                "Taxonomy Level",
                BLOOM_LEVELS,
                index=BLOOM_LEVELS.index(taxonomy["level"]) if taxonomy["level"] in BLOOM_LEVELS else 0,
                key=f"tax_level_{i}"
            )
        
        with c2:
            taxonomy["count"] = st.number_input(
                "Number of Questions",
                min_value=1,
                max_value=max(generated_questions_count, 1),
                value=min(taxonomy["count"], max(generated_questions_count, 1)),
                key=f"tax_count_{i}"
            )
        
        with c3:
            st.markdown("<div style='padding-top: 1.85rem;'></div>", unsafe_allow_html=True)
            if st.button("➕", key=f"add_tax_{i}", use_container_width=True):
                st.session_state["bloom_taxonomy"].append({"level": "Understanding", "count": 1})
                st.rerun()
        
        with c4:
            st.markdown("<div style='padding-top: 1.85rem;'></div>", unsafe_allow_html=True)
            if st.button("➖", key=f"remove_tax_{i}", use_container_width=True):
                st.session_state["bloom_taxonomy"].pop(i)
                st.rerun()

    if len(st.session_state["bloom_taxonomy"]) == 0:
        if st.button("➕ Add Bloom's Taxonomy Distribution", use_container_width=True):
            st.session_state["bloom_taxonomy"].append({"level": "Understanding", "count": 1})
            st.rerun()
    
    # Validate taxonomy distribution (only for pattern questions)
    if st.session_state["bloom_taxonomy"] and generated_questions_count > 0:
        taxonomy_total = sum(t["count"] for t in st.session_state["bloom_taxonomy"])
        
        if taxonomy_total > generated_questions_count:
            st.error(f"❌ Taxonomy distribution ({taxonomy_total}) exceeds pattern menu questions ({generated_questions_count})!")
        elif taxonomy_total < generated_questions_count:
            st.warning(f"⚠️ Taxonomy distribution ({taxonomy_total}) is less than pattern menu questions ({generated_questions_count}). Remaining {generated_questions_count - taxonomy_total} questions will be mixed.")
        else:
            st.success(f"✅ Taxonomy distribution matches pattern menu questions ({taxonomy_total}/{generated_questions_count})")
        
        st.markdown("**Pattern Questions Distribution:**")
        for t in st.session_state["bloom_taxonomy"]:
            st.markdown(f"- {t['level']}: {t['count']} questions")

def question_instruction(custom_qs):
    marks_map = {}

    for q in st.session_state["question_patterns"]:
        marks = int(q["marks"])
        marks_map[marks] = marks_map.get(marks, 0) + int(q["count"])

    for q in custom_qs:
        marks = int(q["marks"])
        marks_map[marks] = marks_map.get(marks, 0) + 1

    return "\n".join(
        f"- {count} questions of {marks} marks each"
        for marks, count in sorted(marks_map.items())
    )

def taxonomy_instruction():
    if not st.session_state["bloom_taxonomy"]:
        return "No specific Bloom's Taxonomy distribution specified for pattern questions. Mix all levels for pattern questions."
    return "FOR PATTERN MENU QUESTIONS ONLY:\n" + "\n".join(
        f"- {t['count']} pattern questions at {t['level']} level"
        for t in st.session_state["bloom_taxonomy"]
    )

def custom_questions_instruction(custom_qs):
    if not custom_qs:
        return "No custom teacher-framed questions provided."
    return "\n".join(
        f"- ({q['marks']} Marks) [Bloom's Level: {q['bloom_level']}] {q['text']}"
        for i, q in enumerate(custom_qs)
    )

# ================== PROMPT TEMPLATES ==================

def professor_prompt(topic):
    return f"""
Provide comprehensive structured notes for {topic}.
Include:
- Core concepts with explanations
- Key definitions
- Important formulas/theorems
- Real-world examples
Use clear headings and bullet points.
"""

def advisor_prompt(topic):
    return f"""
Create a structured learning roadmap for {topic}.
Include:
- Prerequisites
- Main learning stages
- Estimated time for each stage
- Recommended study sequence
"""

def librarian_prompt(topic):
    return f"""
List high-quality learning resources for {topic}.
Include:
- Textbooks/books
- Online courses
- Video tutorials
- Research papers
- GitHub repositories
- Websites/blogs
"""

def assistant_prompt(topic):
    return f"""
You are an exam paper setter. Create a complete question bank with answers for {topic}.

OUTPUT FORMAT (IMPORTANT - FOLLOW EXACTLY - TWO SECTIONS):

═══════════════════════════════════════
SECTION 1: QUESTIONS ONLY (FOR STUDENTS)
═══════════════════════════════════════

**INSTRUCTIONS TO STUDENTS:**
- Attempt all questions
- Write legible answers
- Show all steps/working
- Follow the given mark distribution
- Do NOT look at answers while solving

**MARK DISTRIBUTION:**
{question_instruction()}

**BLOOM'S TAXONOMY DISTRIBUTION:**
{taxonomy_instruction()}

**CUSTOM TEACHER-FRAMED QUESTIONS (MANDATORY TO INCLUDE):**
{custom_questions_instruction()}

**QUESTIONS:**
[Generate exactly {total_questions} questions in total: {generated_questions_count} from the pattern menu + {custom_questions_count} custom teacher-framed questions.]
[Include each custom teacher-framed question exactly once with its exact marks and Bloom's level as provided above, but do NOT label or separate them as custom in the final question paper.]
[Treat all questions as one single question category in the final paper with a single mark distribution block.]
[Ensure answer key contains exactly one matching answer for each question with same numbering and marks alignment.]
[Format each question as:]

Question 1 (X Marks) [Bloom's Level: Understanding]: [Question text]

Question 2 (X Marks) [Bloom's Level: Applying]: [Question text]

... and so on

═══════════════════════════════════════
SECTION 2: ANSWER KEY (FOR TEACHERS)
═══════════════════════════════════════

**ANSWER KEY:**

Answer 1 [Bloom's Level: Understanding]:
[Detailed explanation with steps, formulas, and working]

Answer 2 [Bloom's Level: Applying]:
[Detailed explanation with steps, formulas, and working]

... and so on

Make each answer comprehensive, include formulas, working, and diagrams descriptions where needed.
"""

def master_prompt(topic_text, syllabus, instructions, gen_q_count, custom_q_count, total_q, custom_qs):
    return f"""
You are an academic expert.

TOPIC:
{topic_text or "Derive from syllabus"}

SYLLABUS:
{syllabus or "Not provided"}

INSTRUCTIONS:
{instructions or "None"}

QUESTION STRUCTURE:
{question_instruction(custom_qs)}

BLOOM'S TAXONOMY DISTRIBUTION:
{taxonomy_instruction()}

CUSTOM TEACHER-FRAMED QUESTIONS (MANDATORY TO INCLUDE):
{custom_questions_instruction(custom_qs)}

RULES:
- Strictly syllabus-based
- Exam-oriented language
- Bloom's taxonomy distribution applies ONLY to pattern-menu questions ({gen_q_count} questions)
- Custom questions MUST use their specified Bloom's levels (already defined)
- Total questions must be exactly {total_q}
- Pattern-menu questions count must be exactly {gen_q_count}
- Custom questions count must be exactly {custom_q_count}
- If custom teacher-framed questions are provided, include them verbatim with the same marks and same Bloom's level, and generate answers for them
- Do not label questions as custom; present all questions in one unified list
- Ensure mark distribution and answer key match the final question list exactly
- Provide answers clearly
- Do not add any introduction, disclaimer, or summary before section headers

OUTPUT SECTIONS:
SECTION 1: STRUCTURED NOTES
SECTION 2: LEARNING ROADMAP
SECTION 3: IMPORTANT RESOURCES
SECTION 4: QUESTION BANK WITH ANSWERS

QUESTION BANK FORMAT (IMPORTANT - FOLLOW EXACTLY):

═══════════════════════════════════════
SECTION 1: QUESTIONS ONLY (FOR STUDENTS)
═══════════════════════════════════════

INSTRUCTIONS:
- Attempt all questions
- Write legible answers
- Show all steps/working
- Follow the given mark distribution

MARK DISTRIBUTION:
{question_instruction(custom_qs)}

BLOOM'S TAXONOMY DISTRIBUTION:
{taxonomy_instruction()}

QUESTIONS:

Question 1 (X Marks) [Bloom's Level: Understanding]: ...

Question 2 (X Marks) [Bloom's Level: Applying]: ...

═══════════════════════════════════════
SECTION 2: ANSWER KEY (FOR TEACHERS)
═══════════════════════════════════════

ANSWER KEY:

Answer 1 [Bloom's Level: Understanding]:
[Detailed explanation]

Answer 2 [Bloom's Level: Applying]:
[Detailed explanation]
"""

# ================== GENERATE ==================

if input_ready:
    if st.button("🚀 Generate Learning Pack", type="primary", use_container_width=True):

        # Calculate question totals for conditional generation
        generated_questions_count = sum(qp["count"] for qp in st.session_state["question_patterns"])
        active_custom_questions = [
            {
                "text": q.get("text", "").strip(),
                "marks": int(q.get("marks", 1)),
                "bloom_level": q.get("bloom_level") if q.get("bloom_level", "Understanding") in BLOOM_LEVELS else "Understanding"
            }
            for q in st.session_state["custom_questions"]
            if q.get("text", "").strip()
        ]
        custom_questions_count = len(active_custom_questions)
        total_questions = generated_questions_count + custom_questions_count

        # Generate prompt
        prompt = master_prompt(
            topic_text=topic,
            syllabus=syllabus_text,
            instructions=extra_prompt,
            gen_q_count=generated_questions_count,
            custom_q_count=custom_questions_count,
            total_q=total_questions,
            custom_qs=active_custom_questions
        )

        with st.spinner("🔄 Generating content... (this may take 30-60 seconds)"):
            try:
                content = gemini.run(prompt)
                st.success("✅ Content generated successfully!")
            except RuntimeError as e:
                st.error(f"❌ Gemini API Error: {str(e)}")
                st.info("💡 **Possible solutions:**\n- Check your API key is valid\n- Verify you have quota remaining\n- Try reducing the complexity of your request\n- Wait a few moments and try again")
                st.stop()
            except Exception as e:
                st.error(f"❌ Unexpected error: {str(e)}")
                st.info(f"Error type: {type(e).__name__}")
                import traceback
                st.code(traceback.format_exc())
                st.stop()

        # Validate content
        if is_quota_exhausted(content):
            st.warning("⚠️ Gemini free quota exhausted. Please retry after some time.")
            st.stop()
        
        if not content or len(content.strip()) < 100:
            st.error("❌ Received empty or too short response from Gemini API")
            st.info(f"Response length: {len(content)} characters")
            with st.expander("View Response"):
                st.text(content)
            st.stop()
        
        st.info(f"📊 Processing content... ({len(content)} characters received)")

        # ================== SPLIT SECTIONS ==================

        # Try to split sections intelligently
        sections = {
            "notes": "",
            "roadmap": "",
            "resources": "",
            "qbank": ""
        }

        normalized_content = content.replace("\r", "")
        section_patterns = {
            "notes": r"(?:^|\n)\s*(?:SECTION\s*1\s*:\s*STRUCTURED\s*NOTES|1\.\s*STRUCTURED\s*NOTES)",
            "roadmap": r"(?:^|\n)\s*(?:SECTION\s*2\s*:\s*LEARNING\s*ROADMAP|2\.\s*LEARNING\s*ROADMAP)",
            "resources": r"(?:^|\n)\s*(?:SECTION\s*3\s*:\s*IMPORTANT\s*RESOURCES|3\.\s*IMPORTANT\s*RESOURCES)",
            "qbank": r"(?:^|\n)\s*(?:SECTION\s*4\s*:\s*QUESTION\s*BANK\s*WITH\s*ANSWERS|4\.\s*QUESTION\s*BANK\s*WITH\s*ANSWERS|4\.\s*QUESTION\s*BANK|SECTION\s*4\s*:\s*QUESTION\s*BANK|SECTION\s*1\s*:\s*QUESTIONS\s*ONLY\s*\(FOR\s*STUDENTS\)|SECTION\s*1\s*:\s*QUESTION\s*PAPER)",
        }

        section_positions = {}
        for key, pattern in section_patterns.items():
            match = re.search(pattern, normalized_content, flags=re.IGNORECASE)
            if match:
                section_positions[key] = match.start()

        if section_positions:
            ordered_sections = sorted(section_positions.items(), key=lambda item: item[1])
            for idx, (name, start_idx) in enumerate(ordered_sections):
                end_idx = ordered_sections[idx + 1][1] if idx + 1 < len(ordered_sections) else len(normalized_content)
                sections[name] = normalized_content[start_idx:end_idx].strip()

            if not sections["notes"]:
                sections["notes"] = normalized_content
        else:
            sections["notes"] = normalized_content

        if not sections["qbank"]:
            qbank_fallback = re.search(
                r"(?:^|\n)\s*(?:SECTION\s*1\s*:\s*QUESTIONS\s*ONLY\s*\(FOR\s*STUDENTS\)|SECTION\s*1\s*:\s*QUESTION\s*PAPER)",
                normalized_content,
                flags=re.IGNORECASE,
            )
            if qbank_fallback:
                sections["qbank"] = normalized_content[qbank_fallback.start():].strip()

        # Extract questions and answers separately
        qbank = sections["qbank"] or normalized_content
        qbank_text = qbank.replace("\r", "")

        qpaper_start = re.search(
            r"(?:SECTION\s*1\s*:\s*QUESTIONS\s*ONLY|SECTION\s*1\s*:\s*QUESTION\s*PAPER|QUESTIONS\s*ONLY\s*\(FOR\s*STUDENTS\))",
            qbank_text,
            flags=re.IGNORECASE,
        )
        if qpaper_start:
            qbank_text = qbank_text[qpaper_start.start():]

        questions_only = ""
        answers_only = ""
        
        # Split by SECTION 2 marker (more robust)
        if "SECTION 2" in qbank_text:
            idx = qbank_text.find("SECTION 2")
            questions_only = qbank_text[:idx].strip()
            answers_only = qbank_text[idx:].strip()
            
            # Clean up section headers
            questions_only = re.sub(r"SECTION\s*1.*?(?:QUESTIONS?:|$)", "", questions_only, flags=re.IGNORECASE | re.DOTALL).strip()
            answers_only = re.sub(r"SECTION\s*2.*?(?:ANSWER\s*KEY:?|$)", "", answers_only, flags=re.IGNORECASE | re.DOTALL).strip()
        else:
            # Fallback: split by ANSWER KEY marker
            answer_key_match = re.search(r"ANSWER\s*KEY\s*:?", qbank_text, flags=re.IGNORECASE)
            if answer_key_match:
                idx = answer_key_match.start()
                questions_only = qbank_text[:idx].strip()
                answers_only = qbank_text[answer_key_match.end():].strip()

            # Regex fallback: extract Question/Answer blocks if markers missing
            if not answers_only:
                answer_blocks = re.findall(
                    r"Answer\s*\d+\s*[:.)-]\s*(.*?)(?=\n\s*Answer\s*\d+\s*[:.)-]|\Z)",
                    qbank_text,
                    flags=re.IGNORECASE | re.DOTALL,
                )
                if answer_blocks:
                    answers_only = "\n\n".join(a.strip() for a in answer_blocks).strip()

            if not questions_only:
                question_blocks = re.findall(
                    r"Question\s*\d+\s*\([^\n]*\)\s*[:.)-]\s*(.*?)(?=\n\s*Question\s*\d+\s*\(|\Z)",
                    qbank_text,
                    flags=re.IGNORECASE | re.DOTALL,
                )
                if question_blocks:
                    questions_only = "\n\n".join(q.strip() for q in question_blocks).strip()

            # If still no split happened
            if not answers_only and not questions_only:
                questions_only = qbank_text
                answers_only = "No answer key found"

        # ================== CREATE PDFs ==================

        if total_questions > 0:
            # Add instructions to question paper (include mark distribution)
            question_instructions = """═══════════════════════════════════════
QUESTION PAPER
═══════════════════════════════════════

INSTRUCTIONS:
- Attempt all questions
- Write legible answers
- Show all steps/working
- Follow the given mark distribution
"""

            mark_distribution = question_instruction(active_custom_questions)
            if mark_distribution:
                question_instructions = f"{question_instructions}\nMARK DISTRIBUTION:\n{mark_distribution}\n"
            
            taxonomy_dist = taxonomy_instruction()
            if taxonomy_dist and st.session_state["bloom_taxonomy"]:
                question_instructions = f"{question_instructions}\nBLOOM'S TAXONOMY DISTRIBUTION:\n{taxonomy_dist}\n"

            questions_only = f"{question_instructions}\n{questions_only}".strip()

            qa_combined = f"{questions_only}\n\n{'═'*40}\nANSWER KEY\n{'═'*40}\n\n{answers_only}".strip()

            pdfs = {
                "01_Notes": create_pdf("Structured Notes", sections["notes"]),
                "02_Roadmap": create_pdf("Learning Roadmap", sections["roadmap"]),
                "03_Resources": create_pdf("Important Resources", sections["resources"]),
                "04_QA": create_pdf("Question Bank", qa_combined),
            }
            
            display_content = {
                "01_Notes": sections["notes"],
                "02_Roadmap": sections["roadmap"],
                "03_Resources": sections["resources"],
                "04_QA": qa_combined,
            }
        else:
            # Skip question bank when no questions
            pdfs = {
                "01_Notes": create_pdf("Structured Notes", sections["notes"]),
                "02_Roadmap": create_pdf("Learning Roadmap", sections["roadmap"]),
                "03_Resources": create_pdf("Important Resources", sections["resources"]),
            }
            
            display_content = {
                "01_Notes": sections["notes"],
                "02_Roadmap": sections["roadmap"],
                "03_Resources": sections["resources"],
            }
        
        st.session_state["pdfs"] = pdfs
        st.session_state["sections"] = display_content
        st.session_state["generation_id"] = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]

        st.success("✅ Learning pack generated successfully!")

# ================== DISPLAY DOWNLOADS (outside button block - persists) ==================

if st.session_state["pdfs"]:
    st.markdown("## 📥 Downloads & Preview")
    st.markdown("---")
    
    gen_id = st.session_state.get("generation_id", "default")

    for idx, (name, pdf) in enumerate(st.session_state["pdfs"].items()):
        with st.expander(f"📄 {name}", expanded=(idx == 0)):
            tab1, tab2 = st.tabs(["👁️ Preview Content", "📥 Download PDF"])
            
            with tab1:
                if name in st.session_state["sections"]:
                    content_to_show = st.session_state["sections"][name]
                    if content_to_show and content_to_show.strip():
                        # Use a container with custom styling
                        with st.container():
                            # Format content better for display
                            formatted_content = content_to_show.replace("═", "─")
                            st.markdown(formatted_content, unsafe_allow_html=True)
                    else:
                        st.warning(f"No content for {name}")
                else:
                    st.warning(f"Preview not available for {name}")
            
            with tab2:
                pdf.seek(0)
                st.download_button(
                    f"⬇️ Download {name}",
                    pdf,
                    file_name=f"{name}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"dl_{gen_id}_{idx}_{name}"
                )

    st.markdown("---")
    st.markdown("## 📦 Download All as ZIP")
    
    # ================== ZIP DOWNLOAD ==================

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for name, pdf in st.session_state["pdfs"].items():
            pdf.seek(0)
            zipf.writestr(f"{name}.pdf", pdf.read())

    zip_buffer.seek(0)

    st.download_button(
        "📦 Download Complete Learning Pack",
        zip_buffer,
        file_name="Mentorix_Complete_Pack.zip",
        mime="application/zip",
        use_container_width=True,
        type="primary",
        key=f"zip_{gen_id}"
    )
