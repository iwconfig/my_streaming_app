<!--
  Track list page for displaying user's tracks.
  Modern card grid layout, album art, status badges, and floating upload button.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { goto } from '$app/navigation';

  const API_BASE = 'http://192.168.0.189:5000/api';

  interface Track {
    id: number;
    title: string;
    artist: string | null;
    album: string | null;
    status: 'PENDING' | 'PROCESSING' | 'READY' | 'ERROR';
    manifest_url: string | null;
    manifest_type: 'HLS' | 'DASH' | null;
  }

  let tracks: Track[] = [];
  let loading = true;
  let error: string | null = null;

  async function fetchTracks() {
    if (!browser) return;
    loading = true;
    error = null;
    const token = localStorage.getItem('jwt_token');
    try {
      const res = await fetch(`${API_BASE}/tracks`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) {
        if (res.status === 401) {
          localStorage.removeItem('jwt_token');
          goto('/login');
          return;
        }
        error = 'Failed to fetch tracks.';
        tracks = [];
        return;
      }
      const data = await res.json();
      tracks = (Array.isArray(data) ? data : data.tracks || [])
        .map((track: any): Track => ({
          id: track.id,
          title: track.title || 'Untitled',
          artist: track.artist,
          album: track.album,
          status: track.status,
          manifest_url: track.manifest_url,
          manifest_type: track.manifest_type
        }));
    } catch (e) {
      error = 'Network error. Please try again later.';
      tracks = [];
    } finally {
      loading = false;
    }
  }

  function playTrack(track: Track) {
    goto(`/player/${track.id}`);
  }

  onMount(() => {
    fetchTracks();
  });
</script>

<div class="flex justify-between items-center mb-8">
  <h1 class="text-3xl font-extrabold tracking-tight text-white">Your Tracks</h1>
  <button
    class="hidden md:inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold shadow transition"
    on:click={() => goto('/upload')}
  >
    <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
    Upload
  </button>
</div>

{#if loading}
  <div class="flex items-center justify-center p-8">
    <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-400"></div>
  </div>
{:else if error}
  <div class="bg-red-50 border border-red-200 text-red-600 rounded p-4">
    {error}
  </div>
{:else if tracks.length === 0}
  <div class="text-gray-400 text-center py-16 text-lg">
    No tracks found. Try uploading some music!
  </div>
{:else}
  <div class="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
    {#each tracks as track (track.id)}
      <div class="bg-slate-800 rounded-xl shadow-lg p-5 flex flex-col gap-3 hover:shadow-2xl transition group relative">
        <!-- Album Art Placeholder -->
        <div class="w-full aspect-square bg-gradient-to-br from-blue-900 to-slate-700 rounded-lg flex items-center justify-center mb-2">
          <svg class="w-16 h-16 text-blue-400 opacity-60" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 19V6a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v13m-6 0h6"/></svg>
        </div>
        <div class="flex flex-col gap-1">
          <div class="font-bold text-lg text-white truncate" title={track.title}>{track.title}</div>
          <div class="text-sm text-blue-200 truncate">{track.artist || 'Unknown Artist'}</div>
          <div class="text-xs text-slate-400 truncate">{track.album || 'Unknown Album'}</div>
        </div>
        <div class="flex items-center gap-2 mt-2">
          {#if track.status === 'READY'}
            <span class="inline-flex items-center px-2 py-0.5 rounded bg-green-600 text-xs font-semibold text-white">READY</span>
          {:else if track.status === 'PROCESSING'}
            <span class="inline-flex items-center px-2 py-0.5 rounded bg-amber-500 text-xs font-semibold text-white animate-pulse">PROCESSING</span>
          {:else if track.status === 'PENDING'}
            <span class="inline-flex items-center px-2 py-0.5 rounded bg-blue-500 text-xs font-semibold text-white">PENDING</span>
          {:else if track.status === 'ERROR'}
            <span class="inline-flex items-center px-2 py-0.5 rounded bg-red-600 text-xs font-semibold text-white">ERROR</span>
          {/if}
          {#if track.manifest_type}
            <span class="ml-auto px-2 py-0.5 rounded bg-slate-700 text-xs text-blue-300 font-mono uppercase">{track.manifest_type}</span>
          {/if}
        </div>
        <button
          class="mt-4 w-full py-2 rounded-lg bg-blue-500 hover:bg-blue-600 text-white font-bold shadow transition group-hover:scale-105"
          on:click={() => playTrack(track)}
          disabled={track.status !== 'READY'}
        >
          {track.status === 'READY' ? 'Play' : 'Not Ready'}
        </button>
      </div>
    {/each}
  </div>
{/if}

<!-- Floating Upload Button (Mobile) -->
<button
  class="fixed bottom-6 right-6 z-40 md:hidden flex items-center gap-2 px-5 py-3 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-bold shadow-lg text-lg transition"
  on:click={() => goto('/upload')}
  aria-label="Upload"
>
  <svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
  Upload
</button>
