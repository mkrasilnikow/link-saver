"use client";

interface TagCount {
  tag: string;
  count: number;
}

interface Props {
  tags: TagCount[];
  activeTag: string | null;
  onSelect: (tag: string | null) => void;
}

export default function TagFilter({ tags, activeTag, onSelect }: Props) {
  return (
    <aside className="w-full md:w-56 shrink-0">
      <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Теги</h2>
      <ul className="space-y-1">
        <li>
          <button
            onClick={() => onSelect(null)}
            className={`w-full text-left px-3 py-1.5 rounded-md text-sm transition-colors ${
              activeTag === null
                ? "bg-blue-100 text-blue-700 font-medium"
                : "text-gray-700 hover:bg-gray-100"
            }`}
          >
            Все ссылки
          </button>
        </li>
        {tags.map(({ tag, count }) => (
          <li key={tag}>
            <button
              onClick={() => onSelect(activeTag === tag ? null : tag)}
              className={`w-full text-left px-3 py-1.5 rounded-md text-sm flex justify-between items-center transition-colors ${
                activeTag === tag
                  ? "bg-blue-100 text-blue-700 font-medium"
                  : "text-gray-700 hover:bg-gray-100"
              }`}
            >
              <span>#{tag}</span>
              <span className="text-xs text-gray-400">{count}</span>
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
