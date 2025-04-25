import { redirect } from '@sveltejs/kit';
import type { LayoutLoad } from './$types';

export const load = (({ url }) => {
    // Always allow these paths
    const unprotectedPaths = ['/', '/login', '/register'];
    const path = url.pathname;

    // For protected routes, check auth in the client
    if (!unprotectedPaths.includes(path)) {
        return {
            url: url.pathname
        };
    }

    return {};
}) satisfies LayoutLoad;
