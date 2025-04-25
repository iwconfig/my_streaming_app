<!--
  Modern player page for individual track playback.
  Large album art, bold info, big controls, custom progress bar, responsive layout.
-->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { goto } from '$app/navigation';
  import { loadHlsJs } from '$lib/hlsLoader';
  import { loadDashJs } from '$lib/dashLoader';
  import type Hls from 'hls.js';

  export let data;
  const { track } = data;

  const PLAYBACK_BASE = 'http://192.168.0.189:5000';
  let videoEl: HTMLVideoElement;
  let hls: Hls | null = null;
  let dashPlayer: any = null;
  let loading = true;
  let error: string | null = null;
  let debugInfo: string[] = [];
  let isPlaying = false;
  let currentTime = 0;
  let duration = 0;

  function addDebug(msg: string) {
    console.log(msg);
    debugInfo = [...debugInfo, msg];
  }

  function formatTime(sec: number) {
    if (!sec || isNaN(sec)) return '0:00';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  }

  function handlePlay() { isPlaying = true; }
  function handlePause() { isPlaying = false; }
  function handleTimeUpdate() { currentTime = videoEl?.currentTime || 0; }
  function handleLoadedMetadata() { duration = videoEl?.duration || 0; }
  function seek(e: MouseEvent) {
    if (!videoEl || !duration) return;
    const bar = e.currentTarget as HTMLElement;
    const rect = bar.getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    videoEl.currentTime = percent * duration;
  }

  async function initializePlayer() {
    if (!videoEl || !track?.manifest_url) {
      error = 'Missing video element or manifest URL';
      loading = false;
      return;
    }
    const url = `${PLAYBACK_BASE}${track.manifest_url}`;
    addDebug(`Initializing player for URL: ${url}`);
    try {
      if (track.manifest_type === 'HLS') {
        const Hls = await loadHlsJs();
        if (!Hls) {
          if (videoEl.canPlayType('application/vnd.apple.mpegurl')) {
            addDebug('Using native HLS support');
            videoEl.src = url;
            loading = false;
          } else {
            error = 'HLS playback is not supported in your browser';
            loading = false;
          }
          return;
        }
        addDebug('Creating new HLS.js instance');
        if (hls) hls.destroy();
        hls = new Hls({ debug: false });
        hls.on(Hls.Events.ERROR, (event, data) => {
          if (data.fatal) {
            error = 'Failed to play track. Please try again later.';
            hls?.destroy();
          }
        });
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          addDebug('HLS manifest parsed successfully');
          loading = false;
        });
        hls.loadSource(url);
        hls.attachMedia(videoEl);
      } else if (track.manifest_type === 'DASH') {
        addDebug('Loading dash.js...');
        const dashjs = await loadDashJs();
        if (!dashjs) {
          error = 'DASH.js is not supported in this browser';
          loading = false;
          return;
        }
        addDebug('Creating new dash.js player instance');
        if (dashPlayer) dashPlayer.reset();
        dashPlayer = dashjs.MediaPlayer().create();
        dashPlayer.on('error', (e: any) => {
          addDebug(`DASH.js error: ${JSON.stringify(e)}`);
          error = 'DASH playback error.';
        });
        dashPlayer.on('streamInitialized', () => {
          addDebug('DASH stream initialized');
          loading = false;
        });
        dashPlayer.initialize(videoEl, url, true);
      }
    } catch (e) {
      addDebug(`Player initialization error: ${e}`);
      error = 'Failed to initialize player';
      loading = false;
    }
  }

  onMount(() => {
    addDebug('Component mounted');
    if (!track) {
      goto('/tracks');
      return;
    }
    initializePlayer();
  });

  onDestroy(() => {
    if (hls) hls.destroy();
    if (dashPlayer) dashPlayer.reset();
  });
</script>

<div class="flex flex-col items-center justify-center min-h-[70vh]">
  <div class="w-full max-w-lg bg-slate-900 rounded-2xl shadow-2xl p-8 flex flex-col items-center gap-6">
    <button class="self-start text-blue-400 hover:text-blue-200 mb-2" on:click={() => goto('/tracks')}>
      ← Back to tracks
    </button>
    <!-- Album Art Placeholder -->
    <div class="w-48 h-48 rounded-xl bg-gradient-to-br from-blue-800 to-slate-700 flex items-center justify-center shadow-lg">
      <svg class="w-24 h-24 text-blue-300 opacity-70" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 19V6a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v13m-6 0h6"/></svg>
    </div>
    <div class="w-full flex flex-col items-center gap-1">
      <h1 class="text-2xl font-bold text-white truncate">{track.title}</h1>
      <div class="text-blue-200 text-lg font-medium truncate">{track.artist || 'Unknown Artist'}</div>
      <div class="text-slate-400 text-sm truncate">{track.album || 'Unknown Album'}</div>
      <div class="flex items-center gap-2 mt-2">
        <span class="px-2 py-0.5 rounded bg-slate-700 text-xs text-blue-300 font-mono uppercase">{track.manifest_type}</span>
        {#if track.status === 'READY'}
          <span class="inline-flex items-center px-2 py-0.5 rounded bg-green-600 text-xs font-semibold text-white">READY</span>
        {:else if track.status === 'PROCESSING'}
          <span class="inline-flex items-center px-2 py-0.5 rounded bg-amber-500 text-xs font-semibold text-white animate-pulse">PROCESSING</span>
        {:else if track.status === 'PENDING'}
          <span class="inline-flex items-center px-2 py-0.5 rounded bg-blue-500 text-xs font-semibold text-white">PENDING</span>
        {:else if track.status === 'ERROR'}
          <span class="inline-flex items-center px-2 py-0.5 rounded bg-red-600 text-xs font-semibold text-white">ERROR</span>
        {/if}
      </div>
    </div>
    <!-- Custom Progress Bar & Controls -->
    <div class="w-full flex flex-col gap-2 items-center">
      <video
        bind:this={videoEl}
        class="w-full rounded-lg bg-black shadow"
        style="max-height: 220px;"
        controls
        preload="auto"
        crossorigin="anonymous"
        on:play={handlePlay}
        on:pause={handlePause}
        on:timeupdate={handleTimeUpdate}
        on:loadedmetadata={handleLoadedMetadata}
      ></video>
      <div class="w-full flex items-center gap-3 mt-2">
        <span class="text-xs text-slate-300 w-10 text-right">{formatTime(currentTime)}</span>
        <div class="flex-1 h-2 bg-slate-700 rounded-full cursor-pointer relative group" on:click={seek}>
          <div class="absolute top-0 left-0 h-2 bg-blue-400 rounded-full transition-all" style={`width: ${(duration ? (currentTime/duration)*100 : 0)}%`}></div>
        </div>
        <span class="text-xs text-slate-300 w-10">{formatTime(duration)}</span>
      </div>
    </div>
    {#if error}
      <div class="w-full p-3 bg-red-50 text-red-600 text-sm rounded mt-2">{error}</div>
    {/if}
    {#if debugInfo.length > 0}
      <div class="w-full mt-4 p-3 bg-slate-800 rounded text-xs font-mono overflow-auto max-h-32">
        <div class="font-semibold mb-2 text-blue-300">Debug Log:</div>
        {#each debugInfo as msg}
          <div class="whitespace-pre-wrap">{msg}</div>
        {/each}
      </div>
    {/if}
  </div>
</div>
