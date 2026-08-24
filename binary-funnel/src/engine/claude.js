const API_URL = "https://api.anthropic.com/v1/messages";
const MODEL = "claude-sonnet-5";

async function callClaude(system, userContent) {
  const apiKey = import.meta.env.VITE_ANTHROPIC_API_KEY;
  const response = await fetch(API_URL, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
      "anthropic-dangerous-direct-browser-access": "true",
    },
    body: JSON.stringify({
      model: MODEL,
      max_tokens: 512,
      system,
      messages: [{ role: "user", content: userContent }],
    }),
  });

  if (!response.ok) {
    throw new Error(`Claude API error: ${response.status}`);
  }

  const data = await response.json();
  const text = data.content?.[0]?.text ?? "{}";
  return JSON.parse(text);
}

const GENERATE_PACK_SYSTEM = `Ти дефинираш нов Domain Pack за да/не фуния.
Върни само JSON от вида {"title": string, "description": string, "firstQuestion": string}.
firstQuestion трябва да е въпрос с отговор само да/не.`;

const ASK_NEXT_SYSTEM = `Ти водиш да/не фуния стъпка по стъпка за дадена тема.
На база историята от досегашни да/не отговори, върни следващата стъпка
като JSON от точно един от двата вида:
{"done": false, "question": string}
{"done": true, "resolution": {"title": string, "detail": string}}
Никога не връщай нищо друго освен този JSON.`;

export async function generatePack(topic) {
  const result = await callClaude(
    GENERATE_PACK_SYSTEM,
    `Тема на pack-а: ${topic}`
  );
  return {
    id: `generated:${Date.now()}`,
    title: result.title,
    description: result.description,
    verified: false,
    topic,
    firstQuestion: result.firstQuestion,
  };
}

export async function askNext(pack, history) {
  const transcript = history
    .map((step) => `- ${step.question} => ${step.answer ? "да" : "не"}`)
    .join("\n");
  return callClaude(
    ASK_NEXT_SYSTEM,
    `Тема: ${pack.topic}\nИстория на отговорите:\n${transcript || "(няма още)"}`
  );
}
