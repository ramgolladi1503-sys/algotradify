import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AlgoTradify",
  description: "Live tradebot dashboard wired to local backend adapter",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
