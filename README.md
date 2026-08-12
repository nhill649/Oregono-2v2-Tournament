# Oregano 2v2 Tournament

Live Rainbow Six Siege tournament website for Memphis & Sam, Preston & Roman, Eli & Sanath, and Nolan & Xavier.

## Format
- 4 pool-play matches; each team plays exactly 2 matches and no matchup repeats.
- Pool results seed a 4-team double-elimination bracket.
- Higher seed chooses Attack or Defend first in bracket matches.
- Oregon 2nd Floor; first to 4 round wins; 3 overtime rounds.
- Rules: no roaming, no shields, no tracking operators, no team-killing.
- Tiebreakers: round differential -> score against common opponent -> strength of pool-play schedule.

## Make it live
The repository includes a GitHub Pages deployment workflow. The site uses Firebase Firestore for shared live state and Firebase Authentication for the tournament admin.

1. Create a Firebase project.
2. Add a Firebase Web App.
3. Enable Authentication -> Email/Password.
4. Create the tournament admin user.
5. Enable Firestore Database.
6. Copy `firebase-config.example.js` to `firebase-config.js` locally and paste the Web App config values into it.
7. Replace the placeholder admin UID in `firestore.rules` with the admin user's UID, then deploy those rules from Firebase.
8. In GitHub, open **Settings -> Pages** and choose **GitHub Actions** as the source. The included workflow will publish the site after the next push.
9. Share the GitHub Pages URL. Everyone sees the same Firestore-backed live state; only the admin can change scores or Attack/Defend-first choices.

The GitHub Pages workflow is `.github/workflows/pages.yml`.
