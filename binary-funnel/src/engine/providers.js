function anthropicProvider(system, userContent) {
  return {
    name: "anthropic",
    url: "https://api.anthropic.com/v1/messages",
    headers: {
      "content-type": "application/json",
      "x-api-key": import.meta.env.VITE_ANTHROPIC_API_KEY,
      "anthropic-version": "2023-06-01",
      "anthropic-dangerous-direct-browser-access": "true",
    },
    body: JSON.stringify({
      model: "claude-sonnet-5",
      max_tokens: 512,
      system,
      messages: [{ role: "user", content: userContent }],
    }),
    extractText: (data) => data.content?.[0]?.text ?? "",
  };
}

function secondaryProvider(system, userContent) {
  const name = import.meta.env.VITE_SECONDARY_PROVIDER_NAME;
  const url = import.meta.env.VITE_SECONDARY_PROVIDER_URL;
  const key = import.meta.env.VITE_SECONDARY_PROVIDER_KEY;
  const model = import.meta.env.VITE_SECONDARY_PROVIDER_MODEL;
  if (!name || !url || !key) return null;

  return {
    name,
    url,
    headers: {
      "content-type": "application/json",
      authorization: `Bearer ${key}`,
    },
    body: JSON.stringify({
      model,
      messages: [
        { role: "system", content: system },
        { role: "user", content: userContent },
      ],
    }),
    extractText: (data) => data.choices?.[0]?.message?.content ?? "",
  };
}

export function configuredProviders(system, userContent) {
  return [anthropicProvider, secondaryProvider]
    .map((build) => build(system, userContent))
    .filter(Boolean);
}

export async function callProvider(provider) {
  const response = await fetch(provider.url, {
    method: "POST",
    headers: provider.headers,
    body: provider.body,
  });
  if (!response.ok) {
    throw new Error(`${provider.name} error: ${response.status}`);
  }
  const data = await response.json();
  return provider.extractText(data);
}
