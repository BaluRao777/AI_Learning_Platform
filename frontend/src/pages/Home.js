import React, { useState } from "react";
import InputForm from "../components/InputForm";
import { useNavigate } from "react-router-dom";
import Loader from "../components/Loader";
import { generateContent } from "../services/api"; // ✅ backend API

function Home() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleGenerate = async (data) => {
    setLoading(true);
    setError("");

    try {
      const res = await generateContent({
        topic: data.topic,
        level: data.level,
        mode: data.mode
      });

      // ✅ SAME FLOW (just real data instead of fake)
      navigate("/result", { state: res.data });

    } catch (err) {
      setError(err?.response?.data?.error || "Generation failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="d-flex justify-content-center align-items-center"
      style={{ minHeight: "80vh" }}
    >
      <div style={{ width: "100%", maxWidth: "500px" }}>

        {/* 🔥 HERO TITLE */}
        <div className="text-center mb-4">
          <h1
            style={{
              fontWeight: "700",
              background: "linear-gradient(90deg, #60a5fa, #a78bfa)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent"
            }}
          >
            AI Learning Experience
          </h1>

          <p style={{ color: "#cbd5f5" }}>
            Smart explanations • Visual learning • Instant insights
          </p>
        </div>

        {/* FORM */}
        <InputForm onGenerate={handleGenerate} />
        {error && (
          <div className="alert alert-danger mt-3 py-2" role="alert">
            {error}
          </div>
        )}

        {/* LOADER */}
        {loading && <Loader />}

      </div>
    </div>
  );
}

export default Home;