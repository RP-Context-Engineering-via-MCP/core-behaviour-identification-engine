import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "CBIE Admin — Core Behaviour Identification Engine",
  description: "Administration panel for the Core Behaviour Identification Engine",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen bg-slate-50 font-sans antialiased">
        {/* Top nav */}
        <header className="sticky top-0 z-40 border-b border-slate-200 bg-white shadow-sm">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="flex h-14 items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="h-6 w-1.5 rounded-full bg-indigo-600" aria-hidden="true" />
                <span className="text-sm font-semibold text-slate-900 tracking-tight">
                  CBIE
                  <span className="ml-1.5 font-normal text-slate-400">Admin</span>
                </span>
              </div>
              <nav className="flex items-center gap-4 text-sm">
                <Link
                  href="/admin/users"
                  className="font-medium text-slate-600 transition-colors hover:text-slate-900"
                >
                  Users
                </Link>
              </nav>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main>{children}</main>
      </body>
    </html>
  );
}
