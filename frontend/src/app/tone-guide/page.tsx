"use client";

import { useEffect, useState } from "react";
import { getToneGuide, updateToneGuide } from "@/lib/api";

export default function ToneGuidePage() {
  const [useWords, setUseWords] = useState<string[]>([]);
  const [avoidWords, setAvoidWords] = useState<string[]>([]);
  const [principles, setPrinciples] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  // Input fields for adding new words
  const [newUseWord, setNewUseWord] = useState("");
  const [newAvoidWord, setNewAvoidWord] = useState("");
  const [newPrinciple, setNewPrinciple] = useState("");

  useEffect(() => {
    load();
  }, []);

  async function load() {
    setLoading(true);
    try {
      const data = await getToneGuide();
      setUseWords(data.use_words || []);
      setAvoidWords(data.avoid_words || []);
      setPrinciples(data.principles || []);
    } catch (e: any) {
      setMessage(`Error loading: ${e.message}`);
    }
    setLoading(false);
  }

  async function handleSave() {
    setSaving(true);
    try {
      await updateToneGuide({
        use_words: useWords,
        avoid_words: avoidWords,
        principles,
      });
      setMessage("Tone guide saved");
    } catch (e: any) {
      setMessage(`Error saving: ${e.message}`);
    }
    setSaving(false);
  }

  function addUseWord() {
    const word = newUseWord.trim();
    if (!word || useWords.includes(word)) return;
    setUseWords([...useWords, word]);
    setNewUseWord("");
  }

  function removeUseWord(word: string) {
    setUseWords(useWords.filter((w) => w !== word));
  }

  function addAvoidWord() {
    const word = newAvoidWord.trim();
    if (!word || avoidWords.includes(word)) return;
    setAvoidWords([...avoidWords, word]);
    setNewAvoidWord("");
  }

  function removeAvoidWord(word: string) {
    setAvoidWords(avoidWords.filter((w) => w !== word));
  }

  function addPrinciple() {
    const p = newPrinciple.trim();
    if (!p) return;
    setPrinciples([...principles, p]);
    setNewPrinciple("");
  }

  function removePrinciple(idx: number) {
    setPrinciples(principles.filter((_, i) => i !== idx));
  }

  function updatePrinciple(idx: number, value: string) {
    const next = [...principles];
    next[idx] = value;
    setPrinciples(next);
  }

  if (loading) {
    return <div className="text-zinc-500 py-8 text-center">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Tone Guide</h1>
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white text-sm font-medium rounded transition-colors"
        >
          {saving ? "Saving..." : "Save Changes"}
        </button>
      </div>

      {message && (
        <div className="text-sm text-zinc-400 bg-zinc-800 rounded px-3 py-2">
          {message}
        </div>
      )}

      {/* Use Words */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
        <h2 className="font-semibold mb-3 text-green-400">Use Words</h2>
        <p className="text-xs text-zinc-500 mb-3">
          Words and phrases Mina should prefer using in generated content.
        </p>
        <div className="flex flex-wrap gap-2 mb-3">
          {useWords.map((word) => (
            <span
              key={word}
              className="inline-flex items-center gap-1 px-3 py-1 bg-green-900/30 border border-green-700 text-green-300 text-sm rounded-full"
            >
              {word}
              <button
                onClick={() => removeUseWord(word)}
                className="text-green-500 hover:text-green-200 ml-1"
              >
                x
              </button>
            </span>
          ))}
          {useWords.length === 0 && (
            <span className="text-zinc-600 text-sm">No words added yet</span>
          )}
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={newUseWord}
            onChange={(e) => setNewUseWord(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addUseWord()}
            className="flex-1 bg-zinc-800 border border-zinc-700 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-zinc-500"
            placeholder="Add a word or phrase..."
          />
          <button
            onClick={addUseWord}
            className="px-3 py-1.5 text-sm bg-zinc-700 hover:bg-zinc-600 text-white rounded"
          >
            Add
          </button>
        </div>
      </div>

      {/* Avoid Words */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
        <h2 className="font-semibold mb-3 text-red-400">Avoid Words</h2>
        <p className="text-xs text-zinc-500 mb-3">
          Words and phrases Mina should never use in generated content.
        </p>
        <div className="flex flex-wrap gap-2 mb-3">
          {avoidWords.map((word) => (
            <span
              key={word}
              className="inline-flex items-center gap-1 px-3 py-1 bg-red-900/30 border border-red-700 text-red-300 text-sm rounded-full"
            >
              {word}
              <button
                onClick={() => removeAvoidWord(word)}
                className="text-red-500 hover:text-red-200 ml-1"
              >
                x
              </button>
            </span>
          ))}
          {avoidWords.length === 0 && (
            <span className="text-zinc-600 text-sm">No words added yet</span>
          )}
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={newAvoidWord}
            onChange={(e) => setNewAvoidWord(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addAvoidWord()}
            className="flex-1 bg-zinc-800 border border-zinc-700 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-zinc-500"
            placeholder="Add a word or phrase..."
          />
          <button
            onClick={addAvoidWord}
            className="px-3 py-1.5 text-sm bg-zinc-700 hover:bg-zinc-600 text-white rounded"
          >
            Add
          </button>
        </div>
      </div>

      {/* Principles */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
        <h2 className="font-semibold mb-3">Principles</h2>
        <p className="text-xs text-zinc-500 mb-3">
          Guiding principles for Mina&apos;s tone and communication style.
        </p>
        <div className="space-y-2 mb-3">
          {principles.map((p, idx) => (
            <div key={idx} className="flex gap-2 items-start">
              <span className="text-zinc-600 text-sm mt-2 w-6 shrink-0">{idx + 1}.</span>
              <input
                type="text"
                value={p}
                onChange={(e) => updatePrinciple(idx, e.target.value)}
                className="flex-1 bg-zinc-800 border border-zinc-700 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-zinc-500"
              />
              <button
                onClick={() => removePrinciple(idx)}
                className="px-2 py-1.5 text-xs bg-red-900 hover:bg-red-800 text-red-300 rounded"
              >
                Remove
              </button>
            </div>
          ))}
          {principles.length === 0 && (
            <span className="text-zinc-600 text-sm">No principles added yet</span>
          )}
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={newPrinciple}
            onChange={(e) => setNewPrinciple(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addPrinciple()}
            className="flex-1 bg-zinc-800 border border-zinc-700 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-zinc-500"
            placeholder="Add a new principle..."
          />
          <button
            onClick={addPrinciple}
            className="px-3 py-1.5 text-sm bg-zinc-700 hover:bg-zinc-600 text-white rounded"
          >
            Add
          </button>
        </div>
      </div>
    </div>
  );
}
