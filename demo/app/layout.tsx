import type { Metadata } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";
import { cookies } from "next/headers";
import { SESSION_COOKIE } from "@/lib/http";
import { store } from "@/lib/store";
import NavBar from "./nav-bar";
import Providers from "./providers";
import "./globals.css";

const jakarta = Plus_Jakarta_Sans({ subsets: ["latin"], variable: "--font-jakarta" });

export const metadata: Metadata = {
  title: "LightRBA: risk-based login protection",
  description: "Lightweight risk-based authentication: every sign-in scored, challenged or blocked in real time.",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value ?? "";
  const username = store.sessions.get(token) ?? null;

  return (
    <html lang="en" className={jakarta.variable}>
      <body>
        <Providers>
          <NavBar username={username} />
          {children}
        </Providers>
      </body>
    </html>
  );
}
