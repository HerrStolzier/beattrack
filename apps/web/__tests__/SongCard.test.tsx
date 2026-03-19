import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SongCard from "../app/components/SongCard";
import { type Song } from "@/lib/api";

const baseSong: Song = {
  id: "s1",
  title: "Neon Pulse",
  artist: "Synthwave Corp",
  album: "Retro Futures",
  bpm: 128,
  musical_key: "Am",
  duration_sec: 245,
  genre: "Techno",
};

describe("SongCard", () => {
  it("renders title, artist, and album", () => {
    render(<SongCard song={baseSong} onFindSimilar={vi.fn()} isSelected={false} />);
    expect(screen.getByText("Neon Pulse")).toBeInTheDocument();
    expect(screen.getByText("Synthwave Corp")).toBeInTheDocument();
    expect(screen.getByText("Retro Futures")).toBeInTheDocument();
  });

  it("shows BPM and key badges", () => {
    render(<SongCard song={baseSong} onFindSimilar={vi.fn()} isSelected={false} />);
    expect(screen.getByText("128 BPM")).toBeInTheDocument();
    expect(screen.getByText("Am")).toBeInTheDocument();
  });

  it("shows genre badge", () => {
    render(<SongCard song={baseSong} onFindSimilar={vi.fn()} isSelected={false} />);
    expect(screen.getByText("Techno")).toBeInTheDocument();
  });

  it("hides genre badge when null", () => {
    const noGenre = { ...baseSong, genre: null };
    render(<SongCard song={noGenre} onFindSimilar={vi.fn()} isSelected={false} />);
    expect(screen.queryByText("Techno")).not.toBeInTheDocument();
  });

  it("formats duration as m:ss", () => {
    render(<SongCard song={baseSong} onFindSimilar={vi.fn()} isSelected={false} />);
    expect(screen.getByText("4:05")).toBeInTheDocument();
  });

  it("hides album when null", () => {
    const noAlbum = { ...baseSong, album: null };
    render(<SongCard song={noAlbum} onFindSimilar={vi.fn()} isSelected={false} />);
    expect(screen.queryByText("Retro Futures")).not.toBeInTheDocument();
  });

  it("hides BPM badge when null", () => {
    const noBpm = { ...baseSong, bpm: null };
    render(<SongCard song={noBpm} onFindSimilar={vi.fn()} isSelected={false} />);
    expect(screen.queryByText(/BPM/)).not.toBeInTheDocument();
  });

  it("calls onFindSimilar when button is clicked", async () => {
    const onFindSimilar = vi.fn();
    render(<SongCard song={baseSong} onFindSimilar={onFindSimilar} isSelected={false} />);

    await userEvent.click(screen.getByText("Ähnliche finden"));
    expect(onFindSimilar).toHaveBeenCalledWith(baseSong);
  });

  it("applies selected styling when isSelected is true", () => {
    const { container } = render(
      <SongCard song={baseSong} onFindSimilar={vi.fn()} isSelected={true} />
    );
    const card = container.firstElementChild as HTMLElement;
    expect(card.className).toContain("amber");
  });

  it("shows dash for null duration", () => {
    const noDuration = { ...baseSong, duration_sec: null };
    render(<SongCard song={noDuration} onFindSimilar={vi.fn()} isSelected={false} />);
    expect(screen.queryByText("—")).not.toBeInTheDocument();
  });
});
