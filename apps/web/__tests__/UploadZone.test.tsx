import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import UploadZone from "../app/components/UploadZone";

function createFile(name: string, size: number, type: string): File {
  const buffer = new ArrayBuffer(Math.min(size, 1024));
  const file = new File([buffer], name, { type });
  Object.defineProperty(file, "size", { value: size });
  return file;
}

describe("UploadZone", () => {
  it("renders the drop zone", () => {
    render(<UploadZone onFileSelected={vi.fn()} />);
    expect(screen.getByTestId("upload-zone")).toBeInTheDocument();
    expect(screen.getByText(/Audio-Datei hierher ziehen/)).toBeInTheDocument();
  });

  it("accepts a valid audio file", () => {
    const onFileSelected = vi.fn();
    render(<UploadZone onFileSelected={onFileSelected} />);

    const input = screen.getByTestId("upload-input") as HTMLInputElement;
    const file = createFile("song.mp3", 5 * 1024 * 1024, "audio/mpeg");
    fireEvent.change(input, { target: { files: [file] } });

    expect(onFileSelected).toHaveBeenCalledWith(file);
  });

  it("rejects files over 50 MB", () => {
    const onFileSelected = vi.fn();
    render(<UploadZone onFileSelected={onFileSelected} />);

    const input = screen.getByTestId("upload-input") as HTMLInputElement;
    const file = createFile("huge.mp3", 51 * 1024 * 1024, "audio/mpeg");
    fireEvent.change(input, { target: { files: [file] } });

    expect(onFileSelected).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/zu groß/);
  });

  it("rejects non-audio files", () => {
    const onFileSelected = vi.fn();
    render(<UploadZone onFileSelected={onFileSelected} />);

    const input = screen.getByTestId("upload-input") as HTMLInputElement;
    const file = createFile("doc.pdf", 1024, "application/pdf");
    fireEvent.change(input, { target: { files: [file] } });

    expect(onFileSelected).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/Ungültiges Format/);
  });

  it("accepts files by extension fallback", () => {
    const onFileSelected = vi.fn();
    render(<UploadZone onFileSelected={onFileSelected} />);

    const input = screen.getByTestId("upload-input") as HTMLInputElement;
    // Some browsers report empty MIME but the extension is valid
    const file = createFile("track.flac", 10 * 1024 * 1024, "");
    fireEvent.change(input, { target: { files: [file] } });

    expect(onFileSelected).toHaveBeenCalledWith(file);
  });

  it("disables interaction when disabled prop is set", () => {
    render(<UploadZone onFileSelected={vi.fn()} disabled />);
    const zone = screen.getByTestId("upload-zone");
    expect(zone.className).toContain("opacity-50");
  });

  it("handles drag and drop", () => {
    const onFileSelected = vi.fn();
    render(<UploadZone onFileSelected={onFileSelected} />);

    const zone = screen.getByTestId("upload-zone");
    const file = createFile("song.wav", 1024, "audio/wav");

    fireEvent.dragOver(zone);
    // dragOver state is handled via Framer Motion animations (boxShadow/scale),
    // not via className changes — no class assertion needed here

    fireEvent.drop(zone, { dataTransfer: { files: [file] } });
    expect(onFileSelected).toHaveBeenCalledWith(file);
  });
});
