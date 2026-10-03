import React, { useState, useRef, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import ReactDOM from "react-dom";

function Navbar() {
  const navigate = useNavigate();
  const token = localStorage.getItem("token");
  const user = localStorage.getItem("user") || "User";

  const [open, setOpen] = useState(false);
  const menuRef = useRef();

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    navigate("/login");
  };

  // ✅ FIXED useEffect + handler
  useEffect(() => {
    const handler = (e) => {
      // if click is inside avatar → ignore
      if (menuRef.current && menuRef.current.contains(e.target)) {
        return;
      }

      // if click is inside dropdown → ignore
      if (e.target.closest("#profile-dropdown")) {
        return;
      }

      // otherwise close
      setOpen(false);
    };

    document.addEventListener("click", handler);
    return () => document.removeEventListener("click", handler);
  }, []);

  return (
    <nav className="navbar px-4">
      <div className="container d-flex justify-content-between align-items-center">

        {/* Logo */}
        <h4
          style={{
            fontWeight: "700",
            background: "linear-gradient(90deg, #60a5fa, #a78bfa)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent"
          }}
        >
          🤖 AI Learning
        </h4>

        {/* Right side */}
        <div className="d-flex align-items-center gap-3">

          <Link to="/home" className="btn btn-outline-light">Home</Link>
          <Link to="/history" className="btn btn-outline-light">History</Link>

          {!token ? (
            <Link to="/login" className="btn btn-glow">
              Login
            </Link>
          ) : (
            <div ref={menuRef} style={{ position: "relative" }}>

              {/* Avatar */}
              <div
                onClick={() => setOpen(!open)}
                style={{
                  width: "38px",
                  height: "38px",
                  borderRadius: "50%",
                  background: "linear-gradient(135deg, #3b82f6, #9333ea)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  cursor: "pointer",
                  fontWeight: "bold",
                  transition: "0.3s"
                }}
              >
                {user.charAt(0).toUpperCase()}
              </div>

              {/* ✅ FIXED PORTAL */}
              {open &&
                typeof document !== "undefined" &&
                document.body &&
                ReactDOM.createPortal(
                  <div
                    id="profile-dropdown"   // ✅ ADDED
                    style={{
                      position: "fixed",
                      top: "70px",
                      right: "30px",
                      width: "240px",
                      padding: "15px",
                      borderRadius: "12px",
                      background: "rgba(15, 23, 42, 0.98)",
                      backdropFilter: "blur(20px)",
                      boxShadow: "0 20px 60px rgba(0,0,0,0.8)",
                      zIndex: 999999,
                      animation: "fadeSlide 0.25s ease"
                    }}
                  >

                    {/* User Info */}
                    <div className="mb-3">
                      <strong
                        style={{
                          color: "#f1f5f9",
                          fontSize: "14px",
                          display: "block"
                        }}
                      >
                        {user.length > 20 ? user.slice(0, 20) + "..." : user}
                      </strong>

                      <span style={{ fontSize: "12px", color: "#94a3b8" }}>
                        Logged in
                      </span>
                    </div>

                    <hr style={{ borderColor: "rgba(255,255,255,0.08)" }} />

                    {/* View Full */}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();   // ✅ ADDED
                        navigate("/history-list");
                      }}
                      className="btn btn-sm btn-outline-light w-100 mb-2"
                    >
                      View Full History →
                    </button>

                    {/* Logout */}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();   // ✅ ADDED
                        handleLogout();
                      }}
                      className="btn btn-sm btn-danger w-100"
                      style={{ borderRadius: "8px" }}
                    >
                      Logout
                    </button>

                  </div>,
                  document.body
                )}
            </div>
          )}

        </div>
      </div>
    </nav>
  );
}

export default Navbar;