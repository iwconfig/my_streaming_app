import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { browser } from '$app/environment';

// Disable SSR for player page to avoid media-related errors
export const ssr = false;

interface Track {
    id: number;
    title: string;
    artist: string | null;
    album: string | null;
    status: 'PENDING' | 'PROCESSING' | 'READY' | 'ERROR';
    manifest_url: string | null;
    manifest_type: 'HLS' | 'DASH' | null;
}

export const load = (async ({ params }) => {
    if (!browser) return { track: null };
    
    console.log('[Player] Loading track:', params.id);
    const token = localStorage.getItem('jwt_token');
    if (!token) {
        throw error(401, 'Please log in to access this content');
    }

    try {
        const res = await fetch(`http://192.168.0.189:5000/api/tracks/${params.id}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        console.log('[Player] Response status:', res.status);
        
        if (!res.ok) {
            if (res.status === 401) {
                localStorage.removeItem('jwt_token');
                throw error(401, 'Session expired. Please log in again');
            }
            throw error(res.status, 'Failed to load track');
        }

        const track: Track = await res.json();
        console.log('[Player] Track data:', track);
        
        if (!track) {
            throw error(404, 'Track not found');
        }

        if (track.status !== 'READY') {
            throw error(400, 'This track is not ready for playback');
        }

        if (!track.manifest_url || !track.manifest_type) {
            throw error(400, 'Track is missing playback information');
        }

        return { track };
    } catch (e) {
        console.error('[Player] Error loading track:', e);
        throw error(500, 'Failed to load track');
    }
}) satisfies PageLoad;
