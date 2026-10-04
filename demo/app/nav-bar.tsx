"use client";

import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAVY } from "./theme";

const LINKS = [
  { href: "/", label: "Overview" },
  { href: "/demo", label: "Live demo" },
  { href: "/dashboard", label: "Security dashboard" },
];

export default function NavBar({ username }: { username: string | null }) {
  const pathname = usePathname();
  return (
    <AppBar position="sticky" elevation={0} sx={{ bgcolor: NAVY, borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
      <Toolbar className="mx-auto w-full max-w-7xl gap-2">
        <Box component={Link} href="/" sx={{ display: "flex", alignItems: "center", gap: 1, color: "white", textDecoration: "none", mr: "auto" }}>
          <ShieldOutlinedIcon sx={{ color: "secondary.main" }} />
          <Typography variant="h6" component="span" sx={{ fontWeight: 800 }}>
            Light<Box component="span" sx={{ color: "secondary.main" }}>RBA</Box>
          </Typography>
        </Box>
        <Box sx={{ display: { xs: "none", sm: "flex" }, gap: 0.5 }}>
          {LINKS.map((link) => (
            <Button key={link.href} component={Link} href={link.href}
                    sx={{ color: pathname === link.href ? "white" : "rgba(255,255,255,0.7)",
                          bgcolor: pathname === link.href ? "rgba(255,255,255,0.08)" : "transparent" }}>
              {link.label}
            </Button>
          ))}
        </Box>
        <Button component={Link} href={username ? "/account" : "/login"} variant="contained" color="secondary" sx={{ ml: 1 }}>
          {username ? `Signed in as ${username}` : "Sign in"}
        </Button>
      </Toolbar>
    </AppBar>
  );
}
