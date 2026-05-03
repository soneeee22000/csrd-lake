import { ImageResponse } from "next/og";

// 180x180 home-screen icon for iOS / iPadOS — same mark as /icon, scaled.

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

const FOREST_GREEN = "#1c4d3d";

export default function AppleIcon() {
  return new ImageResponse(
    <div
      style={{
        background: FOREST_GREEN,
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        borderRadius: 36,
      }}
    >
      <svg
        width="120"
        height="120"
        viewBox="0 0 24 24"
        fill="none"
        stroke="white"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <ellipse cx="12" cy="5" rx="9" ry="3" />
        <path d="M3 5v14a9 3 0 0 0 18 0V5" />
        <path d="M3 12a9 3 0 0 0 18 0" />
      </svg>
    </div>,
    { ...size },
  );
}
