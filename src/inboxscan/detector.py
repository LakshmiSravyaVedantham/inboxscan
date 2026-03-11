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
    "replicate.com": ("Replicate", "https://replicate.com/account/billing", "monthly"),
    "x.ai": ("xAI Grok", "https://x.ai/account", "monthly"),
    "soundcloud.com": ("SoundCloud", "https://soundcloud.com/settings/subscription", "monthly"),
    "codeium.com": ("Windsurf", "https://windsurf.com/account/billing", "monthly"),
    "suno.com": ("Suno", "https://suno.com/account", "monthly"),
    "suno.ai": ("Suno", "https://suno.com/account", "monthly"),
}

# Payment processors that send receipts on behalf of other services.
# Maps keyword found in email body/subject -> (display name, cancel URL, frequency)
PAYMENT_PROCESSOR_DOMAINS = {"stripe.com", "paypal.com"}

STRIPE_SERVICE_KEYWORDS: dict[str, tuple[str, str, str]] = {
    "xai": ("xAI Grok", "https://x.ai/account", "monthly"),
    "x.ai": ("xAI Grok", "https://x.ai/account", "monthly"),
    "cursor": ("Cursor Pro", "https://cursor.sh/settings", "monthly"),
    "linear": ("Linear", "https://linear.app/settings/billing", "monthly"),
    "vercel": ("Vercel Pro", "https://vercel.com/account/billing", "monthly"),
    "railway": ("Railway", "https://railway.app/account/billing", "monthly"),
    "supabase": ("Supabase", "https://supabase.com/dashboard/account/billing", "monthly"),
    "replicate": ("Replicate", "https://replicate.com/account/billing", "monthly"),
    "sentry": ("Sentry", "https://sentry.io/settings/billing/", "monthly"),
    "render": ("Render", "https://dashboard.render.com/billing", "monthly"),
    "github": ("GitHub Pro", "https://github.com/settings/billing", "monthly"),
    "notion": ("Notion", "https://www.notion.so/profile/billing", "monthly"),
    "figma": ("Figma", "https://www.figma.com/settings#billing", "monthly"),
    "anthropic": ("Claude Pro", "https://claude.ai/settings", "monthly"),
    "openai": ("ChatGPT Plus", "https://chat.openai.com/account/billing", "monthly"),
    "google": ("Google One", "https://one.google.com/about", "monthly"),
}

# Merchants known to be transactional (not subscriptions), filter even if recurring
TRANSACTIONAL_MERCHANTS = {
    "uber", "ubereats", "uber eats", "lyft", "instacart", "doordash",
    "grubhub", "postmates", "temu", "amazon", "ebay", "etsy",
    "cineplex", "fandango", "ticketmaster",
}


def _resolve_payment_processor(body: str, subject: str) -> Optional[tuple[str, str, str]]:
    """If email is from a payment processor, identify the real service.

    For PayPal: extracts the merchant name from "Receipt for Your Payment to X"
    For Stripe: matches known service keywords in the subject line only
    """
    # PayPal subjects say exactly who was paid
    paypal_match = re.search(r"payment to (.+?)(?:\.|$)", subject, re.IGNORECASE)
    if paypal_match:
        merchant = paypal_match.group(1).strip()
        # Check if it's a known service
        merchant_lower = merchant.lower()
        for keyword, service_info in STRIPE_SERVICE_KEYWORDS.items():
            if keyword in merchant_lower:
                return service_info
        # Unknown merchant — return it as-is with no cancel URL
        return (merchant, None, "monthly")

    # Stripe subjects say "Your receipt from COMPANY NAME #XXXX-XXXX"
    stripe_match = re.search(r"your receipt from (.+?)(?:\s+#[\d-]+)?$", subject, re.IGNORECASE)
    if stripe_match:
        merchant = stripe_match.group(1).strip()
        merchant_lower = merchant.lower()
        for keyword, service_info in STRIPE_SERVICE_KEYWORDS.items():
            if keyword in merchant_lower:
                return service_info
        # Unknown Stripe merchant — return as-is
        return (merchant, None, "monthly")

    return None


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


