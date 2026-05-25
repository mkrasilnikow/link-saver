"use client";

import { useEffect, useState, useCallback } from "react";
import LinkCard from "@/components/LinkCard";
import TagFilter from "@/components/TagFilter";
import SearchBar from "@/components/SearchBar";

interface Link {
  id: string;
  url: string;
  title: string | null;
  description: string | null;
  thumbnail: string | null;
  type: string;
  tags: string[];
  status: string;
  source: string;
  created_at: string;
}

export default function Home() {
  const [links, setLinks] = useState<Link[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTag, setActiveTag] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 400);
    return () => clearTimeout(timer);
  }, [search]);

  const fetchLinks = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (activeTag) params.set("tag", activeTag);
    if (statusFilter) params.set("status", statusFilter);
    if (debouncedSearch) params.set("search", debouncedSearch);

    const res = await fetch(`/api/links?${params.toString()}`);
    const data = await res.json();
    setLinks(Array.isArray(data) ? data : []);
    setLoading(false);
  }, [activeTag, statusFilter, debouncedSearch]);

  useEffect(() => {
    fetchLinks();
  }, [fetchLinks]);

  const allTags = links.reduce<Record<string, number>>((acc, link) => {
    (link.tags || []).forEach((t) => { acc[t] = (acc[t] || 0) + 1; });
    return acc;
  }, {});

  const tagList = Object.entries(allTags)
    .map(([tag, count]) => ({ tag, count }))
    .sort((a, b) => b.count - a.count);

  const handleStatusChange = async (id: string, status: string) => {
    await fetch("/api/links", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, status }),
    });
    fetchLinks();
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Удалить ссылку?")) return;
    await fetch(`/api/links?id=${id}`, { method: "DELETE" });
    fetchLinks();
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-8">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <h1 className="text-2xl font-bold text-gray-900">📚 LinkSaver</h1>
          <div className="flex items-center gap-3 flex-wrap">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-sm border border-gray-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Все статусы</option>
              <option value="unread">Непрочитанные</option>
              <option value="read">Прочитанные</option>
            </select>
            <a
              href="/api/export?format=md"
              className="text-sm px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-gray-700 transition-colors"
            >
              ⬇ Экспорт .md
            </a>
          </div>
        </div>
        <div className="mt-4">
          <SearchBar value={search} onChange={setSearch} />
        </div>
      </header>

      <div className="flex gap-8 flex-col md:flex-row">
        <TagFilter tags={tagList} activeTag={activeTag} onSelect={setActiveTag} />

        <main className="flex-1">
          {loading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="bg-white rounded-xl border border-gray-100 h-64 animate-pulse" />
              ))}
            </div>
          ) : links.length === 0 ? (
            <div className="text-center py-20 text-gray-400">
              <p className="text-4xl mb-3">🔗</p>
              <p className="text-lg">Ссылок пока нет</p>
              <p className="text-sm mt-1">Отправь URL в Telegram-бота, чтобы сохранить</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {links.map((link) => (
                <LinkCard
                  key={link.id}
                  link={link}
                  onStatusChange={handleStatusChange}
                  onDelete={handleDelete}
                />
              ))}
            </div>
          )}
          {!loading && links.length > 0 && (
            <p className="text-xs text-gray-400 text-center mt-6">{links.length} ссылок</p>
          )}
        </main>
      </div>
    </div>
  );
}
