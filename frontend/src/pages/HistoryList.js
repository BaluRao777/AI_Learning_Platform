import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getHistory } from "../services/api";

function HistoryList() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await getHistory();
        setHistory(res.data);
      } catch (err) {
        setError(err?.response?.data?.error || `Network Error: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, []);

  return (
    <div style={{ color: "#e2e8f0" }}>

      {/* Title */}
      <div className="text-center mb-4">
        <h2
          style={{
            fontWeight: "700",
            background: "linear-gradient(90deg, #60a5fa, #a78bfa)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent"
          }}
        >
          📜 Your Search History
        </h2>

        <p style={{ color: "#94a3b8" }}>
          Click any topic to view full explanation
        </p>
      </div>

      {/* List */}
      <div className="glass-card p-3">

        {loading ? (
          <p style={{ color: "#94a3b8" }}>Loading...</p>
        ) : error ? (
          <p style={{ color: "#fca5a5" }}>{error}</p>
        ) : history.length === 0 ? (
          <p style={{ color: "#94a3b8" }}>No history found</p>
        ) : (
          history.map((item, index) => (
            <div
              key={index}
              onClick={() => navigate("/result", { state: item })}
              style={{
                padding: "12px",
                borderBottom: "1px solid rgba(255,255,255,0.1)",
                cursor: "pointer",
                transition: "all 0.2s ease"
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(59,130,246,0.12)";
                e.currentTarget.style.transform = "translateX(4px)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "transparent";
                e.currentTarget.style.transform = "translateX(0)";
              }}
            >
              <strong style={{ color: "#e2e8f0" }}>
                {item.topic || "Unknown"}
              </strong>

              <div style={{ fontSize: "12px", color: "#94a3b8" }}>
                {item.timestamp || "No date"}
              </div>
            </div>
          ))
        )}

      </div>
    </div>
  );
}

export default HistoryList;