import { ClerkProvider } from "@clerk/nextjs";
import type { Metadata } from "next";
import { Toaster } from "sonner";

import { Header } from "@/components/layout/Header";
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
        <body className="min-h-full flex flex-col bg-gray-50 text-gray-900 font-sans">
          <Header />
          <div className="flex flex-col flex-1 pt-14">
            {children}
          </div>
          <Toaster
            position="top-right"
            toastOptions={{
              classNames: {
                toast:
                  "bg-white border border-gray-200 text-gray-800 shadow-sm",
                success: "border-green-300 text-green-700",
                error: "border-red-300 text-red-700",
              },
            }}
          />
        </body>
      </html>
    </ClerkProvider>
  );
}
