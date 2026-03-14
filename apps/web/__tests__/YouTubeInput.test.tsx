import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import YouTubeInput from "../app/components/YouTubeInput";

// Mock the API module
vi.mock("@/lib/api", () => ({
  identifyYouTube: vi.fn(),
}));

import { identifyYouTube } from "@/lib/api";
const mockIdentify = vi.mocked(identifyYouTube);

describe("YouTubeInput", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders input and button", () => {
    render(<YouTubeInput onMatch={vi.fn()} />);
    expect(screen.getByTestId("youtube-input")).toBeInTheDocument();
    expect(screen.getByTestId("youtube-submit")).toBeInTheDocument();
  });

  it("rejects invalid URLs", async () => {
    render(<YouTubeInput onMatch={vi.fn()} />);

    const input = screen.getByTestId("youtube-input");
    const button = screen.getByTestId("youtube-submit");

    fireEvent.change(input, { target: { value: "https://example.com/video" } });
    fireEvent.click(button);

    expect(screen.getByRole("alert")).toHaveTextContent(/gültige YouTube-URL/);
    expect(mockIdentify).not.toHaveBeenCalled();
  });

  it("accepts valid youtube.com/watch URLs", async () => {
    mockIdentify.mockResolvedValue({
      matched: true,
      song: {
        id: "1",
        title: "Test Song",
        artist: "Test Artist",
        album: null,
        bpm: 120,
        musical_key: "C",
        duration_sec: 200,
      },
      parsed_artist: "Test Artist",
      parsed_title: "Test Song",
      message: "Found match",
    });

    const onMatch = vi.fn();
    render(<YouTubeInput onMatch={onMatch} />);

    const input = screen.getByTestId("youtube-input");
    fireEvent.change(input, { target: { value: "https://www.youtube.com/watch?v=dQw4w9WgXcQ" } });
    fireEvent.click(screen.getByTestId("youtube-submit"));

    await waitFor(() => {
      expect(mockIdentify).toHaveBeenCalledWith("https://www.youtube.com/watch?v=dQw4w9WgXcQ");
      expect(onMatch).toHaveBeenCalled();
    });
  });

  it("accepts youtu.be short URLs", async () => {
    mockIdentify.mockResolvedValue({
      matched: false,
      song: null,
      parsed_artist: "Artist",
      parsed_title: "Title",
      message: "No match",
    });

    const onMatch = vi.fn();
    render(<YouTubeInput onMatch={onMatch} />);

    const input = screen.getByTestId("youtube-input");
    fireEvent.change(input, { target: { value: "https://youtu.be/abc123" } });
    fireEvent.click(screen.getByTestId("youtube-submit"));

    await waitFor(() => {
      expect(mockIdentify).toHaveBeenCalled();
    });
  });

  it("shows error on API failure", async () => {
    mockIdentify.mockRejectedValue(new Error("Could not fetch YouTube metadata"));

    render(<YouTubeInput onMatch={vi.fn()} />);

    const input = screen.getByTestId("youtube-input");
    fireEvent.change(input, { target: { value: "https://youtube.com/watch?v=test" } });
    fireEvent.click(screen.getByTestId("youtube-submit"));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/Could not fetch YouTube metadata/);
    });
  });

  it("disables button when input is empty", () => {
    render(<YouTubeInput onMatch={vi.fn()} />);
    expect(screen.getByTestId("youtube-submit")).toBeDisabled();
  });
});
