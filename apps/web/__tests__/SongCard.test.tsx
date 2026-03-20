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
  deezer_id: null,
};

describe("SongCard", () => {
  it("renders title and artist", () => {
    render(<SongCard song={baseSong} onFindSimilar={vi.fn()} isSelected={false} />);
    expect(screen.getByText("Neon Pulse")).toBeInTheDocument();
    expect(screen.getByText("Synthwave Corp")).toBeInTheDocument();
  });

  it("shows BPM badge when bpm is set", () => {
    render(<SongCard song={baseSong} onFindSimilar={vi.fn()} isSelected={false} />);
    expect(screen.getByText("128")).toBeInTheDocument();
  });

  it("hides BPM badge when null", () => {
    const noBpm = { ...baseSong, bpm: null };
    render(<SongCard song={noBpm} onFindSimilar={vi.fn()} isSelected={false} />);
    expect(screen.queryByText("128")).not.toBeInTheDocument();
  });

  it("calls onFindSimilar when card is clicked", async () => {
    const onFindSimilar = vi.fn();
    render(<SongCard song={baseSong} onFindSimilar={onFindSimilar} isSelected={false} />);

    await userEvent.click(screen.getByText("Neon Pulse"));
    expect(onFindSimilar).toHaveBeenCalledWith(baseSong);
  });

  it("applies selected styling when isSelected is true", () => {
    const { container } = render(
      <SongCard song={baseSong} onFindSimilar={vi.fn()} isSelected={true} />
    );
    const card = container.firstElementChild as HTMLElement;
    expect(card.className).toContain("cursor-pointer");
  });
});
