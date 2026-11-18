import type { ReactElement } from "react";
import { QuoteForm } from "../features/quote/ui/QuoteForm";

export function App(): ReactElement {
  return (
    <main className="mx-auto max-w-prose bg-surface">
      <h1 className="p-4 text-2xl font-semibold text-ink">Quote</h1>
      <QuoteForm />
    </main>
  );
}
