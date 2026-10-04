"use client";

import Button from "@mui/material/Button";
import { useRouter } from "next/navigation";

export default function LogoutButton() {
  const router = useRouter();

  async function logout() {
    await fetch("/api/logout", { method: "POST" });
    router.push("/");
    router.refresh();
  }

  return <Button variant="outlined" onClick={logout} sx={{ mt: 3 }}>Sign out</Button>;
}
