import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "Etsy Laser Automation",
  description: "Générez et automatisez vos fichiers de découpe laser et vos fiches produits Etsy",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr" className="h-full scroll-smooth dark">
      <body className="min-h-screen bg-slate-950 text-slate-100 flex flex-col antialiased">
        <Navbar />
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 pb-16 md:px-6">
          {children}
        </main>
      </body>
    </html>
  );
}
