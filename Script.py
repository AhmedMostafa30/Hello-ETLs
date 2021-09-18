from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import urllib.parse as p
import re
import os
import pickle

from pandas.core.frame import DataFrame

# SCOPES is a list of scopes of using YouTube API, we're using this one to be able to view all YouTube data without any problems.
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

def youtube_authenticate():
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    api_service_name = "youtube"
    api_version = "v3"
    client_secrets_file = "credentials.json"
    creds = None
    # the file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    # if there are no (valid) credentials availablle, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
            creds = flow.run_local_server(port=0)
        # save the credentials for the next run
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return build(api_service_name, api_version, credentials=creds)
    
youtube = youtube_authenticate()

def get_videos_urls_from_playlist(playlist_url):    
    """
    Return a list conataining videos urls from the playlist url
    """
    import googleapiclient.discovery
    from urllib.parse import parse_qs, urlparse
    #extract playlist id from url
    url = playlist_url
    query = parse_qs(urlparse(url).query, keep_blank_values=True)
    playlist_id = query["list"][0]

    # print(f'get all playlist items links from {playlist_id}')
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey = "AIzaSyBsNGOvfW7H_lf1T8xRbY1Y3Xox-95CqBE")

    request = youtube.playlistItems().list(
        part = "snippet",
        playlistId = playlist_id,
        maxResults = 50
    )
    response = request.execute()

    playlist_items = []
    videos_urls = []
    while request is not None:
        response = request.execute()
        playlist_items += response["items"]
        request = youtube.playlistItems().list_next(request, response)

    # print(f"total: {len(playlist_items)}")
    for t in playlist_items:
        videos_urls += {f'https://www.youtube.com/watch?v={t["snippet"]["resourceId"]["videoId"]}&list={playlist_id}&t=0s'}
    # print([ 
    #     f'https://www.youtube.com/watch?v={t["snippet"]["resourceId"]["videoId"]}&list={playlist_id}&t=0s'
    #     for t in playlist_items
    # ])
    return videos_urls

def get_video_id_by_url(url):
    """
    Return the Video ID from the video `url`
    """
    # split URL parts
    parsed_url = p.urlparse(url)
    # get the video ID by parsing the query of the URL
    video_id = p.parse_qs(parsed_url.query).get("v")
    if video_id:
        return video_id[0]
    else:
        raise Exception(f"Wasn't able to parse video URL: {url}")

def get_video_details(youtube, **kwargs):
    return youtube.videos().list(
        part="snippet,contentDetails,statistics",
        **kwargs
    ).execute()

def video_infos(video_response):
    items = video_response.get("items")[0]
    # get the snippet, statistics & content details from the video response
    snippet           = items["snippet"]
    # statistics      = items["statistics"]
    # content_details = items["contentDetails"]
    # get infos from the snippet
    # channel_title = snippet["channelTitle"]
    title         = snippet["title"]
    # description   = snippet["description"]
    # publish_time  = snippet["publishedAt"]
    # get stats infos
    # comment_count = statistics["commentCount"]
    # like_count    = statistics["likeCount"]
    # dislike_count = statistics["dislikeCount"]
    # view_count    = statistics["viewCount"]
    # get duration from content details
    # duration = content_details["duration"]
    # duration in the form of something like 'PT5H50M15S'
    # parsing it to be something like '5:50:15'
    # parsed_duration = re.search(f"PT(\d+H)?(\d+M)?(\d+S)", duration).groups()
    # duration_str = ""
    # for d in parsed_duration:
    #     if d:
    #         duration_str += f"{d[:-1]}:"
    # duration_str = duration_str.strip(":")
    # print(f"""\
    # Title: {title}
    # Description: {description}
    # Channel Title: {channel_title}
    # Publish time: {publish_time}
    # Duration: {duration_str}
    # Number of comments: {comment_count}
    # Number of likes: {like_count}
    # Number of dislikes: {dislike_count}
    # Number of views: {view_count}
    # """)
    return title
def get_comments(youtube, **kwargs):
    return youtube.commentThreads().list(
        part="snippet",
        **kwargs
    ).execute()

playlist_url = 'https://www.youtube.com/playlist?list=PLLasX02E8BPArtrhIH0FP8bJU2odUbNR7'

def prepare_JSON_file (playlist_url):
    import json
    videos_urls = get_videos_urls_from_playlist(playlist_url)
    rowObject = []
    video_number = 1
    for video_url in videos_urls:
        video_id = get_video_id_by_url(video_url)
        response = get_video_details(youtube, id=video_id)
        video_title = video_infos(response)
        if "watch" in video_url:
            # that's a video
            # video_id = get_video_id_by_url(url)
            params = {
                'videoId': video_id, 
                'maxResults': 10,
                'order': 'relevance', # default is 'time' (newest)
            }
        # get the first 2 pages (2 API requests)
        n_pages = 1
        for i in range(n_pages):
            # make API call to get all comments from the channel (including posts & videos)
            response = get_comments(youtube, **params)
            items = response.get("items")
            # print(f'items size = {len(items)}')
            # if items is empty, breakout of the loop
            if not items:
                break
            comment_data = []
            for item in items:
                comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
                # comment = item.snippet.topLevelComment.snippet.textDisplay
                updated_at = item["snippet"]["topLevelComment"]["snippet"]["updatedAt"]
                # like_count = item["snippet"]["topLevelComment"]["snippet"]["likeCount"]
                # comment_id = item["snippet"]["topLevelComment"]["id"]
                comment_author = item["snippet"]["topLevelComment"]["snippet"]["authorDisplayName"]
                comment_data.append({"Comment Text": comment, "Updated At": updated_at, "Comment Author": comment_author})
                # print(f"""\
                # Comment: {comment}
                # Likes: {like_count}
                # Updated At: {updated_at}
                # Comment Author: {comment_author}
                # ==================================\
                # """)
            if "nextPageToken" in response:
                # if there is a next page
                # add next page token to the params we pass to the function
                params["pageToken"] =  response["nextPageToken"]
            else:
                # must be end of comments!!!!
                break
            # print("*"*70)
        # print(f'comment data size: {len(comment_data)}')
        if len(items):
            for comment in comment_data:
                rowObject.append({"Video Number": video_number, "Video ID" : video_id, "Video Title": video_title ,"Comment Text": comment["Comment Text"], "Comment Author": comment["Comment Author"], "Comment Date": comment["Updated At"]})
        video_number+=1
    
    jsonString = json.dumps(rowObject)
    jsonFile = open("data.json", "w")
    jsonFile.write(jsonString)
    jsonFile.close()

def view_data():
    #from IPython.display import display
    import pandas as pd
    from IPython.display import HTML
    import json
    # df = pd.DataFrame({'Vedio Number': ""})
    # print(df)
    file = open('data.json',)
    data = json.load(file)
    df = pd.DataFrame(data)
    print(df)
    # df.style
    # for i in data:
    #     print(i['Comment Text'])

def main():
    prepare_JSON_file(playlist_url)
    view_data()

if __name__ == "__main__":
    main()