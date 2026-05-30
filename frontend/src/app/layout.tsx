import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ShopMind AI",
  description: "AI-Native Headless Commerce Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
