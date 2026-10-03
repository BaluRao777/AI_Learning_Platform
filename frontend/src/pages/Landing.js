import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion, useMotionValue, useSpring } from "framer-motion";
import { BrainCircuit, Image as ImageIcon, Zap, ArrowRight, ShieldCheck, Sparkles } from "lucide-react";

// ─── Hero text ───
const HERO_LINE_1 = "Master Complex Topics with";
const HERO_LINE_2 = "AI-Powered Clarity";

function Landing() {
  const navigate = useNavigate();

  const wordsPart1 = HERO_LINE_1.split(" ");
  const wordsPart2 = HERO_LINE_2.split(" ");

  const wordVariants = {
    hidden: () => ({
      opacity: 0,
      x: (Math.random() - 0.5) * 1000,
      y: (Math.random() - 0.5) * 1000,
      rotate: (Math.random() - 0.5) * 200,
      scale: 0.1,
    }),
    visible: {
      opacity: 1,
      x: 0,
      y: 0,
      rotate: 0,
      scale: 1,
      transition: {
        type: "spring",
        damping: 12,
        stiffness: 40,
        mass: 2.5
      }
    }
  };

  const textContainerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.2,
      }
    }
  };

  // Custom Cursor Logic
  const cursorX = useMotionValue(-100);
  const cursorY = useMotionValue(-100);
  const springConfig = { damping: 25, stiffness: 150, mass: 0.5 };
  const cursorXSpring = useSpring(cursorX, springConfig);
  const cursorYSpring = useSpring(cursorY, springConfig);

  useEffect(() => {
    const moveCursor = (e) => {
      cursorX.set(e.clientX - 16);
      cursorY.set(e.clientY - 16);
    };
    window.addEventListener("mousemove", moveCursor);
    return () => window.removeEventListener("mousemove", moveCursor);
  }, [cursorX, cursorY]);

  // ── Landing page (the cinematic intro was removed; the page shows immediately) ──
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 1.2, ease: "easeOut" }}
      style={{ color: "#fff", position: "relative", overflowX: "hidden", minHeight: "100vh" }}
    >
      {/* Antigraviti Style Cursor */}
      <motion.div
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          width: "32px",
          height: "32px",
          borderRadius: "50%",
          backgroundColor: "rgba(139, 92, 246, 0.4)",
          filter: "blur(4px)",
          border: "2px solid rgba(139, 92, 246, 0.8)",
          pointerEvents: "none",
          zIndex: 9999,
          x: cursorXSpring,
          y: cursorYSpring,
        }}
      />

      {/* Background Animated Grid & Orbs */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5, duration: 1 }}>
        <div className="bg-grid"></div>
        <div className="floating-orb orb-1"></div>
        <div className="floating-orb orb-2"></div>
        <div className="floating-orb orb-3"></div>
      </motion.div>

      {/* 🚀 HERO SECTION */}
      <section
        style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          textAlign: "center",
          padding: "20px",
          position: "relative",
          zIndex: 2,
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          style={{ maxWidth: "800px" }}
        >
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 1, delay: 0.2 }}
            style={{ marginBottom: "20px" }}
          >
            <span style={{
              background: "rgba(139, 92, 246, 0.1)",
              border: "1px solid rgba(139, 92, 246, 0.3)",
              padding: "8px 16px",
              borderRadius: "20px",
              fontSize: "14px",
              color: "#c4b5fd",
              display: "inline-flex",
              alignItems: "center",
              gap: "8px"
            }}>
              <Sparkles size={16} /> Welcome to the Future of Learning
            </span>
          </motion.div>

          <motion.h1
            variants={textContainerVariants}
            initial="hidden"
            animate="visible"
            style={{
              fontSize: "clamp(40px, 6vw, 64px)",
              fontWeight: "800",
              lineHeight: "1.2",
              marginBottom: "20px",
              display: "flex",
              flexWrap: "wrap",
              justifyContent: "center",
              gap: "12px"
            }}>
            {wordsPart1.map((word, i) => (
              <motion.span key={`p1-${i}`} variants={wordVariants} custom={i} style={{ display: "inline-block" }}>
                {word}
              </motion.span>
            ))}
            <div style={{ width: "100%", height: 0 }}></div>
            {wordsPart2.map((word, i) => (
              <motion.span key={`p2-${i}`} variants={wordVariants} custom={i} className="gradient-text" style={{ display: "inline-block" }}>
                {word}
              </motion.span>
            ))}
          </motion.h1>

          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5, duration: 1 }}>
            <p style={{ maxWidth: "600px", margin: "0 auto 40px auto", color: "#94a3b8", fontSize: "18px", lineHeight: "1.6" }}>
              Transform the way you learn. Generate intelligent explanations,
              stunning visuals, and structured knowledge instantly. Built for the modern mind.
            </p>

            <div className="d-flex gap-3 justify-content-center">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="btn btn-glow px-4 py-3 d-flex align-items-center gap-2"
                onClick={() => navigate("/login")}
                style={{ fontSize: "16px" }}
              >
                <Zap size={20} /> Login Now
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="btn btn-glow px-4 py-3 d-flex align-items-center gap-2"
                onClick={() => navigate("/signup")}
                style={{ fontSize: "16px" }}
              >
                Sign Up <ArrowRight size={20} />
              </motion.button>
            </div>
          </motion.div>
        </motion.div>
      </section>

      {/* 💡 FEATURES SECTION */}
      <section style={{ padding: "100px 20px", position: "relative", zIndex: 2 }}>
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8 }}
          style={{ textAlign: "center", marginBottom: "60px" }}
        >
          <h2 style={{ fontWeight: "700", fontSize: "36px", marginBottom: "16px" }}>Why This Platform?</h2>
          <p style={{ color: "#94a3b8", maxWidth: "600px", margin: "0 auto" }}>
            Experience an intelligence-first approach to acquiring new skills and understanding the world.
          </p>
        </motion.div>

        <div className="container">
          <div className="row g-4">
            {[
              {
                icon: <BrainCircuit size={32} color="#3b82f6" />,
                title: "Smart Learning",
                desc: "AI generates structured explanations instantly, tailored to your pace."
              },
              {
                icon: <ImageIcon size={32} color="#8b5cf6" />,
                title: "Visual Understanding",
                desc: "Learn concepts with powerful, context-aware AI-generated visuals."
              },
              {
                icon: <Zap size={32} color="#ec4899" />,
                title: "Fast & Efficient",
                desc: "Get comprehensive results in seconds, turning hours of study into minutes."
              }
            ].map((feature, idx) => (
              <div className="col-md-4" key={idx}>
                <motion.div
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: "-50px" }}
                  transition={{ duration: 0.5, delay: idx * 0.2 }}
                  className="glass-card p-5 h-100"
                  style={{ textAlign: "left" }}
                >
                  <div style={{
                    background: "rgba(255,255,255,0.05)",
                    width: "64px",
                    height: "64px",
                    borderRadius: "16px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    marginBottom: "24px",
                    border: "1px solid rgba(255,255,255,0.1)"
                  }}>
                    {feature.icon}
                  </div>
                  <h4 style={{ fontWeight: "600", marginBottom: "16px" }}>{feature.title}</h4>
                  <p style={{ color: "#94a3b8", margin: 0, lineHeight: "1.6" }}>{feature.desc}</p>
                </motion.div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 🚀 ABOUT SECTION */}
      <section style={{ padding: "100px 20px", position: "relative", zIndex: 2 }}>
        <div className="container">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="glass-card p-5"
            style={{
              background: "linear-gradient(145deg, rgba(15, 23, 42, 0.8), rgba(2, 6, 23, 0.9))",
              textAlign: "center",
              border: "1px solid rgba(59, 130, 246, 0.2)",
              maxWidth: "900px",
              margin: "0 auto"
            }}
          >
            <ShieldCheck size={48} color="#3b82f6" style={{ marginBottom: "24px" }} />
            <h2 style={{ fontWeight: "700", fontSize: "32px", marginBottom: "24px" }}>About the Project</h2>
            <p style={{ color: "#cbd5e1", fontSize: "18px", lineHeight: "1.8", margin: 0 }}>
              This AI-powered platform is designed to simplify complex topics
              into understandable visual and textual content. It helps students,
              engineers, and learners grasp difficult concepts quickly and effectively, bridging the gap between curiosity and mastery.
            </p>
          </motion.div>
        </div>
      </section>

      {/* 🎯 FINAL CTA */}
      <section style={{ padding: "120px 20px", textAlign: "center", position: "relative", zIndex: 2 }}>
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
        >
          <h2 style={{ fontWeight: "800", fontSize: "40px", marginBottom: "24px" }}>
            Ready to Transform Your Learning?
          </h2>
          <p style={{ color: "#94a3b8", marginBottom: "40px", fontSize: "18px" }}>Join the revolution of AI-assisted education today.</p>

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="btn btn-glow px-5 py-3 d-inline-flex align-items-center gap-2"
            onClick={() => navigate("/signup")}
            style={{ fontSize: "18px", borderRadius: "30px" }}
          >
            Get Started <ArrowRight size={20} />
          </motion.button>
        </motion.div>
      </section>
    </motion.div>
  );
}

export default Landing;