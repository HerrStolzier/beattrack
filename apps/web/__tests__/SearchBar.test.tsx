import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SearchBar from "../app/components/SearchBar";

vi.mock("@/lib/api", () => ({
  searchSongs: vi.fn(),
}));

import { searchSongs } from "@/lib/api";
const mockSearch = vi.mocked(searchSongs);

describe("SearchBar", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.clearAllMocks();
    mockSearch.mockResolvedValue([]);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders search input with placeholder", () => {
    render(<SearchBar onResults={vi.fn()} />);
    expect(screen.getByPlaceholderText("Songs durchsuchen...")).toBeInTheDocument();
  });

  it("focuses input on mount", () => {
    render(<SearchBar onResults={vi.fn()} />);
    const input = screen.getByPlaceholderText("Songs durchsuchen...");
    expect(input).toHaveFocus();
  });

  it("calls searchSongs after 300ms debounce on initial render", async () => {
    const onResults = vi.fn();
    render(<SearchBar onResults={onResults} />);

    await vi.advanceTimersByTimeAsync(300);

    await waitFor(() => {
      expect(mockSearch).toHaveBeenCalledWith("", expect.objectContaining({
        signal: expect.any(AbortSignal),
      }));
      expect(onResults).toHaveBeenCalledWith([]);
    });
  });

  it("passes genre filter to searchSongs", async () => {
    render(<SearchBar onResults={vi.fn()} genre="Techno" />);

    await vi.advanceTimersByTimeAsync(300);

    await waitFor(() => {
      expect(mockSearch).toHaveBeenCalledWith("", expect.objectContaining({
        genre: "Techno",
      }));
    });
  });

  it("shows result count when provided", () => {
    render(<SearchBar onResults={vi.fn()} resultCount={23} />);
    expect(screen.getByText("23")).toBeInTheDocument();
  });

  it("debounces search on typing", async () => {
    const onResults = vi.fn();
    const fakeSongs = [{ id: "1", title: "Test", artist: "A", album: null, bpm: 120, musical_key: null, duration_sec: 200, genre: null }];
    mockSearch.mockResolvedValue(fakeSongs);

    render(<SearchBar onResults={onResults} />);

    const input = screen.getByPlaceholderText("Songs durchsuchen...");
    await userEvent.type(input, "techno", { delay: 50 });

    expect(mockSearch).not.toHaveBeenCalledWith("techno", expect.anything());

    await vi.advanceTimersByTimeAsync(300);

    await waitFor(() => {
      expect(mockSearch).toHaveBeenCalledWith("techno", expect.objectContaining({
        signal: expect.any(AbortSignal),
      }));
      expect(onResults).toHaveBeenCalledWith(fakeSongs);
    });
  });

  it("shows error message when search fails", async () => {
    mockSearch.mockRejectedValue(new Error("API down"));

    render(<SearchBar onResults={vi.fn()} />);
    await vi.advanceTimersByTimeAsync(300);

    await waitFor(() => {
      expect(screen.getByText("Suche fehlgeschlagen. Erneut versuchen.")).toBeInTheDocument();
    });
  });
});
