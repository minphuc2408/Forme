import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { commentSort, FieldGrid, setPath } from "./fields.jsx";
import { AIUsagePanel, ModelPicker, tokenNumber } from "./ai-usage.jsx";
import { ResizeHandle, SegmentCards, useRoute, useStoredState, Workflow, workflow } from "./workspace.jsx";
import "./studio.css";

const editableStages = new Set(["awaiting_review", "failed"]);
const defaultLayout = { aspect_ratio: "9:16", card_x_pct: 50, card_y_pct: 28, card_scale_pct: 108, card_radius_px: 0, card_theme: "light", hide_username: false, sub_enabled: true, sub_x_pct: 50, sub_y_pct: 64, sub_w_pct: 86, sub_h_pct: 26, sub_radius_px: 0, sub_fit: "cover" };
const nav = [
  ["SẢN XUẤT", [["queue", "Tạo lô · Hàng đợi", "layers"], ["inspector", "Duyệt kịch bản", "edit"]]],
  ["CẤU HÌNH STUDIO", [["voices", "Giọng đọc AI", "volume"], ["media", "Nguồn video · Nhạc", "folder"], ["layout", "Bố cục video", "sliders"], ["ai", "AI · Model", "layers"], ["settings", "Hệ thống · Đa luồng", "settings"]]],
  ["KHO MEME", [["meme_sound", "Meme Sound", "music"], ["meme_image", "Meme Image · Sắp có", "image"]]],
];
const referenceNav = [
  ["THƯ VIỆN", [["videos", "Video đã tạo", "video"], ["layout", "Cấu hình video", "sliders"]]],
  ["SÁNG TẠO", [["resources", "Kho tài nguyên", "folder"], ["tools", "Công cụ", "tool"]]],
];

async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json", "X-Studio-Token": document.querySelector('meta[name="studio-token"]').content }, body: JSON.stringify(body),
  });
  if (!response.ok) {
    const text = await response.text();
    let message = text;
    try { message = JSON.parse(text).error || text; } catch { /* HTTP errors can be plain text. */ }
    throw new Error(message || `Lỗi HTTP ${response.status}`);
  }
  return response;
}

async function action(name, body = {}) {
  return (await (await api("/api/action", { ...body, action: name })).json()).result;
}

function Icon({ name, className = "size-5" }) {
  const paths = {
    layers: "m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5",
    edit: "m16 3 5 5-12 12-6 1 1-6L16 3ZM14 5l5 5",
    volume: "M11 4 5 9H2v6h3l6 5V4Zm5 4a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14",
    folder: "M3 7V4h6l2 3h10v13H3V7Z",
    settings: "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8ZM12 2v3m0 14v3M2 12h3m14 0h3M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2",
    music: "M9 18V5l11-2v13M9 8l11-2M9 18c0 2-6 4-6 1s6-4 6-1Zm11-2c0 2-6 4-6 1s6-4 6-1Z",
    image: "M3 3h18v18H3V3Zm0 14 6-6 4 4 3-3 5 5M16 7h.01",
    menu: "M4 6h16M4 12h16M4 18h16",
    play: "m8 4 12 8-12 8V4Z",
    check: "m5 12 4 4L19 6",
    video: "M3 6h12v12H3V6Zm12 4 6-3v10l-6-3",
    sliders: "M4 7h16M4 17h16M8 4v6m8 4v6",
    tool: "m14 6 4 4 3-3a7 7 0 0 1-9 9l-7 6-3-3 7-7a7 7 0 0 1 9-9l-4 3Z",
    inbox: "M5 3h14l3 12v6H2v-6L5 3Zm-3 12h6l2 3h4l2-3h6",
    home: "m3 11 9-8 9 8M5 9v12h5v-7h4v7h5V9",
    plus: "M12 5v14M5 12h14",
    chevron: "m14 6-6 6 6 6",
  };
  return <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name] || paths.layers} /></svg>;
}

function Heading({ eyebrow, title, children, actions }) {
  return <div className="mb-6 flex flex-wrap items-center justify-between gap-4"><div><p className="mb-2 text-xs font-semibold tracking-widest text-accent">{eyebrow}</p><h1>{title}</h1>{children && <p className="hint mt-2">{children}</p>}</div>{actions}</div>;
}

function Panel({ title, actions, children, className = "" }) {
  return <section className={`panel ${className}`}><div className="mb-4 flex flex-wrap items-center justify-between gap-3"><h2>{title}</h2>{actions && <div className="actions">{actions}</div>}</div>{children}</section>;
}

function VoiceSelect({ voices, value, onChange, disabled = false, label }) {
  const choices = [...voices];
  if (value && !choices.some(v => v.full_id === value)) choices.unshift({ full_id: value, display_name: value, badge: "Đã lưu" });
  return <select aria-label={label || "Giọng đọc"} value={value || ""} disabled={disabled} onChange={event => onChange(event.target.value)}><option value="">Chọn giọng…</option>{choices.map(voice => <option key={voice.full_id} value={voice.full_id}>[{voice.badge}] {voice.display_name}</option>)}</select>;
}

function ReviewOptions({ config, onConfig }) {
  return <div className="actions gap-x-5"><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={config.require_review_default} onChange={event => onConfig("require_review_default", event.target.checked)} />Duyệt nội dung trước khi xuất</label><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={config.layout.hide_username} onChange={event => onConfig("layout.hide_username", event.target.checked)} />Che tên tài khoản</label></div>;
}

