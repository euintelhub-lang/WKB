import VerifiedBadge from "./VerifiedBadge";

function exportForWkb(pack, resolution) {
  const payload = {
    topic: resolution.title,
    status: "SUCCESS",
    regime: `${pack.verified ? "verified" : "generated"}@binary-funnel`,
    body: resolution.detail,
    positions: resolution.dispatch?.positions ?? [],
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${pack.id}-resolution.json`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function ResolutionScreen({ pack, resolution, onRestart }) {
  const dispatchInfo = resolution.dispatch;

  return (
    <div className="resolution-box">
      <div className="resolution-title">
        <h2>{resolution.title}</h2>
        <VerifiedBadge verified={pack.verified} verdict={dispatchInfo?.verdict} />
      </div>
      <p className="resolution-detail">{resolution.detail}</p>
      {!pack.verified && (
        <div className="disclaimer">
          Този резултат идва от генериран pack и не е верифициран.
          Разглеждайте го като ориентировъчен, не като окончателна
          препоръка.
          {dispatchInfo?.verdict === "DISAGREE" && (
            <div className="dispatch-positions">
              <p>Доставчиците се разминаха:</p>
              {dispatchInfo.positions.map((p) => (
                <div key={p.provider} className="dispatch-position">
                  <strong>{p.provider}:</strong> {p.text}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      {!pack.verified && (
        <button
          type="button"
          className="export-link"
          onClick={() => exportForWkb(pack, resolution)}
        >
          Export за WKB
        </button>
      )}
      <span className="restart-link" onClick={onRestart}>
        ← Започни отново
      </span>
    </div>
  );
}
