import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Loopline — Voice Agent Learning Control Plane",
  description: "Evaluate, improve, and govern Sarvam Indus voice-agent candidates with trace-level evidence.",
  openGraph: {
    title: "Loopline — Make every failure teach the next release",
    description: "A governed evaluation, improvement, and release control plane for production voice agents.",
    type: "website",
    images: [{ url: "/loopline-social.png", width: 1674, height: 941, alt: "A precision learning loop held at its release gate" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Loopline — Voice Agent Learning Control Plane",
    description: "Execution truth, bounded repairs, and human-gated release for production voice agents.",
    images: ["/loopline-social.png"],
  },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
