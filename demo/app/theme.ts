"use client";

import { createTheme } from "@mui/material/styles";

export const NAVY = "#0b1437";

export const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#3d5afe", dark: "#2a3eb1", contrastText: "#ffffff" },
    secondary: { main: "#00bfa5", contrastText: "#04201b" },
    success: { main: "#2e7d32" },
    warning: { main: "#ed6c02" },
    error: { main: "#d32f2f" },
    background: { default: "#f4f6fb", paper: "#ffffff" },
    text: { primary: "#0f172a", secondary: "#475569" },
    divider: "#e2e8f0",
  },
  shape: { borderRadius: 12 },
  typography: {
    fontFamily: "var(--font-jakarta), system-ui, sans-serif",
    h1: { fontWeight: 800, letterSpacing: "-0.03em" },
    h2: { fontWeight: 800, letterSpacing: "-0.02em" },
    h3: { fontWeight: 700, letterSpacing: "-0.02em" },
    h4: { fontWeight: 700 },
    h5: { fontWeight: 700 },
    h6: { fontWeight: 700 },
    button: { textTransform: "none", fontWeight: 600 },
    overline: { fontWeight: 700, letterSpacing: "0.12em" },
  },
  components: {
    MuiButton: { defaultProps: { disableElevation: true }, styleOverrides: { sizeLarge: { padding: "10px 22px" } } },
    MuiCard: { defaultProps: { variant: "outlined" } },
    MuiChip: { styleOverrides: { root: { fontWeight: 600 } } },
    MuiTableCell: { styleOverrides: { head: { fontWeight: 700, color: "#475569" } } },
  },
});
