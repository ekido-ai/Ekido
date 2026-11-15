import type { Metadata } from "next";
import { Atkinson_Hyperlegible, Saira_Semi_Condensed } from "next/font/google";
import "./globals.css";

const display = Saira_Semi_Condensed({ variable: "--font-display", subsets: ["latin"], weight: ["500", "600", "700"] });
const body = Atkinson_Hyperlegible({ variable: "--font-body", subsets: ["latin"], weight: ["400", "700"] });

export const metadata: Metadata = {
  title: "Ekido",
  description: "Watch a training job survive a provider failure, and see who gets paid for what.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable}`}>
      <body>{children}</body>
    </html>
  );
}
