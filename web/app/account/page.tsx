import CheckCircleOutlinedIcon from "@mui/icons-material/CheckCircleOutlined";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { SESSION_COOKIE } from "@/lib/http";
import { store } from "@/lib/store";
import LogoutButton from "./logout-button";

export default async function AccountPage() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value ?? "";
  const username = store.sessions.get(token);
  if (!username) redirect("/login");

  return (
    <Box className="mx-auto max-w-2xl px-4 py-16">
      <Card sx={{ boxShadow: "0 12px 40px rgba(15,23,42,0.08)" }}>
        <CardContent sx={{ p: 4 }}>
          <Chip icon={<CheckCircleOutlinedIcon />} label="Signed in" color="success" />
          <Typography variant="h3" sx={{ mt: 2 }}>Welcome, {username}</Typography>
          <Typography color="text.secondary" sx={{ mt: 2 }}>
            This sign-in passed the risk check and has been added to your login history, so next time this device
            and location will look familiar. Sign-ins that are refused or fail the one-time code never are.
          </Typography>
          <LogoutButton />
        </CardContent>
      </Card>
    </Box>
  );
}
