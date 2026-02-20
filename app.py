import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from collections import Counter
import re

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Meta Content Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=DM+Sans:wght@300;400;500&display=swap');

:root {
    --bg: #0a0a0f;
    --surface: #12121a;
    --card: #1a1a26;
    --border: #2a2a3d;
    --accent: #7c6fff;
    --accent2: #ff6fb0;
    --accent3: #40e0b0;
    --text: #e8e8f0;
    --muted: #7a7a9a;
}

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: var(--bg);
    color: var(--text);
}

.stApp { background-color: var(--bg); }

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border);
}

/* Headers */
h1, h2, h3 { font-family: 'Syne', sans-serif; }

/* Metric Cards */
.metric-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 24px;
    text-align: center;
    transition: border-color 0.2s;
}
.metric-card:hover { border-color: var(--accent); }
.metric-value {
    font-family: 'Syne', sans-serif;
    font-size: 2.2rem;
    font-weight: 800;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.metric-label {
    font-size: 0.8rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: 4px;
}

/* Section Headers */
.section-header {
    font-family: 'Syne', sans-serif;
    font-size: 1.4rem;
    font-weight: 700;
    color: var(--text);
    border-left: 4px solid var(--accent);
    padding-left: 12px;
    margin: 32px 0 16px;
}

/* Tag chips */
.chip {
    display: inline-block;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.8rem;
    color: var(--accent);
    margin: 3px;
}

/* Sentiment badges */
.badge-pos { color: var(--accent3); font-weight: 600; }
.badge-neg { color: var(--accent2); font-weight: 600; }
.badge-neu { color: var(--muted); font-weight: 600; }

/* Input overrides */
.stTextInput input, .stSelectbox select {
    background: var(--card) !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
    border-radius: 10px !important;
}

/* Button */
.stButton button {
    background: linear-gradient(135deg, var(--accent), #9c8fff) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    padding: 10px 24px !important;
    width: 100%;
}

/* Warning / info box */
.info-box {
    background: rgba(124,111,255,0.1);
    border: 1px solid rgba(124,111,255,0.3);
    border-radius: 12px;
    padding: 14px 18px;
    font-size: 0.9rem;
    color: var(--muted);
    margin: 12px 0;
}

div[data-testid="stMetric"] {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 20px;
}

div[data-testid="stMetricValue"] {
    font-family: 'Syne', sans-serif;
    font-size: 2rem !important;
}
</style>
""", unsafe_allow_html=True)

# ── Sentiment (no external deps) ───────────────────────────────────────────────
POSITIVE_WORDS = set(["love","great","amazing","awesome","good","excellent","fantastic",
    "wonderful","best","perfect","nice","happy","beautiful","cool","thanks","thank",
    "brilliant","superb","outstanding","incredible","delightful","enjoy","liked"])
NEGATIVE_WORDS = set(["hate","bad","terrible","awful","horrible","worst","poor","ugly",
    "boring","disappointing","useless","waste","annoying","disgusting","sad",
    "dislike","failed","error","problem","issue","broken","wrong","spam"])

def simple_sentiment(text):
    if not text:
        return "neutral", 0.0
    words = re.findall(r'\w+', text.lower())
    pos = sum(1 for w in words if w in POSITIVE_WORDS)
    neg = sum(1 for w in words if w in NEGATIVE_WORDS)
    if pos > neg:
        return "positive", round(pos / (pos + neg + 1e-9), 2)
    elif neg > pos:
        return "negative", round(-neg / (pos + neg + 1e-9), 2)
    return "neutral", 0.0

# ── Graph API Helpers ──────────────────────────────────────────────────────────
BASE = "https://graph.facebook.com/v19.0"

def api_get(endpoint, params):
    try:
        r = requests.get(f"{BASE}/{endpoint}", params=params, timeout=15)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def get_page_info(token):
    return api_get("me", {"fields": "id,name,fan_count,picture", "access_token": token})

def get_posts(page_id, token, limit=50):
    data = api_get(f"{page_id}/posts", {
        "fields": "id,message,created_time,likes.summary(true),comments.summary(true),shares,full_picture",
        "limit": limit,
        "access_token": token,
    })
    return data.get("data", [])

def get_post_insights(post_id, token):
    metrics = "post_impressions,post_engaged_users,post_clicks,post_reactions_by_type_total"
    data = api_get(f"{post_id}/insights", {"metric": metrics, "access_token": token})
    result = {}
    for item in data.get("data", []):
        result[item["name"]] = item["values"][0]["value"] if item.get("values") else 0
    return result

def get_comments(post_id, token, limit=100):
    data = api_get(f"{post_id}/comments", {
        "fields": "message,created_time,like_count",
        "limit": limit,
        "access_token": token,
    })
    return data.get("data", [])

def get_ig_user(token):
    data = api_get("me/accounts", {"fields": "instagram_business_account", "access_token": token})
    pages = data.get("data", [])
    for p in pages:
        ig = p.get("instagram_business_account")
        if ig:
            return ig["id"]
    return None

def get_ig_media(ig_id, token, limit=30):
    data = api_get(f"{ig_id}/media", {
        "fields": "id,caption,timestamp,like_count,comments_count,media_type,thumbnail_url,permalink",
        "limit": limit,
        "access_token": token,
    })
    return data.get("data", [])

def get_ig_hashtag(ig_id, tag, token):
    search = api_get("ig-hashtag-search", {"user_id": ig_id, "q": tag, "access_token": token})
    ht_id = search.get("data", [{}])[0].get("id") if search.get("data") else None
    if not ht_id:
        return []
    media = api_get(f"{ht_id}/top_media", {
        "fields": "id,like_count,comments_count,media_type",
        "user_id": ig_id,
        "access_token": token,
    })
    return media.get("data", [])

def get_video_insights(video_id, token):
    metrics = "total_video_views,total_video_avg_time_watched,total_video_complete_views,total_video_view_time"
    data = api_get(f"{video_id}/video_insights", {"metric": metrics, "access_token": token})
    result = {}
    for item in data.get("data", []):
        v = item.get("values", [{}])[0].get("value", 0)
        result[item["name"]] = v
    return result

def get_videos(page_id, token):
    data = api_get(f"{page_id}/videos", {
        "fields": "id,title,description,created_time,length,views",
        "limit": 20,
        "access_token": token,
    })
    return data.get("data", [])

# ── Chart Theme ────────────────────────────────────────────────────────────────
CHART_THEME = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font_color="#e8e8f0",
    font_family="DM Sans",
    colorway=["#7c6fff","#ff6fb0","#40e0b0","#ffd166","#06d6a0"],
)

def styled_fig(fig):
    fig.update_layout(**CHART_THEME,
        xaxis=dict(gridcolor="#2a2a3d", zerolinecolor="#2a2a3d"),
        yaxis=dict(gridcolor="#2a2a3d", zerolinecolor="#2a2a3d"),
        margin=dict(l=10, r=10, t=30, b=10),
    )
    return fig

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔮 Meta Analytics")
    st.markdown("---")
    token = st.text_input("Access Token", type="password", placeholder="Paste your Meta token…")
    
    st.markdown("**Analyses**")
    run_posting = st.checkbox("📅 Best Posting Times", value=True)
    run_sentiment = st.checkbox("💬 Sentiment Analysis", value=True)
    run_hashtag = st.checkbox("# Hashtag Performance", value=True)
    run_video = st.checkbox("🎬 Video Retention", value=True)

    hashtag_input = ""
    if run_hashtag:
        hashtag_input = st.text_input("Hashtag to analyse", placeholder="e.g. python (no #)")

    post_limit = st.slider("Posts to fetch", 10, 100, 30)
    run_btn = st.button("🚀 Run Analysis")
    
    st.markdown("---")
    st.markdown('<div class="info-box">💡 Token needs <b>pages_read_engagement</b> and <b>instagram_basic</b> permissions.</div>', unsafe_allow_html=True)

# ── Main Layout ────────────────────────────────────────────────────────────────
st.markdown("# Meta Content Analytics 📊")
st.markdown('<p style="color:#7a7a9a;margin-top:-12px">Powered by Meta Graph API</p>', unsafe_allow_html=True)

if not token:
    st.markdown("""
    <div style="background:linear-gradient(135deg,#1a1a26,#12121a);border:1px solid #2a2a3d;
    border-radius:20px;padding:48px;text-align:center;margin-top:40px;">
        <div style="font-size:3rem">🔐</div>
        <h2 style="font-family:Syne,sans-serif;margin:16px 0 8px">Enter your Meta Token</h2>
        <p style="color:#7a7a9a">Paste your access token in the sidebar to get started.<br>
        Get one at <b>developers.facebook.com → Tools → Graph API Explorer</b></p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Run ────────────────────────────────────────────────────────────────────────
if run_btn or "page_data" in st.session_state:

    if run_btn:
        # Fetch fresh data
        with st.spinner("Connecting to Meta API…"):
            page_info = get_page_info(token)
        
        if "error" in page_info:
            st.error(f"❌ API Error: {page_info['error'].get('message', page_info['error'])}")
            st.stop()

        page_id = page_info.get("id")
        page_name = page_info.get("name", "Your Page")
        fans = page_info.get("fan_count", 0)

        with st.spinner("Fetching posts…"):
            posts = get_posts(page_id, token, post_limit)

        st.session_state["page_info"] = page_info
        st.session_state["page_id"] = page_id
        st.session_state["posts"] = posts
        st.session_state["page_name"] = page_name
        st.session_state["fans"] = fans

    # Restore from state
    page_info = st.session_state["page_info"]
    page_id = st.session_state["page_id"]
    posts = st.session_state["posts"]
    page_name = st.session_state["page_name"]
    fans = st.session_state["fans"]

    # ── Page Overview ──────────────────────────────────────────────────────────
    st.markdown(f'<div class="section-header">👤 {page_name}</div>', unsafe_allow_html=True)

    total_posts = len(posts)
    total_likes = sum(p.get("likes", {}).get("summary", {}).get("total_count", 0) for p in posts)
    total_comments = sum(p.get("comments", {}).get("summary", {}).get("total_count", 0) for p in posts)
    avg_engagement = round((total_likes + total_comments) / max(total_posts, 1), 1)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Page Fans", f"{fans:,}")
    with c2:
        st.metric("Posts Analysed", total_posts)
    with c3:
        st.metric("Total Likes", f"{total_likes:,}")
    with c4:
        st.metric("Avg Engagement", avg_engagement)

    # Build DataFrame
    rows = []
    for p in posts:
        dt = datetime.strptime(p["created_time"], "%Y-%m-%dT%H:%M:%S%z")
        rows.append({
            "post_id": p["id"],
            "message": p.get("message", ""),
            "created_time": dt,
            "hour": dt.hour,
            "day_name": dt.strftime("%A"),
            "day_num": dt.weekday(),
            "likes": p.get("likes", {}).get("summary", {}).get("total_count", 0),
            "comments": p.get("comments", {}).get("summary", {}).get("total_count", 0),
            "shares": p.get("shares", {}).get("count", 0),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["engagement"] = df["likes"] + df["comments"] + df["shares"]

    # ──────────────────────────────────────────────────────────────────────────
    # 1. BEST POSTING TIMES
    # ──────────────────────────────────────────────────────────────────────────
    if run_posting and not df.empty:
        st.markdown('<div class="section-header">📅 Best Posting Times</div>', unsafe_allow_html=True)

        col_left, col_right = st.columns([2, 1])

        with col_left:
            # Heatmap: day × hour
            pivot = df.pivot_table(values="engagement", index="day_name", columns="hour", aggfunc="mean").fillna(0)
            day_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
            pivot = pivot.reindex([d for d in day_order if d in pivot.index])

            fig = go.Figure(go.Heatmap(
                z=pivot.values,
                x=[f"{h:02d}:00" for h in pivot.columns],
                y=pivot.index.tolist(),
                colorscale=[[0,"#12121a"],[0.5,"#7c6fff"],[1,"#ff6fb0"]],
                hovertemplate="Day: %{y}<br>Hour: %{x}<br>Avg Engagement: %{z:.1f}<extra></extra>",
            ))
            fig.update_layout(title="Avg Engagement by Day & Hour", **CHART_THEME,
                              margin=dict(l=10,r=10,t=40,b=10))
            st.plotly_chart(fig, use_container_width=True)

        with col_right:
            # Best hours bar
            hour_avg = df.groupby("hour")["engagement"].mean().sort_values(ascending=False).head(8).reset_index()
            fig2 = px.bar(hour_avg, x="engagement", y=hour_avg["hour"].apply(lambda h: f"{h:02d}:00"),
                          orientation="h", title="Top Hours",
                          color="engagement", color_continuous_scale=["#7c6fff","#ff6fb0"])
            fig2.update_layout(**CHART_THEME, margin=dict(l=10,r=10,t=40,b=10),
                               yaxis=dict(autorange="reversed", gridcolor="#2a2a3d"),
                               xaxis=dict(gridcolor="#2a2a3d"), coloraxis_showscale=False)
            st.plotly_chart(fig2, use_container_width=True)

        # Insight callout
        best_hour = df.groupby("hour")["engagement"].mean().idxmax()
        best_day = df.groupby("day_name")["engagement"].mean().idxmax()
        st.markdown(f"""
        <div class="info-box">
        🏆 <b>Best time to post:</b> {best_day}s at <b>{best_hour:02d}:00</b> — highest average engagement across your last {total_posts} posts.
        </div>""", unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────────────────────
    # 2. SENTIMENT ANALYSIS
    # ──────────────────────────────────────────────────────────────────────────
    if run_sentiment and not df.empty:
        st.markdown('<div class="section-header">💬 Sentiment Analysis on Comments</div>', unsafe_allow_html=True)

        with st.spinner("Fetching comments from recent posts…"):
            all_comments = []
            sample_posts = df.head(10)["post_id"].tolist()
            prog = st.progress(0)
            for i, pid in enumerate(sample_posts):
                comments = get_comments(pid, token, limit=50)
                for c in comments:
                    label, score = simple_sentiment(c.get("message",""))
                    all_comments.append({
                        "post_id": pid,
                        "message": c.get("message",""),
                        "created_time": c.get("created_time",""),
                        "like_count": c.get("like_count", 0),
                        "sentiment": label,
                        "score": score,
                    })
                prog.progress((i+1)/len(sample_posts))

        if all_comments:
            cdf = pd.DataFrame(all_comments)
            sent_counts = cdf["sentiment"].value_counts()

            col1, col2 = st.columns([1, 2])

            with col1:
                fig = go.Figure(go.Pie(
                    labels=sent_counts.index,
                    values=sent_counts.values,
                    hole=0.6,
                    marker_colors=["#40e0b0","#ff6fb0","#7a7a9a"],
                ))
                fig.update_layout(title="Sentiment Split", **CHART_THEME,
                                  margin=dict(l=10,r=10,t=40,b=10))
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Score distribution
                fig2 = px.histogram(cdf, x="score", color="sentiment",
                    title="Sentiment Score Distribution",
                    color_discrete_map={"positive":"#40e0b0","negative":"#ff6fb0","neutral":"#7a7a9a"},
                    nbins=30)
                styled_fig(fig2)
                fig2.update_layout(**CHART_THEME, margin=dict(l=10,r=10,t=40,b=10))
                st.plotly_chart(fig2, use_container_width=True)

            # Top comments
            st.markdown("**Most Liked Comments**")
            top_comments = cdf.nlargest(5, "like_count")[["message","like_count","sentiment"]]
            for _, row in top_comments.iterrows():
                badge_class = f"badge-{'pos' if row.sentiment=='positive' else 'neg' if row.sentiment=='negative' else 'neu'}"
                emoji = "✅" if row.sentiment=="positive" else "❌" if row.sentiment=="negative" else "➖"
                st.markdown(f"""
                <div class="metric-card" style="text-align:left;margin-bottom:8px">
                    <span class="{badge_class}">{emoji} {row.sentiment.title()}</span>
                    <span style="color:#7a7a9a;font-size:0.8rem;margin-left:8px">👍 {int(row.like_count)}</span>
                    <p style="margin:6px 0 0;font-size:0.9rem">{row.message[:180]}</p>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("No comments found on recent posts.")

    # ──────────────────────────────────────────────────────────────────────────
    # 3. HASHTAG PERFORMANCE
    # ──────────────────────────────────────────────────────────────────────────
    if run_hashtag:
        st.markdown('<div class="section-header"># Hashtag Performance (Instagram)</div>', unsafe_allow_html=True)

        with st.spinner("Looking for Instagram Business account…"):
            ig_id = get_ig_user(token)

        if not ig_id:
            st.warning("⚠️ No Instagram Business account linked to this token. Make sure your FB page is connected to an IG Business account.")
        else:
            with st.spinner("Fetching Instagram posts…"):
                ig_media = get_ig_media(ig_id, token, limit=50)

            if ig_media:
                # Extract hashtags from captions
                all_tags = []
                for m in ig_media:
                    caption = m.get("caption","") or ""
                    tags = re.findall(r'#(\w+)', caption.lower())
                    all_tags.extend(tags)
                    m["tags"] = tags
                    m["engagement"] = m.get("like_count",0) + m.get("comments_count",0)

                tag_counts = Counter(all_tags)
                most_common_tags = [t for t,_ in tag_counts.most_common(20)]

                # Per-tag average engagement
                tag_eng = {}
                for m in ig_media:
                    for t in m["tags"]:
                        tag_eng.setdefault(t, []).append(m["engagement"])

                tag_df = pd.DataFrame([
                    {"hashtag": f"#{t}", "uses": tag_counts[t],
                     "avg_engagement": round(np.mean(tag_eng[t]),1),
                     "total_engagement": sum(tag_eng[t])}
                    for t in most_common_tags
                ]).sort_values("avg_engagement", ascending=False)

                col1, col2 = st.columns(2)
                with col1:
                    fig = px.bar(tag_df.head(12), x="avg_engagement", y="hashtag",
                                 orientation="h", title="Avg Engagement per Hashtag",
                                 color="avg_engagement",
                                 color_continuous_scale=["#7c6fff","#ff6fb0"])
                    fig.update_layout(**CHART_THEME, margin=dict(l=10,r=10,t=40,b=10),
                                      yaxis=dict(autorange="reversed",gridcolor="#2a2a3d"),
                                      xaxis=dict(gridcolor="#2a2a3d"), coloraxis_showscale=False)
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    fig2 = px.scatter(tag_df, x="uses", y="avg_engagement",
                                      text="hashtag", title="Uses vs Avg Engagement",
                                      size="total_engagement", color="avg_engagement",
                                      color_continuous_scale=["#7c6fff","#ff6fb0"])
                    fig2.update_traces(textposition="top center", textfont_size=9)
                    fig2.update_layout(**CHART_THEME, margin=dict(l=10,r=10,t=40,b=10),
                                       coloraxis_showscale=False)
                    st.plotly_chart(fig2, use_container_width=True)

                # Fetch live hashtag data if provided
                if hashtag_input:
                    with st.spinner(f"Fetching live data for #{hashtag_input}…"):
                        ht_media = get_ig_hashtag(ig_id, hashtag_input, token)
                    if ht_media:
                        likes = [m.get("like_count",0) for m in ht_media]
                        comms = [m.get("comments_count",0) for m in ht_media]
                        st.markdown(f"**Live: #{hashtag_input}** — {len(ht_media)} top posts | avg likes {round(np.mean(likes),1)} | avg comments {round(np.mean(comms),1)}")
                    else:
                        st.info(f"No public data found for #{hashtag_input}.")

                # Tag cloud display
                st.markdown("**Your top hashtags:**")
                chips = " ".join([f'<span class="chip">#{t}</span>' for t,_ in tag_counts.most_common(25)])
                st.markdown(chips, unsafe_allow_html=True)

            else:
                st.info("No Instagram media found.")

    # ──────────────────────────────────────────────────────────────────────────
    # 4. VIDEO RETENTION
    # ──────────────────────────────────────────────────────────────────────────
    if run_video:
        st.markdown('<div class="section-header">🎬 Video Views & Retention</div>', unsafe_allow_html=True)

        with st.spinner("Fetching video data…"):
            videos = get_videos(page_id, token)

        if not videos:
            st.info("No videos found on this page.")
        else:
            vid_rows = []
            prog2 = st.progress(0)
            for i, v in enumerate(videos):
                insights = get_video_insights(v["id"], token)
                dur = v.get("length", 0)
                avg_watch = insights.get("total_video_avg_time_watched", 0)
                vid_rows.append({
                    "title": (v.get("title") or v.get("description","") or "Untitled")[:40],
                    "created": v.get("created_time","")[:10],
                    "duration_s": dur,
                    "duration_min": round(dur/60,1),
                    "views": insights.get("total_video_views",0),
                    "complete_views": insights.get("total_video_complete_views",0),
                    "avg_watch_s": avg_watch,
                    "view_time_min": round(insights.get("total_video_view_time",0)/60,1),
                })
                prog2.progress((i+1)/len(videos))

            vdf = pd.DataFrame(vid_rows)
            vdf["completion_rate"] = (vdf["complete_views"] / vdf["views"].replace(0,1) * 100).round(1)
            vdf["retention_pct"] = (vdf["avg_watch_s"] / vdf["duration_s"].replace(0,1) * 100).round(1)

            # KPIs
            cv1, cv2, cv3 = st.columns(3)
            with cv1:
                st.metric("Total Videos", len(vdf))
            with cv2:
                st.metric("Avg Completion Rate", f"{vdf['completion_rate'].mean():.1f}%")
            with cv3:
                st.metric("Avg Retention", f"{vdf['retention_pct'].mean():.1f}%")

            col1, col2 = st.columns(2)

            with col1:
                fig = px.bar(vdf.sort_values("views", ascending=False).head(10),
                             x="title", y="views", title="Top Videos by Views",
                             color="completion_rate",
                             color_continuous_scale=["#7c6fff","#40e0b0"])
                fig.update_layout(**CHART_THEME, margin=dict(l=10,r=10,t=40,b=10),
                                  xaxis_tickangle=-30, coloraxis_showscale=False)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                fig2 = px.scatter(vdf, x="duration_min", y="retention_pct",
                                  size="views", color="completion_rate",
                                  text="title", title="Duration vs Retention %",
                                  color_continuous_scale=["#ff6fb0","#40e0b0"],
                                  hover_data=["views","completion_rate"])
                fig2.update_traces(textposition="top center", textfont_size=8)
                fig2.update_layout(**CHART_THEME, margin=dict(l=10,r=10,t=40,b=10),
                                   coloraxis_showscale=False)
                st.plotly_chart(fig2, use_container_width=True)

            # Table
            st.markdown("**All Videos**")
            display_cols = ["title","created","duration_min","views","complete_views","completion_rate","retention_pct","view_time_min"]
            rename = {"duration_min":"Duration (min)","view_time_min":"Total View Time (min)",
                      "completion_rate":"Completion %","retention_pct":"Retention %",
                      "complete_views":"Complete Views"}
            st.dataframe(
                vdf[display_cols].rename(columns=rename).sort_values("views", ascending=False),
                use_container_width=True, hide_index=True
            )

    st.markdown("---")
    st.markdown('<p style="text-align:center;color:#2a2a3d;font-size:0.8rem">Meta Content Analytics · Built with Streamlit & Graph API v19</p>', unsafe_allow_html=True)
