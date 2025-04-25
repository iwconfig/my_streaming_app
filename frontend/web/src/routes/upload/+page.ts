import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { browser } from '$app/environment';

export const load = (() => {
    if (browser) {
        const token = localStorage.getItem('jwt_token');
        if (!token) {
            throw redirect(302, '/login');
        }
    }
}) satisfies PageLoad;
