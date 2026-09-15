import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import UrlInput from "../app/components/UrlInput";

// Mock API
vi.mock("@/lib/api", () => ({
  identifyUrl: vi.fn(),
  searchSongs: vi.fn(),
  detectPlatform: vi.fn((url: string) => {
    if (/youtube|youtu\.be/.test(url)) return "youtube";
    if (/soundcloud/.test(url)) return "soundcloud";
    if (/spotify/.test(url)) return "spotify";
    return null;
  }),
}));

import { identifyUrl, searchSongs } from "@/lib/api";
const mockIdentifyUrl = vi.mocked(identifyUrl);

describe("UrlInput", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders input and button", () => {
    render(<UrlInput onMatch={vi.fn()} />);
    expect(screen.getByTestId("url-input")).toBeInTheDocument();
    expect(screen.getByTestId("url-submit")).toBeInTheDocument();
  });

  it("shows YouTube badge for YouTube URLs", () => {
    render(<UrlInput onMatch={vi.fn()} />);
    fireEvent.change(screen.getByTestId("url-input"), {
      target: { value: "https://youtube.com/watch?v=abc123" },
    });
    expect(screen.getByTestId("platform-badge")).toHaveTextContent("YouTube");
  });

  it("shows SoundCloud badge for SoundCloud URLs", () => {
    render(<UrlInput onMatch={vi.fn()} />);
    fireEvent.change(screen.getByTestId("url-input"), {
      target: { value: "https://soundcloud.com/artist/track" },
    });
    expect(screen.getByTestId("platform-badge")).toHaveTextContent("SoundCloud");
  });

  it("shows Spotify badge for Spotify URLs", () => {
    render(<UrlInput onMatch={vi.fn()} />);
    fireEvent.change(screen.getByTestId("url-input"), {
      target: { value: "https://open.spotify.com/track/abc123" },
    });
    expect(screen.getByTestId("platform-badge")).toHaveTextContent("Spotify");
  });

  it("rejects invalid URLs", async () => {
    render(<UrlInput onMatch={vi.fn()} />);
    fireEvent.change(screen.getByTestId("url-input"), {
      target: { value: "https://example.com" },
    });
    fireEvent.click(screen.getByTestId("url-submit"));
    expect(await screen.findByTestId("url-error")).toBeInTheDocument();
  });

  it("calls onMatch on success", async () => {
    const onMatch = vi.fn();
    const mockResult = { matched: true, song: { id: "1" }, parsed_artist: "A", parsed_title: "B", message: "ok" };
    mockIdentifyUrl.mockResolvedValue(mockResult as any);

    render(<UrlInput onMatch={onMatch} />);
    fireEvent.change(screen.getByTestId("url-input"), {
      target: { value: "https://youtube.com/watch?v=abc123" },
    });
    fireEvent.click(screen.getByTestId("url-submit"));

    await waitFor(() => expect(onMatch).toHaveBeenCalledWith(mockResult));
  });

  it("searches titles and lets the user choose the recording", async () => {
    const song = { id: "remix", title: "Example (Remix)", artist: "Artist", album: "Album" };
    vi.mocked(searchSongs).mockResolvedValue([song as any]);
    const onMatch = vi.fn();
    render(<UrlInput onMatch={onMatch} />);
    const input = screen.getByRole("textbox", { name: "Titel, Künstler oder Song-Link" });
    fireEvent.change(input, { target: { value: "Example" } });
    fireEvent.submit(input.closest("form")!);
    fireEvent.click(await screen.findByRole("button", { name: /Example \(Remix\)/ }));
    expect(searchSongs).toHaveBeenCalledWith("Example", { limit: 10 });
    expect(identifyUrl).not.toHaveBeenCalled();
    expect(onMatch).toHaveBeenCalledWith(expect.objectContaining({ matched: true, song }));
    fireEvent.change(input, { target: { value: "Changed" } });
    expect(screen.queryByRole("list", { name: "Gefundene Songs" })).not.toBeInTheDocument();
  });

  it("explains a catalogue miss without starting ingestion", async () => {
    vi.mocked(searchSongs).mockResolvedValue([]);
    render(<UrlInput onMatch={vi.fn()} />);
    fireEvent.change(screen.getByTestId("url-input"), { target: { value: "Missing song" } });
    fireEvent.click(screen.getByTestId("url-submit"));
    expect(await screen.findByRole("status")).toHaveTextContent("Kein Katalogtreffer");
    expect(identifyUrl).not.toHaveBeenCalled();
  });
});
