import { useState } from "react"
import "./App.css"

function App() {
  const [file, setFile] = useState(null)
  const [summary, setSummary] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  const handleFileChange = (e) => {
    setFile(e.target.files[0])
  }

  const handleUpload = async () => {
    if (!file) {
      alert("Please select a PDF file first")
      return
    }

    const formData = new FormData()
    formData.append("file", file)

    try {
      setLoading(true)
      setError("")
      setSummary("")

      const response = await fetch("http://localhost:8000/OCR", {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        throw new Error("Failed to fetch summary")
      }

      const data = await response.json()
      console.log("Data :", data)
      setSummary(data.summary)

    } catch (err) {
      setError("Error uploading file or summarizing.")
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: "40px", fontFamily: "Arial" }}>
      <h1>Understand AI - PDF Summarizer</h1>

      <input 
        type="file" 
        accept="application/pdf"
        onChange={handleFileChange} 
      />

      <br /><br />

      <button onClick={handleUpload}>
        Upload & Summarize
      </button>

      <br /><br />

      {loading && <p>⏳ Summarizing...</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      {summary && (
        <div style={{
          marginTop: "20px",
          padding: "20px",
          border: "1px solid #ccc",
          borderRadius: "8px",
          background: "#000000"
        }}>
          <h3>Summary:</h3>
          <p style={{ whiteSpace: "pre-wrap" }}>
            {summary}
          </p>
        </div>
      )}
    </div>
  )
}

export default App
