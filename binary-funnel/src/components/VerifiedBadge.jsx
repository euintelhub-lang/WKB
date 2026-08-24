export default function VerifiedBadge({ verified }) {
  if (verified) {
    return <span className="badge badge-verified">✓ Проверено</span>;
  }
  return <span className="badge badge-generated">○ Ориентировъчно</span>;
}
