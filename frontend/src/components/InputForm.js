import React, { useState } from "react";

function InputForm({ onGenerate }) {
  const [topic, setTopic] = useState("");
  const [level, setLevel] = useState("school");
  const [mode, setMode] = useState("learn");

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!topic.trim()) {
      alert("Please enter a topic");
      return;
    }

    onGenerate({ topic, level, mode });
  };

  return (
    <div className="card shadow p-4">
      <h4 className="mb-3">Generate Learning Content</h4>

      <form onSubmit={handleSubmit}>
        <div className="mb-3">
          <label className="form-label">Topic</label>
          <input
            type="text"
            className="form-control"
            placeholder="Enter topic (e.g., Photosynthesis)"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
          />
        </div>

        <div className="mb-3">
          <label className="form-label">Difficulty Level</label>
          <select
            className="form-select"
            value={level}
            onChange={(e) => setLevel(e.target.value)}
          >
            <option value="school">School</option>
            <option value="college">College</option>
          </select>
        </div>

        <div className="mb-3">
          <label className="form-label">Learning Mode</label>
          <select
            className="form-select"
            value={mode}
            onChange={(e) => setMode(e.target.value)}
          >
            <option value="learn">Learn</option>
            <option value="exam">Exam</option>
          </select>
        </div>

        <button className="btn btn-primary w-100 py-2 fw-bold">
        🚀 Generate Content
        </button>
      </form>
    </div>
  );
}

export default InputForm;