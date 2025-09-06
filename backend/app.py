import os
import fitz
import json
from flask import Flask, request, jsonify, Response
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from langchain_text_splitters import RecursiveCharacterTextSplitter
import google.generativeai as genai
import cohere
import groq
from flask_cors import CORS

load_dotenv()

# --- INITIALIZE CLIENTS ---
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
co = cohere.Client(os.getenv("COHERE_API_KEY"))
groq_client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))

# --- CONFIGURATION ---
INDEX_NAME = "rag-app-index"
EMBEDDING_MODEL = "models/text-embedding-004"
LLM_MODEL = "llama-3.1-8b-instant"
DIMENSIONALITY = 768 # For Google's text-embedding-004

app = Flask(__name__)
CORS(app) # Enable Cross-Origin Resource Sharing

# --- CREATE PINECONE INDEX (if it doesn't exist) ---
if INDEX_NAME not in pc.list_indexes().names():
    pc.create_index(
        name=INDEX_NAME,
        dimension=DIMENSIONALITY,
        metric="cosine", # Cosine similarity is great for text
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
index = pc.Index(INDEX_NAME)

# --- API ENDPOINTS ---
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200


@app.route('/ingest', methods=['POST'])
def ingest():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    text_content = ""
    # Check for .txt files
    if file.filename.endswith('.txt'):
        text_content = file.read().decode('utf-8')
    # Check for .pdf files
    elif file.filename.endswith('.pdf'):
        try:
            # Use PyMuPDF to open the PDF
            pdf_document = fitz.open(stream=file.read(), filetype="pdf")
            for page in pdf_document:
                text_content += page.get_text()
            pdf_document.close()
        except Exception as e:
            return jsonify({"error": f"Error processing PDF file: {str(e)}"}), 500
    else:
        return jsonify({"error": "Unsupported file type. Please upload a .txt or .pdf file."}), 400

    # --- The rest of the logic is the same as before ---
    try:
        # Chunking
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = text_splitter.split_text(text_content)

        # Clear the index before ingesting new content
        # index.delete(delete_all=True)
        if not chunks:
            return jsonify({"error": "Could not process text from the document. The file might be empty or contain no usable text."}), 400

            # Embedding and Upserting
        vectors_to_upsert = []
        for i, chunk in enumerate(chunks):
            embedding = genai.embed_content(
                model=EMBEDDING_MODEL,
                content=chunk,
                task_type="RETRIEVAL_DOCUMENT"
            )["embedding"]

            vectors_to_upsert.append({
                "id": f"chunk_{i}",
                "values": embedding,
                "metadata": {
                    "text": chunk,
                    "source": file.filename,
                    "position": i
                }
            })
        
        index.upsert(vectors=vectors_to_upsert)
        
        return jsonify({"message": f"Successfully ingested {len(chunks)} chunks from {file.filename}."}), 200

    except Exception as e:
        return jsonify({"error": f"Error during embedding/upserting: {str(e)}"}), 500
        
@app.route('/query', methods=['POST'])
def query():
    data = request.get_json()
    user_query = data.get('query')

    if not user_query:
        return jsonify({"error": "No query provided"}), 400

    def generate_response():
        try:
            # 1. Embed the query
            query_embedding = genai.embed_content(
                model=EMBEDDING_MODEL,
                content=user_query,
                task_type="RETRIEVAL_QUERY"
            )["embedding"]

            # 2. Retrieve from Vector DB
            retrieval_results = index.query(vector=query_embedding, top_k=10, include_metadata=True)
            retrieved_docs = [match['metadata']['text'] for match in retrieval_results['matches']]

            # 3. Rerank the results
            reranked_docs = co.rerank(
                query=user_query,
                documents=retrieved_docs,
                top_n=3,
                model="rerank-english-v3.0"
            )

            # 4. Build context for LLM
            context_chunks = []
            source_citations = []
            for i, doc in enumerate(reranked_docs.results):
                doc_text = retrieved_docs[doc.index]
                context_chunks.append(doc_text)
                source_citations.append({
                    "id": i + 1,
                    "source_text": doc_text
                })
            
            context_str = "\n\n".join(context_chunks)

            # 5. Generate Answer with LLM, now with streaming
            prompt = f"""
            You are an expert Q&A assistant. Your task is to answer the user's question based ONLY on the provided context.
            Provide a clear, concise answer and cite the context using inline citations like [1], [2], etc.
            The number in the citation should correspond to the source number.
            If the answer is not in the context, state that you cannot answer based on the information provided.

            Context:
            ---
            [1] {source_citations[0]['source_text']}
            ---
            [2] {source_citations[1]['source_text']}
            ---
            [3] {source_citations[2]['source_text']}
            ---

            Question: {user_query}

            Answer:
            """

            # The key change: stream=True
            stream = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=LLM_MODEL,
                stream=True,
            )

            # Yield each chunk of the response as it comes in
            for chunk in stream:
                chunk_text = chunk.choices[0].delta.content
                if chunk_text:
                    # Send each piece of the text stream
                    yield json.dumps({"type": "chunk", "data": chunk_text}) + "\n"
            
            # After the text stream is finished, send the citations
            yield json.dumps({"type": "citations", "data": source_citations}) + "\n"

        except Exception as e:
            # Handle potential errors during streaming
            yield json.dumps({"type": "error", "data": str(e)}) + "\n"
    
    # Return a streaming response
    return Response(generate_response(), mimetype='application/json')


# (Query endpoint will be added next)
if __name__ == '__main__':
    app.run(debug=True)