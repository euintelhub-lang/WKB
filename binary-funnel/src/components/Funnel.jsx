import { useState } from "react";
import VerifiedBadge from "./VerifiedBadge";
import ResolutionScreen from "./ResolutionScreen";
import { generatePack, askNext } from "../engine/claude";

export default function Funnel({ packs }) {
  const [pack, setPack] = useState(null);
  const [step, setStep] = useState(null);
  const [stepDispatch, setStepDispatch] = useState(null);
  const [history, setHistory] = useState([]);
  const [resolution, setResolution] = useState(null);
  const [loading, setLoading] = useState(false);

  function reset() {
    setPack(null);
    setStep(null);
    setStepDispatch(null);
    setHistory([]);
    setResolution(null);
  }

  function startVerified(selected) {
    setPack(selected);
    setStep(selected.start);
    setStepDispatch(null);
    setHistory([]);
    setResolution(null);
  }

  async function startGenerated(topic) {
    setLoading(true);
    const generated = await generatePack(topic);
    setPack(generated);
    setStep(generated.firstQuestion);
    setStepDispatch(generated.dispatch);
    setHistory([]);
    setResolution(null);
    setLoading(false);
  }

  async function answer(value) {
    if (pack.verified) {
      const node = pack.questions[step];
      const nextId = value ? node.yes : node.no;
      setHistory((h) => [...h, { question: node.text, answer: value }]);
      if (nextId.startsWith("resolution:")) {
        setResolution(pack.resolutions[nextId.replace("resolution:", "")]);
        setStep(null);
      } else {
        setStep(nextId);
      }
      return;
    }

    const nextHistory = [...history, { question: step, answer: value }];
    setHistory(nextHistory);
    setLoading(true);
    const result = await askNext(pack, nextHistory);
    setLoading(false);
    if (result.done) {
      setResolution({ ...result.resolution, dispatch: result.dispatch });
      setStep(null);
    } else {
      setStep(result.question);
      setStepDispatch(result.dispatch);
    }
  }

  if (resolution) {
    return <ResolutionScreen pack={pack} resolution={resolution} onRestart={reset} />;
  }

  if (pack && step) {
    return (
      <div className="question-box">
        <div className="funnel-header">
          <VerifiedBadge verified={pack.verified} verdict={stepDispatch?.verdict} />
        </div>
        <p className="question-text">{step.text ?? step}</p>
        <div className="yes-no-row">
          <button className="yes" onClick={() => answer(true)} disabled={loading}>
            Да
          </button>
          <button className="no" onClick={() => answer(false)} disabled={loading}>
            Не
          </button>
        </div>
        {loading && <p className="loading">Зареждане на следваща стъпка…</p>}
      </div>
    );
  }

  return (
    <div className="pack-list">
      {packs.map((p) => (
        <button key={p.id} className="pack-card" onClick={() => startVerified(p)}>
          <div className="pack-card-title">
            <span>{p.title}</span>
            <VerifiedBadge verified={p.verified} />
          </div>
          <div className="pack-card-desc">{p.description}</div>
        </button>
      ))}
      <button
        className="pack-card"
        disabled={loading}
        onClick={() => {
          const topic = window.prompt("Опиши темата за нова фуния:");
          if (topic) startGenerated(topic);
        }}
      >
        <div className="pack-card-title">
          <span>Нов домейн (генериран)</span>
          <VerifiedBadge verified={false} />
        </div>
        <div className="pack-card-desc">
          Създава pack на момента чрез dispatch към няколко модела — не е верифициран.
        </div>
      </button>
    </div>
  );
}
