/**
 * Playwright global setup — builds the extension before tests run.
 */

import { execSync } from "child_process";
import path from "path";

export default async function globalSetup(): Promise<void> {
  console.log("[Playwright Setup] Building extension...");
  execSync("npm run build", { stdio: "inherit", cwd: path.resolve(__dirname, "..") });
  console.log("[Playwright Setup] Extension built successfully.");
}
