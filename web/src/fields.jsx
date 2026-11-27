import React from "react";

export const commentSort = [["likes", "Nhiều tim"], ["replies", "Nhiều phản hồi"], ["reposts", "Nhiều đăng lại"], ["quotes", "Nhiều trích dẫn"]];
const fit = [["cover", "Cover · Kín khung"], ["contain", "Contain · Giữ toàn hình"]];
export const groups = {
  queue: [
    ["comment_mode", "Chế độ bình luận", "select", { options: [["top_likes_with_author", "Gồm cả tác giả"], ["top_likes_no_author", "Không lấy tác giả"], ["author_only", "Chỉ tác giả · Kể chuyện"]] }],
    ["comment_sort", "Xếp hạng trước khi chọn", "select", { options: commentSort }],
    ["max_comments", "Số bình luận", "number", { min: 1, max: 25 }],
    ["voice_speed", "Tốc độ đọc", "number", { min: .75, max: 1.8, step: .05 }],
  ],
  voice: [
    ["voice_assign_mode", "Cách phân giọng", "select", { options: [["random", "Ngẫu nhiên"], ["round_robin", "Xoay vòng"], ["single", "Một giọng"]] }],
    ["voice_speed", "Tốc độ đọc", "number", { min: .75, max: 1.8, step: .05 }],
  ],
  tts: [
    ["capcut_device_json", "Đường dẫn device JSON CapCut", "text", { wide: true }],
    ["vieneu_endpoint", "Endpoint VieNeu (để trống dùng SDK)", "text", { wide: true }],
    ["vieneu_clone_ref_audio", "Đường dẫn audio mẫu clone", "text", { wide: true }],
    ["vieneu_clone_ref_text", "Lời đọc tương ứng audio mẫu", "textarea", { wide: true }],
  ],
  video: [
    ["media.bg_video_path", "File video nền riêng", "text", { wide: true }],
    ["media.bg_video_dir", "Thư mục video nền", "text", { wide: true }],
    ["media.sub_video_dir", "Thư mục video phụ / B-roll", "text", { wide: true }],
  ],
  video_options: [
    ["media.bg_random_start", "Random Start · Chọn đoạn nền ngẫu nhiên", "checkbox"],
    ["media.bg_fit", "Cách đặt nền", "select", { options: fit }],
  ],
  audio_paths: [
    ["media.bgm_dir", "Thư mục nhạc nền", "text", { wide: true }],
    ["media.sfx_dir", "Thư mục SFX chuyển cảnh", "text", { wide: true }],
  ],
  audio: [
    ["media.bgm_enabled", "Bật nhạc nền", "checkbox"],
    ["media.bgm_volume_pct", "Âm lượng nhạc nền (%)", "number", { min: 0, max: 100 }],
    ["media.sfx_enabled", "Bật SFX", "checkbox"],
    ["media.sfx_volume_pct", "Âm lượng SFX (%)", "number", { min: 0, max: 100 }],
  ],
  ai: [
    ["ai_provider", "AI xử lý nội dung", "select", { options: [["codex", "Codex · Tài khoản ChatGPT"], ["antigravity", "Antigravity · Tài khoản Google"], ["offline", "Từ điển Offline · Không OCR"]] }],
  ],
  workers: [
    ["max_scrape_workers", "Worker thu thập", "number", { min: 1, max: 12 }],
    ["max_ai_workers", "Worker AI", "number", { min: 1, max: 12 }],
    ["max_tts_workers", "Worker TTS", "number", { min: 1, max: 12 }],
    ["max_render_workers", "Worker render", "number", { min: 1, max: 12 }],
    ["prefer_nvenc", "Ưu tiên GPU NVIDIA NVENC", "checkbox"],
  ],
  output: [
    ["output_root", "Thư mục kết quả (trống: output/)", "text", { wide: true }],
  ],
  meme: [
    ["media.meme_sound_dir", "Thư mục kho meme sound", "text", { wide: true }],
    ["media.meme_sound_enabled", "AI chọn sound sau nội dung đã duyệt", "checkbox", { wide: true }],
    ["media.meme_sound_volume_pct", "Âm lượng sound (%)", "number", { min: 0, max: 100 }],
    ["media.meme_sound_max_per_video", "Số sound tối đa / video", "number", { min: 0, max: 20 }],
    ["media.meme_sound_max_duration_sec", "Thời lượng tối đa / sound (giây)", "number", { min: .1, max: 30, step: .1 }],
  ],
  layout: [
    ["aspect_ratio", "Tỷ lệ video", "select", { options: [["9:16", "9:16 · Dọc"], ["16:9", "16:9 · Ngang"]] }],
    ["card_theme", "Theme thẻ", "select", { options: [["light", "Sáng"], ["dark", "Tối"]] }],
    ["hide_username", "Che tên tài khoản", "checkbox", { wide: true }],
    ["card_x_pct", "Thẻ · X (%)", "number", { min: 5, max: 95, step: .1 }],
    ["card_y_pct", "Thẻ · Y (%)", "number", { min: 5, max: 95, step: .1 }],
    ["card_scale_pct", "Thẻ · Kích thước (%)", "number", { min: 55, max: 122, step: .1 }],
    ["card_radius_px", "Thẻ · Bo góc (px)", "number", { min: 0, max: 64 }],
    ["sub_enabled", "Hiện video phụ", "checkbox", { wide: true }],
    ["sub_x_pct", "Video phụ · X (%)", "number", { min: 5, max: 95, step: .1 }],
    ["sub_y_pct", "Video phụ · Y (%)", "number", { min: 5, max: 95, step: .1 }],
    ["sub_w_pct", "Video phụ · Rộng (%)", "number", { min: 25, max: 100, step: .1 }],
    ["sub_h_pct", "Video phụ · Cao (%)", "number", { min: 12, max: 65, step: .1 }],
    ["sub_radius_px", "Video phụ · Bo góc (px)", "number", { min: 0, max: 64 }],
    ["sub_fit", "Video phụ · Fit", "select", { options: fit }],
  ],
};

export function getPath(object, path) {
  return path.split(".").reduce((value, key) => value?.[key], object);
}

export function setPath(object, path, value) {
  const next = structuredClone(object);
  const keys = path.split(".");
  const parent = keys.slice(0, -1).reduce((item, key) => item[key], next);
  parent[keys.at(-1)] = value;
  return next;
}

export function FieldGrid({ group, value, onChange, disabled = false }) {
  return <div className="my-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
    {groups[group].map(([path, label, type, extra = {}]) => {
      const current = getPath(value, path);
      const { options, wide, ...inputProps } = extra;
      const change = (event) => onChange(path, type === "checkbox" ? event.target.checked : type === "number" ? event.target.value === "" ? "" : Number(event.target.value) : event.target.value);
      return <label key={path} className={`flex min-w-0 flex-col gap-1.5 text-sm ${wide ? "sm:col-span-2" : ""}`}>
        {type === "checkbox" ? <span className="flex min-h-9 items-center gap-2"><input type="checkbox" checked={Boolean(current)} disabled={disabled} onChange={change} />{label}</span>
          : <><span>{label}</span>{type === "select" ? <select value={current ?? ""} disabled={disabled} onChange={change}>{options.map(([key, text]) => <option key={key} value={key}>{text}</option>)}</select>
            : type === "textarea" ? <textarea rows={3} value={current ?? ""} disabled={disabled} onChange={change} />
              : <input type={type} value={current ?? ""} disabled={disabled} onChange={change} {...inputProps} />}</>}
      </label>;
    })}
  </div>;
}
