import type { Metadata } from "next";
import { Lexend, Source_Sans_3, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const lexend = Lexend({ subsets: ["latin"], variable: "--font-heading-loaded", weight: ["500", "600", "700"] });
const sourceSans = Source_Sans_3({ subsets: ["latin"], variable: "--font-body-loaded", weight: ["400", "500", "600"] });
const plexMono = IBM_Plex_Mono({ subsets: ["latin"], variable: "--font-mono-loaded", weight: ["400", "500"] });

export const metadata: Metadata = {
  title: "Stacks",
  description: "Library task-completion agent, staff console.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${lexend.variable} ${sourceSans.variable} ${plexMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
