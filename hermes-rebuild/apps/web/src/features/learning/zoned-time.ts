// Convert between an IANA-zoned wall-clock value (what <input type="datetime-local">
// shows) and an absolute instant. The session freezes its own timezone, so the
// correction UI must speak in that timezone rather than the browser's.

function zonedParts(date: Date, timezone: string) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: timezone,
    hour12: false,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).formatToParts(date);
  const values: Record<string, string> = {};
  for (const part of parts) values[part.type] = part.value;
  return values;
}

function offsetMinutes(date: Date, timezone: string) {
  const parts = zonedParts(date, timezone);
  const asUtc = Date.UTC(
    Number(parts.year),
    Number(parts.month) - 1,
    Number(parts.day),
    Number(parts.hour) % 24,
    Number(parts.minute),
    Number(parts.second),
  );
  return (asUtc - date.getTime()) / 60000;
}

/** Absolute instant -> "YYYY-MM-DDTHH:mm" in the given timezone. */
export function instantToZonedInput(instant: string, timezone: string): string {
  const parts = zonedParts(new Date(instant), timezone);
  const hour = parts.hour === '24' ? '00' : parts.hour;
  return `${parts.year}-${parts.month}-${parts.day}T${hour}:${parts.minute}`;
}

/** "YYYY-MM-DDTHH:mm" in the given timezone -> absolute ISO instant. */
export function zonedInputToInstant(value: string, timezone: string): string | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(value);
  if (!match) return null;
  const [, year, month, day, hour, minute] = match;
  const guess = Date.UTC(Number(year), Number(month) - 1, Number(day), Number(hour), Number(minute));
  const first = new Date(guess - offsetMinutes(new Date(guess), timezone) * 60000);
  // One correction pass handles a DST boundary that falls inside the span.
  return new Date(guess - offsetMinutes(first, timezone) * 60000).toISOString();
}
