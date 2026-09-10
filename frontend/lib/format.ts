export function formatBytes(value?: number | null): string {
  if (!value || value < 0) return "—";
  const units = ["B", "KB", "MB", "GB"];
  let size = value;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size >= 10 || index === 0 ? size.toFixed(0) : size.toFixed(1)} ${units[index]}`;
}

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function initials(name: string): string {
  const pieces = name.trim().split(/\s+/).filter(Boolean);
  if (!pieces.length) return "U";
  return pieces.slice(0, 2).map((piece) => piece[0]?.toUpperCase()).join("");
}

export function shortTitle(text: string): string {
  const clean = text.trim().replace(/\s+/g, " ");
  return clean.length > 48 ? `${clean.slice(0, 48).trim()}…` : clean || "New chat";
}
