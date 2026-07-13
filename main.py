import os

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import HTMLResponse

#import json

import psycopg
from psycopg_pool import ConnectionPool
from pgvector.psycopg import register_vector

from google import genai
from google.genai import types


POSTGRES_USER = os.getenv('POSTGRES_USER', "postgres")
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', "f3f974")
POSTGRES_DB = os.getenv('POSTGRES_DB', "rag")
POSTGRES_URL = os.getenv('POSTGRES_URL', "localhost")
POSTGRES_PORT = os.getenv('POSTGRES_PORT', "5432")

RAG_DB_URL = os.getenv('RAG_DB_URL', f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_URL}:{POSTGRES_PORT}/{POSTGRES_DB}")
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', "")

app = FastAPI()

def configure_db(conn):
    register_vector(conn)

pool = ConnectionPool(conninfo=RAG_DB_URL, configure=configure_db)

client = genai.Client()

TOKEN_SIZE = client.models.get(model="models/gemini-embedding-001").input_token_limit
OVERLAPPING_WINDOW = round(TOKEN_SIZE/10)
STEP = round(OVERLAPPING_WINDOW*.8)

class ChatRequest(BaseModel):
    question: str | None = None

@app.post("/chat")
def chat(req: ChatRequest):

    response = client.models.embed_content(
        model="gemini-embedding-001", 
        contents=req.question,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY"
        )
    )

    query = "SELECT chunk_id, document_id, chunk_content FROM chunks ORDER BY embeddings <=> %s::vector LIMIT 5;"
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (response.embeddings[0].values,))
            records = cur.fetchall()
            
            formatted_context = "\n".join([f"Contexto {i}: {row[2]}" for i, row in enumerate(records)])
            
            prompt = f"""Usando APENAS as informações contidas no contexto abaixo, responda à pergunta: "{req.question}"

            Se a informação necessária para responder não estiver no contexto, responda apenas: "Não encontrei essa informação nos documentos fornecidos." Não tente adivinhar a resposta.

            {formatted_context}
            """
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )

            return response.text



class DocumentRequest(BaseModel):
    name: str
    content: str

@app.post("/document")
def chat(req: DocumentRequest):
    with pool.connection() as conn:
        with conn.cursor() as cur:
            document_id = cur.execute("INSERT INTO documents (name) VALUES (%s) RETURNING document_id;", (req.name,)).fetchone()[0];

            chunk_order = 0
            while True:
                start = chunk_order*STEP
                end = start + OVERLAPPING_WINDOW
                chunk_content = req.content[start:end]

                response = client.models.embed_content(
                    model="gemini-embedding-001", 
                    contents=chunk_content,
                    config=types.EmbedContentConfig(
                        task_type="RETRIEVAL_DOCUMENT",
                        title=req.name 
                    )
                )

                embeddings = response.embeddings[0].values

                cur.execute("INSERT INTO chunks (document_id, chunk_content, chunk_order, embeddings) VALUES (%s, %s, %s, %s::vector)",
                            (document_id, chunk_content, chunk_order, embeddings))

                if end >= len(req.content):
                    break

                chunk_order += 1
                
@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset="utf-8">
            <title>Labarq RAG</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 900px;
                    margin: 40px auto;
                    padding: 0 20px;
                }

                textarea {
                    width: 100%;
                    height: 120px;
                    font-size: 16px;
                    box-sizing: border-box;
                }

                button {
                    margin-top: 10px;
                    padding: 10px 20px;
                    font-size: 16px;
                }

                #response {
                    margin-top: 30px;
                    padding: 15px;
                    border: 1px solid #ccc;
                    white-space: pre-wrap;
                    min-height: 100px;
                }
            </style>
        </head>
        <body>
            <h1>Labarq RAG</h1>

            <textarea id="question"
                      placeholder="Digite sua pergunta"></textarea>

            <br>

            <button onclick="sendQuestion()">Perguntar</button>

            <h2>Resposta</h2>

            <div id="response"></div>

            <script>
                async function sendQuestion() {
                    const question = document.getElementById("question").value;
                    const responseDiv = document.getElementById("response");

                    responseDiv.textContent = "Consultando...";

                    try {
                        const response = await fetch("/chat", {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json"
                            },
                            body: JSON.stringify({
                                question: question
                            })
                        });

                        if (!response.ok) {
                            responseDiv.textContent =
                                "Erro HTTP " + response.status;
                            return;
                        }

                        const text = await response.text();
                        responseDiv.textContent = text;
                    } catch (e) {
                        responseDiv.textContent = e.toString();
                    }
                }
            </script>
        </body>
    </html>
    """
