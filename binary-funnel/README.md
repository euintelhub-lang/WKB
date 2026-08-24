# Binary Funnel v0.2

Да/не фуния, базирана на Domain Pack-ове. Виж `CLAUDE.md` за петте
инварианта, преди да променяш поведение.

## Структура

- `CLAUDE.md` — петте инварианта.
- `src/engine/claude.js` — цялата комуникация с Anthropic API
  (`generatePack()`, `askNext()`).
- `src/packs/*.json` — верифицирани домейни, вдигани автоматично чрез
  `import.meta.glob`.
- `src/components/VerifiedBadge.jsx` — маркировка verified/generated.
- `src/components/ResolutionScreen.jsx` — краен екран с resolution и
  disclaimer за генерирани pack-ове.
- `src/styles.css` — импортира `src/app.css`.

## Стартиране

```
npm install
cp .env.example .env
# добави ANTHROPIC_API_KEY в .env
npm run dev
```
