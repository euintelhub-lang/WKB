import Funnel from "./components/Funnel";
import { loadVerifiedPacks } from "./usePacks";

const packs = loadVerifiedPacks();

export default function App() {
  return (
    <div className="funnel">
      <div className="funnel-header">
        <h1>Binary Funnel</h1>
        <p>Избери домейн и отговаряй само с да/не.</p>
      </div>
      <Funnel packs={packs} />
    </div>
  );
}
