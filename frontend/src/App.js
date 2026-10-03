import React from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  useLocation
} from "react-router-dom";

import Navbar from "./components/Navbar";
import Landing from "./pages/Landing";
import Home from "./pages/Home";
import Result from "./pages/Result";
import History from "./pages/History";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import HistoryList from "./pages/HistoryList";
import ProtectedRoute from "./components/ProtectedRoute";
import ErrorBoundary from "./components/ErrorBoundary";
import TubesCursor from "./components/TubesCursor";

function AppContent() {
  const location = useLocation();

  // 🔥 Centralized route control (easy to scale later)
  const noNavbarRoutes = ["/", "/login", "/signup"];

  const showNavbar = !noNavbarRoutes.includes(location.pathname);

  return (
    <ErrorBoundary>
      {/* ✅ Navbar control */}
      {showNavbar && <Navbar />}

      {/* 🔥 Full-width layout for landing/login/signup */}
      <div
        className={
          noNavbarRoutes.includes(location.pathname)
            ? ""
            : "container mt-4"
        }
      >
        <Routes>

          {/* 🔥 Landing (First Page) */}
          <Route path="/" element={<Landing />} />

          {/* 🔐 Auth Pages */}
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />

          {/* 🔥 Main App Pages */}
          <Route path="/home" element={<ProtectedRoute><Home /></ProtectedRoute>} />
          <Route path="/result" element={<ProtectedRoute><Result /></ProtectedRoute>} />
          <Route path="/history" element={<ProtectedRoute><History /></ProtectedRoute>} />
          <Route path="/history-list" element={<ProtectedRoute><HistoryList /></ProtectedRoute>} />

          {/* 🔥 Fallback (important for production) */}
          <Route path="*" element={<Landing />} />

        </Routes>
      </div>
      <TubesCursor />
    </ErrorBoundary>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;