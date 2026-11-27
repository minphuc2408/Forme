import React, { useState } from "react";

export const tokenNumber = value => Number.isInteger(value) ? value.toLocaleString("vi-VN") : "—";
const localTime = value => value ? new Date(typeof value === "number" ? value * 1000 : value).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "Chưa có dữ liệu";
const windowName = minutes => minutes === 300 ? "5 giờ" : minutes % 1440 === 0 ? `${minutes / 1440} ngày` : minutes % 60 === 0 ? `${minutes / 60} giờ` : `${minutes} phút`;

export function QuotaSnapshot({ snapshot }) {
  if (!snapshot) return <p className="hint">Chưa ghi nhận.</p>;
  const quota = snapshot.quota;
  return <div className="space-y-3 text-sm">
    <p className="text-xs text-muted">Ghi nhận lúc {localTime(snapshot.captured_at)}</p>
    {quota?.windows?.length ? quota.windows.map(window => <div key={`${window.bucket}/${window.window_minutes}`}>
      <div className="flex flex-wrap justify-between gap-2"><span>{window.name} · {windowName(window.window_minutes)}</span><span className="tabular-nums">Còn {window.remaining_percent}%</span></div>
      <progress className="my-1 w-full" max="100" value={window.used_percent} aria-label={`Đã dùng ${window.used_percent}% hạn mức ${windowName(window.window_minutes)}`} />
      <p className="text-xs text-muted">Đã dùng {window.used_percent}% · Reset {localTime(window.resets_at)} (giờ Việt Nam)</p>
    </div>) : <p className="hint leading-relaxed">{quota?.message || "CLI chưa cung cấp hạn mức."}</p>}
  </div>;
}

export function ModelPicker({ provider, value, onChange, metadata, busy, refresh, openQuota }) {
  const [custom, setCustom] = useState(false);
  const choices = metadata?.models || [];
  const known = choices.some(model => model.id === value);
  const label = provider === "codex" ? "Codex" : "Antigravity";
  if (provider === "offline") return <p className="hint my-4">Từ điển Offline không gọi model và không dùng token AI.</p>;
  return <div className="my-4 space-y-4">
    <div className="flex flex-wrap items-end gap-3"><label className="flex min-w-52 flex-1 flex-col gap-1.5 text-sm">Model {label}
      <select aria-label={`Chọn model ${label}`} value={custom ? "__custom__" : value} onChange={event => { if (event.target.value === "__custom__") setCustom(true); else { setCustom(false); onChange(event.target.value); } }}>
        {!known && <option value={value}>{value || "Chưa chọn"} · Đang lưu</option>}
        {choices.map(model => <option key={model.id} value={model.id}>{model.name} ({model.id})</option>)}
        <option value="__custom__">Nhập tên model khác…</option>
      </select>
    </label><button disabled={busy} onClick={refresh}>{busy ? "Đang đọc CLI…" : "Tải lại model và hạn mức"}</button></div>
    {custom && <label className="flex flex-col gap-1.5 text-sm">Tên model theo CLI<input aria-label={`Nhập model ${label}`} value={value} onChange={event => onChange(event.target.value)} placeholder="Nhập chính xác ID model…" /></label>}
    <p className="hint">{choices.length ? `${choices.length} model từ CLI hiện tại. ` : "Chưa tải được danh sách model. Có thể nhập tên khác. "}Chọn model không cấp thêm quyền hoặc quota; bấm Lưu cấu hình trước khi tạo job.</p>
    <div className="border-t border-line pt-4"><h3 className="mb-3 text-sm font-semibold">Hạn mức tài khoản hiện tại</h3><QuotaSnapshot snapshot={metadata} /></div>
    {provider === "antigravity" && <button onClick={openQuota}>Mở CLI xem /usage</button>}
  </div>;
}

export function AIUsagePanel({ job, compact = false }) {
  const usage = job.ai_usage || {};
  const summary = job.ai_summary || {};
  const calls = usage.calls || [];
  const providers = [...new Set([...Object.keys(usage.quota_before || {}), ...Object.keys(usage.quota_after || {})])];
  return <details className={`panel ${compact ? "usage-compact" : ""}`} open={compact || job.stage === "completed"}>
    <summary className="cursor-pointer text-sm font-semibold">AI · Token và hạn mức <span className="ml-2 font-normal text-muted">Vào {tokenNumber(summary.input_tokens)} · Ra {tokenNumber(summary.output_tokens)}</span></summary>
    <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">{[["Token vào", summary.input_tokens], ["Token ra", summary.output_tokens], ["Cache đọc", summary.cached_input_tokens], ["Suy luận", summary.reasoning_tokens]].map(([label, value]) => <div key={label} className="border-l-2 border-line pl-3"><p className="text-xs text-muted">{label}</p><p className="mt-1 text-lg font-semibold tabular-nums">{tokenNumber(value)}</p></div>)}</div>
    <p className="hint mt-4">{calls.length ? `${calls.length} lượt xử lý · ${summary.reported_calls ?? 0} lượt có đủ token vào/ra · ${summary.failed_calls ?? 0} lượt lỗi.` : "Chưa có số liệu AI cho job này; không truy hồi số token của các job cũ."} Dấu — nghĩa là CLI không cung cấp số liệu, không phải 0 token.</p>
    {calls.length > 0 && <div className="mt-4 overflow-auto"><table className="w-full border-collapse"><thead><tr><th>Công việc</th><th>Provider / Model yêu cầu</th><th>Token vào</th><th>Token ra</th><th>Cache</th><th>Suy luận</th><th>Thời gian</th><th>Kết quả</th></tr></thead><tbody>{calls.map((call, index) => <tr key={index}><td className="min-w-40">{call.operation}{call.image_count > 0 && <span className="mt-1 block text-xs text-muted">{call.image_count} ảnh gửi OCR</span>}</td><td><p>{call.provider}</p><p className="mt-1 whitespace-nowrap text-xs text-muted">{call.model || "Không dùng model"}</p></td>{["input_tokens", "output_tokens", "cached_input_tokens", "reasoning_tokens"].map(field => <td key={field} className="text-right tabular-nums">{tokenNumber(call[field])}</td>)}<td className="whitespace-nowrap tabular-nums">{call.duration_seconds}s</td><td className={call.status === "failed" ? "text-danger" : ""}>{call.status === "failed" ? "Lỗi" : "Hoàn tất"}</td></tr>)}</tbody></table></div>}
    {providers.map(provider => <div key={provider} className="mt-5 border-t border-line pt-4"><h3 className="mb-3 text-sm font-semibold">Hạn mức {provider}</h3><div className="grid gap-5 sm:grid-cols-2"><div><p className="mb-2 text-sm font-medium">Trước khi xử lý AI</p><QuotaSnapshot snapshot={usage.quota_before?.[provider]} /></div><div><p className="mb-2 text-sm font-medium">Sau khi job kết thúc</p><QuotaSnapshot snapshot={usage.quota_after?.[provider]} /></div></div></div>)}
    <p className="mt-4 text-xs leading-relaxed text-muted">Số token lấy từ CLI, không ước tính từ độ dài văn bản. Cache của Codex đã nằm trong token vào; không cộng thêm lần nữa. Hạn mức là của toàn tài khoản, có thể gồm tác vụ khác và có thể reset trong lúc xử lý. TTS và FFmpeg không nằm trong token AI này.</p>
  </details>;
}
