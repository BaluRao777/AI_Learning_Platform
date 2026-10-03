import React, { useEffect, useState } from "react";

const POLL_INTERVAL_MS = 3000;
const POLL_MAX_MS = 10 * 60 * 1000;

// Locally generated images (/generated/<id>.png) are rendered in the background.
// Poll their status and return a cache-busted URL once the PNG is ready.
// Any other URL is returned unchanged.
export function useGeneratedImage(src) {
  const [resolvedSrc, setResolvedSrc] = useState(src);

  useEffect(() => {
    setResolvedSrc(src);
    if (typeof src !== "string" || !/\/generated\/[0-9a-f]{32}\.png$/.test(src)) {
      return undefined;
    }

    const statusUrl = `${src.slice(0, -4)}/status`;
    const startedAt = Date.now();
    let cancelled = false;
    let timer = null;

    const poll = async () => {
      let status = "pending";
      try {
        const res = await fetch(statusUrl, { cache: "no-store" });
        if (res.ok) {
          status = (await res.json()).status;
        }
      } catch (err) {
        // backend unreachable: keep polling until the time limit
      }
      if (cancelled) return;
      if (status === "done" || status === "failed") {
        setResolvedSrc(`${src}?v=${Date.now()}`);
        return;
      }
      if (Date.now() - startedAt < POLL_MAX_MS) {
        timer = setTimeout(poll, POLL_INTERVAL_MS);
      }
    };

    poll();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [src]);

  return resolvedSrc;
}

function ImageCard({ src, label }) {
  const resolvedSrc = useGeneratedImage(src);
  const fallbackSvg = `data:image/svg+xml;utf8,${encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="768" height="512">
      <rect width="100%" height="100%" fill="#1e3a8a"/>
      <text x="50%" y="48%" text-anchor="middle" fill="#e2e8f0" font-size="24" font-family="Arial">Image unavailable</text>
      <text x="50%" y="58%" text-anchor="middle" fill="#bfdbfe" font-size="16" font-family="Arial">Try generate again</text>
    </svg>`
  )}`;

  return (
    <div
      style={{
        borderRadius: "12px",
        overflow: "hidden",
        transition: "0.3s",
        cursor: "pointer"
      }}
      onMouseOver={(e) => (e.currentTarget.style.transform = "scale(1.05)")}
      onMouseOut={(e) => (e.currentTarget.style.transform = "scale(1)")}
    >
      <img
        src={resolvedSrc}
        alt="generated"
        loading="lazy"
        onError={(e) => {
          if (e.currentTarget.src !== fallbackSvg) {
            e.currentTarget.src = fallbackSvg;
          }
        }}
        style={{
          width: "100%",
          height: "200px",
          objectFit: "cover"
        }}
      />
      {label ? (
        <div
          style={{
            padding: "6px 8px",
            fontSize: "12px",
            color: "#94a3b8",
            background: "rgba(15, 23, 42, 0.6)",
            textAlign: "center"
          }}
        >
          {label}
        </div>
      ) : null}
    </div>
  );
}

export default ImageCard;