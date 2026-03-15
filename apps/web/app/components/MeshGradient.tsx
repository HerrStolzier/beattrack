"use client";

export default function MeshGradient() {
  return (
    <div className="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden="true" style={{ zIndex: -1 }}>
      {/* Amber blob - top left */}
      <div
        className="absolute -top-[20%] -left-[10%] h-[60vh] w-[60vh] rounded-full opacity-20"
        style={{
          background: "radial-gradient(circle, rgba(245, 158, 11, 0.4) 0%, transparent 70%)",
          animation: "mesh-drift 25s ease-in-out infinite",
          filter: "blur(80px)",
        }}
      />
      {/* Violet blob - center right */}
      <div
        className="absolute top-[20%] -right-[10%] h-[50vh] w-[50vh] rounded-full opacity-15"
        style={{
          background: "radial-gradient(circle, rgba(167, 139, 250, 0.4) 0%, transparent 70%)",
          animation: "mesh-drift 30s ease-in-out infinite reverse",
          filter: "blur(100px)",
        }}
      />
      {/* Cyan blob - bottom */}
      <div
        className="absolute -bottom-[10%] left-[30%] h-[40vh] w-[40vh] rounded-full opacity-10"
        style={{
          background: "radial-gradient(circle, rgba(34, 211, 238, 0.4) 0%, transparent 70%)",
          animation: "mesh-drift 35s ease-in-out infinite",
          animationDelay: "-10s",
          filter: "blur(90px)",
        }}
      />
      {/* Rose accent - subtle */}
      <div
        className="absolute top-[60%] left-[10%] h-[30vh] w-[30vh] rounded-full opacity-[0.08]"
        style={{
          background: "radial-gradient(circle, rgba(251, 113, 133, 0.5) 0%, transparent 70%)",
          animation: "mesh-drift 28s ease-in-out infinite",
          animationDelay: "-5s",
          filter: "blur(70px)",
        }}
      />
    </div>
  );
}
