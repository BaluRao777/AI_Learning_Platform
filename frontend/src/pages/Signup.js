import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { signupUser } from "../services/api";

function Signup() {
  const navigate = useNavigate();
  const firstNameRef = useRef();

  const [form, setForm] = useState({
    firstName: "",
    lastName: "",
    email: "",
    day: "",
    month: "",
    year: "",
    phone: "",
    password: "",
    confirmPassword: ""
  });

  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [submitError, setSubmitError] = useState("");

  useEffect(() => {
    firstNameRef.current.focus();
  }, []);

  // 🔥 PASSWORD RULE
  const passwordRegex = /^(?=.*[A-Z])(?=.*[!@#$%^&*]).{8,}$/;

  const handleChange = (e) => {
    const { name, value } = e.target;

    if (name === "phone") {
      const numeric = value.replace(/\D/g, "");
      if (numeric.length <= 10) {
        setForm({ ...form, phone: numeric });
      }
      return;
    }

    setForm({ ...form, [name]: value });
  };

  const validate = () => {
    let newErrors = {};

    if (!form.firstName) newErrors.firstName = true;
    if (!form.lastName) newErrors.lastName = true;
    if (!form.email) newErrors.email = true;

    if (!form.day || !form.month || !form.year) {
      newErrors.dob = true;
    }

    if (form.phone.length !== 10) newErrors.phone = true;

    if (!passwordRegex.test(form.password)) {
      newErrors.password = true;
    }

    if (form.password !== form.confirmPassword) {
      newErrors.confirmPassword = true;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const triggerShake = () => {
    document.querySelectorAll(".input-box").forEach((el) => {
      el.classList.add("shake");
      setTimeout(() => el.classList.remove("shake"), 400);
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
  
    if (!validate()) {
      triggerShake();
      return;
    }
  
    setLoading(true);
    setSubmitError("");
  
    try {
      await signupUser({
        email: form.email,
        password: form.password
      });
  
      navigate("/login");
  
    } catch (err) {
      setSubmitError(err?.response?.data?.error || "Signup failed");
    } finally {
      setLoading(false);
    }
  };



  const getBorder = (field) => {
    if (errors[field]) return "2px solid #ef4444";
    if (form[field]) return "2px solid #22c55e";
    return "2px solid #334155";
  };

  const getStrength = () => {
    let score = 0;
    if (form.password.length >= 8) score += 30;
    if (/[A-Z]/.test(form.password)) score += 30;
    if (/[!@#$%^&*]/.test(form.password)) score += 40;
    return score;
  };

  return (
    <div
      className="d-flex justify-content-center align-items-center"
      style={{ minHeight: "100vh", position: "relative" }}
    >
      {/* 🔙 BACK */}
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
          cursor: "pointer"
        }}
      >
        ← Back
      </button>

      <div className="glass-card p-4 animate-card" style={{ width: "420px" }}>
        <h3 className="text-center mb-3">Create Account</h3>

        <form onSubmit={handleSubmit}>
          {submitError && (
            <div className="alert alert-danger py-2" role="alert">
              {submitError}
            </div>
          )}

          <input
            ref={firstNameRef}
            name="firstName"
            placeholder="First name"
            className="form-control mb-2 input-box"
            style={{ border: getBorder("firstName") }}
            onChange={handleChange}
          />

          <input
            name="lastName"
            placeholder="Last name"
            className="form-control mb-2 input-box"
            style={{ border: getBorder("lastName") }}
            onChange={handleChange}
          />

          <input
            name="email"
            placeholder="Email"
            className="form-control mb-2 input-box"
            style={{ border: getBorder("email") }}
            onChange={handleChange}
          />

          {/* DOB */}
          <div className="d-flex gap-2 mb-2">
            <select
              className="form-control input-box"
              style={{ border: getBorder("dob") }}
              onChange={(e) => setForm({ ...form, day: e.target.value })}
            >
              <option>Day</option>
              {[...Array(31)].map((_, i) => <option key={i}>{i + 1}</option>)}
            </select>

            <select
              className="form-control input-box"
              style={{ border: getBorder("dob") }}
              onChange={(e) => setForm({ ...form, month: e.target.value })}
            >
              <option>Month</option>
              {["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
                .map((m, i) => <option key={i}>{m}</option>)}
            </select>

            <select
              className="form-control input-box"
              style={{ border: getBorder("dob") }}
              onChange={(e) => setForm({ ...form, year: e.target.value })}
            >
              <option>Year</option>
              {[...Array(50)].map((_, i) => <option key={i}>{2026 - i}</option>)}
            </select>
          </div>

          <input
            name="phone"
            placeholder="Phone number"
            className="form-control mb-2 input-box"
            value={form.phone}
            style={{ border: getBorder("phone") }}
            onChange={handleChange}
          />

          {/* PASSWORD */}
          <div className="position-relative mb-2">
            <input
              type={showPassword ? "text" : "password"}
              name="password"
              placeholder="Password"
              className="form-control input-box"
              style={{ border: getBorder("password") }}
              onChange={handleChange}
            />
            <span
              onClick={() => setShowPassword(!showPassword)}
              style={{ position: "absolute", right: "10px", top: "10px", cursor: "pointer" }}
            >
              👁
            </span>
          </div>

          <div style={{ fontSize: "12px", color: "#94a3b8" }}>
            ✔ Minimum 8 characters <br />
            ✔ One Capital Letter <br />
            ✔ One Special Symbol
          </div>

          <input
            type={showPassword ? "text" : "password"}
            name="confirmPassword"
            placeholder="Confirm password"
            className="form-control mb-2 input-box"
            style={{ border: getBorder("confirmPassword") }}
            onChange={handleChange}
          />

          {/* STRENGTH */}
          <div style={{ height: "5px", background: "#1e293b", marginBottom: "12px" }}>
            <div
              style={{
                width: `${getStrength()}%`,
                height: "100%",
                background: getStrength() === 100 ? "#22c55e" : "#f59e0b"
              }}
            />
          </div>

          <button className="btn btn-glow w-100" disabled={loading}>
            {loading ? "⏳ Creating..." : "Sign Up"}
          </button>

        </form>

        <div className="text-center mt-3">
          Already have an account?{" "}
          <span
            style={{ color: "#60a5fa", cursor: "pointer" }}
            onClick={() => navigate("/login")}
          >
            Log in
          </span>
        </div>
      </div>
    </div>
  );
}

export default Signup;