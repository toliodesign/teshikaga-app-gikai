#!/usr/bin/env python3
"""弟子屈町議会の公式YouTubeチャンネルから動画情報を集めて data/videos.json を作る。
必要なもの: 環境変数 YOUTUBE_API_KEY（YouTube Data API v3 のAPIキー）。標準ライブラリだけで動く。"""
import json, os, re, sys, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

CHANNEL_ID = "UCp1bEH7DOpEjf_hjgCmZFlQ"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "videos.json")
DIGITS = str.maketrans("０１２３４５６７８９：", "0123456789:")
_T = r"(?:[0-9０-９]+[:：])?[0-9０-９]+[:：][0-9０-９]{2}"          # 4:45 / 1:02:03 / 全角も可
TIME_LINE = re.compile(r"^[\[【(（\s]*(" + _T + r")[\]】)）\s]*[-–—〜~:：]?\s*(.*)$")   # 行の先頭が時刻
TIME_ANY = re.compile(r"(?<![0-9０-９:：])" + _T + r"(?![0-9０-９])")          # 文中のどこかにある時刻
JST = timezone(timedelta(hours=9))

def _parse(desc):
    body = desc.split("********")[0]   # 「********」より下は全動画共通の注意書きなので使わない
    items, qbuf, gbuf, mode, last, n = [], [], [], None, None, 0
    for raw in body.splitlines():
        l = raw.strip()
        m = TIME_LINE.match(l)
        if m:   # 時刻で始まる行は、どの場所にあっても必ずリンク元にする
            last = m.group(1).translate(DIGITS); n += 1; mode = None
            items.append([last, m.group(2).strip()]); continue
        if l.startswith("【質問事項】"): mode = "q"; continue
        if l.startswith("【質問要旨】"): mode = "g"; continue
        if mode == "q":
            if l: qbuf.append(l)
            continue
        if mode == "g":
            if l: gbuf.append(l)
            continue
        if not l: last = None; continue
        if last and not l.startswith(("※", "http")):
            if items and items[-1][0] == last and items[-1][1] == "":
                items[-1][1] = l      # 時刻だけの行の、次の行を件名にする
            else:
                items.append([last, l])   # 同じ時刻にまとまっている続きの行
    for it in items:   # 行の途中にある時刻も、画面でリンクにするので数字を半角にそろえる
        it[1] = TIME_ANY.sub(lambda m: m.group(0).translate(DIGITS), it[1])
    n += sum(len(TIME_ANY.findall(it[1])) for it in items)   # 行の途中の時刻もリンクにできた数に入れる
    return " ".join(qbuf), "\n".join(gbuf), items, n

def parse_description(desc):
    """戻り値: (質問事項, 質問要旨, [[時刻, 内容], ...])。一般質問でも時刻は残す。"""
    q, g, items, _ = _parse(desc)
    return q, g, items

def time_check(desc):
    """(説明欄にある時刻らしい文字の数, リンクにできた時刻の数)。差があれば見落としの疑い。"""
    body = desc.split("********")[0]
    return len(TIME_ANY.findall(body)), _parse(desc)[3]

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
            desc = sn.get("description", "")
            q, gist, items = parse_description(desc)
            found, linked = time_check(desc)
            if found != linked:   # GitHubの実行記録に黄色い注意として出る
                print("::warning::時刻の見落としの疑い：%s（時刻らしい文字 %d 個、リンクにできたのは %d 個）" % (sn["title"], found, linked))
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
