# ⚖️ SpaceL AI — AI-Powered Legal Research Assistant

**Think Like a Lawyer. Research Like a Judge.**

SpaceL AI is an **AI-powered legal research assistant** built using **Retrieval-Augmented Generation (RAG)** over **real Indian Supreme Court judgments**.

It helps **law students, legal professionals, and solo advocates** perform faster legal research by retrieving relevant judgments and generating **grounded, citation-backed legal explanations** in plain English.

---

## 🚀 Live Demo

🔗 Streamlit App:  
https://legal-vakta-uw6ab4aj9bwvngbbowjcbd.streamlit.app/

---

## 🎥 Demo Video

Watch the product demo here:

https://drive.google.com/file/d/14NmwQS3R-TJIc1PEsw9JHay78_61NE55/view?usp=sharing

---

## ❓ Problem Statement

Legal research in India is often:

- ⏳ **Time-consuming** — lawyers spend hours manually scanning judgments
- 📚 **Complex** — legal reasoning is difficult for students to understand
- 🔍 **Keyword-dependent** — existing systems struggle with legal context
- ⚠️ **Not beginner-friendly** — junior advocates face a steep learning curve

India has **1.7M+ advocates** and **1700+ law colleges**, yet legal research remains slow and inaccessible.

---

## 💡 Our Solution

SpaceL AI enables users to:

✅ Ask legal questions in **plain English**  
✅ Retrieve **real Supreme Court judgments**  
✅ Get **grounded legal explanations** with citations  
✅ Understand legal reasoning in **student-friendly language**  
✅ Switch between **Legal Mode** and **Student Mode**

Example legal queries:

- *“Bail conditions in serious offences”*
- *“Benefit of doubt in criminal appeals”*
- *“Circumstantial evidence cases”*
- *“Sentencing principles in criminal law”*

---

## 🏗️ Architecture

SpaceL AI uses a **Retrieval-Augmented Generation (RAG)** pipeline to provide grounded legal answers.

### Workflow

1. User enters legal query in plain English  
2. FAISS retrieves semantically relevant Supreme Court judgments  
3. LangChain + LangGraph orchestrate retrieval and reasoning  
4. LLM synthesises legal explanation from retrieved context  
5. Grounded answer returned with source citations

### Architecture Diagram

<img width="1210" height="869" alt="diagram-export-5-13-2026-8_19_51-PM" src="https://github.com/user-attachments/assets/75245543-ef45-4f93-b72f-fbbfa3d7969a" />


```md
![SpaceL AI Architecture](architecture.png)
```

---

## ⚙️ Tech Stack

### Core Technologies

| Technology | Purpose |
|------------|---------|
| LangChain | RAG orchestration |
| LangGraph | Agentic workflow |
| FAISS | Vector similarity search |
| HuggingFace Embeddings | Semantic retrieval |
| Streamlit | Frontend / deployment |
| Python | Backend development |
| LLM API / OpenRouter | Grounded legal reasoning |

---

## ✨ Features

### 🔎 Real Judgment Retrieval
Searches actual Supreme Court judgments instead of generic web content.

### 📖 Grounded Legal Reasoning
Answers are generated using retrieved legal context.

### 📌 Citation-Backed Responses
Every answer includes traceable legal references and source snippets.

### 🎓 Student Mode
Simplifies legal explanations for law students and beginners.

### ⚖️ Legal Mode
Professional-style responses for legal practitioners.

### 👍 Feedback System
Users can rate answer quality to improve retrieval performance.

### 📬 Waitlist System
Users can join the early-access waitlist for future releases.

---

## 🛠️ Installation

### Clone Repository

```bash
git clone https://github.com/AnushaNarayananP/legal-vakta.git
cd legal-vakta
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment Variables

Create a `.env` file:

```env
SPACEL_DEMO_VIDEO_URL=your_demo_video_url
SPACEL_FALLBACK_QUERY_COUNT=120
SPACEL_FALLBACK_HELPFUL_PERCENT=78
```

---

## 📦 Build Vector Index

If the vector index is missing:

```bash
python scripts/build_index.py
```

---

## ▶️ Run Application

```bash
python -m streamlit run streamlit_app.py
```

Or:

```bash
streamlit run streamlit_app.py
```

---

## 🧪 Example Use Cases

### For Law Students
- Understand legal concepts in simple language
- Study precedent-based reasoning
- Learn criminal law faster

### For Lawyers
- Reduce legal research time
- Find relevant precedents quickly
- Retrieve grounded legal insights

### For Solo Practitioners
- Affordable AI-assisted legal research
- Faster case preparation

---

## 📈 Roadmap

### Phase 1 — MVP
✅ Working Streamlit MVP  
✅ Supreme Court judgment retrieval  
✅ Legal + Student mode  

### Phase 2 — Beta
🔄 First 50 law student users  
🔄 Advocate feedback loop  

### Phase 3 — Scale
🔄 Multi-case reasoning  
🔄 Expanded legal corpus  
🔄 Institutional partnerships

---

## 👩‍💻 Founder

**Anusha Narayanan P**  
AI & Data Science Researcher | Builder of SpaceL AI

GitHub:  
https://github.com/AnushaNarayananP

LinkedIn:  
https://www.linkedin.com/in/anusha-narayanan-b9184423a/

---

## ⚠️ Disclaimer

SpaceL AI is an educational and research-oriented legal assistant MVP.

It is **not legal advice** and should not replace consultation with licensed legal professionals.

```env
SPACEL_FALLBACK_QUERY_COUNT=120
SPACEL_FALLBACK_HELPFUL_PERCENT=78
```