function Stage({ layout, onChange, job, segment, readonly, video, notify, perform, controls = false }) {
  const [tab, setTab] = useState("layout");
  const [card, setCard] = useState("");
  const [cardError, setCardError] = useState("");
  const [selected, setSelected] = useState("card");
  const stageRef = useRef(null);
  const imageRef = useRef(null);
  const drag = useRef(null);
  const portrait = layout.aspect_ratio !== "16:9";
  const width = portrait ? 1080 : 1920;
  const cardWidth = Math.max(240, Math.min(width - 24, Math.round(880 * layout.card_scale_pct / 100)));
  const previewKey = JSON.stringify([job?.job_id, segment?.seg_id, segment?.raw_text, layout.card_theme, layout.card_radius_px, layout.hide_username]);

  useEffect(() => {
    let disposed = false;
    let objectUrl;
    const timer = setTimeout(async () => {
      try {
        const response = await api("/api/card", { layout, job_id: segment ? job?.job_id : "", seg_id: segment?.seg_id, ...(segment ? { raw_text: segment.raw_text } : {}) });
        const blob = await response.blob();
        if (!disposed) { objectUrl = URL.createObjectURL(blob); setCard(objectUrl); setCardError(""); }
      } catch (error) { if (!disposed) setCardError(error.message); }
    }, 180);
    return () => { disposed = true; clearTimeout(timer); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [previewKey]);

  useEffect(() => { if (video) setTab("video"); }, [video]);

  function updateLayer(layer, x, y) {
    onChange({ ...layout, [`${layer}_x_pct`]: Math.round(Math.max(5, Math.min(95, x)) * 10) / 10, [`${layer}_y_pct`]: Math.round(Math.max(5, Math.min(95, y)) * 10) / 10 });
  }

  function pointerDown(event, layer) {
    if (readonly) return;
    const rect = stageRef.current.getBoundingClientRect();
    drag.current = { layer, x: event.clientX - rect.left - rect.width * layout[`${layer}_x_pct`] / 100, y: event.clientY - rect.top - rect.height * layout[`${layer}_y_pct`] / 100 };
    setSelected(layer);
    event.currentTarget.setPointerCapture(event.pointerId);
    event.preventDefault();
  }

  function pointerMove(event) {
    if (!drag.current || readonly) return;
    const rect = stageRef.current.getBoundingClientRect();
    updateLayer(drag.current.layer, (event.clientX - rect.left - drag.current.x) / rect.width * 100, (event.clientY - rect.top - drag.current.y) / rect.height * 100);
  }

  function wheel(event, layer) {
    if (readonly) return;
    const step = event.deltaY < 0 ? 3 : -3;
    setSelected(layer);
    if (layer === "card") onChange({ ...layout, card_scale_pct: Math.max(55, Math.min(122, layout.card_scale_pct + step)) });
    else onChange({ ...layout, sub_w_pct: Math.max(25, Math.min(100, layout.sub_w_pct + step)), sub_h_pct: Math.max(12, Math.min(65, layout.sub_h_pct + step / 2)) });
  }

  function keyboard(event, layer) {
    if (readonly || !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) return;
    event.preventDefault();
    const step = event.shiftKey ? 5 : 1;
    updateLayer(layer, layout[`${layer}_x_pct`] + (event.key === "ArrowLeft" ? -step : event.key === "ArrowRight" ? step : 0), layout[`${layer}_y_pct`] + (event.key === "ArrowUp" ? -step : event.key === "ArrowDown" ? step : 0));
  }

  async function snapshot() {
    if (!imageRef.current?.complete || !imageRef.current.naturalWidth) throw new Error("Đợi thẻ xem trước tải xong.");
    const height = portrait ? 1920 : 1080;
    const canvas = document.createElement("canvas");
    canvas.width = width / 2; canvas.height = height / 2;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#090b12"; ctx.fillRect(0, 0, canvas.width, canvas.height);
    if (layout.sub_enabled) {
      ctx.fillStyle = "#172554";
      const w = canvas.width * layout.sub_w_pct / 100, h = canvas.height * layout.sub_h_pct / 100;
      ctx.beginPath(); ctx.roundRect(canvas.width * layout.sub_x_pct / 100 - w / 2, canvas.height * layout.sub_y_pct / 100 - h / 2, w, h, layout.sub_radius_px / 2); ctx.fill();
    }
    const w = cardWidth / 2, h = w * imageRef.current.naturalHeight / imageRef.current.naturalWidth;
    ctx.drawImage(imageRef.current, canvas.width * layout.card_x_pct / 100 - w / 2, canvas.height * layout.card_y_pct / 100 - h / 2, w, h);
    const link = document.createElement("a"); link.download = `preview_snapshot_${layout.aspect_ratio.replace(":", "x")}.png`; link.href = canvas.toDataURL("image/png"); link.click();
    notify("Đã tạo ảnh bố cục để tải xuống.");
  }

  const layerProps = layer => ({ tabIndex: 0, role: "button", "aria-disabled": readonly, "aria-label": `${layer === "card" ? "Thẻ Threads" : "Video phụ"}. Dùng phím mũi tên để di chuyển.`, onPointerDown: event => pointerDown(event, layer), onPointerMove: pointerMove, onPointerUp: () => { drag.current = null; }, onPointerCancel: () => { drag.current = null; }, onKeyDown: event => keyboard(event, layer), onWheel: event => wheel(event, layer) });

  return <aside className="min-w-0 border-t border-line bg-surface px-5 py-6 lg:overflow-y-auto lg:border-t-0 lg:border-l">
    <div className="mb-4 flex items-center justify-between"><h2>Sân khấu</h2><span className="badge">{layout.aspect_ratio}</span></div>
    <div className="mb-4 flex border-b border-line">{[["layout", "Bố cục"], ["video", "Thành phẩm"]].map(([key, label]) => <button key={key} className={`tab ${tab === key ? "active" : ""}`} aria-pressed={tab === key} onClick={() => setTab(key)}>{label}</button>)}</div>
    <div hidden={tab !== "layout"}>
      <div className="rounded-md border border-line bg-well p-3"><div ref={stageRef} className="stage relative mx-auto w-full overflow-hidden" style={{ aspectRatio: portrait ? "9 / 16" : "16 / 9", maxWidth: portrait ? 310 : "100%" }}>
        {layout.sub_enabled && <div {...layerProps("sub")} className={`stage-layer sub-layer grid place-content-center text-center text-sm ${selected === "sub" ? "selected" : ""}`} style={{ left: `${layout.sub_x_pct}%`, top: `${layout.sub_y_pct}%`, width: `${layout.sub_w_pct}%`, height: `${layout.sub_h_pct}%`, borderRadius: `${layout.sub_radius_px / width * (stageRef.current?.clientWidth || 300)}px` }}>VIDEO PHỤ<br /><small>Meme / B-roll</small></div>}
        {card && <img {...layerProps("card")} ref={imageRef} src={card} alt="Thẻ Threads xem trước" draggable={false} className={`stage-layer z-10 h-auto ${selected === "card" ? "selected" : ""}`} style={{ left: `${layout.card_x_pct}%`, top: `${layout.card_y_pct}%`, width: `${cardWidth / width * 100}%` }} />}
      </div></div>
      {cardError && <p className="mt-2 text-sm text-danger" role="alert">{cardError}</p>}
      <p className="mt-3 text-xs leading-relaxed text-muted">Kéo thả / phím mũi tên để di chuyển · Lăn chuột đổi cỡ.<br />Nền lưới minh họa; xem video thực ở Thành phẩm.</p>
      {controls && <FieldGrid group="layout" value={layout} disabled={readonly} onChange={(path, value) => onChange(setPath(layout, path, value))} />}
      <div className="actions"><button disabled={readonly} onClick={() => onChange({ ...defaultLayout })}>Đặt lại bố cục</button><button onClick={() => perform(snapshot)}>Lưu ảnh bố cục</button></div>
      <p className="hint mt-3">{job ? `Bố cục riêng của job #${job.job_id}${readonly ? " · Chỉ xem" : " · Lưu cùng kịch bản"}` : "Áp dụng cho video tạo mới."}</p>
    </div>
    <div hidden={tab !== "video"}>{video ? <><video key={video} src={video} controls preload="metadata" className="max-h-140 w-full rounded-md bg-black" /><a className="button primary mt-3" href={video} download>Tải MP4</a></> : <div className="empty"><Icon name="play" className="size-8" /><p>Chọn một video hoàn tất trong hàng đợi.</p></div>}</div>
  </aside>;
}

function Candidates({ job, disabled, reselect }) {
  const [sort, setSort] = useState(["likes", -1]);
  const [page, setPage] = useState(0);
  const [criterion, setCriterion] = useState(job.comment_sort || "likes");
  const [count, setCount] = useState(job.max_comments || 6);
  const rows = [...job.comment_candidates].sort((a, b) => ((a[sort[0]] ?? -1) - (b[sort[0]] ?? -1)) * sort[1]);
  const maxPage = Math.max(0, Math.ceil(rows.length / 25) - 1), currentPage = Math.min(page, maxPage);
  if (!job.comment_candidates.length) return null;
  return <Panel title="Bình luận đã tải">
    <p className="hint mb-3">Dữ liệu sau 10 lần cuộn Edge · {job.comment_candidates.length} mục trong pool. Chỉ xếp hạng tập đã tải; không bảo đảm toàn bài.</p>
    <div className="max-h-72 overflow-auto"><table className="w-full border-collapse"><thead><tr><th>Tài khoản</th><th>Nội dung</th>{commentSort.map(([key, label]) => <th key={key}><button className="quiet min-w-18" onClick={() => { setSort([key, sort[0] === key ? -sort[1] : -1]); setPage(0); }}>{label.replace("Nhiều ", "")}{sort[0] === key ? sort[1] === -1 ? " ↓" : " ↑" : ""}</button></th>)}</tr></thead><tbody>{rows.slice(currentPage * 25, (currentPage + 1) * 25).map((item, index) => <tr key={item.seg_id || item.source_post_id || index}><td>@{item.username}</td><td className="min-w-52 whitespace-pre-wrap">{item.text || item.raw_text || ""}</td>{commentSort.map(([key]) => <td key={key} className="text-right tabular-nums">{item[key] ?? "—"}</td>)}</tr>)}</tbody></table></div>
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3"><div className="actions"><button disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)}>Trang trước</button><span className="hint">{currentPage + 1}/{maxPage + 1}</span><button disabled={currentPage === maxPage} onClick={() => setPage(currentPage + 1)}>Trang sau</button></div><div className="actions"><select aria-label="Tiêu chí chọn lại" className="max-w-44" value={criterion} onChange={e => setCriterion(e.target.value)}>{commentSort.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select><input aria-label="Số bình luận chọn lại" type="number" min="1" max="25" className="max-w-18" value={count} onChange={e => setCount(Number(e.target.value))} /><button disabled={disabled} onClick={() => reselect(criterion, count)}>Chọn lại top N</button></div></div>
    <p className="mt-3 text-xs text-muted">Chọn lại sẽ thay kịch bản và chuẩn hóa từ pool đã tải. Chỉ tác giả giữ thứ tự thời gian. Sắp xếp bảng để xem không đổi thứ tự video.</p>
  </Panel>;
}

function SoundLibrary({ config, onConfig, save, perform, taskAction, notify }) {
  const [catalog, setCatalog] = useState(null);
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const [newGroup, setNewGroup] = useState("");
  async function load(name, extra = {}) {
    setBusy(true);
    try {
      const data = await taskAction(name, { folder: config.media.meme_sound_dir, ...extra });
      setCatalog(data);
    } finally { setBusy(false); }
  }
  const groups = catalog?.emotion_groups || {};
  const filtered = (catalog?.sounds || []).filter(item => `${item.title} ${item.description} ${item.emotion_group || ""}`.toLocaleLowerCase().includes(search.toLocaleLowerCase()));
  const canEdit = !busy && catalog?.folder === config.media.meme_sound_dir;
  async function saveGroup(name, patch) { await load("update_emotion_group", { name, ...patch }); notify("Đã lưu cấu hình nhóm cảm xúc."); }
  return <><Heading eyebrow="KHO MEME" title="Meme Sound">Quản lý sound local và mô tả để AI chọn sau khi duyệt lời đọc.</Heading>
    <Panel title="Cấu hình kho sound"><FieldGrid group="meme" value={config} onChange={onConfig} /><div className="actions"><button disabled={busy} onClick={() => perform(() => load("catalog"))}>Đọc danh mục</button><button disabled={busy} onClick={() => perform(() => load("scan_sounds"))}>Nhập / Quét lại kho</button><button className="primary" onClick={() => perform(save)}>Lưu cấu hình</button></div><p className="hint mt-3">Chỉ đọc audio và JSON local. Không tải web hoặc đoán mô tả sound từ tên file.</p>{busy && <p className="hint mt-2" role="status">Đang đọc kho sound…</p>}</Panel>
    <Panel title="Danh mục sound" actions={<input className="max-w-60" type="search" value={search} aria-label="Tìm sound" placeholder="Tìm tên hoặc mô tả…" onChange={e => setSearch(e.target.value)} />}>
      {catalog && <><div className="actions mb-4"><input aria-label="Tên nhóm cảm xúc mới" className="max-w-60" value={newGroup} onChange={event => setNewGroup(event.target.value)} placeholder="Tên nhóm cảm xúc mới…" maxLength={60} /><button disabled={!canEdit || !newGroup.trim()} onClick={() => perform(async () => { await saveGroup(newGroup.trim(), { description: "", enabled: true }); setNewGroup(""); })}>Thêm nhóm</button></div><p className="hint mb-4">Gán sound vào nhóm bằng tay. Ngữ cảnh và bật/tắt của nhóm áp dụng chung cho AI chọn sound; không tự đoán cảm xúc từ tên file.</p></>}
      {catalog && <><p className="hint">{catalog.sounds.length} sound · {catalog.sounds.filter(item => item.needs_review).length} cần kiểm tra · {catalog.duplicate_files?.length || 0} file trùng · {catalog.missing_files?.length || 0} mô tả chưa có file.</p>{catalog.folder !== config.media.meme_sound_dir && <p className="text-sm text-danger">Đường dẫn kho đã thay đổi. Đọc lại danh mục trước khi sửa sound.</p>}</>}
      {catalog?.missing_files?.length > 0 && <details className="mt-3 text-sm"><summary className="cursor-pointer text-muted">Mô tả chưa có file</summary><ul className="mt-2 list-inside list-disc">{catalog.missing_files.map((item, index) => <li key={index}>{item.file}</li>)}</ul></details>}
      {!catalog ? <div className="empty">Đọc danh mục hoặc quét thư mục để hiển thị sound.</div> : [...new Set(["", ...Object.keys(groups), ...filtered.map(item => item.emotion_group || "")])].filter(name => !search || filtered.some(item => (item.emotion_group || "") === name)).map(name => <SoundGroup key={`${catalog.folder}/${name}`} name={name} group={groups[name]} items={filtered.filter(item => (item.emotion_group || "") === name)} groups={groups} disabled={!canEdit} saveGroup={patch => perform(() => saveGroup(name, patch))} saveSound={(item, patch) => perform(async () => { await load("update_sound", { sound_id: item.id, ...patch }); notify("Đã lưu sound."); })} />)}
    </Panel></>;
}

function SoundGroup({ name, group, items, groups, disabled, saveGroup, saveSound }) {
  const [description, setDescription] = useState(group?.description || "");
  const [enabled, setEnabled] = useState(group?.enabled !== false);
  useEffect(() => { setDescription(group?.description || ""); setEnabled(group?.enabled !== false); }, [group?.description, group?.enabled]);
  return <details className="sound-group" open={!name}><summary>{name || "Chưa phân nhóm"} <span className="badge ml-2">{items.length} sound{group?.enabled === false ? " · Nhóm đã tắt" : ""}</span></summary>{name && group && <div className="group-config"><label className="text-sm">Ngữ cảnh dùng chung<textarea aria-label={`Ngữ cảnh nhóm ${name}`} rows={2} disabled={disabled} value={description} onChange={event => setDescription(event.target.value)} /></label><div className="actions mt-3"><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={enabled} disabled={disabled} onChange={event => setEnabled(event.target.checked)} />Bật nhóm cho AI chọn</label><button disabled={disabled} onClick={() => saveGroup({ description, enabled })}>Lưu nhóm</button></div></div>}{items.map(item => <SoundRow key={item.id} item={item} groups={groups} disabled={disabled} save={patch => saveSound(item, patch)} />)}{!items.length && <p className="hint mt-3">Chọn nhóm này trong một sound rồi bấm Lưu sound.</p>}</details>;
}

function SoundRow({ item, groups, disabled, save }) {
  const [description, setDescription] = useState(item.description || "");
  const [enabled, setEnabled] = useState(item.enabled !== false);
  const [emotion, setEmotion] = useState(item.emotion_group || "");
  return <div className="grid gap-4 border-b border-line py-4 sm:grid-cols-[1fr_1.5fr]"><div><h3 className="text-sm font-semibold">{item.title}</h3><p className="mt-1 text-xs text-muted">{item.duration_sec || 0}s · {item.error ? "Lỗi file" : groups[emotion]?.enabled === false ? "Nhóm đã tắt" : !enabled ? "Đã tắt" : item.needs_review ? "Cần mô tả" : "Sẵn sàng"}</p>{item.audio_url && <audio src={item.audio_url} controls preload="none" className="mt-3 h-9 w-full" />}</div><div><label className="text-sm">Nhóm cảm xúc<select aria-label={`Nhóm cảm xúc ${item.title}`} value={emotion} disabled={disabled} onChange={event => setEmotion(event.target.value)}><option value="">Chưa phân nhóm</option>{Object.keys(groups).map(name => <option key={name} value={name}>{name}</option>)}</select></label><label className="mt-3 block text-sm">Mô tả ngữ cảnh<textarea rows={3} value={description} onChange={e => setDescription(e.target.value)} disabled={disabled} className="mt-1" /></label><div className="actions mt-2"><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} disabled={disabled} />Bật sound</label><button disabled={disabled} onClick={() => save({ description, enabled, emotion_group: emotion })}>Lưu sound</button></div></div></div>;
}

function App() {
  const [state, setState] = useState(null);
  const [config, setConfig] = useState(null);
  const [route, navigate] = useRoute();
  const page = route.page;
  const [collapsed, setCollapsed] = useStoredState("sidebarCollapsed", false);
  const [railWidth, setRailWidth] = useStoredState("railWidth", 224);
  const [rightWidth, setRightWidth] = useStoredState("rightWidth", 380);
  const [stageHeight, setStageHeight] = useStoredState("stageHeight", 460);
  const [orderWidth, setOrderWidth] = useStoredState("orderWidth", 220);
  const [logsOpen, setLogsOpen] = useStoredState("logsOpen", false);
  const [logsHeight, setLogsHeight] = useStoredState("logsHeight", 180);
  const [theme, setTheme] = useStoredState("theme", "light");
  const [flowActive, setFlowActive] = useStoredState("flowActive", false);
  const [notice, setNotice] = useState(null);
  const [connected, setConnected] = useState(true);
  const [stopped, setStopped] = useState(false);
  const [pending, setPending] = useState(false);
  const [mode, setMode] = useState("urls");
  const [input, setInput] = useState("");
  const [preset, setPreset] = useState("");
  const [presetName, setPresetName] = useState("");
  const [jobId, setJobId] = useStoredState("selectedJob", route.jobId || "");
  const [drafts, setDrafts] = useState({});
  const [segmentId, setSegmentId] = useStoredState("selectedSegment", "");
  const [voiceSearch, setVoiceSearch] = useState("");
  const [auditionVoice, setAuditionVoice] = useState("");
  const [auditionText, setAuditionText] = useState("Xin chào từ Threads Studio Pro. Mỗi cuộc trò chuyện đều có một câu chuyện riêng.");
  const [audio, setAudio] = useState("");
  const [video, setVideo] = useState("");
  const [homeConfig, setHomeConfig] = useState(false);
  const [metadataBusy, setMetadataBusy] = useState({});
  const metadataRequested = useRef(new Set());
  const waiting = useRef(new Map());
  const pollRef = useRef(null);
  const notifiedTasks = useRef(new Set());
  const finishedTasks = useRef(new Map());
  const noticeTimer = useRef(null);
  const detailKey = useRef("");
  const audioRef = useRef(null);
  const job = drafts[jobId] || null;
  const summary = state?.jobs.find(item => item.job_id === jobId);
  const editable = job && editableStages.has(summary?.stage || job.stage) && !summary?.busy && !pending;
  const segment = job?.segments.find(item => item.seg_id === segmentId) || job?.segments[0];
  const contentPage = page;
  const stageJob = contentPage === "inspector" ? job : null;
  const layout = stageJob?.layout || config?.layout;
  function setPage(next) { navigate(next, jobId); }

  function notify(message, error = false, duration = error ? 12000 : 6000) {
    clearTimeout(noticeTimer.current); setNotice({ message, error });
    if (duration) noticeTimer.current = setTimeout(() => setNotice(null), duration);
  }

  async function perform(work) {
    setPending(true);
    try { return await work(); }
    catch (error) { notify(error.message, true); }
    finally { setPending(false); }
  }

  async function refresh() {
    const data = await (await api("/api/state")).json();
    setState(data); setConfig(previous => previous || data.settings); setConnected(true);
    for (const [id, task] of Object.entries(data.tasks)) {
      if (task.state === "running" || notifiedTasks.current.has(id)) continue;
      notifiedTasks.current.add(id);
      finishedTasks.current.set(id, task);
      const waiter = waiting.current.get(id);
      if (waiter) {
        waiting.current.delete(id);
        task.state === "done" ? waiter.resolve(task.result) : waiter.reject(new Error(task.error));
      } else if (task.state === "failed") notify(`${task.label}: ${task.error}`, true);
    }
    return data;
  }

  useEffect(() => {
    let disposed = false;
    async function poll() {
      try { await refresh(); }
      catch { if (!disposed) setConnected(false); }
      if (!disposed) pollRef.current = setTimeout(poll, 1100);
    }
    poll();
    return () => { disposed = true; clearTimeout(pollRef.current); clearTimeout(noticeTimer.current); };
  }, []);

  useEffect(() => { document.documentElement.dataset.theme = ["dark", "high-contrast"].includes(theme) ? theme : "light"; }, [theme]);
  useEffect(() => { if (route.jobId) setJobId(route.jobId); }, [route.jobId]);
  useEffect(() => {
    const provider = config?.ai_provider;
    if (contentPage !== "ai" || !provider || provider === "offline" || metadataRequested.current.has(provider)) return;
    metadataRequested.current.add(provider);
    refreshMetadata(provider).catch(error => notify(error.message, true));
  }, [contentPage, config?.ai_provider]);
  useEffect(() => {
    const beforeUnload = event => { if (Object.values(drafts).some(item => item.dirty)) { event.preventDefault(); event.returnValue = ""; } };
    window.addEventListener("beforeunload", beforeUnload);
    return () => window.removeEventListener("beforeunload", beforeUnload);
  }, [drafts]);
  useEffect(() => {
    if (audio && audioRef.current) audioRef.current.play().catch(() => notify("Âm thanh đã sẵn sàng. Bấm phát để nghe."));
  }, [audio]);

  async function loadJob(id, force = false) {
    if (!id) return;
    const data = await (await api(`/api/jobs/${encodeURIComponent(id)}`)).json();
    setDrafts(previous => ({ ...previous, [id]: previous[id]?.dirty && !force ? { ...previous[id], stage: data.stage, busy: data.busy, ai_usage: data.ai_usage, ai_summary: data.ai_summary } : { ...data, dirty: false } }));
  }

  useEffect(() => {
    if (!jobId || !summary) return;
    const key = `${jobId}:${summary.stage}:${summary.busy}:${summary.segment_count}:${summary.ai_summary?.calls}:${summary.ai_summary?.input_tokens}:${summary.ai_summary?.output_tokens}`;
    if (key !== detailKey.current) {
      detailKey.current = key;
      loadJob(jobId).catch(error => notify(error.message, true));
    }
  }, [jobId, summary]);
  useEffect(() => {
    if (flowActive && page === "queue" && summary?.stage === "awaiting_review") navigate("inspector", jobId);
    if (flowActive && ["queue", "inspector"].includes(page) && summary?.stage === "completed") { setVideo(summary.video_url || ""); navigate("videos", jobId); setFlowActive(false); }
  }, [flowActive, page, jobId, summary?.stage]);

  function waitForTask(taskId) {
    return new Promise((resolve, reject) => {
      const finished = finishedTasks.current.get(taskId);
      if (finished) finished.state === "done" ? resolve(finished.result) : reject(new Error(finished.error));
      else waiting.current.set(taskId, { resolve, reject });
    });
  }

  async function taskAction(name, body = {}) {
    const result = await action(name, body);
    return waitForTask(result.task_id);
  }

  async function refreshMetadata(provider) {
    setMetadataBusy(previous => ({ ...previous, [provider]: true }));
    try { await taskAction("ai_metadata", { provider }); }
    finally { setMetadataBusy(previous => ({ ...previous, [provider]: false })); }
  }

  function onConfig(path, value) { setConfig(previous => setPath(previous, path, value)); }
  function jobPatch(patch) { setDrafts(previous => ({ ...previous, [jobId]: { ...previous[jobId], ...patch, dirty: true } })); }
  function segmentPatch(patch) { jobPatch({ segments: job.segments.map(item => item.seg_id === segment.seg_id ? { ...item, ...patch } : item) }); }
  function onLayout(next) { if (stageJob) jobPatch({ layout: next }); else onConfig("layout", next); }
  function jobPayload() { return { job_id: jobId, segments: job.segments.map(({ seg_id, raw_text, spoken_text, voice_id, enabled }) => ({ seg_id, raw_text, spoken_text, voice_id, enabled })), layout: job.layout }; }

  async function saveSettings() {
    const { presets, ...settings } = { ...config, theme };
    const saved = await action("settings", { settings }); setConfig(saved); notify("Đã lưu cấu hình studio."); return saved;
  }

  async function saveJob() {
    await action("save_job", jobPayload()); await loadJob(jobId, true); notify("Đã lưu kịch bản và bố cục.");
  }

  async function resumeJob(id) {
    if (drafts[id]?.dirty) throw new Error("Hãy lưu kịch bản đang sửa trước khi tiếp tục tạo.");
    await action("resume", { job_id: id });
    await refresh();
    if (id === jobId) await loadJob(id, true);
    notify("Đang tiếp tục tạo, dùng lại nội dung và audio phù hợp đã lưu.");
  }

  async function enqueue() {
    const { presets, ...settings } = config;
    const ids = await action("enqueue", { mode, text: input, settings });
    setJobId(ids[0]); await refresh(); navigate("queue", ids[0]); notify(`Đã thêm ${ids.length} video vào hàng đợi.`);
  }

  async function previewVoice(text, voiceId) {
    await saveSettings();
    notify("Đang tạo giọng đọc mẫu…");
    const result = await taskAction("preview_voice", { text, voice_id: voiceId });
    setAudio(result.audio_url);
    notify("Giọng đọc đã sẵn sàng.");
  }

  function selectJob(id) { setJobId(id); setSegmentId(""); navigate("inspector", id); }
  async function nextStep() {
    if (page === "home") { if (!input.trim()) throw new Error("Hãy nhập link hoặc kịch bản trước."); setFlowActive(true); setJobId(""); setSegmentId(""); setPage("voices"); return; }
    if (["voices", "media", "layout", "ai"].includes(page)) {
      await saveSettings();
      if (page === "ai") { if (!input.trim()) { setPage("home"); throw new Error("Hãy nhập link hoặc kịch bản để bắt đầu video."); } await enqueue(); }
      else setPage(workflow[workflow.findIndex(([key]) => key === page) + 1][0]);
    }
  }

  async function login(provider) {
    if (provider === "threads") {
      notify("Đăng nhập trong Edge, sau đó đóng tất cả cửa sổ Edge do app mở để quay lại tạo video.", false, 0);
      const { task_id } = await action("login", { provider });
      waitForTask(task_id).then(message => notify(message), error => notify(error.message, true));
      await refresh();
    } else notify(await action("login", { provider }));
  }

  if (stopped) return <div className="mx-auto max-w-xl p-12"><h1>Studio đã dừng</h1><p className="hint mt-4">Bạn có thể đóng tab này. Chạy lại run_studio.py để mở studio.</p></div>;
  if (!config || !state) return <div className="empty min-h-screen"><Icon name="layers" className="size-10 text-accent" /><h1>Threads Studio Pro</h1><p>{connected ? "Đang mở studio local…" : "Không kết nối được Python. Kiểm tra terminal đang chạy run_studio.py rồi tải lại trang."}</p></div>;

  const voices = [...state.voices];
  for (const id of config.selected_voices) if (!voices.some(v => v.full_id === id)) voices.push({ full_id: id, display_name: id, badge: "Đã lưu", provider: id.split(":")[0] });
  const saveButton = <button className="primary" disabled={pending} onClick={() => perform(saveSettings)}>Lưu cấu hình</button>;
  const threadsLogin = state.threads_login || { state: "idle", profile_available: false };
  const threadsWaiting = threadsLogin.state === "waiting";
  const threadsButtonLabel = threadsWaiting ? "Đang chờ đóng Edge…" : threadsLogin.profile_available ? "Mở lại Edge của app" : "Đăng nhập Threads";
  const threadsStatus = threadsWaiting ? "Đang chờ bạn hoàn tất trong Edge" : threadsLogin.state === "failed" ? "Chưa hoàn tất bước đăng nhập" : threadsLogin.state === "closed" ? "Edge đã đóng · Hồ sơ được giữ lại" : threadsLogin.profile_available ? "Có hồ sơ Edge được giữ trên máy" : "Chưa có hồ sơ Edge của app";
  const threadsHint = threadsWaiting ? "Đăng nhập xong hãy đóng tất cả cửa sổ Edge do app mở. App đang chờ Edge đóng trước khi dùng lại hồ sơ để đọc bài." : threadsLogin.state === "failed" ? threadsLogin.message : threadsLogin.state === "closed" ? threadsLogin.message : threadsLogin.profile_available ? "App sẽ dùng lại hồ sơ này khi đọc Threads. Có hồ sơ không đồng nghĩa phiên đăng nhập đã được xác minh." : "Đăng nhập một lần trong Edge của app. Edge giữ phiên trên máy để lần đọc bài tiếp theo dùng lại.";

  return <>
    {notice && <div role={notice.error ? "alert" : "status"} className={`fixed top-5 left-1/2 z-50 flex w-[min(640px,calc(100%-32px))] -translate-x-1/2 items-center gap-4 rounded-md border bg-surface px-4 py-3 text-sm shadow-lg ${notice.error ? "border-danger text-danger" : "border-line"}`}><span className="flex-1">{notice.message}</span><button className="quiet min-h-6 px-1" aria-label="Đóng thông báo" onClick={() => setNotice(null)}>×</button></div>}
    <div className="flex h-dvh overflow-hidden bg-well text-ink">
      <aside className="studio-sidebar relative flex shrink-0 flex-col border-r border-line bg-surface" style={{ width: collapsed ? 64 : railWidth }}>
        <div className="flex h-14 shrink-0 items-center justify-between gap-2 px-3">
          {!collapsed && <a href="#" onClick={event => { event.preventDefault(); setPage("home"); }} className="flex items-center gap-1.5 font-semibold tracking-tight text-ink no-underline"><Icon name="layers" className="size-6" /><span className="text-lg italic">Threads Studio</span></a>}
          <button className="quiet min-h-7 shrink-0 px-1.5" aria-label="Thu gọn thanh điều hướng" aria-expanded={!collapsed} onClick={() => setCollapsed(!collapsed)}><Icon name={collapsed ? "menu" : "chevron"} className="size-4" /></button>
        </div>
        <div className="px-2 pb-2"><button className="primary w-full gap-2 py-2" title="Tạo video mới" onClick={() => setPage("home")}><Icon name="plus" className="size-4" />{!collapsed && "Tạo video mới"}</button></div>
        <nav className="min-h-0 flex-1 overflow-y-auto px-2 pb-5" aria-label="Điều hướng studio">
          <div aria-label="Menu tham khảo">
            {referenceNav.map(([section, items]) => <React.Fragment key={section}>{!collapsed && <p className="mt-5 mb-1 px-2.5 text-[10px] font-medium tracking-wide text-muted">{section}</p>}{items.map(([key, label, icon]) => <button key={key} title={label} aria-current={page === key ? "page" : undefined} className={`sidebar-item quiet ${page === key ? "is-active" : ""}`} onClick={() => setPage(key)}><Icon name={icon} className="size-4 shrink-0" />{!collapsed && <span>{label}</span>}</button>)}</React.Fragment>)}
          </div>
          <div aria-label="Menu công cụ của bạn" className="mt-6 border-t border-line pt-1">
            {!collapsed && <p className="mt-4 px-2.5 text-[11px] font-semibold tracking-wider text-ink">CÔNG CỤ CỦA BẠN</p>}
            {nav.map(([section, items]) => <React.Fragment key={section}>{!collapsed && <p className="mt-4 mb-1 px-2.5 text-[10px] font-medium tracking-wide text-muted">{section}</p>}{items.map(([key, label, icon]) => <button key={key} title={label} aria-current={page === key ? "page" : undefined} className={`sidebar-item quiet ${page === key ? "is-active" : ""}`} onClick={() => setPage(key)}><Icon name={icon} className="size-4 shrink-0" />{!collapsed && <><span>{label}</span>{["queue", "inspector"].includes(key) && <span className="ml-auto text-xs">{key === "queue" ? state.active_count : state.review_count}</span>}</>}</button>)}</React.Fragment>)}
          </div>
        </nav>
        <div className="shrink-0 border-t border-line px-2 py-2"><button className={`sidebar-item quiet ${page === "home" ? "is-active" : ""}`} title="Trang chủ" onClick={() => setPage("home")}><Icon name="home" className="size-4" />{!collapsed && "Trang chủ"}</button></div>
        {!collapsed && <ResizeHandle label="Đổi rộng thanh điều hướng" value={railWidth} onChange={setRailWidth} min={192} max={340} />}
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex min-h-14 shrink-0 flex-wrap items-center justify-between gap-3 border-b border-line bg-surface px-5 py-2 text-sm font-semibold"><span>{page === "home" ? "Tạo Video" : [...referenceNav, ...nav].flatMap(([, items]) => items).find(([key]) => key === page)?.[1] || "Threads Studio"}</span><div className="actions"><button className="quiet" aria-pressed={logsOpen} aria-controls="processing-log" onClick={() => setLogsOpen(!logsOpen)}>Nhật ký</button><button className="quiet" aria-label="Chuyển giao diện sáng tối" aria-pressed={theme === "dark"} onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>{theme === "dark" ? "☀ Sáng" : "☾ Tối"}</button></div></header>
        <Workflow page={page} navigate={navigate} jobId={jobId} />
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden"><div className="workspace-top flex min-h-0 flex-1 flex-col overflow-y-auto lg:flex-row lg:overflow-hidden">
      <main className={`min-w-0 flex-1 px-4 py-7 sm:px-6 lg:overflow-y-auto ${page === "home" ? "home-workspace" : ""}`}>
        {!connected && <p className="mb-4 rounded-md border border-danger p-3 text-sm text-danger" role="alert">Mất kết nối Python. Đang thử kết nối lại; chỉnh sửa đang nhập được giữ trong tab này.</p>}
        <div hidden={contentPage !== "home"} className="mx-auto max-w-[672px] pt-3 sm:pt-4">
          <h1 className="mb-10 text-center text-[30px] font-semibold tracking-tight">Dựng video mới</h1>
          <section className="home-composer rounded-lg border border-line bg-surface" aria-label="Tạo video từ nội dung">
            <div className="flex items-center gap-1 px-3 pt-2"><button className={`composer-mode quiet ${mode === "urls" ? "!text-ink" : "!text-muted"}`} aria-pressed={mode === "urls"} onClick={() => setMode("urls")}>Link bài viết</button><button className={`composer-mode quiet ${mode === "manual" ? "!text-ink" : "!text-muted"}`} aria-pressed={mode === "manual"} onClick={() => setMode("manual")}>Tự viết</button></div>
            <textarea aria-label="Nội dung tạo video" className="!min-h-28 !resize-none !border-0 !bg-transparent !px-4 !pt-2 !outline-none" rows={4} value={input} onChange={event => setInput(event.target.value)} placeholder={mode === "urls" ? "Dán link bài viết Threads, mỗi dòng một link..." : "Nhập kịch bản của bạn. Ngăn cách các đoạn bằng dòng trống..."} />
            <div className="flex flex-wrap items-center justify-between gap-2 px-3 pb-3"><div className="flex gap-1"><button className={`quiet !px-2 ${homeConfig ? "!text-ink" : "!text-muted"}`} aria-expanded={homeConfig} onClick={() => setHomeConfig(!homeConfig)}><Icon name="sliders" className="size-4" />Cấu hình</button><button className="quiet !px-2 !text-muted" onClick={() => setPage("videos")}><Icon name="inbox" className="size-4" />Sản phẩm</button></div><button className="primary !min-h-9 gap-2" disabled={pending || !connected || !input.trim()} onClick={() => perform(nextStep)}><Icon name="video" className="size-4" />Tiếp tục · Giọng đọc</button></div>
          </section>
          {homeConfig && <section className="mt-4 rounded-lg border border-line bg-surface p-5" aria-label="Cấu hình tạo video"><FieldGrid group="queue" value={config} onChange={onConfig} /><ReviewOptions config={config} onConfig={onConfig} /><div className="actions mt-4"><button onClick={() => setPage("voices")}>Chọn giọng đọc</button><button onClick={() => setPage("media")}>Nguồn video · Bố cục</button></div></section>}
        </div>
        <div hidden={contentPage !== "videos"}>
          <Heading eyebrow="THƯ VIỆN" title="Video đã tạo">Các thành phẩm đã lưu trên máy của bạn.</Heading>
          {!state.jobs.some(item => item.stage === "completed") ? <div className="empty"><Icon name="video" className="size-10" /><p>Chưa có video hoàn tất.</p><button onClick={() => setPage("home")}>Tạo video mới</button></div> : <div className="grid gap-5 sm:grid-cols-2 2xl:grid-cols-3">{state.jobs.filter(item => item.stage === "completed").map(item => <article key={item.job_id} className="overflow-hidden rounded-lg border border-line bg-surface"><div className="flex aspect-video items-center justify-center overflow-hidden bg-black">{item.video_url ? <video src={item.video_url} controls preload="none" className="h-full w-full object-contain" /> : <span className="px-5 text-center text-sm text-muted">File không còn ở đường dẫn đã lưu.</span>}</div><div className="p-4"><h2 className="truncate">{item.title_slug}</h2><p className="mt-2 truncate text-xs text-muted" title={item.output_mp4}>{item.output_mp4 || "Chưa có đường dẫn video"}</p><div className="actions mt-4">{item.video_url && <a className="button" href={item.video_url} download>Tải MP4</a>}<button onClick={() => selectJob(item.job_id)}>Xem kịch bản</button></div></div></article>)}</div>}
        </div>
        <div hidden={contentPage !== "resources"}>
          <Heading eyebrow="SÁNG TẠO" title="Kho tài nguyên">Nguồn media local đang dùng trong studio.</Heading>
          <div className="divide-y divide-line">{[["Video nền", config.media.bg_video_path || config.media.bg_video_dir], ["Video phụ", config.media.sub_video_dir], ["Nhạc nền", config.media.bgm_dir], ["SFX chuyển cảnh", config.media.sfx_dir], ["Meme Sound", config.media.meme_sound_dir]].map(([label, path]) => <div key={label} className="flex flex-wrap items-center justify-between gap-3 py-5"><div className="min-w-0"><h2>{label}</h2><p className="hint mt-1 break-all">{path || "Chưa chọn nguồn"}</p></div><button onClick={() => setPage(label === "Meme Sound" ? "meme_sound" : "media")}>Quản lý</button></div>)}</div>
        </div>
        <div hidden={contentPage !== "tools"}>
          <Heading eyebrow="SÁNG TẠO" title="Công cụ">Các công cụ sản xuất đang có trong studio của bạn.</Heading>
          <div className="grid gap-3 sm:grid-cols-2">{nav.flatMap(([, items]) => items).map(([key, label, icon]) => <button key={key} className="justify-start gap-3 !p-5" onClick={() => setPage(key)}><Icon name={icon} /><span>{label}</span></button>)}</div>
        </div>
        <div hidden={contentPage !== "queue"}>
          <Heading eyebrow="KHÔNG GIAN SẢN XUẤT" title="Từ cuộc trò chuyện đến video">Nhập bài viết, duyệt lời đọc và xuất video theo bố cục của bạn.</Heading>
          {(!flowActive || !jobId) && <Panel title="Nhập nội dung" actions={<><button disabled={pending || threadsWaiting} onClick={() => perform(() => login("threads"))}>{threadsButtonLabel}</button><button disabled={pending} onClick={() => perform(async () => { setInput(await action("demo")); setMode("manual"); })}>Bài mẫu Video 1</button></>}>
            <div className="mb-4 flex border-b border-line">{[["urls", "Link Threads"], ["manual", "Kịch bản nhập tay"]].map(([key, text]) => <button key={key} className={`tab ${mode === key ? "active" : ""}`} aria-pressed={mode === key} onClick={() => setMode(key)}>{text}</button>)}</div>
            <textarea aria-label="Nội dung đầu vào" rows={5} value={input} onChange={e => setInput(e.target.value)} placeholder={mode === "urls" ? "Dán link Threads, mỗi dòng một bài viết…" : "@tac_gia: Nội dung bài viết…\n\n@binh_luan: Nội dung bình luận…"} />
            <p className="hint mt-2">{mode === "urls" ? "Tối đa 50 bài/lô. Edge cuộn 10 lần; chỉ xếp hạng bình luận đã tải, không bảo đảm toàn bài." : "Chia các đoạn bằng dòng trống hoặc ---. Tách nhiều kịch bản bằng ===, tối đa 50 kịch bản/lô."}</p>
            {threadsWaiting && <p className="hint mt-3" role="status">{threadsHint}</p>}
            <FieldGrid group="queue" value={config} onChange={onConfig} />
            <div className="flex flex-wrap items-center justify-between gap-3"><ReviewOptions config={config} onConfig={onConfig} /><button className="primary" disabled={pending || !connected} onClick={() => perform(enqueue)}><Icon name="play" className="size-4" />Tạo video đa luồng</button></div>
          </Panel>}
          <Panel title={<span className="flex items-center gap-2">Hàng đợi xử lý <span className="badge">{state.jobs.length} video</span></span>} actions={<><button disabled={pending} onClick={() => perform(async () => { if (Object.values(drafts).some(item => item.dirty)) throw new Error("Hãy lưu các kịch bản đang sửa trước khi duyệt tất cả."); const count = await action("approve_all"); notify(`Đã duyệt ${count} video.`); await refresh(); })}>Duyệt tất cả chờ</button><button className="danger" disabled={pending} onClick={() => perform(async () => { await action("cancel_all"); await refresh(); })}>Dừng lô</button></>}>
            <div className="mb-4 flex items-center gap-4"><span className="hint whitespace-nowrap">{state.active_count} đang chạy · {state.review_count} chờ duyệt</span><progress className="w-full" max="100" value={state.jobs.length ? state.jobs.reduce((total, item) => total + item.progress_pct, 0) / state.jobs.length : 0} aria-label="Tiến độ cả lô" /></div>
            {!state.jobs.length ? <div className="empty"><Icon name="layers" className="size-9 text-accent" /><h3 className="font-semibold">Sẵn sàng cho video đầu tiên</h3><p>Dán link Threads hoặc nạp bài mẫu để bắt đầu.</p></div> : <div className="overflow-auto"><table className="w-full border-collapse"><thead><tr><th>Bài viết / Chủ đề</th><th>Khâu hiện tại</th><th>Tiến độ</th><th>Thao tác</th></tr></thead><tbody>{state.jobs.map(item => <tr key={item.job_id}><td><p className="max-w-64 truncate font-medium">{item.title_slug === "threads-video" ? item.source_url || "Kịch bản nhập tay" : item.title_slug}</p><p className="mt-1 font-mono text-xs text-muted">#{item.job_id} · {item.segment_count} đoạn</p><p className="mt-1 text-xs text-muted">AI: {tokenNumber(item.ai_summary?.input_tokens)} / {tokenNumber(item.ai_summary?.output_tokens)} token vào/ra</p></td><td><span className={`badge ${item.stage === "failed" ? "!text-danger" : ""}`}>{item.stage_label}</span><p className="mt-1 max-w-72 text-xs break-words text-muted">{item.status_detail}</p></td><td className="min-w-20 tabular-nums">{Math.round(item.progress_pct)}%<progress className="mt-2 block w-full" value={item.progress_pct} max="100" aria-label={`Tiến độ ${item.job_id}`} /></td><td><div className="actions flex-nowrap"><button onClick={() => selectJob(item.job_id)}>Xem / Sửa</button>{item.can_resume && <button className="primary" disabled={pending || !connected} onClick={() => perform(() => resumeJob(item.job_id))}>Tiếp tục tạo</button>}{item.video_url && <button onClick={() => setVideo(item.video_url)}>Xem MP4</button>}{!["completed", "failed", "cancelled"].includes(item.stage) && <button className="danger" onClick={() => perform(async () => { await action("cancel", { job_id: item.job_id }); await refresh(); })}>Dừng</button>}</div></td></tr>)}</tbody></table></div>}
          </Panel>
        </div>
        <div hidden={contentPage !== "inspector"}>
          <Heading eyebrow="DUYỆT NỘI DUNG" title="Kịch bản của bạn">Sửa lời đọc, giữ giọng kể và chọn thứ tự xuất hiện.</Heading>
          <div className="actions border-b border-line pb-4"><label htmlFor="inspect-job" className="text-sm">Đang kiểm tra job</label><select id="inspect-job" className="min-w-44 flex-1" value={jobId} onChange={e => selectJob(e.target.value)}><option value="">Chọn một job…</option>{state.jobs.map(item => <option key={item.job_id} value={item.job_id}>#{item.job_id} · {item.title_slug} · {item.stage_label}{drafts[item.job_id]?.dirty ? " · Chưa lưu" : ""}</option>)}</select>{summary && <span className="badge">{summary.busy ? (["cancelled", "failed"].includes(summary.stage) ? "Đang chờ dừng hẳn…" : "Đang chuẩn hóa…") : summary.stage_label}</span>}</div>
          {!job ? <div className="empty">Chọn một job trong hàng đợi để xem và duyệt nội dung.</div> : <>
            {["cancelled", "failed"].includes(summary?.stage) && <Panel title="Tiếp tục video đang dở" actions={<button className="primary" disabled={pending || !connected || !summary?.can_resume} onClick={() => perform(() => resumeJob(jobId))}><Icon name="play" className="size-4" />Tiếp tục tạo</button>}><p className="hint">{summary?.busy ? "Đang chờ tác vụ cũ kết thúc trước khi có thể chạy tiếp." : "Giữ nội dung đã duyệt, dùng lại audio còn phù hợp và tạo phần còn thiếu. Nếu nội dung chưa được duyệt, video sẽ trở lại bước duyệt."}</p></Panel>}
            <Candidates key={job.job_id} job={job} disabled={!editable} reselect={(comment_sort, max_comments) => perform(async () => { await action("reselect", { ...jobPayload(), comment_sort, max_comments }); await loadJob(jobId, true); await refresh(); notify("Đang chọn lại top N và chuẩn hóa từ dữ liệu đã tải."); })} />
            {!job.segments.length ? <div className="empty">{summary?.stage === "failed" ? job.error_message : "Đang chuẩn bị nội dung. Các đoạn sẽ xuất hiện sau bước thu thập và AI."}</div> : <div className="inspector-split">
              <div className="order-pane" style={{ "--order-width": `${orderWidth}px` }}><Panel title="Thứ tự xuất hiện" actions={<span className="badge">{job.segments.length} đoạn</span>}><p className="hint mb-3">Kéo thẻ để đổi thứ tự. Alt + phím lên/xuống cũng di chuyển thẻ. Bấm Lưu kịch bản để giữ thay đổi.</p><SegmentCards job={job} selected={segment?.seg_id} editable={editable} select={setSegmentId} reorder={segments => jobPatch({ segments })} /></Panel><ResizeHandle label="Đổi rộng danh sách thẻ" value={orderWidth} onChange={setOrderWidth} min={170} max={380} /></div>
              {segment && <Panel className="min-w-0 flex-1" title={`@${segment.username}`} actions={<label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={segment.enabled} disabled={!editable} onChange={e => segmentPatch({ enabled: e.target.checked })} />Bật đoạn</label>}>
                <div className="flex flex-col gap-3"><label className="text-sm">Nội dung gốc · Hiển thị trên thẻ<textarea rows={5} className="mt-1" value={segment.raw_text} disabled={!editable} onChange={e => segmentPatch({ raw_text: e.target.value })} /></label><label className="text-sm">Lời đọc · Dùng cho TTS<textarea rows={6} className="mt-1" value={segment.spoken_text} disabled={!editable} onChange={e => segmentPatch({ spoken_text: e.target.value })} /></label><label className="text-sm">Giọng đọc của đoạn<VoiceSelect voices={voices} value={segment.voice_id} disabled={!editable} onChange={value => segmentPatch({ voice_id: value })} /></label><div className="actions"><button disabled={pending} onClick={() => perform(() => previewVoice(segment.spoken_text || segment.raw_text, segment.voice_id || config.selected_voices[0]))}>Nghe thử đoạn</button><button disabled={!editable} onClick={() => perform(async () => { await saveSettings(); notify("Đang chuẩn hóa lại lời đọc…"); await saveJob(); await taskAction("normalize", jobPayload()); await refresh(); await loadJob(jobId, true); notify("Đã chuẩn hóa lời đọc."); })}>Chuẩn hóa lại</button></div></div>
              </Panel>}
            </div>}
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line bg-well py-4 lg:sticky lg:bottom-0"><span className={`text-sm ${job.dirty ? "text-accent" : "text-muted"}`}>{job.dirty ? "Có chỉnh sửa chưa lưu" : editable ? "Kịch bản đã lưu" : "Chỉ xem trong khi job đang xử lý hoặc đã hoàn tất"}</span><div className="actions"><button disabled={!editable} onClick={() => perform(saveJob)}>Lưu kịch bản</button><button className="primary" disabled={!editable || !job.segments.length} onClick={() => perform(async () => { await action("approve", jobPayload()); await loadJob(jobId, true); await refresh(); notify("Đã duyệt — đang tạo giọng và xuất video."); if (flowActive) setPage("queue"); })}><Icon name="check" className="size-4" />Duyệt xong · Xuất video</button></div></div>
          </>}
        </div>
        <div hidden={contentPage !== "voices"}>
          <Heading eyebrow="GIỌNG KỂ" title="Giọng đọc AI" actions={<button disabled={pending} onClick={() => perform(async () => { notify("Đang tải danh sách giọng…"); const count = await taskAction("voices"); await refresh(); notify(`Đã tải ${count} giọng.`); })}>Tải danh sách giọng</button>}>Chọn một hoặc nhiều giọng cho cuộc trò chuyện.</Heading>
          <Panel title="Phân giọng"><FieldGrid group="voice" value={config} onChange={onConfig} /><input aria-label="Tìm giọng" type="search" value={voiceSearch} onChange={e => setVoiceSearch(e.target.value)} placeholder="Tìm tên giọng hoặc nhà cung cấp…" /><div className="mt-4 grid max-h-100 grid-cols-1 gap-2 overflow-auto sm:grid-cols-2">{voices.filter(voice => `${voice.display_name} ${voice.badge}`.toLocaleLowerCase().includes(voiceSearch.toLocaleLowerCase())).map(voice => <label key={voice.full_id} className={`flex items-start gap-3 rounded-md border p-3 text-sm ${config.selected_voices.includes(voice.full_id) ? "border-accent bg-accent-soft" : "border-line"}`}><input type="checkbox" className="mt-1" checked={config.selected_voices.includes(voice.full_id)} onChange={e => onConfig("selected_voices", e.target.checked ? [...config.selected_voices, voice.full_id] : config.selected_voices.filter(id => id !== voice.full_id))} /><span className="min-w-0 break-words">{voice.display_name}<small className="mt-1 block text-xs text-muted">{voice.badge}</small></span></label>)}</div><p className="hint mt-3">{config.selected_voices.length} giọng đã chọn. Các ID đã lưu vẫn dùng được trước khi tải catalog đầy đủ.</p></Panel>
          <Panel title="Nghe thử"><div className="flex flex-col gap-3"><VoiceSelect voices={voices} value={auditionVoice || config.preview_voice_id} onChange={value => { setAuditionVoice(value); onConfig("preview_voice_id", value); }} /><textarea aria-label="Lời đọc mẫu" rows={3} value={auditionText} onChange={e => setAuditionText(e.target.value)} /><div><button className="primary" disabled={pending} onClick={() => perform(() => previewVoice(auditionText, auditionVoice || config.preview_voice_id))}>Tạo và nghe thử</button></div><p className="hint">Nghe thử gọi TTS. Offline ở phần AI không làm TTS hoạt động offline.</p></div></Panel>
          <Panel title="VieNeu · Clone giọng và CapCut"><FieldGrid group="tts" value={config} onChange={onConfig} />{saveButton}</Panel>
        </div>
        <div hidden={contentPage !== "media"}>
          <Heading eyebrow="NGUYÊN LIỆU" title="Nguồn video · Nhạc">Nhập đường dẫn file hoặc thư mục trên máy này.</Heading>
          <Panel title="Nạp preset"><div className="actions"><select aria-label="Chọn preset" className="max-w-80" value={preset} onChange={event => setPreset(event.target.value)}><option value="">Chọn preset…</option>{config.presets.map((item, index) => <option key={index} value={index}>{item.name}</option>)}</select><button disabled={preset === ""} onClick={() => { const { name, ...profile } = config.presets[Number(preset)]; setConfig(previous => ({ ...previous, ...structuredClone(profile) })); notify(`Đã nạp preset: ${name}`); }}>Nạp preset</button></div></Panel>
          <Panel title="Đường dẫn video nền và video phụ"><FieldGrid group="video" value={config} onChange={onConfig} /></Panel>
          <Panel title="Cách dùng video nền"><FieldGrid group="video_options" value={config} onChange={onConfig} /><p className="hint">File nền riêng được ưu tiên hơn thư mục. Nền ngắn được lặp; Random Start chọn một đoạn liên tục khi nguồn dài hơn video.</p></Panel>
          <Panel title="Đường dẫn nhạc và hiệu ứng"><FieldGrid group="audio_paths" value={config} onChange={onConfig} /></Panel>
          <Panel title="Nhạc nền và hiệu ứng"><FieldGrid group="audio" value={config} onChange={onConfig} /></Panel>
          <Panel title="Đường dẫn kết quả"><FieldGrid group="output" value={config} onChange={onConfig} /><button onClick={() => perform(() => action("open_outputs"))}>Mở thư mục kết quả</button></Panel>
          <Panel title="Preset của bạn"><div className="actions"><input aria-label="Tên preset mới" className="max-w-72" value={presetName} onChange={e => setPresetName(e.target.value)} placeholder="Tên preset mới…" /><button disabled={pending} onClick={() => perform(async () => { const { presets, ...settings } = config; const saved = await action("preset_save", { name: presetName, settings }); setConfig(saved); setPresetName(""); notify("Đã lưu preset mới."); })}>Lưu preset mới</button>{saveButton}</div><p className="hint mt-3">Nguồn media và bố cục được chụp riêng khi tạo từng job.</p></Panel>
        </div>
        <div hidden={contentPage !== "layout"}><Heading eyebrow="BỐ CỤC" title="Khung hình và thẻ video">Cấu hình cho video mới. Kéo trực tiếp các lớp trong sân khấu để xem trước.</Heading><Panel title="Bố cục mặc định"><FieldGrid group="layout" value={config.layout} onChange={(path, value) => onConfig(`layout.${path}`, value)} /><div className="actions"><button onClick={() => onConfig("layout", { ...defaultLayout })}>Đặt lại bố cục</button>{saveButton}</div></Panel></div>
        <div hidden={contentPage !== "settings"}>
          <Heading eyebrow="THIẾT LẬP" title="Hệ thống studio">Kết nối, lưu trữ và giới hạn xử lý. Model và đường dẫn media có trang riêng.</Heading>
          <Panel title="Lưu trữ local"><div className="flex flex-wrap items-center justify-between gap-4"><div><span className={`badge ${state.database?.enabled && !state.database.connected ? "!text-danger" : ""}`}>{state.database?.connected ? "PostgreSQL đã kết nối" : state.database?.enabled ? "PostgreSQL mất kết nối" : "Chưa cấu hình PostgreSQL"}</span><p className="hint mt-2">{state.database?.connected ? `Cấu hình và dữ liệu video được lưu trong schema ${state.database.schema}. Video chỉ lưu đường dẫn file.` : "Các file media vẫn nằm trên máy của bạn."}</p></div><button onClick={() => perform(() => action("open_outputs"))}>Mở thư mục kết quả</button></div></Panel>
          <Panel title="Threads · Phiên đăng nhập"><div role="status" aria-live="polite"><span className={`badge ${threadsLogin.state === "failed" ? "!text-danger" : ""}`}>{threadsStatus}</span><p className="hint mt-3">{threadsHint}</p></div><div className="actions mt-4"><button disabled={pending || threadsWaiting} onClick={() => perform(() => login("threads"))}>{threadsButtonLabel}</button><button disabled={threadsWaiting} onClick={() => setPage("home")}>Về dựng video mới</button></div><p className="hint mt-3">Edge giữ phiên trên máy. Đăng nhập không tự tạo video: sau khi đóng Edge, về trang chủ và dán link bài viết. </p></Panel>
        </div>
        <div hidden={contentPage !== "ai"}><Heading eyebrow="AI" title="Model và tài khoản AI">Chọn model xử lý lời đọc, OCR và meme sound.</Heading>
          <Panel title="AI chuẩn hóa và OCR"><FieldGrid group="ai" value={config} onChange={onConfig} /><ModelPicker key={config.ai_provider} provider={config.ai_provider} value={config.ai_provider === "codex" ? config.codex_model : config.antigravity_model} onChange={value => onConfig(config.ai_provider === "codex" ? "codex_model" : "antigravity_model", value)} metadata={state.ai_metadata?.[config.ai_provider]} busy={Boolean(metadataBusy[config.ai_provider])} refresh={() => perform(() => refreshMetadata(config.ai_provider))} openQuota={() => perform(async () => notify(await action("quota_terminal", { provider: "antigravity" })))} /><div className="actions">{config.ai_provider !== "offline" && <button onClick={() => perform(() => login(config.ai_provider))}>Đăng nhập {config.ai_provider === "codex" ? "ChatGPT / Codex" : "Google / Antigravity"}</button>}</div><p className="hint mt-3">{config.ai_provider === "offline" ? "Chỉ dùng từ điển viết tắt; không OCR." : "Hoàn tất đăng nhập trong cửa sổ CLI được mở. Chọn model không cấp thêm quyền hoặc quota."}</p></Panel>
        </div>
        <div hidden={contentPage !== "settings"}>
          <Panel title="Xử lý đa luồng và đầu ra"><p className="hint">Một job là một video. Worker là một suất xử lý song song; tăng worker không phải lúc nào cũng nhanh hơn.</p><FieldGrid group="workers" value={config} onChange={onConfig} /><dl className="grid gap-3 text-sm sm:grid-cols-2"><div><dt className="font-medium">Worker thu thập</dt><dd className="hint mt-1">Số job lấy bài/bình luận cùng lúc. Các lần dùng chung hồ sơ Edge vẫn xếp hàng.</dd></div><div><dt className="font-medium">Worker AI</dt><dd className="hint mt-1">Số job chuẩn hóa/OCR/chọn sound cùng lúc. OCR là đọc chữ trong ảnh; tăng số này có thể chạm quota nhanh hơn.</dd></div><div><dt className="font-medium">TTS / Render</dt><dd className="hint mt-1">TTS tạo giọng đọc; render ghép hình, audio và xuất MP4. Mỗi job TTS còn chia tối đa 4 đoạn song song.</dd></div><div><dt className="font-medium">NVENC / Hàng đợi</dt><dd className="hint mt-1">NVENC dùng GPU NVIDIA để mã hóa video. Hết worker trống thì job chờ; nhiều worker hơn cần thêm RAM/CPU/GPU.</dd></div></dl><p className="hint mb-4">Chỉ đổi số worker khi các job đang xử lý đã hoàn tất. Dừng job được kiểm tra giữa các bước, không ngắt ngay mọi subprocess.</p><div className="actions">{saveButton}<button className="danger" onClick={() => perform(async () => { if (Object.values(drafts).some(item => item.dirty)) throw new Error("Hãy lưu các kịch bản đang sửa trước khi dừng studio."); await action("shutdown"); clearTimeout(pollRef.current); setStopped(true); })}>Dừng studio</button></div></Panel>
        </div>
        <div hidden={contentPage !== "meme_sound"}><SoundLibrary config={config} onConfig={onConfig} save={saveSettings} perform={perform} taskAction={taskAction} notify={notify} /></div>
        <div hidden={contentPage !== "meme_image"}><Heading eyebrow="KHO MEME" title="Meme Image" /><div className="empty"><Icon name="image" className="size-10" /><h2>Tính năng sẽ phát triển sau</h2><p>Quản lý kho ảnh meme và chọn ảnh theo ngữ cảnh bình luận.</p></div></div>
        {audio && <div className="sticky bottom-3 z-20 mt-5 flex flex-wrap items-center gap-3 rounded-md border border-line bg-surface p-3"><span className="text-sm">Nghe thử giọng đọc</span><audio ref={audioRef} src={audio} controls className="h-9 min-w-48 flex-1" /><button className="quiet" aria-label="Đóng trình nghe thử" onClick={() => setAudio("")}>×</button></div>}
        {["voices", "media", "layout", "ai"].includes(page) && <div className="flow-actions actions"><button disabled={pending} onClick={() => setPage(workflow[Math.max(0, workflow.findIndex(([key]) => key === page) - 1)][0])}>Quay lại</button><button className="primary" disabled={pending || !connected} onClick={() => perform(nextStep)}>{page === "ai" ? "Thu thập · Tạo kịch bản" : `Tiếp tục · ${workflow[workflow.findIndex(([key]) => key === page) + 1][1]}`}</button></div>}
      </main>
      {page !== "home" && <aside className="right-dock" aria-label="Sân khấu và token AI" style={{ "--right-width": `${rightWidth}px` }}><ResizeHandle label="Đổi rộng panel bên phải" value={rightWidth} onChange={setRightWidth} min={290} max={680} reverse /><div className="stage-pane" style={{ "--stage-height": `${stageHeight}px` }}><Stage layout={layout} onChange={onLayout} job={stageJob} segment={stageJob ? segment : null} readonly={Boolean(stageJob && !editable)} video={video || (summary?.stage === "completed" ? summary.video_url : "")} notify={notify} perform={perform} controls={page === "inspector"} /><ResizeHandle label="Đổi chiều cao sân khấu" value={stageHeight} onChange={setStageHeight} min={180} max={720} axis="y" /></div><div className="token-pane">{job ? <><p className="text-xs text-muted">Job #{job.job_id} · {job.title_slug}</p><AIUsagePanel job={job} compact /></> : <><h2>AI · Token vào / ra</h2><p className="hint mt-3">Chọn một job trong hàng đợi để theo dõi số liệu.</p></>}</div></aside>}
        </div>
        <section id="processing-log" className={`log-dock ${logsOpen ? "is-open" : ""}`} style={{ "--log-height": `${logsHeight}px` }} aria-label="Nhật ký xử lý">{logsOpen && <ResizeHandle label="Đổi chiều cao nhật ký" value={logsHeight} onChange={setLogsHeight} min={100} max={460} axis="y" reverse />}<div className="flex shrink-0 items-center justify-between gap-3 border-b border-line px-4 py-1"><button className="quiet !min-h-7 !py-0" aria-expanded={logsOpen} onClick={() => setLogsOpen(!logsOpen)}>Nhật ký xử lý · {state.logs.length} dòng</button>{logsOpen && <button className="quiet !min-h-7" aria-label="Đóng nhật ký" onClick={() => setLogsOpen(false)}>×</button>}</div>{logsOpen && <pre className="min-h-0 flex-1 overflow-auto px-4 py-3 font-mono text-xs leading-relaxed break-words whitespace-pre-wrap text-muted">{state.logs.join("\n") || "Studio sẵn sàng."}</pre>}</section>
        </div>
      </div>
    </div>
  </>;
}

createRoot(document.getElementById("root")).render(<App />);
