import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import GenreFilter from "../app/components/GenreFilter";

const genres = ["Techno", "House", "Ambient"];

describe("GenreFilter", () => {
  it("renders 'Alle' chip and all genre names", () => {
    render(<GenreFilter genres={genres} selected={null} onSelect={vi.fn()} />);
    expect(screen.getByText("Alle")).toBeInTheDocument();
    expect(screen.getByText("Techno")).toBeInTheDocument();
    expect(screen.getByText("House")).toBeInTheDocument();
    expect(screen.getByText("Ambient")).toBeInTheDocument();
  });

  it("calls onSelect(null) when 'Alle' is clicked", async () => {
    const onSelect = vi.fn();
    render(<GenreFilter genres={genres} selected="Techno" onSelect={onSelect} />);
    await userEvent.click(screen.getByText("Alle"));
    expect(onSelect).toHaveBeenCalledWith(null);
  });

  it("calls onSelect with genre name when genre chip is clicked", async () => {
    const onSelect = vi.fn();
    render(<GenreFilter genres={genres} selected={null} onSelect={onSelect} />);
    await userEvent.click(screen.getByText("House"));
    expect(onSelect).toHaveBeenCalledWith("House");
  });

  it("calls onSelect(null) when active genre is clicked again (toggle)", async () => {
    const onSelect = vi.fn();
    render(<GenreFilter genres={genres} selected="Techno" onSelect={onSelect} />);
    await userEvent.click(screen.getByText("Techno"));
    expect(onSelect).toHaveBeenCalledWith(null);
  });
});
