import type { Metadata, Viewport } from "next";
import { Lexend, Source_Sans_3, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const lexend = Lexend({ subsets: ["latin"], variable: "--font-heading-loaded", weight: ["500", "600", "700"] });
const sourceSans = Source_Sans_3({ subsets: ["latin"], variable: "--font-body-loaded", weight: ["400", "500", "600"] });
const plexMono = IBM_Plex_Mono({ subsets: ["latin"], variable: "--font-mono-loaded", weight: ["400", "500"] });

export const metadata: Metadata = {
  title: {
    default: "Stacks",
    template: "%s | Stacks",
  },
  description: "Stacks resolves room-booking conflicts, routes ambiguous interlibrary-loan requests, and chases overdue items for library staff, automatically when it's safe and with a human in the loop when it isn't.",
  openGraph: {
    siteName: "Stacks",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#0A0E11",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${lexend.variable} ${sourceSans.variable} ${plexMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