def detect_from_batch(emails: list[ParsedEmail]) -> list[Subscription]:
    """
    Detect subscriptions from a batch of emails by grouping by sender domain.
    Any domain that appears 2+ times with a charge amount is treated as a
    recurring subscription — even if not in KNOWN_SERVICES.
    Returns one Subscription per domain (most recent charge).
    """
    from collections import defaultdict

    # Group emails by sender domain, keep only those with amounts
    by_domain: dict[str, list[ParsedEmail]] = defaultdict(list)
    for email in emails:
        if email.amount is not None:
            domain = _extract_sender_domain(email.sender)
            if domain:
                by_domain[domain].append(email)

    subscriptions = []
    for domain, domain_emails in by_domain.items():
        # Check known services first
        known_match = None
        for service_domain, (name, cancel_url, frequency) in KNOWN_SERVICES.items():
            if domain.endswith(service_domain):
                known_match = (name, cancel_url, frequency)
                break

        # Sort by date, take most recent
        domain_emails.sort(key=lambda e: e.date, reverse=True)
        latest = domain_emails[0]

        # Payment processor: split by merchant and only keep recurring ones
        is_processor = any(domain.endswith(p) for p in PAYMENT_PROCESSOR_DOMAINS)
        if is_processor:
            by_merchant: dict[str, list[ParsedEmail]] = defaultdict(list)
            for e in domain_emails:
                resolved = _resolve_payment_processor(e.body_text, e.subject)
                merchant_key = resolved[0] if resolved else "__unknown__"
                by_merchant[merchant_key].append((e, resolved))

            for merchant_key, merchant_entries in by_merchant.items():
                if merchant_key == "__unknown__":
                    continue
                # Skip known transactional merchants
                if any(t in merchant_key.lower() for t in TRANSACTIONAL_MERCHANTS):
                    continue
                # Known services need only 1 charge — we know they're subscriptions.
                # Unknown merchants need 2+ charges to confirm they're recurring.
                _, resolved_info = merchant_entries[0]
                is_known_service = any(
                    kw in merchant_key.lower() for kw in STRIPE_SERVICE_KEYWORDS
                )
                if not is_known_service and len(merchant_entries) < 2:
                    continue
                # Filter out repeat purchases: subscriptions charge similar amounts.
                # If min/max ratio < 0.5, the amounts vary too much to be a subscription.
                amounts = [e.amount for e, _ in merchant_entries if e.amount]
                if len(amounts) >= 2:
                    ratio = min(amounts) / max(amounts)
                    if ratio < 0.5:
                        continue
                merchant_entries.sort(key=lambda x: x[0].date, reverse=True)
                latest_e, resolved = merchant_entries[0]
                name, cancel_url, frequency = resolved
                subscriptions.append(Subscription(
                    service_name=name,
                    amount=latest_e.amount,
                    currency=latest_e.currency,
                    billing_frequency=frequency,
                    last_charge_date=latest_e.date,
                    source_email="",
                    status=classify_status(latest_e.date),
                    cancellation_url=cancel_url,
                ))
            continue  # skip generic domain-level handling for processors

        if known_match:
            name, cancel_url, frequency = known_match
        elif len(domain_emails) >= 2:
            # Unknown service but recurring — use cleaned domain as name
            name = domain.replace(".com", "").replace(".io", "").replace(".app", "").title()
            cancel_url = None
            frequency = "monthly"
        else:
            continue  # single email, unknown service — skip

        # Deduplicate: skip if same service name already detected
        if any(s.service_name == name for s in subscriptions):
            continue

        subscriptions.append(Subscription(
            service_name=name,
            amount=latest.amount,
            currency=latest.currency,
            billing_frequency=frequency,
            last_charge_date=latest.date,
            source_email="",
            status=classify_status(latest.date),
            cancellation_url=cancel_url,
        ))

    return subscriptions


def classify_status(last_charge_date: date) -> SubscriptionStatus:
    days_since = (date.today() - last_charge_date).days
    if days_since <= DORMANT_THRESHOLD_DAYS:
        return SubscriptionStatus.ACTIVE
    return SubscriptionStatus.DORMANT
