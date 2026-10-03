import React from "react";

function Loader() {
  return (
    <div className="text-center mt-4">
      <div className="spinner-border text-primary" style={{ width: "3rem", height: "3rem" }} />
      <p className="mt-3 text-muted">Generating content...</p>
    </div>
  );
}

export default Loader;