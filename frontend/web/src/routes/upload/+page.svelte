<!--
  Modern upload page: card layout, drag-and-drop, styled form, responsive.
-->
<script lang="ts">
  import { browser } from '$app/environment';
  import { goto } from '$app/navigation';

  const API_BASE = 'http://192.168.0.189:5000/api';

  let file: File | null = null;
  let title = '';
  let artist = '';
  let album = '';
  let track_number = '';
  let output_format = 'hls';
  let loading = false;
  let error: string | null = null;
  let success: string | null = null;
  let dragActive = false;
  let uploadProgress = 0;

  function handleFileChange(e: Event) {
    const input = e.target as HTMLInputElement;
    file = input.files && input.files[0] ? input.files[0] : null;
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    dragActive = false;
    if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
      file = e.dataTransfer.files[0];
    }
  }

  function handleDragOver(e: DragEvent) {
    e.preventDefault();
    dragActive = true;
  }
  function handleDragLeave(e: DragEvent) {
    e.preventDefault();
    dragActive = false;
  }

  async function handleUpload(event: Event) {
    event.preventDefault();
    if (!browser) return;
    error = null;
    success = null;
    uploadProgress = 0;
    if (!file || !title || !artist || !album || !track_number) {
      error = 'All fields are required.';
      return;
    }
    loading = true;
    const token = localStorage.getItem('jwt_token');
    try {
      const formData = new FormData();
      formData.append('audio_file', file);
      formData.append('title', title);
      formData.append('artist', artist);
      formData.append('album', album);
      formData.append('track_number', track_number);
      formData.append('output_format', output_format.toUpperCase());
      // Use XMLHttpRequest for progress
      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', `${API_BASE}/tracks/upload`);
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) {
            uploadProgress = Math.round((e.loaded / e.total) * 100);
          }
        };
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            success = 'Upload successful! Track will appear when processed.';
            setTimeout(() => goto('/tracks'), 1500);
            resolve();
          } else {
            try {
              const data = JSON.parse(xhr.responseText);
              error = data.message || 'Upload failed.';
            } catch {
              error = 'Upload failed.';
            }
            reject();
          }
        };
        xhr.onerror = () => {
          error = 'Network error.';
          reject();
        };
        xhr.send(formData);
      });
    } catch (e) {
      error = 'Network error.';
    } finally {
      loading = false;
    }
  }
</script>

<div class="flex flex-col items-center justify-center min-h-[70vh]">
  <div class="w-full max-w-md bg-slate-900 rounded-2xl shadow-2xl p-8 flex flex-col gap-6">
    <h1 class="text-2xl font-extrabold text-white mb-2 text-center">Upload New Track</h1>
    <!-- Drag-and-drop area -->
    <div
      class="w-full h-32 flex flex-col items-center justify-center border-2 border-dashed rounded-xl transition bg-slate-800 hover:border-blue-400 cursor-pointer mb-2 relative"
      class:bg-blue-900/30={dragActive}
      on:dragover={handleDragOver}
      on:dragleave={handleDragLeave}
      on:drop={handleDrop}
      on:click={() => document.getElementById('fileInput')?.click()}
    >
      <svg class="w-10 h-10 text-blue-400 mb-2" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
      <span class="text-blue-200">{file ? file.name : 'Drag & drop audio file or click to select'}</span>
      <input id="fileInput" class="hidden" type="file" accept="audio/*" on:change={handleFileChange} />
    </div>
    <form class="flex flex-col gap-4" on:submit|preventDefault={handleUpload}>
      <input class="w-full p-3 rounded-lg bg-slate-800 text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-400" type="text" placeholder="Title" bind:value={title} required />
      <input class="w-full p-3 rounded-lg bg-slate-800 text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-400" type="text" placeholder="Artist" bind:value={artist} required />
      <input class="w-full p-3 rounded-lg bg-slate-800 text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-400" type="text" placeholder="Album" bind:value={album} required />
      <input class="w-full p-3 rounded-lg bg-slate-800 text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-400" type="number" placeholder="Track Number" bind:value={track_number} required />
      <select class="w-full p-3 rounded-lg bg-slate-800 text-white focus:outline-none focus:ring-2 focus:ring-blue-400" bind:value={output_format} required>
        <option value="hls">HLS</option>
        <option value="dash">DASH</option>
      </select>
      <button class="w-full py-3 rounded-lg bg-green-600 hover:bg-green-700 text-white font-bold shadow transition disabled:opacity-50" type="submit" disabled={loading}>
        {loading ? 'Uploading...' : 'Upload'}
      </button>
      {#if uploadProgress > 0 && loading}
        <div class="w-full bg-slate-700 rounded-full h-2 mt-2 overflow-hidden">
          <div class="bg-blue-400 h-2 rounded-full transition-all" style={`width: ${uploadProgress}%`}></div>
        </div>
      {/if}
      {#if error}
        <div class="w-full p-2 bg-red-50 text-red-600 text-sm rounded mt-2">{error}</div>
      {/if}
      {#if success}
        <div class="w-full p-2 bg-green-50 text-green-700 text-sm rounded mt-2">{success}</div>
      {/if}
    </form>
  </div>
</div>
