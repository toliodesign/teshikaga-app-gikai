#!/usr/bin/env python3
"""弟子屈町議会の公式YouTubeチャンネルから動画情報を集めて data/videos.json を作る。
必要なもの: 環境変数 YOUTUBE_API_KEY（YouTube Data API v3 のAPIキー）。標準ライブラリだけで動く。"""
import json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

CHANNEL_ID = "UCp1bEH7DOpEjf_hjgCmZFlQ"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "videos.json")
DIGITS = str.maketrans("０１２３４５６７８９：", "0123456789:")
_T = r"(?:[0-9０-９]+[:：])?[0-9０-９]+[:：][0-9０-９]{2}"          # 4:45 / 1:02:03 / 全角も可
TIME_LINE = re.compile(r"^[\[【(（\s]*(" + _T + r")[\]】)）\s]*[-–—〜~:：]?\s*(.*)$")   # 行の先頭が時刻
TIME_ANY = re.compile(r"(?<![0-9０-９:：])" + _T + r"(?![0-9０-９])")          # 文中のどこかにある時刻
JST = timezone(timedelta(hours=9))
VID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")   # YouTubeの動画IDの形

def _cmd(s):
    """GitHubの実行記録に出す文字を安全な形にする（%や改行で、記録の命令が書き換わらないように）。"""
    return str(s).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
DEFAULT_RULES = [{"name": "一般質問", "title": ["一般質問"]},
                 {"name": "決算審査特別委員会", "title": ["決算審査特別委員"]},
                 {"name": "予算特別委員会", "title": ["予算特別委員"]},
                 {"name": "臨時会", "title": ["臨時会"]},
                 {"name": "方針説明", "title": ["執行方針", "行政方針"]},
                 {"name": "議案の審議", "title": ["議案"]}]
KINDS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "kinds.json")

def load_rules(path=KINDS):
    """data/kinds.json の「rules」を読む。読めなければ、内蔵の既定を使う。"""
    try:
        rules = json.load(open(path, encoding="utf-8"))["rules"]
        return rules if isinstance(rules, list) else DEFAULT_RULES
    except Exception:
        return DEFAULT_RULES

def classify(title, rules=None):
    """上から順に、タイトルに言葉が入っていた最初の種類を返す。どれにも合わなければ「その他」。"""
    for r in (DEFAULT_RULES if rules is None else rules):
        if any(w in title for w in r.get("title", [])): return r["name"]
    return "その他"

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

def parse_questions(desc):
    """一般質問の説明欄を、質問ごとのまとまり [{time, label, q, gist}, ...] にする。
    時刻の行で新しいまとまりが始まり、【質問事項】【質問要旨】はそのまとまりに入る。"""
    body = desc.split("********")[0]
    blocks, cur, mode = [], None, None
    def new(time="", label=""):
        b = {"time": time, "label": label, "q": [], "gist": []}
        blocks.append(b); return b
    for raw in body.splitlines():
        l = raw.strip()
        m = TIME_LINE.match(l)
        if m:
            cur = new(m.group(1).translate(DIGITS), m.group(2).strip()); mode = None; continue
        for tag, key in (("【質問事項】", "q"), ("【質問要旨】", "g")):
            if l.startswith(tag):
                if cur is None or (key == "q" and cur["q"]): cur = new()   # 時刻のない質問も取りこぼさない
                mode, rest = key, l[len(tag):].strip()
                if rest: cur["q" if key == "q" else "gist"].append(rest)
                break
        else:
            if cur and l and mode == "q": cur["q"].append(l)
            elif cur and l and mode == "g": cur["gist"].append(l)
    for b in blocks:
        b["q"], b["gist"] = " ".join(b["q"]), "\n".join(b["gist"])
    return blocks

def time_check(desc):
    """(説明欄にある時刻らしい文字の数, リンクにできた時刻の数)。差があれば見落としの疑い。"""
    body = desc.split("********")[0]
    return len(TIME_ANY.findall(body)), _parse(desc)[3]

