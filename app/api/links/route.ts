import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const tag = searchParams.get("tag");
  const status = searchParams.get("status");
  const folder = searchParams.get("folder");
  const search = searchParams.get("search");
  const limit = parseInt(searchParams.get("limit") || "50");

  let query = supabase.from("links").select("*").order("created_at", { ascending: false }).limit(limit);

  if (tag) query = query.contains("tags", [tag]);
  if (status) query = query.eq("status", status);
  if (folder) query = query.eq("folder", folder);
  if (search) query = query.textSearch("fts", search);

  const { data, error } = await query;
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json(data);
}

export async function PATCH(req: NextRequest) {
  const body = await req.json();
  const { id, status, folder } = body;

  if (!id) return NextResponse.json({ error: "id required" }, { status: 400 });

  const update: Record<string, string> = {};
  if (status !== undefined) update.status = status;
  if (folder !== undefined) update.folder = folder;

  if (Object.keys(update).length === 0) {
    return NextResponse.json({ error: "nothing to update" }, { status: 400 });
  }

  const { data, error } = await supabase
    .from("links")
    .update(update)
    .eq("id", id)
    .select()
    .single();

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json(data);
}

export async function DELETE(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");

  if (!id) return NextResponse.json({ error: "id required" }, { status: 400 });

  const { error } = await supabase.from("links").delete().eq("id", id);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ success: true });
}
