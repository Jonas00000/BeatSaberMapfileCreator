from ytmusicapi import YTMusic


def get_ytmusic_link(query):
    ytmusic = YTMusic()

    try:
        results = ytmusic.search(query, filter="songs", limit=3)

        if not results:
            return None
        return [(
            f"https://music.youtube.com/watch?v={res['videoId']}",
            ", ".join([a["name"] for a in res["artists"]]),
            res["title"]
        ) for res in results]

    except Exception:
        return []

