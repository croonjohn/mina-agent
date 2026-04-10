"use client";

import { useEffect, useState } from "react";
import {
  getTemplates,
  createTemplate,
  updateTemplate,
  deleteTemplate,
  seedTemplates,
  Template,
} from "@/lib/api";

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [editingText, setEditingText] = useState<{ id: string; text: string } | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [message, setMessage] = useState("");

  // New template form
  const [newName, setNewName] = useState("");
  const [newPlatform, setNewPlatform] = useState("reddit");
  const [newContentType, setNewContentType] = useState("post");
  const [newText, setNewText] = useState("");

  useEffect(() => {
    load();
  }, []);

  async function load() {
    setLoading(true);
    try {
      const data = await getTemplates();
      setTemplates(data);
    } catch (e: any) {
      setMessage(`Error: ${e.message}`);
    }
    setLoading(false);
  }

  async function handleCreate() {
    if (!newName.trim() || !newText.trim()) {
      setMessage("Name and template text are required");
      return;
    }
    try {
      await createTemplate({
        name: newName,
        platform: newPlatform,
        content_type: newContentType,
        template_text: newText,
      });
      setShowCreate(false);
      setNewName("");
      setNewPlatform("reddit");
      setNewContentType("post");
      setNewText("");
      setMessage("Template created");
      load();
    } catch (e: any) {
      setMessage(`Error: ${e.message}`);
    }
  }

  async function handleSaveEdit() {
    if (!editingText) return;
    try {
      await updateTemplate(editingText.id, { template_text: editingText.text });
      setEditingText(null);
      setMessage("Template updated");
      load();
    } catch (e: any) {
      setMessage(`Error: ${e.message}`);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this template?")) return;
    try {
      await deleteTemplate(id);
      setMessage("Template deleted");
      load();
    } catch (e: any) {
      setMessage(`Error: ${e.message}`);
    }
  }

  async function handleSeed() {
    try {
      const result = await seedTemplates();
      setMessage(result.message);
      load();
    } catch (e: any) {
      setMessage(`Error: ${e.message}`);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Templates</h1>
        <div className="flex gap-2">
          <button
            onClick={handleSeed}
            className="px-3 py-1.5 text-sm bg-zinc-700 hover:bg-zinc-600 text-zinc-200 rounded border border-zinc-600"
          >
            Seed Default Templates
          </button>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded"
          >
            {showCreate ? "Cancel" : "New Template"}
          </button>
        </div>
      </div>

      {message && (
        <div className="text-sm text-zinc-400 bg-zinc-800 rounded px-3 py-2">
          {message}
        </div>
      )}

      {/* Create Form */}
      {showCreate && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 space-y-4">
          <h2 className="font-semibold">New Template</h2>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-zinc-400 mb-1">Name</label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-zinc-500"
                placeholder="e.g. reddit_post_helpful"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1">Platform</label>
              <select
                value={newPlatform}
                onChange={(e) => setNewPlatform(e.target.value)}
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-zinc-500"
              >
                <option value="reddit">reddit</option>
                <option value="itchio">itchio</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1">Content Type</label>
              <select
                value={newContentType}
                onChange={(e) => setNewContentType(e.target.value)}
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-zinc-500"
              >
                <option value="post">post</option>
                <option value="comment">comment</option>
                <option value="devlog">devlog</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs text-zinc-400 mb-1">Template Text</label>
            <textarea
              value={newText}
              onChange={(e) => setNewText(e.target.value)}
              rows={8}
              className="w-full bg-zinc-800 border border-zinc-700 rounded p-3 text-sm font-mono resize-y focus:outline-none focus:border-zinc-500"
              placeholder="Enter template text with {placeholders}..."
            />
          </div>
          <button
            onClick={handleCreate}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded"
          >
            Create Template
          </button>
        </div>
      )}

      {/* Template List */}
      {loading ? (
        <div className="text-zinc-500 py-8 text-center">Loading...</div>
      ) : templates.length === 0 ? (
        <div className="text-zinc-500 py-8 text-center">
          No templates yet. Click &quot;Seed Default Templates&quot; to get started.
        </div>
      ) : (
        <div className="space-y-3">
          {templates.map((tmpl) => (
            <div
              key={tmpl.id}
              className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden"
            >
              <div className="flex items-center gap-3 px-4 py-3">
                <span className="text-sm font-medium flex-1">{tmpl.name}</span>
                <span className="text-xs text-zinc-500 font-mono">{tmpl.platform}</span>
                <span className="text-xs text-zinc-600">{tmpl.content_type}</span>
                <button
                  onClick={() => setExpanded(expanded === tmpl.id ? null : tmpl.id)}
                  className="px-2 py-1 text-xs border border-zinc-600 text-zinc-300 hover:bg-zinc-700 hover:text-white rounded transition-colors"
                >
                  {expanded === tmpl.id ? "Collapse" : "Expand"}
                </button>
                <button
                  onClick={() => handleDelete(tmpl.id)}
                  className="px-2 py-1 text-xs bg-red-900 hover:bg-red-800 text-red-300 rounded"
                >
                  Delete
                </button>
              </div>

              {expanded === tmpl.id && (
                <div className="border-t border-zinc-800 px-4 py-4">
                  {editingText?.id === tmpl.id ? (
                    <div className="space-y-2">
                      <textarea
                        value={editingText.text}
                        onChange={(e) =>
                          setEditingText({ ...editingText, text: e.target.value })
                        }
                        rows={10}
                        className="w-full bg-zinc-800 border border-zinc-700 rounded p-3 text-sm font-mono resize-y focus:outline-none focus:border-zinc-500"
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={handleSaveEdit}
                          className="px-3 py-1.5 text-xs bg-blue-600 hover:bg-blue-500 text-white rounded"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setEditingText(null)}
                          className="px-3 py-1.5 text-xs bg-zinc-700 hover:bg-zinc-600 text-zinc-300 rounded"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <pre className="whitespace-pre-wrap text-sm text-zinc-300 leading-relaxed font-mono bg-zinc-800/50 rounded p-3">
                        {tmpl.template_text}
                      </pre>
                      <button
                        onClick={() =>
                          setEditingText({ id: tmpl.id, text: tmpl.template_text })
                        }
                        className="mt-3 text-xs text-zinc-500 hover:text-zinc-300"
                      >
                        Edit
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
