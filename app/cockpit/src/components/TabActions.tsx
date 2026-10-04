import { useState } from "react";
import type { CockpitData, Conditions } from "../data/types";
import { labelError, MAX_LABEL, MAX_TABS } from "../state/tabs";
import { presetOf } from "../state/url";
import { toYaml, yamlFileName } from "../state/yaml";

interface Props {
  data: CockpitData; // presets include the saved tabs
  conditions: Conditions;
  edited: boolean;
  tabCount: number;
  onSave: (label: string) => void;
  onRemove: () => void;
}

/** Keeps the current scenario: as a named tab beside the presets, or as a conditions file for the engine. */
export function TabActions({ data, conditions: c, edited, tabCount, onSave, onRemove }: Props) {
  const preset = presetOf(data, c.presetId);
  const custom = "base" in preset;
  const [naming, setNaming] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const close = () => {
    setNaming(false);
    setName("");
    setError(null);
  };
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const err = labelError(data, name);
    setError(err);
    if (err) return;
    onSave(name.trim());
    close();
  };
  const download = () => {
    const title = edited ? `${preset.label} (edited)` : preset.label;
    const url = URL.createObjectURL(new Blob([toYaml(data, c, title, preset.robustness)], { type: "text/yaml" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = yamlFileName(title);
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="scenario-tab" aria-labelledby="scenario-h">
      <div className="rail-head">
        <h2 id="scenario-h">Scenario</h2>
        <span className="rail-meta">{edited ? "Edited" : custom ? "Custom tab" : "Preset"}</span>
      </div>
      <p className="fine">
        {edited
          ? `${preset.label}, with your changes.`
          : custom
            ? preset.description
            : "Change a weight, gate, cooling type, or horizon, then save it as your own tab."}
      </p>
      {naming ? (
        <form className="tab-form" onSubmit={submit}>
          <label htmlFor="tab-name" className="visually-hidden">
            Tab name
          </label>
          <input
            id="tab-name"
            type="text"
            value={name}
            maxLength={MAX_LABEL}
            placeholder="Name this tab"
            autoFocus
            aria-invalid={error !== null}
            onChange={(e) => {
              setName(e.target.value);
              setError(null);
            }}
          />
          <button className="btn btn-quiet" type="submit">
            Save
          </button>
          <button className="btn btn-quiet" type="button" onClick={close}>
            Cancel
          </button>
          {error && (
            <p className="tab-error" role="alert">
              {error}
            </p>
          )}
        </form>
      ) : (
        <div className="tab-actions">
          {edited && tabCount < MAX_TABS && (
            <button className="btn btn-quiet" onClick={() => setNaming(true)}>
              Save as tab
            </button>
          )}
          <button className="btn btn-quiet" onClick={download}>
            Download YAML
          </button>
          {custom && (
            <button className="btn btn-quiet" onClick={onRemove}>
              Remove tab
            </button>
          )}
          {edited && tabCount >= MAX_TABS && <p className="fine">Remove a custom tab to save another.</p>}
        </div>
      )}
    </section>
  );
}
