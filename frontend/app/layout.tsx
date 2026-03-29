import { ClerkProvider } from "@clerk/nextjs";
import type { Metadata } from "next";
import { Toaster } from "sonner";
import "./globals.css";

export const metadata: Metadata = {
  title: "ShiftAssist",
  description: "シフト管理システム",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html lang="ja" className="h-full antialiased">
        <body className="min-h-full flex flex-col bg-slate-950 text-slate-200 font-sans">
          {children}
          <Toaster
            position="top-right"
            toastOptions={{
              classNames: {
                toast:
                  "bg-slate-900 border border-slate-700 text-slate-200",
                success: "border-cyan-500/50 text-cyan-300",
                error: "border-red-500/50 text-red-300",
              },
            }}
          />
        </body>
      </html>
    </ClerkProvider>
  );
}