def api(path, **params):
    key = os.environ["YOUTUBE_API_KEY"]
    params["key"] = key
    url = "https://www.googleapis.com/youtube/v3/%s?%s" % (path, urllib.parse.urlencode(params))
    last = ""
    for attempt in range(3):   # 一時的な通信の失敗は、少し待って2回までやり直す
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            reason = ""
            try: reason = json.load(e).get("error", {}).get("message", "")
            except Exception: pass
            last = "HTTP %d %s" % (e.code, reason[:200])
            if e.code < 500 and e.code != 429: break   # キーや上限の問題は、やり直しても同じ
        except Exception as e:
            last = type(e).__name__
        time.sleep(2 * (attempt + 1))
    sys.exit("YouTube APIの呼び出しに失敗しました（%s）：%s" % (path, last.replace(key, "***")))   # キーは記録に出さない

def all_video_ids():
    playlist, ids, token = "UU" + CHANNEL_ID[2:], [], None   # 「アップロード動画」の一覧
    for _ in range(200):   # 念のため、ページ送りの回数に上限をつける
        p = dict(part="contentDetails", playlistId=playlist, maxResults=50)
        if token: p["pageToken"] = token
        d = api("playlistItems", **p)
        ids += [i["contentDetails"]["videoId"] for i in d.get("items", [])]
        token = d.get("nextPageToken")
        if not token: return ids
    sys.exit("動画の一覧が終わりませんでした。")

def fetch_videos():
    ids, out = all_video_ids(), []
    for i in range(0, len(ids), 50):
        d = api("videos", part="snippet", id=",".join(ids[i:i + 50]))
        for it in d.get("items", []):
            if not VID_RE.match(str(it.get("id", ""))): continue   # 形のおかしいIDは使わない
            sn = it["snippet"]
            desc = sn.get("description", "")
            q, gist, items = parse_description(desc)
            found, linked = time_check(desc)
            if found != linked:   # GitHubの実行記録に黄色い注意として出る
                print("::warning::時刻の見落としの疑い：%s（時刻らしい文字 %d 個、リンクにできたのは %d 個）" % (_cmd(sn["title"]), found, linked))
            pub = datetime.fromisoformat(sn["publishedAt"].replace("Z", "+00:00")).astimezone(JST)
            v = {"id": it["id"], "title": sn["title"], "pub": pub.strftime("%Y-%m-%d")}
            qs = parse_questions(desc)
            if any(b["q"] or b["gist"] for b in qs): v["qs"] = qs   # 一般質問：質問ごとのまとまり
            elif items: v["items"] = items
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
    if old and len(old) >= 10 and len(videos) < len(old) * 0.5 and os.environ.get("FORCE_UPDATE") != "1":
        sys.exit("動画の数が前回の%d本から%d本に大きく減ったため、更新を止めました（取得の失敗かもしれません）。"
                 "本当に減った場合は、FORCE_UPDATE=1 をつけて実行してください。" % (len(old), len(videos)))
    rules = load_rules()
    others = [v["title"] for v in videos if classify(v["title"], rules) == "その他"]
    if others:   # 新しい種類の動画が出たら、GitHubの実行記録に青い知らせとして出る
        msg = "%0A".join(_cmd(t) for t in others[:10]) + ("%%0A…ほか%d本" % (len(others) - 10) if len(others) > 10 else "")
        print("::notice title=種類が「その他」の動画（%d本）::新しい種類なら data/kinds.json に1行足してください。%%0A%s" % (len(others), msg))
    if old == videos:
        print("変更なし（%d本）" % len(videos)); return
    data = {"updated": datetime.now(JST).strftime("%Y-%m-%d %H:%M"), "videos": videos}
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:   # 書き込みの途中で止まっても、今のファイルが壊れないようにする
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, OUT)
    print("更新しました（%d本）" % len(videos))

if __name__ == "__main__":
    main()
