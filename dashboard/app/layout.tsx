import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Execution Truth — Self-Improving Voice Agent",
  description:
    "Evaluation, diagnosis, and autonomous improvement of a deployed Hindi voice agent, graded from an append-only tool journal.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
