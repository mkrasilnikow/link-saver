"use client";

interface TagCount { tag: string; count: number }
interface FolderCount { folder: string; count: number }

interface Props {
  tags: TagCount[];
  folders: FolderCount[];
  activeTag: string | null;
  activeFolder: string | null;
  onSelectTag: (tag: string | null) => void;
  onSelectFolder: (folder: string | null) => void;
}

function FilterList<T>({
  items,
  activeKey,
  getKey,
  getLabel,
  getCount,
  onSelect,
}: {
  items: T[];
  activeKey: string | null;
  getKey: (item: T) => string;
  getLabel: (item: T) => string;
  getCount: (item: T) => number;
  onSelect: (key: string | null) => void;
}) {
  return (
    <ul className="space-y-1">
      {items.map((item) => {
        const key = getKey(item);
        return (
          <li key={key}>
            <button
              onClick={() => onSelect(activeKey === key ? null : key)}
              className={`w-full text-left px-3 py-1.5 rounded-md text-sm flex justify-between items-center transition-colors ${
                activeKey === key
                  ? "bg-blue-100 text-blue-700 font-medium"
                  : "text-gray-700 hover:bg-gray-100"
              }`}
            >
              <span>{getLabel(item)}</span>
              <span className="text-xs text-gray-400">{getCount(item)}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

export default function TagFilter({ tags, folders, activeTag, activeFolder, onSelectTag, onSelectFolder }: Props) {
  return (
    <aside className="w-full md:w-56 shrink-0 space-y-5">
      {/* Folders */}
      {folders.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">Папки</h2>
          <ul className="space-y-1">
            <li>
              <button
                onClick={() => onSelectFolder(null)}
                className={`w-full text-left px-3 py-1.5 rounded-md text-sm transition-colors ${
                  activeFolder === null && activeTag === null
                    ? "bg-blue-100 text-blue-700 font-medium"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
              >
                Все ссылки
              </button>
            </li>
            <FilterList
              items={folders}
              activeKey={activeFolder}
              getKey={(f) => f.folder}
              getLabel={(f) => `📁 ${f.folder}`}
              getCount={(f) => f.count}
              onSelect={onSelectFolder}
            />
          </ul>
        </div>
      )}

      {/* Tags */}
      <div>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">Теги</h2>
        <ul className="space-y-1">
          {folders.length === 0 && (
            <li>
              <button
                onClick={() => onSelectTag(null)}
                className={`w-full text-left px-3 py-1.5 rounded-md text-sm transition-colors ${
                  activeTag === null ? "bg-blue-100 text-blue-700 font-medium" : "text-gray-700 hover:bg-gray-100"
                }`}
              >
                Все ссылки
              </button>
            </li>
          )}
          <FilterList
            items={tags}
            activeKey={activeTag}
            getKey={(t) => t.tag}
            getLabel={(t) => `#${t.tag}`}
            getCount={(t) => t.count}
            onSelect={onSelectTag}
          />
        </ul>
      </div>
    </aside>
  );
}
