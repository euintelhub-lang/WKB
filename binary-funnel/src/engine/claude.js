import { dispatch } from "./dispatch";

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
  const round = await dispatch(GENERATE_PACK_SYSTEM, `Тема на pack-а: ${topic}`);
  const result = JSON.parse(round.canonicalText);
  return {
    id: `generated:${Date.now()}`,
    title: result.title,
    description: result.description,
    verified: false,
    topic,
    firstQuestion: result.firstQuestion,
    dispatch: { verdict: round.verdict, positions: round.positions },
  };
}

export async function askNext(pack, history) {
  const transcript = history
    .map((step) => `- ${step.question} => ${step.answer ? "да" : "не"}`)
    .join("\n");
  const round = await dispatch(
    ASK_NEXT_SYSTEM,
    `Тема: ${pack.topic}\nИстория на отговорите:\n${transcript || "(няма още)"}`
  );
  const result = JSON.parse(round.canonicalText);
  return { ...result, dispatch: { verdict: round.verdict, positions: round.positions } };
}
