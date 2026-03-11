import re
from datetime import date, timedelta
from typing import Optional

from inboxscan.models import ParsedEmail, Subscription, SubscriptionStatus

KNOWN_SERVICES: dict[str, tuple[str, str, str]] = {
    "netflix.com": ("Netflix", "https://www.netflix.com/cancelplan", "monthly"),
    "spotify.com": ("Spotify", "https://www.spotify.com/account/subscription/cancel", "monthly"),
    "notion.so": ("Notion", "https://www.notion.so/profile/billing", "monthly"),
    "adobe.com": ("Adobe CC", "https://account.adobe.com/plans", "monthly"),
    "github.com": ("GitHub Pro", "https://github.com/settings/billing", "monthly"),
    "figma.com": ("Figma", "https://www.figma.com/settings#billing", "monthly"),
    "linear.app": ("Linear", "https://linear.app/settings/billing", "monthly"),
    "slack.com": ("Slack", "https://slack.com/intl/en-us/help/articles/203875027", "monthly"),
    "zoom.us": ("Zoom", "https://zoom.us/billing", "monthly"),
    "dropbox.com": ("Dropbox", "https://www.dropbox.com/account/plan", "monthly"),
    "atlassian.com": ("Atlassian", "https://admin.atlassian.com/", "monthly"),
    "anthropic.com": ("Claude Pro", "https://claude.ai/settings", "monthly"),
    "openai.com": ("ChatGPT Plus", "https://chat.openai.com/account/billing", "monthly"),
    "amazon.com": ("Amazon Prime", "https://www.amazon.com/manageprime", "annual"),
    "apple.com": ("Apple One", "https://appleid.apple.com/account/manage", "monthly"),
    "google.com": ("Google One", "https://one.google.com/about", "monthly"),
    "microsoft.com": ("Microsoft 365", "https://account.microsoft.com/services", "annual"),
    "canva.com": ("Canva Pro", "https://www.canva.com/settings/billing", "monthly"),
    "audible.com": ("Audible", "https://www.audible.com/account/optout", "monthly"),
    "skillshare.com": ("Skillshare", "https://www.skillshare.com/settings/membership", "annual"),
    "duolingo.com": ("Duolingo Plus", "https://www.duolingo.com/settings/subscription", "monthly"),
    "grammarly.com": ("Grammarly", "https://account.grammarly.com/subscription", "monthly"),
    "1password.com": ("1Password", "https://my.1password.com/", "annual"),
    "dashlane.com": ("Dashlane", "https://app.dashlane.com/settings/subscription", "annual"),
    "nordvpn.com": ("NordVPN", "https://my.nordaccount.com/dashboard/nordvpn/", "annual"),
    "expressvpn.com": ("ExpressVPN", "https://www.expressvpn.com/subscriptions", "annual"),
    "hulu.com": ("Hulu", "https://secure.hulu.com/account/cancel", "monthly"),
    "disneyplus.com": ("Disney+", "https://www.disneyplus.com/account/subscription", "monthly"),
    "youtube.com": ("YouTube Premium", "https://www.youtube.com/paid_memberships", "monthly"),
    "cursor.sh": ("Cursor Pro", "https://cursor.sh/settings", "monthly"),
    "vercel.com": ("Vercel Pro", "https://vercel.com/account/billing", "monthly"),
    "render.com": ("Render", "https://dashboard.render.com/billing", "monthly"),
    "railway.app": ("Railway", "https://railway.app/account/billing", "monthly"),
    "supabase.com": ("Supabase", "https://supabase.com/dashboard/account/billing", "monthly"),
    "datadog.com": ("Datadog", "https://app.datadoghq.com/billing/plan", "monthly"),
    "sentry.io": ("Sentry", "https://sentry.io/settings/billing/", "monthly"),
    "cloudflare.com": ("Cloudflare", "https://dash.cloudflare.com/profile/billing", "monthly"),
    "twilio.com": ("Twilio", "https://console.twilio.com/billing", "monthly"),
    "mailchimp.com": ("Mailchimp", "https://us1.admin.mailchimp.com/account/billing/", "monthly"),
}

DORMANT_THRESHOLD_DAYS = 90


def _extract_sender_domain(sender: str) -> str:
    match = re.search(r"@([\w.]+)", sender)
    return match.group(1).lower() if match else ""


def detect_service(parsed_email: ParsedEmail) -> Optional[Subscription]:
    domain = _extract_sender_domain(parsed_email.sender)
    for service_domain, (name, cancel_url, frequency) in KNOWN_SERVICES.items():
        if domain.endswith(service_domain):
            if parsed_email.amount is None:
                return None
            return Subscription(
                service_name=name,
                amount=parsed_email.amount,
                currency=parsed_email.currency,
                billing_frequency=frequency,
                last_charge_date=parsed_email.date,
                source_email="",
                status=classify_status(parsed_email.date),
                cancellation_url=cancel_url,
            )
    return None


def classify_status(last_charge_date: date) -> SubscriptionStatus:
    days_since = (date.today() - last_charge_date).days
    if days_since <= DORMANT_THRESHOLD_DAYS:
        return SubscriptionStatus.ACTIVE
    return SubscriptionStatus.DORMANT
