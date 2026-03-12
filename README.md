# inboxscan

Find every subscription hiding in your email. See exactly what you're paying for.

Zero credentials stored. Nothing leaves your machine.

## Install

```bash
pip install inboxscan

# For the macOS menu bar app
pip install "inboxscan[menubar]"
```

---

## Quick Start — Gmail with App Password (easiest)

No OAuth setup needed. Works with Gmail and Google Workspace.

**Step 1 — Create a Gmail App Password**

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Enable **2-Step Verification** if not already on
3. Search for **"App passwords"** → create one named `inboxscan`
4. Copy the 16-character password

**Step 2 — Scan**

```bash
inboxscan run --email you@gmail.com --password xxxxxxxxxxxxxxxxxxxx
```

That's it. No accounts to connect, no browser flow.

---

## Gmail OAuth (connect once, scan anytime)

If you want to scan without entering a password every time, use OAuth.

**Step 1 — Create a Google Cloud project**

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (name it anything, e.g. `inboxscan`)
3. Go to **APIs & Services → Enable APIs** → enable **Gmail API**

**Step 2 — Create OAuth credentials**

1. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**
2. Application type: **Desktop app**
3. Name it `inboxscan`
4. Copy the **Client ID** and **Client Secret**

**Step 3 — Configure OAuth consent screen**

1. Go to **APIs & Services → OAuth consent screen**
2. User type: **External**
3. Fill in app name, support email, developer email → Save
4. Scopes: skip (handled automatically)
5. **Test users**: add your Gmail address(es) here — required while app is in Testing status

**Step 4 — Set environment variables**

```bash
export INBOXSCAN_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export INBOXSCAN_CLIENT_SECRET="your-client-secret"
```

Add these to your `~/.zshrc` or `~/.bashrc` to persist across sessions.

**Step 5 — Connect your account**

```bash
inboxscan auth add
# Browser opens → sign in → done

# Add a second account
inboxscan auth add

# List connected accounts
inboxscan auth list
```

> **Note:** Google will show an "unverified app" warning. Click **Advanced → Go to inboxscan (unsafe)** to proceed. This is expected for self-hosted OAuth apps.

**Step 6 — Scan**

```bash
inboxscan run
```

---

## Other Email Providers

inboxscan auto-detects the IMAP server from your email domain.

```bash
# Outlook / Hotmail
inboxscan run --email you@outlook.com --password <app-password>

# Yahoo
inboxscan run --email you@yahoo.com --password <app-password>

# iCloud
inboxscan run --email you@icloud.com --password <app-specific-password>

# Fastmail
inboxscan run --email you@fastmail.com --password <app-password>

# ProtonMail (requires Bridge running)
inboxscan run --email you@proton.me --password <bridge-password>

# Custom IMAP server
inboxscan run --email you@company.com --imap-host mail.company.com --password <password>
```

---

## macOS Menu Bar App

```bash
pip install "inboxscan[menubar]"
inboxscan-menubar
```

Shows your subscription burn rate in the menu bar. Click any subscription to see:
- 🟢 Active / 🟠 Dormant / 🟡 Trial / 🔴 Cancelled
- Started date, next renewal date, trial end date
- Which email account it was found on
- Direct link to cancel

---

## Commands

```bash
inboxscan run                          # Scan all connected accounts
inboxscan run --email you@gmail.com    # Scan specific account
inboxscan auth add                     # Connect a Gmail account (OAuth)
inboxscan auth list                    # List connected accounts
inboxscan auth remove you@gmail.com    # Remove an account
inboxscan cancel netflix               # Get cancellation steps
inboxscan version                      # Print version
```

---

## Example Output

```
INBOXSCAN REPORT
════════════════════════════════════════════════════════════
Scanned: personal@gmail.com, work@gmail.com
Found: 8 subscriptions  |  Total burn: $142.93/mo

 [ACTIVE]   Netflix       $15.99/mo   Jan 2025   Mar 15, 2026
 [ACTIVE]   Claude Pro    $20.00/mo   Feb 2025   Mar 18, 2026
 [ACTIVE]   Adobe CC      $54.99/mo   Jan 2025   Mar 20, 2026
 [DORMANT]  Audible       $14.95/mo   Jun 2024   Oct 02, 2024
 [DORMANT]  Skillshare     $9.99/mo   May 2024   Sep 15, 2024

════════════════════════════════════════════════════════════
Potential savings: $24.94/mo (cancel DORMANT subscriptions)
```

---

## Privacy

- No credentials stored — app password used only during scan session
- OAuth tokens stored locally in `~/.inboxscan/tokens/` (your machine only)
- No network calls beyond your email provider's IMAP server
- All processing happens locally
- Results cached in `~/.inboxscan/cache.db` (your machine only)
- Zero telemetry

---

## Detects 40+ services

Netflix, Spotify, Adobe CC, GitHub Pro, Figma, Notion, Linear, Slack, Zoom, Dropbox, Claude Pro, ChatGPT Plus, Amazon Prime, Apple One, Google One, Microsoft 365, Canva Pro, Audible, Skillshare, Duolingo Plus, Grammarly, 1Password, NordVPN, Hulu, Disney+, YouTube Premium, Cursor Pro, Vercel, Railway, Supabase, Sentry, Datadog, Cloudflare, Replicate, xAI Grok, Suno, Windsurf, and more.

---

## License

MIT
