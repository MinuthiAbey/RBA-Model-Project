import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  poweredByHeader: false,
  agentRules: false, // stop `next dev` adding extra docs files to the project
};

export default nextConfig;
