<!--
  Registration page for new user sign-up.
  Implements registration form and API integration with Flask backend.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { writable } from 'svelte/store';

  // State for form fields
  let username = '';
  let email = '';
  let password = '';
  let confirmPassword = '';
  let loading = false;
  let error: string | null = null;
  let success: string | null = null;

  // Backend API base URL (replace with your dev IP as needed)
  const API_BASE = 'http://192.168.0.189:5000/api';

  // Handle form submission
  async function handleRegister(event: Event) {
    event.preventDefault();
    error = null;
    success = null;

    // Basic validation
    if (!username || !email || !password) {
      error = 'All fields are required.';
      return;
    }
    if (password !== confirmPassword) {
      error = 'Passwords do not match.';
      return;
    }

    loading = true;
    try {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password })
      });
      const data = await res.json();
      if (!res.ok) {
        error = data.message || 'Registration failed.';
      } else {
        success = 'Registration successful! You can now log in.';
        setTimeout(() => goto('/login'), 1200);
      }
    } catch (e) {
      error = 'Network error.';
    } finally {
      loading = false;
    }
  }
</script>

<h1 class="text-2xl font-bold mb-4">Register</h1>
<form class="space-y-4 max-w-sm" on:submit|preventDefault={handleRegister}>
  <input class="w-full p-2 border rounded" type="text" placeholder="Username" bind:value={username} required />
  <input class="w-full p-2 border rounded" type="email" placeholder="Email" bind:value={email} required />
  <input class="w-full p-2 border rounded" type="password" placeholder="Password" bind:value={password} required />
  <input class="w-full p-2 border rounded" type="password" placeholder="Confirm Password" bind:value={confirmPassword} required />
  <button class="w-full bg-green-600 text-white p-2 rounded disabled:opacity-50" type="submit" disabled={loading}>
    {loading ? 'Registering...' : 'Register'}
  </button>
  {#if error}
    <div class="text-red-600">{error}</div>
  {/if}
  {#if success}
    <div class="text-green-600">{success}</div>
  {/if}
</form>
