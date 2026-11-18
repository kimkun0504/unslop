import { useId, useState, type ReactElement } from "react";
import { quote } from "../domain/pricing";

function splitAmounts(raw: string): string[] {
  return raw.split(",").filter((part) => part.trim().length > 0);
}

export function QuoteForm(): ReactElement {
  const inputId = useId();
  const [raw, setRaw] = useState("");
  const result = quote(splitAmounts(raw));

  return (
    <section className="flex flex-col gap-2 p-4">
      <label htmlFor={inputId} className="text-sm font-medium text-ink">
        Line amounts, separated by commas
      </label>
      <input
        id={inputId}
        className="rounded-md border border-line px-3 py-2 text-ink"
        value={raw}
        onChange={(event) => {
          setRaw(event.target.value);
        }}
      />
      <output aria-live="polite" className={result.ok ? "text-ink" : "text-danger"}>
        {result.ok
          ? `Subtotal ${result.value.subtotal.render()}, ${result.value.tier} tier, total ${result.value.total.render()}`
          : result.error}
      </output>
    </section>
  );
}
