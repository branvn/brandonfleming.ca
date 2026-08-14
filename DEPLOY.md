# Deploying brandonfleming.ca

Written assuming you've never used Git. Follow it top to bottom once; after that,
publishing is three commands.

Everything below runs in **PowerShell on Windows 11**. You do not need the
ThinkPad.

---

## 1. Install the two tools

Open PowerShell (press `Win`, type `powershell`, Enter) and run:

```powershell
winget install Hugo.Hugo.Extended
winget install Git.Git
```

**Close PowerShell and open a new one** — installers don't update the PATH of a
window that's already open. Then check both worked:

```powershell
hugo version
git --version
```

`hugo version` must say **extended**. If it doesn't, run
`winget uninstall Hugo.Hugo` and install `Hugo.Hugo.Extended` again.

---

## 2. See the site locally

```powershell
cd "$env:USERPROFILE\Desktop\brandonfleming.ca"
hugo server
```

Open <http://localhost:1313>. Leave it running — it rebuilds and refreshes the
moment you save a file. `Ctrl+C` stops it.

Use `hugo server -D` to also see pages marked `draft = true`.

> If `hugo server` reports an error, read the last line — it names the file and
> line number. That's almost always a typo in front matter (the `+++` block).

---

## 3. Tell Git who you are

One time only:

```powershell
git config --global user.name  "Brandon Fleming"
git config --global user.email "contact@brandonfleming.ca"
git config --global init.defaultBranch main
```

---

## 4. Make the first commit

```powershell
cd "$env:USERPROFILE\Desktop\brandonfleming.ca"
git init
git add .
git status
```

`git status` lists what will be saved. Confirm you do **not** see `public/`,
`resources/`, `_archive/`, or `_preview/` — `.gitignore` should be excluding
them. Then:

```powershell
git commit -m "Initial Hugo site"
```

---

## 5. Put it on GitHub

1. Create an account at <https://github.com> if you don't have one.
2. Click **+** (top right) → **New repository**.
3. Name it `brandonfleming.ca`. Choose **Public**.
4. **Do not** tick "Add a README", "Add .gitignore", or "Choose a license" —
   you already have those, and ticking them creates a conflict.
5. Click **Create repository**.

GitHub then shows a page of commands. Use the ones under *"…or push an existing
repository"* — they'll look like this, with your username:

```powershell
git remote add origin https://github.com/YOUR-USERNAME/brandonfleming.ca.git
git branch -M main
git push -u origin main
```

A browser window will open to authorise. Approve it. Refresh the GitHub page —
your files are there.

---

## 6. Connect Cloudflare Pages

1. Log in to <https://dash.cloudflare.com>.
2. Left sidebar → **Compute (Workers & Pages)** → **Create** → **Pages** tab →
   **Connect to Git**.
3. Authorise GitHub, pick `brandonfleming.ca`, click **Begin setup**.
4. Set the build configuration **exactly**:

   | Field | Value |
   |---|---|
   | Framework preset | `Hugo` |
   | Build command | `hugo --gc --minify` |
   | Build output directory | `public` |

5. Expand **Environment variables** and add one:

   | Variable | Value |
   |---|---|
   | `HUGO_VERSION` | `0.147.7` |

   This matters. Without it Cloudflare uses an ancient default Hugo and the
   build fails with confusing template errors.

6. **Save and Deploy.** First build takes about a minute. You'll get a URL like
   `brandonfleming-ca.pages.dev` — check the site works there before touching
   DNS.

---

## 7. Point the domain at it

Your domain is registered at Porkbun; Cloudflare needs to run its DNS.

**In Cloudflare:**

1. Top level → **Add a domain** → enter `brandonfleming.ca` → choose the **Free**
   plan.
2. Cloudflare shows two nameservers, e.g. `xxx.ns.cloudflare.com` and
   `yyy.ns.cloudflare.com`. Copy both.

**In Porkbun:**

3. **Domain Management** → `brandonfleming.ca` → **Authoritative Nameservers** →
   **Edit**.
4. Replace Porkbun's nameservers with the two from Cloudflare. Save.

> ⚠️ You already set up email forwarding for `contact@brandonfleming.ca`. If that
> was configured **at Porkbun**, moving nameservers will break it — you'll need
> to recreate it with Cloudflare Email Routing. If you set it up in **Cloudflare
> Email Routing** already, the MX records come along automatically and nothing
> breaks. Check which one before you switch, and send yourself a test message
> afterwards either way.

**Back in Cloudflare:**

5. Wait for the domain to show **Active** (usually under an hour, occasionally
   up to 24).
6. Go to your Pages project → **Custom domains** → **Set up a custom domain** →
   enter `brandonfleming.ca`. Repeat for `www.brandonfleming.ca`.

Cloudflare issues the HTTPS certificate automatically. Done.

---

## 8. Publishing from now on

Three commands, every time:

```powershell
git add .
git commit -m "Add thesis summary"
git push
```

Cloudflare rebuilds within a minute or two. Watch progress under your Pages
project → **Deployments**.

---

## 9. Turn on the Bill 44 tracker

The scaffolding is in place but switched off. When you have real entries:

1. Run it once locally to check the sources work:
   ```powershell
   pip install -r scripts\requirements.txt
   python scripts\track_bill44.py --dry-run
   ```
2. Run it for real (`python scripts\track_bill44.py`) — this writes candidates
   into `data\tracker.json` with an empty `note`.
3. Open `data\tracker.json`, delete the junk, and write a `note` for the items
   worth keeping. **Only entries with a note appear on the site.**
4. In `hugo.toml`, set `showTracker = true`.
5. Commit and push.

The GitHub Action in `.github/workflows/track-bill44.yml` then polls weekly on
its own. Nothing publishes without your note.

---

## Troubleshooting

**Cloudflare build fails, works locally.** Almost always `HUGO_VERSION`. Make
sure the environment variable is set and matches `hugo version` on your machine.

**Site loads but has no styling.** `baseURL` in `hugo.toml` must be
`https://brandonfleming.ca/` with the trailing slash.

**`git push` rejected.** Someone (probably the tracker Action) committed since
you last pulled. Run `git pull --rebase` then push again.

**Changed a file but the live site is stale.** Check GitHub actually received the
commit, then check Deployments in Cloudflare. If both look right, hard-refresh
(`Ctrl+Shift+R`).

**Want to take the site down temporarily.** Set `underConstruction = true` in
`hugo.toml`, commit, push. That puts a holding card over everything.
