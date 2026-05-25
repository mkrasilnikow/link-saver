import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LinkSaver",
  description: "Personal link manager with AI auto-tagging",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body className="bg-gray-50 min-h-screen">{children}</body>
    </html>
  );
}
