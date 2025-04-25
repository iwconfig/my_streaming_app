<!--
  Login page for user authentication.
  Implements login form and API integration with Flask backend.
-->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { auth } from '$lib/stores/auth';

  let username = '';
  let password = '';
  let loading = false;
  let error: string | null = null;

  const API_BASE = 'http://192.168.0.189:5000/api';

  async function handleLogin(event: Event) {
    event.preventDefault();
    error = null;
    loading = true;
    console.log('[Login] Attempting login request to:', `${API_BASE}/auth/login`);
    
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        mode: 'cors', // Enable CORS
        credentials: 'omit', // Don't send cookies for now
        body: JSON.stringify({ username, password })
      });
      
      console.log('[Login] Response status:', res.status);
      const data = await res.json();
      console.log('[Login] Response data:', { ...data, access_token: data.access_token ? 'present' : 'missing' });
      
      if (!res.ok) {
        error = data.message || 'Login failed.';
        console.error('[Login] Error response:', error);
      } else if (data.access_token) {
        console.log('[Login] Successfully received token');
        auth.login(data.access_token);
        console.log('[Login] Auth store updated, redirecting to /tracks');
        await goto('/tracks');
      } else {
        error = 'Unexpected response from server.';
        console.error('[Login] Unexpected response:', data);
      }
    } catch (e) {
      console.error('[Login] Network error details:', e);
      error = `Network error: ${e.message || 'Could not reach the server'}`;
    } finally {
      loading = false;
    }
  }
</script>

<h1 class="text-2xl font-bold mb-4">Login</h1>
<form class="space-y-4 max-w-sm" on:submit|preventDefault={handleLogin}>
  <input class="w-full p-2 border rounded" type="text" placeholder="Username" bind:value={username} required />
  <input class="w-full p-2 border rounded" type="password" placeholder="Password" bind:value={password} required />
  <button class="w-full bg-blue-600 text-white p-2 rounded disabled:opacity-50" type="submit" disabled={loading}>
    {loading ? 'Logging in...' : 'Login'}
  </button>
  {#if error}
    <div class="text-red-600 whitespace-pre-wrap">{error}</div>
  {/if}
</form>
