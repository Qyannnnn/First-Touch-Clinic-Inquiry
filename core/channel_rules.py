"""Single declarative source for channel-aware opening strategies.

The matching engine is generic; channel-specific wording/behavior stays here rather
than being scattered through request handlers.
"""
CHANNEL_RULES = {
    "instagram_comment": {
        "strategy": "social_private_transition",
        "opening": "You’re now in a more private space. I can help with general information and help you prepare questions before you decide whether to continue with the clinic.",
    },
    "facebook_comment": {
        "strategy": "social_private_transition",
        "opening": "You’re now in a more private space. I can help with general information and help you prepare questions before you decide whether to continue with the clinic.",
    },
    "tiktok_comment": {
        "strategy": "social_private_transition",
        "opening": "You’re now in a more private space. I can help with general information and help you prepare questions before you decide whether to continue with the clinic.",
    },
    "staff_referral": {
        "strategy": "staff_referral_context",
        "opening": "Your care team shared that you'd like to explore {context}. You can start with general questions here at your own pace.",
    },
    "website_widget": {
        "strategy": "website_context",
        "opening": "I can help with general questions about the clinic and the page you were viewing. You don’t need an account to start.",
    },
    "instagram_ad_click": {
        "strategy": "campaign_context",
        "opening": "You can explore general questions related to {context} here before deciding whether you want to continue securely with the clinic.",
    },
    "default": {
        "strategy": "general_guest",
        "opening": "I can help with general clinic information and help you prepare questions. You don’t need an account to start.",
    },
}
