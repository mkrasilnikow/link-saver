"use client";

import { useState } from "react";

interface Link {
  id: string;
  url: string;
  title: string | null;
  description: string | null;
  thumbnail: string | null;
  type: string;
  tags: string[];
  folder: string | null;
  status: string;
  source: string;
  created_at: string;
}

interface Props {
  link: Link;
  folders: string[];
  onStatusChange: (id: string, status: string) => void;
  onFolderChange: (id: string, folder: string | null) => void;
  onDelete: (id: string) => void;
}

const TYPE_LABELS: Record<string, string> = {
  article: "Статья",
  video: "Видео",
  reel: "Reels",
  other: "Другое",
};

const TYPE_COLORS: Record<string, string> = {
  article: "bg-green-100 text-green-700",
  video: "bg-red-100 text-red-700",
  reel: "bg-purple-100 text-purple-700",
  other: "bg-gray-100 text-gray-600",
};

export default function LinkCard({ link, folders, onStatusChange, onFolderChange, onDelete }: Props) {
  const isRead = link.status === "read";
  const [showFolderPicker, setShowFolderPicker] = useState(false);
  const [newFolder, setNewFolder] = useState("");

  const formattedDate = new Date(link.created_at).toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  const handleFolderSubmit = (folder: string | null) => {
    onFolderChange(link.id, folder);
    setShowFolderPicker(false);
    setNewFolder("");
  };

  return (
    <div className={`bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden flex flex-col transition-opacity ${isRead ? "opacity-60" : ""}`}>
      {link.thumbnail && (
        <a href={link.url} target="_blank" rel="noopener noreferrer">
          <img
            src={link.thumbnail}
            alt={link.title || ""}
            className="w-full h-40 object-cover"
            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
        </a>
      )}
      <div className="p-4 flex flex-col gap-2 flex-1">
        <div className="flex items-start justify-between gap-2">
          <a
            href={link.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-semibold text-gray-900 hover:text-blue-600 line-clamp-2 leading-snug"
          >
            {link.title || link.url}
          </a>
          <span className={`shrink-0 text-xs px-2 py-0.5 rounded-full font-medium ${TYPE_COLORS[link.type] || TYPE_COLORS.other}`}>
            {TYPE_LABELS[link.type] || link.type}
          </span>
        </div>

        {link.description && (
          <p className="text-xs text-gray-500 line-clamp-2">{link.description}</p>
        )}

        {link.tags && link.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1">
            {link.tags.map((tag) => (
              <span key={tag} className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full">
                #{tag}
              </span>
            ))}
          </div>
        )}

        {/* Folder badge + picker */}
        <div className="relative">
          <button
            onClick={() => setShowFolderPicker(!showFolderPicker)}
            className="text-xs text-gray-500 hover:text-blue-500 flex items-center gap-1 transition-colors"
          >
            {link.folder ? (
              <><span>📁</span><span className="font-medium">{link.folder}</span></>
            ) : (
              <span className="text-gray-300 hover:text-blue-400">+ папка</span>
            )}
          </button>

          {showFolderPicker && (
            <div className="absolute left-0 top-full mt-1 z-10 bg-white border border-gray-200 rounded-lg shadow-lg p-2 min-w-40">
              {folders.length > 0 && (
                <ul className="mb-2">
                  {folders.map((f) => (
                    <li key={f}>
                      <button
                        onClick={() => handleFolderSubmit(f)}
                        className="w-full text-left text-xs px-2 py-1 hover:bg-blue-50 rounded"
                      >
                        📁 {f}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              <div className="flex gap-1">
                <input
                  type="text"
                  placeholder="Новая папка"
                  value={newFolder}
                  onChange={(e) => setNewFolder(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && newFolder.trim() && handleFolderSubmit(newFolder.trim())}
                  className="flex-1 text-xs border border-gray-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-400"
                  autoFocus
                />
                <button
                  onClick={() => newFolder.trim() && handleFolderSubmit(newFolder.trim())}
                  className="text-xs bg-blue-500 text-white px-2 py-1 rounded hover:bg-blue-600"
                >
                  ОК
                </button>
              </div>
              {link.folder && (
                <button
                  onClick={() => handleFolderSubmit(null)}
                  className="w-full text-left text-xs text-red-400 hover:text-red-600 px-2 py-1 mt-1"
                >
                  Убрать из папки
                </button>
              )}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between mt-auto pt-2">
          <span className="text-xs text-gray-400">{formattedDate}</span>
          <div className="flex gap-2">
            <button
              onClick={() => onStatusChange(link.id, isRead ? "unread" : "read")}
              title={isRead ? "Отметить непрочитанным" : "Отметить прочитанным"}
              className="text-xs text-gray-400 hover:text-blue-500 transition-colors"
            >
              {isRead ? "↩ Непрочитано" : "✓ Прочитано"}
            </button>
            <button
              onClick={() => onDelete(link.id)}
              title="Удалить"
              className="text-xs text-gray-400 hover:text-red-500 transition-colors"
            >
              ✕
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
