import { createClient } from "@supabase/supabase-js";

const url =
  process.env.NEXT_PUBLIC_SUPABASE_URL || "https://zkjayklsmcqswtiadvja.supabase.co";
const key =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpramF5a2xzbWNxc3d0aWFkdmphIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODc3MTg0ODMsImV4cCI6MjEwMzI5NDQ4M30.dvnotsCJ4TCfHtcI9w12vkVXNgHGwpPV00mh_Tf6Bkg";

export function db() {
  return createClient(url, key, { auth: { persistSession: false } });
}
