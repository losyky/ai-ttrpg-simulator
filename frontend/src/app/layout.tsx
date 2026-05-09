import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI TTRPG Simulator",
  description: "AI 驱动的单人跑团模拟器",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="h-full antialiased dark">
      <body className="min-h-full flex flex-col bg-background text-foreground">
        {children}
      </body>
    </html>
  );
}
