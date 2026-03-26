import { createClient } from "https://esm.sh/@supabase/supabase-js@2?bundle";
import {
  SUPABASE_AUTH_ENABLED,
  SUPABASE_AUTH_REDIRECT_TO,
  SUPABASE_PUBLISHABLE_KEY,
  SUPABASE_URL
} from "./runtime-config.js";

let supabaseClient = null;

export function isSupabaseConfigured() {
  return SUPABASE_AUTH_ENABLED;
}

export function getSupabaseClient() {
  if (!SUPABASE_AUTH_ENABLED) return null;
  if (!supabaseClient) {
    supabaseClient = createClient(
      SUPABASE_URL,
      SUPABASE_PUBLISHABLE_KEY,
      {
        auth: {
          autoRefreshToken: true,
          persistSession: true,
          detectSessionInUrl: true
        }
      }
    );
  }
  return supabaseClient;
}

export async function getCurrentSession() {
  const client = getSupabaseClient();
  if (!client) return null;
  const { data, error } = await client.auth.getSession();
  if (error) throw error;
  return data.session || null;
}

export async function getAccessToken() {
  const session = await getCurrentSession();
  return session ? session.access_token : null;
}

export async function signInWithPassword(email, password) {
  const client = getSupabaseClient();
  if (!client) {
    throw new Error("Supabase auth is not configured.");
  }
  const { data, error } = await client.auth.signInWithPassword({
    email,
    password
  });
  if (error) throw error;
  return data;
}

export async function signUpWithPassword(email, password) {
  const client = getSupabaseClient();
  if (!client) {
    throw new Error("Supabase auth is not configured.");
  }
  const { data, error } = await client.auth.signUp({
    email,
    password,
    options: {
      emailRedirectTo: SUPABASE_AUTH_REDIRECT_TO || undefined
    }
  });
  if (error) throw error;
  return data;
}

export async function signOut() {
  const client = getSupabaseClient();
  if (!client) return;
  const { error } = await client.auth.signOut();
  if (error) throw error;
}

export function onAuthStateChange(callback) {
  const client = getSupabaseClient();
  if (!client) {
    return () => {};
  }
  const { data } = client.auth.onAuthStateChange((event, session) => {
    callback(event, session);
  });
  return () => {
    data.subscription.unsubscribe();
  };
}
