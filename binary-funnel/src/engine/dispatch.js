import { configuredProviders, callProvider } from "./providers";

async function sha256(text) {
  const bytes = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

// Mirrors wkb.py's dispatch(): run every configured provider on the same
// step, hash each response, and report AGREE only on a literal match.
// Disagreement is preserved, never averaged away.
export async function dispatch(system, userContent) {
  const providers = configuredProviders(system, userContent);
  if (providers.length === 0) {
    throw new Error("no LLM provider configured (set VITE_ANTHROPIC_API_KEY)");
  }

  const positions = await Promise.all(
    providers.map(async (provider) => {
      const text = await callProvider(provider);
      return { provider: provider.name, text, sha: await sha256(text) };
    })
  );

  const verdict =
    new Set(positions.map((p) => p.sha)).size === 1 ? "AGREE" : "DISAGREE";

  return { verdict, positions, canonicalText: positions[0].text };
}
