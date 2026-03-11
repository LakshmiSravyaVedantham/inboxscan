# inboxscan

Find every subscription hiding in your email. See exactly what you're paying for.

Zero credentials stored. Nothing leaves your machine.

## Install

```bash
pip install inboxscan
```

## Usage

```bash
# Scan one Gmail account
inboxscan run --email you@gmail.com

# Scan multiple accounts
inboxscan run --email work@gmail.com --email personal@gmail.com

# Get cancellation instructions
inboxscan cancel netflix
inboxscan cancel adobe

# Print version
inboxscan version
```

## Example output

```
INBOXSCAN REPORT
════════════════════════════════════════════════════════════
Scanned: personal@gmail.com, work@gmail.com
Found: 8 subscriptions  |  Total burn: $142.93/mo

 [ACTIVE]   Netflix          $15.99/mo   Mar 01   personal@gmail.com
 [ACTIVE]   Claude Pro       $20.00/mo   Mar 01   work@gmail.com
 [ACTIVE]   Adobe CC         $54.99/mo   Mar 03   work@gmail.com
 [ACTIVE]   GitHub Pro        $4.00/mo   Mar 05   work@gmail.com
 [ACTIVE]   Spotify          $10.99/mo   Mar 02   personal@gmail.com
 [DORMANT]  Audible          $14.95/mo   Nov 02   personal@gmail.com
 [DORMANT]  Skillshare        $9.99/mo   Oct 15   personal@gmail.com

════════════════════════════════════════════════════════════
Potential savings: $24.94/mo (cancel DORMANT subscriptions)

Run 'inboxscan cancel <service>' for cancellation steps.
```

## Gmail App Password

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Enable 2-Step Verification
3. Search "App passwords" → create one named "inboxscan"
4. Use that 16-character password when prompted

Your password is used only for the IMAP connection and is never stored.

## Privacy contract

- No credentials stored — app password used only during the scan session
- No network calls beyond Gmail IMAP fetch
- All processing happens locally on your machine
- Results cached in `~/.inboxscan/cache.db` (your machine only)
- Zero telemetry

## Detects 40+ services

Netflix, Spotify, Adobe CC, GitHub Pro, Figma, Notion, Linear, Slack, Zoom, Dropbox, Claude Pro, ChatGPT Plus, Amazon Prime, Apple One, Google One, Microsoft 365, Canva Pro, Audible, Skillshare, Duolingo Plus, Grammarly, 1Password, NordVPN, Hulu, Disney+, YouTube Premium, Cursor Pro, Vercel, Railway, Supabase, Sentry, Datadog, Cloudflare, and more.

## License

MIT
