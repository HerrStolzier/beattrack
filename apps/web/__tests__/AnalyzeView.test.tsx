import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AnalyzeView from "../app/components/AnalyzeView";
import { type AnalysisResult } from "@/lib/api";

// Mock all API functions
vi.mock("@/lib/api", () => ({
  uploadAudio: vi.fn(),
  findSimilar: vi.fn(),
  NetworkError: class extends Error { constructor(m = "net") { super(m); this.name = "NetworkError"; } },
  TimeoutError: class extends Error { constructor(m = "timeout") { super(m); this.name = "TimeoutError"; } },
  ApiError: class extends Error {
    detail: string;
    constructor(d = "api error", s = 500) { super(d); this.name = "ApiError"; this.detail = d; }
  },
}));

// Mock sub-components to isolate AnalyzeView logic
vi.mock("../app/components/UploadZone", () => ({
  default: ({ onFileSelected }: { onFileSelected: (f: File) => void }) => (
    <div data-testid="upload-zone">
      <button onClick={() => onFileSelected(new File(["x"], "test.mp3", { type: "audio/mpeg" }))}>
        Upload
      </button>
    </div>
  ),
}));

vi.mock("../app/components/ProgressTracker", () => ({
  default: ({ onComplete, onError }: { jobId: string; onComplete: (r: AnalysisResult) => void; onError: (e: string) => void }) => (
    <div data-testid="progress-tracker">
      <button onClick={() => onComplete({
        song_id: "abc",
        bpm: 128,
        key: "Am",
        duration: 240,
        similar_songs: [
          { id: "s1", title: "Similar", artist: "Art", album: null, bpm: 130, musical_key: "Cm", duration_sec: 200, genre: "Electronic", similarity: 0.8 },
        ],
      })}>
        Complete
      </button>
      <button onClick={() => onError("Extraction failed")}>Fail</button>
    </div>
  ),
}));

vi.mock("../app/components/UrlInput", () => ({
  default: ({ onMatch }: { onMatch: (r: unknown) => void }) => (
    <div data-testid="url-input">
      <button onClick={() => onMatch({ matched: false, song: null, parsed_artist: "DJ Test", parsed_title: "Beat", message: "Nicht im Katalog" })}>
        NoMatch
      </button>
    </div>
  ),
}));

vi.mock("../app/components/SimilarResults", () => ({
  default: ({ results }: { results: unknown[] }) => (
    <div data-testid="similar-results">{results.length} results</div>
  ),
}));

import { uploadAudio } from "@/lib/api";
const mockUpload = vi.mocked(uploadAudio);

describe("AnalyzeView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders idle state with upload zone and URL input", () => {
    render(<AnalyzeView />);
    expect(screen.getByTestId("upload-zone")).toBeInTheDocument();
    expect(screen.getByTestId("url-input")).toBeInTheDocument();
    expect(screen.getAllByText("oder").length).toBeGreaterThan(0);
  });

  it("transitions to uploading state on file select", async () => {
    mockUpload.mockReturnValue(new Promise(() => {})); // never resolves
    render(<AnalyzeView />);

    await userEvent.click(screen.getByText("Upload"));

    await waitFor(() => {
      expect(screen.getByText(/test\.mp3/)).toBeInTheDocument();
      expect(screen.getByText(/hoch\.\.\./)).toBeInTheDocument();
    });
  });

  it("transitions to processing after upload succeeds", async () => {
    mockUpload.mockResolvedValue({ job_id: "job-1", status: "queued" });
    render(<AnalyzeView />);

    await userEvent.click(screen.getByText("Upload"));

    await waitFor(() => {
      expect(screen.getByTestId("progress-tracker")).toBeInTheDocument();
    });
  });

  it("shows results after processing completes", async () => {
    mockUpload.mockResolvedValue({ job_id: "job-1", status: "queued" });
    render(<AnalyzeView />);

    await userEvent.click(screen.getByText("Upload"));

    await waitFor(() => {
      expect(screen.getByTestId("progress-tracker")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Complete"));

    await waitFor(() => {
      expect(screen.getByTestId("similar-results")).toBeInTheDocument();
      expect(screen.getByText("1 results")).toBeInTheDocument();
      expect(screen.getByText(/128/)).toBeInTheDocument();
      expect(screen.getByText("Am")).toBeInTheDocument();
    });
  });

  it("shows error state on processing failure", async () => {
    mockUpload.mockResolvedValue({ job_id: "job-1", status: "queued" });
    render(<AnalyzeView />);

    await userEvent.click(screen.getByText("Upload"));

    await waitFor(() => {
      expect(screen.getByTestId("progress-tracker")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Fail"));

    await waitFor(() => {
      expect(screen.getByText("Extraction failed")).toBeInTheDocument();
      expect(screen.getByText("Nochmal versuchen")).toBeInTheDocument();
    });
  });

  it("resets to idle on retry button click", async () => {
    mockUpload.mockResolvedValue({ job_id: "job-1", status: "queued" });
    render(<AnalyzeView />);

    await userEvent.click(screen.getByText("Upload"));
    await waitFor(() => screen.getByTestId("progress-tracker"));

    await userEvent.click(screen.getByText("Fail"));
    await waitFor(() => screen.getByText("Nochmal versuchen"));

    await userEvent.click(screen.getByText("Nochmal versuchen"));

    await waitFor(() => {
      expect(screen.getByTestId("upload-zone")).toBeInTheDocument();
    });
  });

  it("shows YouTube no-match state", async () => {
    render(<AnalyzeView />);

    await userEvent.click(screen.getByText("NoMatch"));

    await waitFor(() => {
      expect(screen.getByText(/DJ Test/)).toBeInTheDocument();
      expect(screen.getByText(/Beat/)).toBeInTheDocument();
      expect(screen.getByText(/Nicht im Katalog/)).toBeInTheDocument();
    });
  });

  it("shows error on upload network failure", async () => {
    const { NetworkError } = await import("@/lib/api");
    mockUpload.mockRejectedValue(new NetworkError());
    render(<AnalyzeView />);

    await userEvent.click(screen.getByText("Upload"));

    await waitFor(() => {
      expect(screen.getByText("Keine Verbindung zum Server. Prüfe deine Internetverbindung.")).toBeInTheDocument();
    });
  });

  it("reset from results goes back to idle", async () => {
    mockUpload.mockResolvedValue({ job_id: "job-1", status: "queued" });
    render(<AnalyzeView />);

    await userEvent.click(screen.getByText("Upload"));
    await waitFor(() => screen.getByTestId("progress-tracker"));

    await userEvent.click(screen.getByText("Complete"));
    await waitFor(() => screen.getByText("Neue Suche"));

    await userEvent.click(screen.getByText("Neue Suche"));

    await waitFor(() => {
      expect(screen.getByTestId("upload-zone")).toBeInTheDocument();
    });
  });
});
