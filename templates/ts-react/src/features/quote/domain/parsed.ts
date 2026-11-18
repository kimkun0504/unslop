export type Parsed<T> = { readonly ok: true; readonly value: T } | { readonly ok: false; readonly error: string };

export function accept<T>(value: T): Parsed<T> {
  return { ok: true, value };
}

export function reject<T>(error: string): Parsed<T> {
  return { ok: false, error };
}
