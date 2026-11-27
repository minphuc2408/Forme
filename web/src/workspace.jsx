import React, { useEffect, useRef, useState } from "react";

export const routes = {
  home: "/tao-video", queue: "/hang-doi", inspector: "/kich-ban", videos: "/video",
  voices: "/cau-hinh/giong-doc", media: "/cau-hinh/nguon", layout: "/cau-hinh/bo-cuc",
  ai: "/cau-hinh/ai", settings: "/cau-hinh/he-thong", resources: "/tai-nguyen",
  tools: "/cong-cu", meme_sound: "/kho-sound", meme_image: "/kho-anh",
};

function readStored(key, fallback) {
  try { const value = JSON.parse(localStorage.getItem(`threadstudio.${key}`)); return typeof value === typeof fallback && (typeof value !== "number" || Number.isFinite(value)) ? value : fallback; }
  catch { return fallback; }
}

export function useStoredState(key, fallback) {
  const [value, setValue] = useState(() => readStored(key, fallback));
  useEffect(() => { try { localStorage.setItem(`threadstudio.${key}`, JSON.stringify(value)); } catch { /* Storage can be disabled. */ } }, [key, value]);
  return [value, setValue];
}

function parseRoute(path) {
  const match = Object.entries(routes).find(([, url]) => path === url || (url === routes.inspector && path.startsWith(`${url}/`)));
  let jobId = "";
  try { if (match?.[0] === "inspector") jobId = decodeURIComponent(path.slice(routes.inspector.length + 1)); } catch { /* Ignore malformed links. */ }
  return { page: match?.[0] || "home", jobId };
}

export function useRoute() {
  const [route, setRoute] = useState(() => parseRoute(location.pathname === "/" ? readStored("route", routes.home) : location.pathname));
  function navigate(page, jobId = "") {
    const path = (routes[page] || routes.home) + (page === "inspector" && jobId ? `/${encodeURIComponent(jobId)}` : "");
    if (location.pathname !== path) history.pushState(null, "", path);
    setRoute(parseRoute(path));
  }
  useEffect(() => {
    const update = () => setRoute(parseRoute(location.pathname));
    window.addEventListener("popstate", update);
    return () => window.removeEventListener("popstate", update);
  }, []);
  useEffect(() => {
    const path = routes[route.page] + (route.page === "inspector" && route.jobId ? `/${encodeURIComponent(route.jobId)}` : "");
    if (location.pathname !== path) history.replaceState(null, "", path);
    try { localStorage.setItem("threadstudio.route", JSON.stringify(path)); } catch { /* Keep navigation usable without storage. */ }
  }, [route]);
  return [route, navigate];
}

export function ResizeHandle({ label, value, onChange, min, max, axis = "x", reverse = false }) {
  const drag = useRef(null);
  const resize = delta => onChange(Math.max(min, Math.min(max, delta)));
  return <div role="separator" tabIndex={0} title={label} aria-label={label} aria-orientation={axis === "x" ? "vertical" : "horizontal"} aria-valuemin={min} aria-valuemax={max} aria-valuenow={Math.round(value)} className={`resize-handle resize-${axis}`}
    onPointerDown={event => { if (event.button !== 0) return; event.preventDefault(); drag.current = { position: axis === "x" ? event.clientX : event.clientY, value }; event.currentTarget.setPointerCapture(event.pointerId); }}
    onPointerMove={event => { if (drag.current) resize(drag.current.value + ((axis === "x" ? event.clientX : event.clientY) - drag.current.position) * (reverse ? -1 : 1)); }}
    onPointerUp={() => { drag.current = null; }} onPointerCancel={() => { drag.current = null; }}
    onKeyDown={event => { const keys = axis === "x" ? ["ArrowLeft", "ArrowRight"] : ["ArrowUp", "ArrowDown"]; if (keys.includes(event.key)) { event.preventDefault(); resize(value + (event.key === keys[0] ? -16 : 16) * (reverse ? -1 : 1)); } }} />;
}

export const workflow = [["home", "Nội dung"], ["voices", "Giọng đọc"], ["media", "Nguồn video"], ["layout", "Bố cục"], ["ai", "AI"], ["queue", "Xử lý"], ["inspector", "Duyệt"], ["videos", "Thành phẩm"]];

export function Workflow({ page, navigate, jobId }) {
  const current = workflow.findIndex(([key]) => key === page);
  if (current < 0) return null;
  return <nav className="workflow" aria-label="Các bước tạo video">{workflow.map(([key, label], index) => <button key={key} className={page === key ? "is-current" : ""} aria-current={page === key ? "step" : undefined} onClick={() => navigate(key, jobId)}><span>{index + 1}</span>{label}</button>)}</nav>;
}

export function SegmentCards({ job, selected, editable, select, reorder }) {
  const [target, setTarget] = useState("");
  const drag = useRef(null);
  function move(source, destination) {
    if (!editable || source === destination) return;
    const items = [...job.segments], from = items.findIndex(item => item.seg_id === source), to = items.findIndex(item => item.seg_id === destination);
    if (from < 0 || to < 0) return;
    items.splice(to, 0, items.splice(from, 1)[0]);
    reorder(items);
  }
  return <div className="segment-cards" role="listbox" aria-label="Thứ tự xuất hiện">{job.segments.map((item, index) => <button key={item.seg_id} data-segment={item.seg_id} role="option" aria-selected={selected === item.seg_id} className={`segment-card ${selected === item.seg_id ? "is-selected" : ""} ${target === item.seg_id ? "drop-target" : ""} ${item.enabled ? "" : "opacity-50"}`} onClick={() => select(item.seg_id)}
    onPointerDown={event => { if (!editable || event.button !== 0 || (event.pointerType === "touch" && !event.target.closest(".drag-grip"))) return; drag.current = { source: item.seg_id, y: event.clientY }; event.currentTarget.setPointerCapture(event.pointerId); }}
    onPointerMove={event => { if (!drag.current || Math.abs(event.clientY - drag.current.y) < 4) return; const card = document.elementFromPoint(event.clientX, event.clientY)?.closest("[data-segment]"); if (card && event.currentTarget.parentElement.contains(card)) setTarget(card.dataset.segment); const list = event.currentTarget.parentElement, rect = list.getBoundingClientRect(); if (event.clientY < rect.top + 28) list.scrollBy(0, -12); if (event.clientY > rect.bottom - 28) list.scrollBy(0, 12); }}
    onPointerUp={event => { const card = document.elementFromPoint(event.clientX, event.clientY)?.closest("[data-segment]"); if (drag.current && card && event.currentTarget.parentElement.contains(card)) move(drag.current.source, card.dataset.segment); drag.current = null; setTarget(""); }}
    onPointerCancel={() => { drag.current = null; setTarget(""); }}
    onKeyDown={event => { if (event.altKey && ["ArrowUp", "ArrowDown"].includes(event.key)) { event.preventDefault(); const next = job.segments[index + (event.key === "ArrowUp" ? -1 : 1)]; if (next) move(item.seg_id, next.seg_id); } }}>
    <span className="drag-grip float-right text-muted" aria-hidden="true">⠿</span><span className="block text-sm font-medium">{index + 1}. @{item.username}</span><span className="mt-2 block text-xs leading-relaxed text-muted">{item.spoken_text || item.raw_text}</span>
  </button>)}</div>;
}
