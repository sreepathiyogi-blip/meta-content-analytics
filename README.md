# 📊 Meta Content Analytics — Streamlit App

A dark-themed, interactive dashboard for analysing your Facebook & Instagram content performance using the Meta Graph API.

## Features
| Module | What it shows |
|---|---|
| 📅 Best Posting Times | Heatmap of avg engagement by day × hour |
| 💬 Sentiment Analysis | Pie chart + score distribution of comment sentiment |
| # Hashtag Performance | Avg engagement per hashtag, uses vs engagement scatter |
| 🎬 Video Retention | Views, completion rates, duration vs retention |

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
streamlit run app.py
```

## Get a Meta Token

1. Go to **developers.facebook.com → Tools → Graph API Explorer**
2. Select your app
3. Add permissions: `pages_read_engagement`, `pages_show_list`, `instagram_basic`, `instagram_manage_insights`
4. Click **Generate Access Token**
5. Paste it into the sidebar

## Permissions Needed
- `pages_read_engagement` — post & comment data
- `pages_show_list` — list your pages
- `instagram_basic` — IG media & hashtags
- `instagram_manage_insights` — video insights

> ⚠️ For production use, implement a long-lived token flow via the OAuth endpoint.
