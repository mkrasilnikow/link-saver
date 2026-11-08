import { NextRequest, NextResponse } from "next/server";
import { GoogleSpreadsheet, GoogleSpreadsheetWorksheet } from "google-spreadsheet";
import { JWT } from "google-auth-library";

const SCOPES = ["https://www.googleapis.com/auth/spreadsheets"];

function loadCredentials(): { client_email: string; private_key: string } {
  const raw = (process.env.GOOGLE_SERVICE_ACCOUNT_JSON || "").trim();
  try {
    return JSON.parse(raw);
  } catch {
    return JSON.parse(Buffer.from(raw, "base64").toString("utf-8"));
  }
}

async function getSheet(): Promise<GoogleSpreadsheetWorksheet> {
  const creds = loadCredentials();
  const jwt = new JWT({
    email: creds.client_email,
    key: creds.private_key,
    scopes: SCOPES,
  });
  const doc = new GoogleSpreadsheet(process.env.GOOGLE_SHEET_ID!, jwt);
  await doc.loadInfo();
  return doc.sheetsByIndex[0];
}

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

// google-spreadsheet row shape: .get(header) returns the cell string.
function rowToLink(row: { get: (key: string) => string }): Link {
  const tagsRaw = row.get("tags") || "";
  return {
    id: row.get("id") || "",
    url: row.get("url") || "",
    title: row.get("title") || null,
    description: row.get("description") || null,
    thumbnail: row.get("thumbnail") || null,
    type: row.get("type") || "other",
    tags: tagsRaw.split(",").map((t) => t.trim()).filter(Boolean),
    folder: row.get("folder") || null,
    status: row.get("status") || "unread",
    source: row.get("source") || "web",
    created_at: row.get("created_at") || "",
  };
}

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const tag = searchParams.get("tag");
  const status = searchParams.get("status");
  const folder = searchParams.get("folder");
  const search = searchParams.get("search")?.toLowerCase();
  const limit = parseInt(searchParams.get("limit") || "50");

  let sheet: GoogleSpreadsheetWorksheet;
  let rows;
  try {
    sheet = await getSheet();
    rows = await sheet.getRows();
  } catch (e) {
    // Empty sheet with no header row yet → no links saved.
    return NextResponse.json([]);
  }

  let links = rows.map(rowToLink);

  if (tag) links = links.filter((l) => l.tags.includes(tag));
  if (status) links = links.filter((l) => l.status === status);
  if (folder) links = links.filter((l) => l.folder === folder);
  if (search) {
    links = links.filter(
      (l) =>
        (l.title || "").toLowerCase().includes(search) ||
        (l.description || "").toLowerCase().includes(search)
    );
  }

  links.sort((a, b) => b.created_at.localeCompare(a.created_at));
  return NextResponse.json(links.slice(0, limit));
}

export async function PATCH(req: NextRequest) {
  const body = await req.json();
  const { id, status, folder } = body;

  if (!id) return NextResponse.json({ error: "id required" }, { status: 400 });
  if (status === undefined && folder === undefined) {
    return NextResponse.json({ error: "nothing to update" }, { status: 400 });
  }

  const sheet = await getSheet();
  const rows = await sheet.getRows();
  const row = rows.find((r) => r.get("id") === id);
  if (!row) return NextResponse.json({ error: "not found" }, { status: 404 });

  if (status !== undefined) row.set("status", status);
  if (folder !== undefined) row.set("folder", folder);
  await row.save();

  return NextResponse.json(rowToLink(row));
}

export async function DELETE(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");
  if (!id) return NextResponse.json({ error: "id required" }, { status: 400 });

  const sheet = await getSheet();
  const rows = await sheet.getRows();
  const row = rows.find((r) => r.get("id") === id);
  if (row) await row.delete();

  return NextResponse.json({ success: true });
}
