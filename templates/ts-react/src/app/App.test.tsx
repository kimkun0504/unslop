import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("App", () => {
  it("renders the quote page", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "Quote" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Subtotal 0.00, standard tier, total 0.00");
  });
});
