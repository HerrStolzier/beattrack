import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import UrlInput from "../app/components/UrlInput";

// Mock API
vi.mock("@/lib/api", () => ({
  identifyUrl: vi.fn(),
  detectPlatform: vi.fn((url: string) => {
    if (/youtube|youtu\.be/.test(url)) return "youtube";
    if (/soundcloud/.test(url)) return "soundcloud";
    if (/spotify/.test(url)) return "spotify";
    return null;
  }),
}));

import { identifyUrl } from "@/lib/api";
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
});
