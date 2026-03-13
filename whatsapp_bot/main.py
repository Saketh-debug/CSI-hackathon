from pathlib import Path
from typing import Optional, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from config import EMBEDDING_MODEL_NAME
from rag_service import RAGService
from translation_service import translate_text
from whatsapp_service import send_whatsapp_message

app = FastAPI(title="RAG Chatbot API", version="1.0.0")

rag_service = RAGService(
    embedding_model_name=EMBEDDING_MODEL_NAME,
    storage_dir=str(Path(__file__).with_name("vector_store")),
)
stored_phone_numbers: list[str] = []


class IngestRequest(BaseModel):
    website_url: Optional[str] = None
    docs_path: Optional[str] = None
    max_pages: int = Field(default=5, ge=1, le=50)
    chunk_size: int = Field(default=900, ge=200, le=4000)
    chunk_overlap: int = Field(default=120, ge=0, le=1000)
    embedding_model: Optional[str] = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=4, ge=1, le=10)


class RetrieveRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=4, ge=1, le=10)
    score_threshold: float = Field(default=0.30, ge=0.0, le=1.0)


class AddPhoneRequest(BaseModel):
    phone: str = Field(min_length=5)


class LocationUpdateRequest(BaseModel):
    location: str = Field(min_length=1)
    zone: str = Field(min_length=1)
    extra_context: Optional[str] = None
    target_language: Literal["te-IN", "hi-IN"] = "te-IN"


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "RAG chatbot backend is running",
        "endpoints": [
            "/status",
            "/ingest",
            "/retrieve",
            "/chat",
            "/add-number",
            "/get-numbers",
            "/clear-numbers",
            "/location-update",
        ],
    }


@app.get("/status")
def status():
    return rag_service.status()


@app.post("/ingest")
def ingest_data(request: IngestRequest):
    if not request.website_url and not request.docs_path:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one source: website_url or docs_path.",
        )

    if request.chunk_overlap >= request.chunk_size:
        raise HTTPException(
            status_code=400,
            detail="chunk_overlap must be smaller than chunk_size.",
        )

    try:
        result = rag_service.build_index(
            website_url=request.website_url,
            docs_path=request.docs_path,
            max_pages=request.max_pages,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            embedding_model_name=request.embedding_model,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc

    return {"status": "success", **result}


@app.post("/retrieve")
def retrieve(request: RetrieveRequest):
    if not rag_service.status().get("index_ready"):
        return {
            "chunks": [],
            "sources": [],
            "count": 0,
            "warning": "Knowledge base is not built yet. Call /ingest first.",
        }

    try:
        chunks = rag_service.retrieve(
            query=request.question,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Retrieve failed: {exc}") from exc

    sources = sorted({item["source"] for item in chunks})
    return {"chunks": chunks, "sources": sources, "count": len(chunks)}


@app.get("/get-numbers")
def get_numbers():
    return {"numbers": stored_phone_numbers}


@app.post("/add-number")
def add_number(request: AddPhoneRequest):
    phone = request.phone.strip()
    if phone in stored_phone_numbers:
        return {"status": "exists", "message": "Phone number already saved."}

    stored_phone_numbers.append(phone)
    return {"status": "success", "message": f"Added {phone}"}


@app.post("/clear-numbers")
def clear_numbers():
    stored_phone_numbers.clear()
    return {"status": "success", "message": "Cleared all saved numbers."}


def _process_zone_alert(request: LocationUpdateRequest):
    zone_normalized = request.zone.strip().lower()
    if zone_normalized == "green":
        return {
            "status": "no_alert",
            "message": "User is in green zone. No alert sent.",
            "zone": request.zone,
            "location": request.location,
        }

    if not stored_phone_numbers:
        return {
            "status": "no_recipients",
            "message": "No saved phone numbers found.",
            "zone": request.zone,
            "location": request.location,
        }

    try:
        generated_message = rag_service.generate_zone_alert(
            location=request.location,
            zone=request.zone,
            extra_context=request.extra_context or "",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate zone alert message: {exc}",
        ) from exc

    try:
        translated_message = translate_text(
            generated_message,
            target_language_code=request.target_language,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to translate generated alert: {exc}",
        ) from exc

    results = []
    for phone in stored_phone_numbers:
        sid = send_whatsapp_message(phone, translated_message)
        results.append(
            {
                "phone": phone,
                "status": "success" if sid else "failure",
                "message_sid": sid,
            }
        )

    return {
        "status": "alert_processed",
        "zone": request.zone,
        "location": request.location,
        "target_language": request.target_language,
        "generated_message": generated_message,
        "translated_message": translated_message,
        "results": results,
    }


@app.post("/location-update")
def location_update(request: LocationUpdateRequest):
    return _process_zone_alert(request)


@app.post("/chat")
def chat(request: ChatRequest):
    if not rag_service.status().get("index_ready"):
        return {
            "answer": "I don't know.",
            "sources": [],
            "chunks": [],
            "warning": "Knowledge base is not built yet. Call /ingest first.",
        }

    try:
        response = rag_service.answer_question(request.question, top_k=request.top_k)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chat failed: {exc}") from exc

    if not response.get("answer"):
        response["answer"] = "I don't know."

    return response
