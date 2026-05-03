import { ImageResponse } from "next/og";

// Generated at build time, served by Next.js as /icon — auto-replaces the
// default Vercel favicon. The mark mirrors the lucide Database icon used
// in the layout header so the browser-tab glyph and the in-page logo are
// the same shape. Forest green matches `--color-primary` in globals.css.

export const size = { width: 32, height: 32 };
export const contentType = "image/png";

const FOREST_GREEN = "#1c4d3d";

export default function Icon() {
  return new ImageResponse(
    <div
      style={{
        background: FOREST_GREEN,
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <svg
        width="22"
        height="22"
        viewBox="0 0 24 24"
        fill="none"
        stroke="white"
        strokeWidth="2.5"
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
