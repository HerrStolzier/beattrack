import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import FeedbackButtons from "../app/components/FeedbackButtons";

vi.mock("@/lib/api", () => ({
  submitFeedback: vi.fn(),
}));

import { submitFeedback } from "@/lib/api";

const mockSubmitFeedback = vi.mocked(submitFeedback);

describe("FeedbackButtons", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSubmitFeedback.mockResolvedValue(undefined);
  });

  it("submits positive feedback immediately", async () => {
    render(<FeedbackButtons querySongId="q1" resultSongId="r1" focusActive="timbre" />);

    await userEvent.click(screen.getByRole("button", { name: /passt$/i }));

    await waitFor(() => {
      expect(mockSubmitFeedback).toHaveBeenCalledWith("q1", "r1", 1, "timbre");
    });
  });

  it("asks for a reason before submitting negative feedback", async () => {
    render(<FeedbackButtons querySongId="q1" resultSongId="r1" />);

    await userEvent.click(screen.getByRole("button", { name: /passt nicht/i }));

    expect(mockSubmitFeedback).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: "Falsche Energie" }));

    await waitFor(() => {
      expect(mockSubmitFeedback).toHaveBeenCalledWith(
        "q1",
        "r1",
        -1,
        undefined,
        "wrong_energy"
      );
    });
  });
});
