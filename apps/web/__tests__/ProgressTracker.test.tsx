import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import ProgressTracker from "../app/components/ProgressTracker";

// Mock the API module
vi.mock("@/lib/api", () => ({
  streamProgress: vi.fn(),
  getJobResults: vi.fn(),
}));

import { streamProgress, getJobResults } from "@/lib/api";
const mockStreamProgress = vi.mocked(streamProgress);
const mockGetJobResults = vi.mocked(getJobResults);

describe("ProgressTracker", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders progress tracker", () => {
    mockStreamProgress.mockReturnValue(() => {});

    render(
      <ProgressTracker jobId="test-123" onComplete={vi.fn()} onError={vi.fn()} />
    );

    expect(screen.getByTestId("progress-tracker")).toBeInTheDocument();
    expect(screen.getByText("In der Warteschlange...")).toBeInTheDocument();
  });

  it("calls streamProgress with job ID", () => {
    mockStreamProgress.mockReturnValue(() => {});

    render(
      <ProgressTracker jobId="job-456" onComplete={vi.fn()} onError={vi.fn()} />
    );

    expect(mockStreamProgress).toHaveBeenCalledWith(
      "job-456",
      expect.any(Function),
      expect.any(Function)
    );
  });

  it("shows cold-start message after threshold", async () => {
    mockStreamProgress.mockReturnValue(() => {});

    render(
      <ProgressTracker jobId="test-123" onComplete={vi.fn()} onError={vi.fn()} />
    );

    // Cold start message should not be visible initially
    expect(screen.queryByTestId("cold-start-message")).not.toBeInTheDocument();

    // Advance past the 10s threshold
    await act(async () => {
      vi.advanceTimersByTime(11_000);
    });

    expect(screen.getByTestId("cold-start-message")).toBeInTheDocument();
    expect(screen.getByTestId("cold-start-message")).toHaveTextContent(/Server wacht gerade auf/);
  });

  it("calls onComplete when SSE reports completed", () => {
    const onComplete = vi.fn();
    let sseCallback: Function;

    mockStreamProgress.mockImplementation((_, onUpdate) => {
      sseCallback = onUpdate;
      return () => {};
    });

    render(
      <ProgressTracker jobId="test-123" onComplete={onComplete} onError={vi.fn()} />
    );

    const mockResult = {
      song_id: "abc",
      bpm: 120,
      key: "Am",
      duration: 200,
      similar_songs: [],
    };

    act(() => {
      sseCallback({
        status: "completed",
        progress: 1.0,
        result: mockResult,
      });
    });

    expect(onComplete).toHaveBeenCalledWith(mockResult);
  });

  it("calls onError when SSE reports failure", () => {
    const onError = vi.fn();
    let sseCallback: Function;

    mockStreamProgress.mockImplementation((_, onUpdate) => {
      sseCallback = onUpdate;
      return () => {};
    });

    render(
      <ProgressTracker jobId="test-123" onComplete={vi.fn()} onError={onError} />
    );

    act(() => {
      sseCallback({
        status: "failed",
        progress: 0,
        error: "Feature extraction failed",
      });
    });

    expect(onError).toHaveBeenCalledWith("Feature extraction failed");
  });

  it("updates progress bar on SSE updates", () => {
    let sseCallback: Function;

    mockStreamProgress.mockImplementation((_, onUpdate) => {
      sseCallback = onUpdate;
      return () => {};
    });

    render(
      <ProgressTracker jobId="test-123" onComplete={vi.fn()} onError={vi.fn()} />
    );

    act(() => {
      sseCallback({
        status: "processing",
        progress: 0.5,
      });
    });

    expect(screen.getByText("50%")).toBeInTheDocument();
    expect(screen.getByText("Analyse läuft...")).toBeInTheDocument();
  });

  it("cleans up SSE on unmount", () => {
    const cleanup = vi.fn();
    mockStreamProgress.mockReturnValue(cleanup);

    const { unmount } = render(
      <ProgressTracker jobId="test-123" onComplete={vi.fn()} onError={vi.fn()} />
    );

    unmount();
    expect(cleanup).toHaveBeenCalled();
  });
});
