import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import RadarChart from "../app/components/RadarChart";

vi.mock("@/lib/api", () => ({
  getSongFeatures: vi.fn(),
}));

import { getSongFeatures } from "@/lib/api";
const mockGetFeatures = vi.mocked(getSongFeatures);

const fakeFeatures = {
  timbre: 0.6,
  harmony: 0.4,
  rhythm: 0.8,
  brightness: 0.3,
  intensity: 0.7,
};

describe("RadarChart", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    mockGetFeatures.mockReturnValue(new Promise(() => {})); // never resolves
    render(<RadarChart querySongId="q1" resultSongId="r1" />);
    expect(screen.getByText("Lade Features...")).toBeInTheDocument();
  });

  it("renders SVG with polygons when features load", async () => {
    mockGetFeatures.mockResolvedValue(fakeFeatures);

    const { container } = render(<RadarChart querySongId="q1" resultSongId="r1" />);

    await waitFor(() => {
      expect(screen.queryByText("Lade Features...")).not.toBeInTheDocument();
    });

    const svg = container.querySelector("svg");
    expect(svg).toBeInTheDocument();

    // Should have legend items
    expect(screen.getByText("Query")).toBeInTheDocument();
    expect(screen.getByText("Result")).toBeInTheDocument();
  });

  it("shows error when both fetches fail", async () => {
    mockGetFeatures.mockRejectedValue(new Error("fail"));

    render(<RadarChart querySongId="q1" resultSongId="r1" />);

    await waitFor(() => {
      expect(screen.getByText("Keine Feature-Daten verfügbar.")).toBeInTheDocument();
    });
  });

  it("renders category labels", async () => {
    mockGetFeatures.mockResolvedValue(fakeFeatures);

    render(<RadarChart querySongId="q1" resultSongId="r1" />);

    await waitFor(() => {
      expect(screen.getByText("Klangfarbe")).toBeInTheDocument();
      expect(screen.getByText("Harmonie")).toBeInTheDocument();
      expect(screen.getByText("Rhythmus")).toBeInTheDocument();
      expect(screen.getByText("Helligkeit")).toBeInTheDocument();
      expect(screen.getByText("Intensität")).toBeInTheDocument();
    });
  });
});
