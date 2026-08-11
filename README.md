# Siege Tournament Website

This is a browser website, not a mobile app.

Visitors open the public website URL and can view the live tournament. The administrator signs in through the website to enter scores and choose Attack/Defend-first. Firebase security rules prevent visitors from editing.

## Publish it
1. Create a Firebase project and Web App.
2. Enable Email/Password Authentication.
3. Create your admin account.
4. Copy `firebase-config.example.js` to `firebase-config.js` and add the Firebase Web App settings.
5. Put your admin Firebase UID into `firestore.rules`.
6. Deploy these files to any static website host (GitHub Pages, Netlify, Vercel, Cloudflare Pages, etc.).
7. Share the resulting `https://...` website URL.

The site is responsive and works on desktop and phones.
