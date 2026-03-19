import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import SimilarResults from "../app/components/SimilarResults";
import { type Song, type SimilarSong } from "@/lib/api";

// Mock sub-components that need API calls
vi.mock("../app/components/RadarChart", () => ({
  default: () => <div data-testid="radar-chart">Radar</div>,
}));

vi.mock("../app/components/DeezerEmbed", () => ({
  default: () => <div data-testid="deezer-embed">Deezer</div>,
}));

vi.mock("../app/components/FeedbackButtons", () => ({
  default: ({ onFeedback }: { onFeedback: (r: 1 | -1) => void }) => (
    <div data-testid="feedback-buttons">
      <button onClick={() => onFeedback(1)}>up</button>
      <button onClick={() => onFeedback(-1)}>down</button>
    </div>
  ),
}));

vi.mock("../app/components/HarmonicBadge", () => ({
  default: () => <div data-testid="harmonic-badge">Harmonic</div>,
}));

vi.mock("../app/components/FocusSelector", () => ({
  default: () => <div data-testid="focus-selector">Focus</div>,
}));

const querySong: Song = {
  id: "q1",
  title: "Query Track",
  artist: "DJ Test",
  album: null,
  bpm: 130,
  musical_key: "Cm",
  duration_sec: 300,
  genre: "Techno",
};

const results: SimilarSong[] = [
  {
    id: "r1",
    title: "Match One",
    artist: "Artist A",
    album: null,
    bpm: 128,
    musical_key: "Am",
    duration_sec: 240,
    genre: "House",
    similarity: 0.85,
  },
  {
    id: "r2",
    title: "Match Two",
    artist: "Artist B",
    album: null,
    bpm: null,
    musical_key: null,
    duration_sec: null,
    genre: null,
    similarity: 0.25,
  },
];

describe("SimilarResults", () => {
  it("renders empty state when no results", () => {
    render(<SimilarResults results={[]} querySong={querySong} />);
    expect(screen.getByText("Keine passenden Treffer")).toBeInTheDocument();
  });

  it("shows query song title in header", () => {
    render(<SimilarResults results={results} querySong={querySong} />);
    expect(screen.getByText("Query Track")).toBeInTheDocument();
  });

  it("renders result titles and artists", () => {
    render(<SimilarResults results={results} querySong={querySong} />);
    expect(screen.getByText("Match One")).toBeInTheDocument();
    expect(screen.getByText("Artist A")).toBeInTheDocument();
    expect(screen.getByText("Match Two")).toBeInTheDocument();
    expect(screen.getByText("Artist B")).toBeInTheDocument();
  });

  it("shows similarity label", () => {
    render(<SimilarResults results={results} querySong={querySong} />);
    expect(screen.getByText("Sehr ähnlich")).toBeInTheDocument();
    expect(screen.getByText("Entfernt")).toBeInTheDocument();
  });

  it("shows rank numbers", () => {
    render(<SimilarResults results={results} querySong={querySong} />);
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("shows genre badge when present", () => {
    render(<SimilarResults results={results} querySong={querySong} />);
    expect(screen.getByText("House")).toBeInTheDocument();
  });

  it("shows BPM when present", () => {
    render(<SimilarResults results={results} querySong={querySong} />);
    expect(screen.getByText("128")).toBeInTheDocument();
  });

  it("renders Spotify and YouTube buttons", () => {
    render(<SimilarResults results={results} querySong={querySong} />);
    const spotifyButtons = screen.getAllByTitle("Auf Spotify suchen");
    const youtubeButtons = screen.getAllByTitle("Auf YouTube suchen");
    expect(spotifyButtons).toHaveLength(2);
    expect(youtubeButtons).toHaveLength(2);
  });

  it("shows result count in header", () => {
    render(<SimilarResults results={results} querySong={querySong} />);
    expect(screen.getByText("2 Treffer")).toBeInTheDocument();
  });
});
