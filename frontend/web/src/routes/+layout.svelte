<!--
  Main layout for the app. Provides navigation between core pages.
  Uses Tailwind CSS for styling.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { goto } from '$app/navigation';
  import { auth } from '$lib/stores/auth';
  import { page } from '$app/stores';

  onMount(() => {
    auth.initialize();
  });

  // Simple logout that uses our auth store
  function logout() {
    auth.logout();
    goto('/login');
  }
</script>

<div class="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-700 text-gray-100 font-sans">
  <!-- Sticky Header -->
  <header class="sticky top-0 z-30 bg-slate-900/80 backdrop-blur border-b border-slate-800 shadow flex items-center justify-between px-6 py-3">
    <div class="flex items-center gap-3">
      <span class="text-2xl font-bold tracking-tight text-blue-400">MyStreamingApp</span>
    </div>
    <nav class="flex items-center gap-6 text-sm font-medium">
      <a href="/tracks" class="hover:text-blue-400 transition">Tracks</a>
      <a href="/upload" class="hover:text-blue-400 transition">Upload</a>
      <button class="ml-4 px-3 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white font-semibold" on:click={() => { localStorage.removeItem('jwt_token'); goto('/login'); }}>Logout</button>
    </nav>
  </header>

  <!-- Main Content -->
  <main class="container mx-auto px-4 py-8 max-w-4xl">
    <slot />
  </main>
</div>
