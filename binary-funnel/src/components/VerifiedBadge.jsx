export default function VerifiedBadge({ verified, verdict }) {
  if (verified) {
    return <span className="badge badge-verified">✓ Проверено</span>;
  }
  const suffix =
    verdict === "AGREE"
      ? " · модели съгласни"
      : verdict === "DISAGREE"
        ? " · модели се разминават"
        : "";
  return <span className="badge badge-generated">○ Ориентировъчно{suffix}</span>;
}
