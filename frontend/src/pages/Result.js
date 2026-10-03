import React, { useState } from "react";
import { useLocation } from "react-router-dom";
import ImageCard from "../components/ImageCard";

const SOURCE_LABELS = {
  sana_base: "SANA 1.5 (base)",
  sana_lora: "SANA 1.5 + LoRA",
  sana_remote: "SANA 1.5 (workstation)",
  pollinations: "Pollinations.ai",
  placeholder: ""
};

// Label for image i: from the image_sources key of /generate, or (for older
// history entries, which do not store it) guessed from the URL.
function imageLabel(sources, url, index) {
  const source = sources && sources[index];
  if (source && source in SOURCE_LABELS) return SOURCE_LABELS[source];
  if (typeof url !== "string") return "";
  if (url.includes("image.pollinations.ai")) return SOURCE_LABELS.pollinations;
  if (/\/generated\/[0-9a-f]{32}\.png$/.test(url)) return "SANA 1.5";
  return "";
}

function Result() {
  const location = useLocation();
  const [selectedImage, setSelectedImage] = useState(null);
  const data = location.state;

  // ✅ Safe fallback (no crash)
  if (!data) {
    return (
      <div className="text-center mt-5" style={{ color: "#e2e8f0" }}>
        <h4>No data found</h4>
        <p>Please generate or select a topic again.</p>
      </div>
    );
  }

  // ✅ fallback values (same logic)
  const explanation = (data.explanation || "").includes("This is a safe fallback explanation.")
    ? `${data.topic || "This topic"} is a foundational concept worth learning step by step. Start with the basic idea, then focus on the important parts and how each part works together. Once the core process is clear, connect it to real-world use cases so it becomes easier to remember. Finally, review common mistakes learners make so you can avoid confusion and build strong understanding.`
    : (data.explanation || "AI-generated explanation will appear here.");
  const subtopics = (data.subtopics || []).map((item) => {
    if (typeof item === "string") {
      return { title: item, brief: "" };
    }
    return {
      title: item?.title || "Untitled",
      brief: item?.brief || ""
    };
  });
  const images = data.images || [];
  const imageSources = data.image_sources || null;

  return (
    <div className="container mt-5">

      {/* 🔥 Explanation */}
      <div className="glass-card p-4 mb-4">
        <h4 className="mb-3">🧠 Explanation</h4>
        <p style={{ color: "#cbd5f5" }}>{explanation}</p>
      </div>

      {/* 🔥 Subtopics */}
      <div className="glass-card p-4 mb-4">
        <h4 className="mb-3">📚 Key Topics</h4>

        {subtopics.length === 0 ? (
          <p style={{ color: "#94a3b8" }}>No subtopics available</p>
        ) : (
          <ul className="list-group list-group-flush">
            {subtopics.map((item, index) => (
              <li
                key={index}
                className="list-group-item"
                style={{
                  background: "transparent",
                  color: "#e2e8f0",
                  borderColor: "rgba(255,255,255,0.1)"
                }}
              >
                <div style={{ fontWeight: 600 }}>{item.title}</div>
                {item.brief ? (
                  <small style={{ color: "#94a3b8" }}>{item.brief}</small>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* 🔥 Images */}
      <div className="glass-card p-4">
        <h4 className="mb-4">🖼️ Visual Learning</h4>

        {images.length === 0 ? (
          <p style={{ color: "#94a3b8" }}>No images available</p>
        ) : (
          <div className="row">
            {images.map((img, index) => (
              <div className="col-md-4 mb-3" key={index} onClick={() => setSelectedImage(img)}>
                <ImageCard src={img} label={imageLabel(imageSources, img, index)} />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Lightbox Overlay */}
      {selectedImage && (
        <div 
          onClick={() => setSelectedImage(null)}
          style={{
            position: "fixed",
            top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: "rgba(0, 0, 0, 0.85)",
            backdropFilter: "blur(5px)",
            zIndex: 9999,
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            cursor: "zoom-out"
          }}
        >
          <img 
            src={selectedImage} 
            alt="Expanded view" 
            style={{
              maxHeight: "90vh",
              maxWidth: "90vw",
              objectFit: "contain",
              borderRadius: "8px",
              boxShadow: "0 10px 30px rgba(0,0,0,0.5)"
            }}
          />
        </div>
      )}

    </div>
  );
}

export default Result;