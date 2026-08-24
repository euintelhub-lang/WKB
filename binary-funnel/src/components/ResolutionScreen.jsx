import VerifiedBadge from "./VerifiedBadge";

export default function ResolutionScreen({ pack, resolution, onRestart }) {
  return (
    <div className="resolution-box">
      <div className="resolution-title">
        <h2>{resolution.title}</h2>
        <VerifiedBadge verified={pack.verified} />
      </div>
      <p className="resolution-detail">{resolution.detail}</p>
      {!pack.verified && (
        <div className="disclaimer">
          Този резултат идва от генериран pack и не е верифициран.
          Разглеждайте го като ориентировъчен, не като окончателна
          препоръка.
        </div>
      )}
      <span className="restart-link" onClick={onRestart}>
        ← Започни отново
      </span>
    </div>
  );
}
