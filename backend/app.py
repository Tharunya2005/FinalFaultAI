# ============================================
# FaultAI - Main Flask App (RENDER DEPLOYMENT)
# Serves frontend UI + handles all API routes
# ============================================
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from grok_client import GrokClient
from rag_engine import RAGEngine

# ✅ Tell Flask where templates and static files are
app = Flask(__name__,
            template_folder="templates",
            static_folder="static")
CORS(app)

# ✅ Load API key from environment
API_KEY = os.getenv("API_KEY")
grok = GrokClient(api_key=API_KEY)

# ✅ FIXED PDF PATH — works on both local and Render
BASE_DIR = Path(__file__).resolve().parent
pdf_path = BASE_DIR / "Fault_diagnosis_and_predictive_maintenance_for_hyd.pdf"

if not pdf_path.exists():
    raise FileNotFoundError(
        f"❌ PDF not found at: {pdf_path}\n"
        f"   Make sure the PDF is in the same folder as app.py"
    )

print(f"✅ PDF found at: {pdf_path}")
rag = RAGEngine(pdf_path=str(pdf_path))


# --------------------------------------------
# ✅ SERVE FRONTEND UI
# --------------------------------------------
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


# --------------------------------------------
# Health Check API (called by script.js)
# --------------------------------------------
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "message": "FaultAI Backend Running 🚀",
        "total_chunks": rag.get_chunk_count(),
        "pdf_loaded": rag.get_chunk_count() > 0,
        "pdf_source": rag.get_source_info()
    })


# --------------------------------------------
# Knowledge Base API
# --------------------------------------------
@app.route("/api/knowledge-base", methods=["GET"])
def knowledge_base():
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 12))
        all_chunks = rag.get_all_chunks()
        total = len(all_chunks)
        start = (page - 1) * per_page
        end = start + per_page
        return jsonify({
            "source": rag.get_source_info(),
            "total": total,
            "total_pages": (total + per_page - 1) // per_page,
            "chunks": all_chunks[start:end]
        })
    except Exception as e:
        print(f"❌ Knowledge base error: {e}")
        return jsonify({"error": "Internal server error"}), 500


# --------------------------------------------
# Diagnosis API
# --------------------------------------------
@app.route("/api/diagnose", methods=["POST"])
def diagnose():
    try:
        data = request.get_json()
        if not data or "symptoms" not in data:
            return jsonify({"error": "Missing 'symptoms'"}), 400
        if rag.get_chunk_count() == 0:
            return jsonify({"error": "Knowledge base is empty. Check PDF and restart."}), 503

        symptoms = data["symptoms"]
        category = data.get("category")
        api_key = data.get("api_key")
        if api_key:
            grok.set_api_key(api_key)

        print(f"\n🔍 Diagnosis Request: {symptoms}")
        rag_results = rag.retrieve(query=symptoms, category=category)
        result = grok.generate_solution(symptoms, rag_results)

        source_pages = list(set(
            [p["page_start"] for p in rag_results] +
            [p.get("page_end", p["page_start"]) for p in rag_results]
        ))
        source_pages.sort()

        return jsonify({
            "fault": result.get("fault_name", "Unknown Fault"),
            "confidence": 85 if rag_results else 0,
            "pdf_source": rag.get_source_info()["filename"],
            "source_pages": source_pages,
            "retrieved_passages": rag_results,
            "grok_solution": result.get("solution_html", ""),
            "total_passages_searched": rag.get_chunk_count()
        })

    except Exception as e:
        print(f"❌ Diagnosis error: {e}")
        return jsonify({"error": "Internal server error"}), 500


# --------------------------------------------
# ✅ FIXED: Run server — works on local + Render
# --------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n🌐 Open your browser at: http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
