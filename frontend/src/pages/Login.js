import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { loginUser } from "../services/api";

function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");

  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();

    setLoading(true);
    setError("");

    try {
      const res = await loginUser({ email, password });
      localStorage.setItem("token", res.data.token);
      localStorage.setItem("user", email);
      navigate("/home");
    } catch (err) {
      setError(err?.response?.data?.error || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="d-flex justify-content-center align-items-center"
      style={{
        minHeight: "100vh",
        position: "relative"
      }}
    >
      {/* 🔙 BACK BUTTON */}
      <button
        onClick={() => navigate("/")}
        style={{
          position: "absolute",
          top: "20px",
          left: "20px",
          background: "transparent",
          border: "1px solid #60a5fa",
          color: "#60a5fa",
          padding: "6px 12px",
          borderRadius: "8px",
          cursor: "pointer",
          fontSize: "14px"
        }}
      >
        ← Back
      </button>

      {/* 🔥 CARD */}
      <div
        className="glass-card p-4 animate-card"
        style={{
          width: "100%",
          maxWidth: "400px",
          backdropFilter: "blur(20px)"
        }}
      >
        {/* 🔥 Title */}
        <div className="text-center mb-4">
          <h3
            style={{
              background: "linear-gradient(90deg, #60a5fa, #a78bfa)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              fontWeight: "700"
            }}
          >
            🔐 Welcome Back
          </h3>

          <p style={{ color: "#94a3b8" }}>
            Login to continue your AI learning journey
          </p>
        </div>

        {/* 🔥 FORM */}
        <form onSubmit={handleLogin}>
          {error && (
            <div className="alert alert-danger py-2" role="alert">
              {error}
            </div>
          )}
          <div className="mb-3">
            <input
              type="email"
              className="form-control"
              placeholder="Enter Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          {/* 🔥 PASSWORD WITH TOGGLE */}
          <div className="mb-3 position-relative">
            <input
              type={showPassword ? "text" : "password"}
              className="form-control"
              placeholder="Enter Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />

            <span
              onClick={() => setShowPassword(!showPassword)}
              style={{
                position: "absolute",
                right: "10px",
                top: "8px",
                cursor: "pointer",
                color: "#94a3b8"
              }}
            >
              👁
            </span>
          </div>

          {/* 🔥 BUTTON */}
          <button
            className="btn btn-glow w-100 py-2"
            disabled={loading}
          >
            {loading ? "⏳ Logging in..." : "🚀 Login"}
          </button>
        </form>

        {/* 🔥 FOOTER */}
        <div className="text-center mt-3">
          <small style={{ color: "#64748b" }}>
            Demo mode works without backend
          </small>
        </div>

        <div className="text-center mt-3">
          <small style={{ color: "#94a3b8" }}>
            Don’t have an account?{" "}
            <Link to="/signup" style={{ color: "#60a5fa" }}>
              Sign up
            </Link>
          </small>
        </div>
      </div>
    </div>
  );
}

export default Login;