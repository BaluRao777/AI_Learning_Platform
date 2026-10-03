import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getHistory } from "../services/api";
import { useGeneratedImage } from "../components/ImageCard";

// Same <img> as before; only adds status polling for locally generated images.
function PreviewImage({ src, ...imgProps }) {
  const resolvedSrc = useGeneratedImage(src);
  return <img src={resolvedSrc} alt="preview" {...imgProps} />;
}

function History() {
  const apiBase = process.env.REACT_APP_API_BASE_URL || "http://localhost:5000";
  const toProxyUrl = (url) => {
    if (!url) return url;
    if (url.includes("/image-proxy?url=")) return url;
    if (url.startsWith("https://image.pollinations.ai/") || url.startsWith("https://picsum.photos/")) {
      return `${apiBase}/image-proxy?url=${encodeURIComponent(url)}`;
    }
    return url;
  };

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
        setError(err?.response?.data?.error || "Failed to fetch history");
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, []);

  return (
    <div className="container mt-5">

      {/* Title */}
      <div className="mb-4 text-center">
        <h2
          style={{
            fontWeight: "700",
            background: "linear-gradient(90deg, #60a5fa, #a78bfa)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent"
          }}
        >
          Your Learning History
        </h2>

        <p style={{ color: "#94a3b8" }}>
          Track your generated topics and visuals
        </p>
      </div>

      {loading ? (
        <div className="glass-card p-4 text-center">
          <p style={{ color: "#94a3b8" }}>Loading history...</p>
        </div>
      ) : error ? (
        <div className="glass-card p-4 text-center">
          <p style={{ color: "#fca5a5" }}>{error}</p>
        </div>
      ) : history.length === 0 ? (
        <div className="glass-card p-4 text-center">
          <p style={{ color: "#94a3b8" }}>
            No history yet. Start learning!
          </p>
        </div>
      ) : (
        <div className="row">

          {history.map((item, index) => (
            <div className="col-md-6 mb-4" key={index}>

              {/* ✅ CLICKABLE CARD (YOUR STEP ADDED HERE) */}
              <div
                className="glass-card p-3"
                onClick={() => navigate("/result", { state: item })}
                style={{
                  cursor: "pointer",
                  transition: "all 0.25s ease"
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = "scale(1.02)";
                  e.currentTarget.style.boxShadow = "0 10px 30px rgba(59,130,246,0.2)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = "scale(1)";
                  e.currentTarget.style.boxShadow = "none";
                }}
              >

                {/* Header */}
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <h5 style={{ color: "#e2e8f0" }}>
                    {item.topic || "Unknown"}
                  </h5>

                  <small style={{ color: "#94a3b8" }}>
                    {item.timestamp || "No date"}
                  </small>
                </div>

                {/* Images */}
                <div className="d-flex gap-2">
                  {(item.images || []).map((img, i) => (
                    <PreviewImage
                      key={i}
                      src={toProxyUrl(img)}
                      loading="lazy"
                      onError={(e) => {
                        const backup = `data:image/svg+xml;utf8,${encodeURIComponent(
                          `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="320">
                            <rect width="100%" height="100%" fill="#1e3a8a"/>
                            <text x="50%" y="50%" text-anchor="middle" fill="#e2e8f0" font-size="18" font-family="Arial">Preview unavailable</text>
                          </svg>`
                        )}`;
                        if (e.currentTarget.src !== backup) e.currentTarget.src = backup;
                      }}
                      style={{
                        width: "100px",
                        height: "80px",
                        objectFit: "cover",
                        borderRadius: "8px"
                      }}
                    />
                  ))}
                </div>

              </div>

            </div>
          ))}

        </div>
      )}

    </div>
  );
}

export default History;