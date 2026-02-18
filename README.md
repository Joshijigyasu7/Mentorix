# 🎓 Mentorix

<div align="center">
  <img src="logo.png" alt="Mentorix Logo" width="200"/>
  
  **Your AI-powered academic mentor**
  
  [![Streamlit](https://img.shields.io/badge/Streamlit-1.41.1-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
  [![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
  [![Gemini](https://img.shields.io/badge/Google_Gemini-2.5_Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
</div>

---

## 📖 Overview

**Mentorix** is an intelligent academic companion that transforms how students prepare for exams. Powered by Google's Gemini 2.5 Flash LLM, it generates comprehensive learning materials from either a simple topic name or an uploaded syllabus document.

### ✨ Key Features

- 📝 **Structured Notes**: Get well-organized, exam-focused notes with key concepts, definitions, and real-world examples
- 🗺️ **Learning Roadmap**: Receive a personalized study plan with prerequisites, stages, and time estimates
- 📚 **Curated Resources**: Access handpicked textbooks, courses, tutorials, and research papers
- 🧠 **Custom Question Banks**: Generate practice questions with detailed answers based on your mark distribution
- 📄 **PDF Export**: Download all materials as individual PDFs or as a complete ZIP package
- 🔍 **Multi-format Support**: Upload syllabi in PDF, DOCX, or TXT format (with OCR support for scanned documents)

---

## 🎯 Usage

### Option 1: Enter a Topic
1. Select **"Enter Topic"** mode
2. Type your subject (e.g., "Machine Learning", "Database Management Systems")
3. Add optional instructions (e.g., "Focus on Module 1 & 2")
4. Configure question patterns (count and marks per question)
5. Click **"🚀 Generate Learning Pack"**

### Option 2: Upload Syllabus
1. Select **"Upload Syllabus"** mode
2. Upload your syllabus file (PDF/DOCX/TXT)
3. The app automatically extracts text (with OCR fallback for scanned PDFs)
4. Add optional instructions and configure question patterns
5. Click **"🚀 Generate Learning Pack"**

### Question Pattern Builder

Customize your question bank by specifying:
- **Number of questions** per section
- **Marks per question**
- Add multiple patterns (e.g., 4×2 marks + 2×5 marks)

---

## 📦 Generated Output

Mentorix creates **4 comprehensive PDFs**:

| File | Description |
|------|-------------|
| `01_Notes.pdf` | Structured notes with concepts, definitions, and examples |
| `02_Roadmap.pdf` | Step-by-step learning path with time estimates |
| `03_Resources.pdf` | Curated list of books, courses, and references |
| `04_QA.pdf` | Question bank with detailed answer key |

All files can be downloaded individually or as `Mentorix_Complete_Pack.zip`.

---

## 🛠️ Technical Architecture

### Core Components

```
teaching_agent_team.py  # Main Streamlit application
├── gemini_llm.py      # Gemini API wrapper with retry logic
├── pdf_helper.py      # PDF generation with custom formatting
└── requirements.txt   # Python dependencies
```

### Technologies Used

- **Frontend**: Streamlit (interactive web UI)
- **LLM**: Google Gemini 2.5 Flash (content generation)
- **PDF Processing**: 
  - `pdfplumber` (text extraction)
  - `pdf2image` + `pytesseract` (OCR for scanned PDFs)
  - `fpdf` (PDF creation)
- **Document Parsing**: `python-docx` (Word documents)

### Key Features Implementation

- **Smart Text Extraction**: Automatically detects scanned PDFs and applies OCR
- **Content Segmentation**: Uses regex patterns to split generated content into sections
- **Dynamic PDF Formatting**: Custom FPDF class with markdown-style rendering
- **Session Persistence**: Streamlit session state maintains generated content across interactions

---

## 📋 Dependencies

### Core Libraries
```
streamlit==1.41.1
fpdf==1.7.2
pdfplumber==0.11.4
python-docx==1.1.2
```

### OCR Support
```
pdf2image==1.17.0
pytesseract==0.3.10
pillow==10.4.0
```

### Additional Tools
```
openai==1.58.1
agno>=2.2.10
composio-phidata==0.6.9
```

> **Note**: Some dependencies (like `composio` packages) appear unused in the current codebase and may be for future features.

---



## 🐛 Known Issues

- ⚠️ **Quota Limits**: Free Gemini API has rate limits; implement delays if quota errors occur
- ⚠️ **Latin-1 Encoding**: PDFs use Latin-1 encoding; some special characters may not render

---


## 📞 Support

For questions, issues, or feature requests:
- 🐛 [Open an issue](https://github.com/Joshijigyasu7/Mentorix/issues)
- 💬 Start a discussion in the repository

---

<div align="center">
  Made with ❤️ by Mentorix Team, for the ease of Teachers and Faculties

</div>