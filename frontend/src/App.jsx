import React, { useState } from 'react';
import './index.css';

function App() {
  const [selectedFile, setSelectedFile] = useState(null); // Changed from textContent
  const [query, setQuery] = useState('');
  const [answer, setAnswer] = useState(null);
  const [citations, setCitations] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const backendUrl = 'http://127.0.0.1:5000';

  const handleIngest = async () => {
    if (!selectedFile) {
      alert("Please select a file first.");
      return;
    }
    setIsLoading(true);
    setError('');

    // Use FormData to send the file
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch(`${backendUrl}/ingest`, {
        method: 'POST',
        body: formData, // The browser will set the correct Content-Type
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.error || 'Ingestion failed. Is the backend running?');
      }

      const data = await response.json();
      alert(data.message);
      setSelectedFile(null); // Clear the file input after successful upload
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuery = async () => {
    setIsLoading(true);
    setError('');
    setAnswer(''); // Reset answer to an empty string for streaming
    setCitations([]);

    try {
        const response = await fetch(`${backendUrl}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query }),
        });

        if (!response.ok) {
            throw new Error('Query failed. Is the backend running?');
        }

        // Use the ReadableStream API to process the response
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        // Loop to read the stream
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n').filter(line => line.trim() !== '');

            for (const line of lines) {
                const parsed = JSON.parse(line);
                if (parsed.type === 'chunk') {
                    // Append the new text chunk to the existing answer
                    setAnswer(prev => prev + parsed.data);
                } else if (parsed.type === 'citations') {
                    // Set the citations once the stream is done
                    setCitations(parsed.data);
                } else if (parsed.type === 'error') {
                    // Handle any errors sent from the backend
                    setError(parsed.data);
                }
            }
        }

    } catch (err) {
        setError(err.message);
    } finally {
        setIsLoading(false);
    }
};
  return (
    <div className="container">
      <h1>📚 RAG Query App</h1>
      
      <div className="card">
        <h2>Step 1: Ingest Document</h2>
        {/* Changed from textarea to file input */}
        <input 
          type="file" 
          accept=".txt,.pdf"
          onChange={(e) => setSelectedFile(e.target.files[0])} 
        />
        <button onClick={handleIngest} disabled={isLoading || !selectedFile}>
          {isLoading ? 'Ingesting...' : 'Ingest File'}
        </button>
      </div>

      <div className="card">
        <h2>Step 2: Ask a Question</h2>
        <input
          type="text"
          placeholder="What do you want to know?"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button onClick={handleQuery} disabled={isLoading || !query}>
          {isLoading ? 'Thinking...' : 'Get Answer'}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {answer && (
        <div className="card answer-card">
          <h2>Answer</h2>
          <p>{answer}</p>
          <h3>Sources</h3>
          {citations.map((citation) => (
            <div key={citation.id} className="citation">
              <strong>[{citation.id}]</strong>
              <p>{citation.source_text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;