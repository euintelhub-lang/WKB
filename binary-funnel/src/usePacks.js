const modules = import.meta.glob("./packs/*.json", { eager: true });

export function loadVerifiedPacks() {
  return Object.values(modules).map((mod) => mod.default ?? mod);
}
