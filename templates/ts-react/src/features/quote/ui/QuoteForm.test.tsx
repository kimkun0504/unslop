import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { QuoteForm } from "./QuoteForm";

describe("QuoteForm", () => {
  it("shows the quote for comma-separated amounts", async () => {
    render(<QuoteForm />);
    await userEvent.type(screen.getByLabelText("Line amounts, separated by commas"), "60, 40,");
    expect(screen.getByRole("status")).toHaveTextContent("Subtotal 100.00, silver tier, total 95.00");
  });

  it("shows the parse error for a malformed amount", async () => {
    render(<QuoteForm />);
    await userEvent.type(screen.getByLabelText("Line amounts, separated by commas"), "1.5");
    expect(screen.getByRole("status")).toHaveTextContent('expected a non-negative amount like 12 or 12.50, got "1.5"');
    expect(screen.getByRole("status")).toHaveClass("text-danger");
  });

  it("ignores blank entries between commas", async () => {
    render(<QuoteForm />);
    await userEvent.type(screen.getByLabelText("Line amounts, separated by commas"), " , 5,  ");
    expect(screen.getByRole("status")).toHaveTextContent("Subtotal 5.00, standard tier, total 5.00");
    expect(screen.getByRole("status")).toHaveClass("text-ink");
  });
});
