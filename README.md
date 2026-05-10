# SpaceL AI

SpaceL AI is a grounded legal research MVP for criminal-law questions over Supreme Court judgment PDFs.

It helps law students and legal professionals:

- ask questions about bail, evidence, sentencing, criminal appeals, and benefit of doubt
- retrieve relevant judgment passages from a local FAISS index
- generate structured legal reasoning with transparent source evidence
- switch between professional Legal Mode and beginner-friendly Student Mode

## Run

```powershell
python -m streamlit run streamlit_app.py
```

If the vector index is missing, build it first:

```powershell
python scripts/build_index.py
```

## Demo Configuration

Set `SPACEL_DEMO_VIDEO_URL` in `.env` to replace the landing-page demo video.

Fallback impact stats can be adjusted with:

```env
SPACEL_FALLBACK_QUERY_COUNT=120
SPACEL_FALLBACK_HELPFUL_PERCENT=78
```
