# 📚 Full-Stack RAG Application with Streaming

This is a comprehensive, full-stack **Retrieval-Augmented Generation (RAG)** application that allows users to upload documents (`.txt` and `.pdf`) and ask questions about their content. The application provides **grounded, streaming answers with source citations**, all delivered through a clean, modern web interface.

This project was built to demonstrate a deep understanding of modern AI application architecture, from frontend development to backend API integration and real-world debugging.

---

## 🏛️ Architecture
The application is composed of a **React frontend** and a **Flask backend**.  
The RAG pipeline follows a **retriever–reranker model** for high-quality, grounded answers.

### Ingestion Flow
User Uploads File (PDF/TXT) → Flask Backend → Text Extraction → Chunking
→ Google AI (Embeddings) → Pinecone (Upsert Vectors)



### Query Flow
User Asks Question → Flask Backend → Google AI (Embeddings) → Pinecone (Retrieve Top-k)
→ Cohere (Rerank) → Groq LLM (Generate Answer) → Real-Time Streaming → React Frontend



---

## ✨ Features
- 📄 **Document Upload**: Supports both `.txt` and `.pdf` file formats.  
- 🧠 **Advanced RAG Pipeline**: Uses Pinecone (retriever) + Cohere (reranker) for highly relevant context.  
- ⚡ **Real-Time Streaming**: Token-by-token streaming from backend to frontend.  
- 🔒 **Grounded Answers with Citations**: Citations point to specific source chunks.  
- ⚙️ **Full-Stack & Deployable**: Built with modern tech stack, deployable on platforms like Render.  

---

## 🛠️ Tech Stack
- **Frontend**: React (Vite), JavaScript  
- **Backend**: Python, Flask  
- **AI & Cloud Services**:
  - Vector Database: **Pinecone**
  - Embedding Model: **Google AI (text-embedding-004)**
  - Reranker: **Cohere (rerank-english-v3.0)**
  - LLM Provider: **Groq Cloud (llama-3.1-8b-instant)**

---

## 🔧 Setup and Local Installation

### Prerequisites
- Git  
- Python **3.10+**  
- Node.js **20+**  
- API keys from Pinecone, Google AI Studio, Cohere, and Groq Cloud  

---

### 1. Clone the Repository
```bash
git clone https://github.com/aaditya-01-28/RAG
cd https://github.com/aaditya-01-28/RAG
```

### 2. Backend Setup
```bash
# Navigate to the backend directory
cd backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate   # On Windows: .\venv\Scripts\activate

# Install dependencies
python -m pip install -r requirements.txt
```

### 3. Environment Variables
Create a .env file inside the backend/ directory with the following content:

```bash
# backend/.env

PINECONE_API_KEY="your_pinecone_api_key"
GOOGLE_API_KEY="your_google_ai_studio_api_key"
COHERE_API_KEY="your_cohere_api_key"
GROQ_API_KEY="your_groq_api_key"
```
### 4. Frontend Setup
```bash
# Navigate to the frontend directory from the root
cd frontend

# Install dependencies
npm install
```
# ▶️ Running the Application
You will need two separate terminals:

Terminal 1: Start the Backend
```bash
Copy code
cd backend
source venv/bin/activate   # Or .\venv\Scripts\activate on Windows
flask run
Backend runs at 👉 http://127.0.0.1:5000
```
Terminal 2: Start the Frontend
```bash
Copy code
cd frontend
npm run dev
Frontend runs at 👉 http://localhost:5173
```
### 📝 Remarks & Tradeoffs
API Model Decommissioning: During development, some providers (Groq, Cohere) decommissioned older models. The app was updated to use the latest models.
👉 Tip: Always keep model IDs configurable, since they change often.

Vector Deletion Strategy: Initially, the ingest endpoint cleared the entire Pinecone index before uploads, causing errors on empty indexes.
👉 Fixed by removing deletion step, now the app supports querying across multiple uploaded documents.