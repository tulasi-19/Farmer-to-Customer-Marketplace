/**
 * Safely turns an Axios error into a readable string, no matter what shape
 * the backend actually sent back — a DRF validation object, a plain string,
 * an HTML error page (e.g. a Django 500 debug page), or nothing at all.
 *
 * This exists because naively doing Object.entries(err.response.data) blows
 * up in an ugly way when data is an HTML string instead of a JSON object
 * (it iterates character-by-character), which is exactly the kind of
 * response you get from an unhandled server error.
 */
export function formatApiError(err, fallback = 'Something went wrong. Please try again.') {
  const data = err?.response?.data;

  if (!data) return fallback;

  // A JSON object of field errors, e.g. { price: ["This field is required."] }
  if (typeof data === 'object' && !Array.isArray(data)) {
    try {
      const parts = Object.entries(data).map(([field, messages]) => {
        const text = Array.isArray(messages) ? messages.join(' ') : String(messages);
        return field === 'detail' || field === 'non_field_errors' ? text : `${field}: ${text}`;
      });
      if (parts.length) return parts.join(' | ');
    } catch {
      // fall through to fallback below
    }
    return fallback;
  }

  // A plain string response that actually looks like a short error message
  if (typeof data === 'string' && data.length < 300 && !data.trim().startsWith('<')) {
    return data;
  }

  // HTML (Django debug page / proxy error page) or anything else unexpected
  return `${fallback} (Server returned an unexpected error — check the Django terminal for details.)`;
}
