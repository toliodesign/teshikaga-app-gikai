#!/usr/bin/env python3
"""弟子屈町議会の公式YouTubeチャンネルから動画情報を集めて data/videos.json を作る。
必要なもの: 環境変数 YOUTUBE_API_KEY（YouTube Data API v3 のAPIキー）。標準ライブラリだけで動く。"""
import json, os, re, sys, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

CHANNEL_ID = "UCp1bEH7DOpEjf_hjgCmZFlQ"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "videos.json")
TIME_LINE = re.compile(r"^((?:\d+:)?\d+:\d{2})\s+(.+)$")
JST = timezone(timedelta(hours=9))

def parse_description(desc):
    """説明欄の「********」より上だけを読む（下は全動画共通の注意書き）。
    戻り値: (質問事項, 質問要旨, [[時刻, 内容], ...])"""
    body = desc.split("********")[0]
    items, qbuf, gbuf, mode, last = [], [], [], None, None
    for raw in body.splitlines():
        l = raw.strip()
        if l.startswith("【質問事項】"): mode = "q"; continue
        if l.startswith("【質問要旨】"): mode = "g"; continue
        if mode == "q":
            if l: qbuf.append(l)
            continue
        if mode == "g":
            if l: gbuf.append(l)
            continue
        m = TIME_LINE.match(l)
        if m:
            last = m.group(1); items.append([last, m.group(2)]); continue
        if not l: last = None; continue
        if last and not l.startswith(("※", "http")):
            items.append([last, l])   # 同じ時刻にまとまっている続きの行
    if qbuf:  # 一般質問の動画は、時刻の目次を使わない
        return " ".join(qbuf), "\n".join(gbuf), []
    return "", "", items

def api(path, **params):
    params["key"] = os.environ["YOUTUBE_API_KEY"]
    url = "https://www.googleapis.com/youtube/v3/%s?%s" % (path, urllib.parse.urlencode(params))
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)

def all_video_ids():
    playlist, ids, token = "UU" + CHANNEL_ID[2:], [], None   # 「アップロード動画」の一覧
    while True:
        p = dict(part="contentDetails", playlistId=playlist, maxResults=50)
        if token: p["pageToken"] = token
        d = api("playlistItems", **p)
        ids += [i["contentDetails"]["videoId"] for i in d.get("items", [])]
        token = d.get("nextPageToken")
        if not token: return ids

def fetch_videos():
    ids, out = all_video_ids(), []
    for i in range(0, len(ids), 50):
        d = api("videos", part="snippet", id=",".join(ids[i:i + 50]))
        for it in d.get("items", []):
            sn = it["snippet"]
            q, gist, items = parse_description(sn.get("description", ""))
            pub = datetime.fromisoformat(sn["publishedAt"].replace("Z", "+00:00")).astimezone(JST)
            v = {"id": it["id"], "title": sn["title"], "pub": pub.strftime("%Y-%m-%d")}
            if q: v["q"], v["gist"] = q, gist
            if items: v["items"] = items
            out.append(v)
    out.sort(key=lambda v: (v["pub"], v["title"]), reverse=True)
    return out

def main():
    if not os.environ.get("YOUTUBE_API_KEY"):
        sys.exit("YOUTUBE_API_KEY が設定されていません。")
    videos = fetch_videos()
    if not videos:
        sys.exit("動画が1本も取得できなかったため、今のデータを残して終了します。")
    try:
        old = json.load(open(OUT, encoding="utf-8")).get("videos")
    except Exception:
        old = None
    if old == videos:
        print("変更なし（%d本）" % len(videos)); return
    data = {"updated": datetime.now(JST).strftime("%Y-%m-%d %H:%M"), "videos": videos}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("更新しました（%d本）" % len(videos))

if __name__ == "__main__":
    main()
