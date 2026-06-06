export function parseApiDate(value) {
  if (!value) return null;
  const stringValue = String(value);
  const normalized = /(?:Z|[+-]\d{2}:\d{2})$/.test(stringValue) ? stringValue : `${stringValue}Z`;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatApiDate(value, locale = 'vi-VN') {
  const date = parseApiDate(value);
  return date ? date.toLocaleDateString(locale) : '';
}

export function formatApiDateTime(value, locale = 'vi-VN') {
  const date = parseApiDate(value);
  return date ? date.toLocaleString(locale) : '';
}
