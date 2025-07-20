<%
page_link_url = lambda search, page: f"?search={search}&page={page}" if search else f"?page={page}"
%>

<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8" >
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>All Songs - Home Music Player</title>

        <link href="static/styles.css" rel="stylesheet"></link>
    </head>

    <body>
        <h1>All Songs</h1>
        <a href="/" class="centre top_spacing bottom_spacing">Back to Queue</a>

        <form id="search" method="GET" action="/songs" class="flex_and_centre">
            <input type="text" name="search" value="{{search}}" placeholder="Search for a song" class="flex_fill" />
            <button type="submit">🔍</button>
        </form>

        <ul id="upcoming">
            % for s in songs:
                % # Can be either a Song or a SearchResult, so act accordingly:
                % if hasattr(s, "downloading"):
                    <li class="flex_and_centre">
                        <img src="data:image/jpg;base64, {{s.thumbnail_base64()}}" alt="{{s.name}}" />
                        <span class="flex_fill">{{s.name}}</span>
                        <span>
                            <form method="POST" action="/songs/play">
                                <input type="hidden" name="id" value="{{s.id}}" />
                                <input type="hidden" name="search" value="{{search}}" />
                                <input type="hidden" name="page" value="{{current_page}}" />
                                <button type="submit">▶</button>
                            </form>
                        </span>
                        <span>
                            <!-- <form method="POST" action="/songs/delete">
                                <input type="hidden" name="id" value="{{s.id}}" />
                                <input type="hidden" name="search" value="{{search}}" />
                                <button type="submit">❌</button>
                            </form> -->
                        </span>
                    </li>
                % else:
                    <li class="flex_and_centre">
                        <img src="{{s.thumbnail}}" alt="{{s.title}}" />
                        <span class="flex_fill">{{s.title}}</span>
                        <span>
                            <form method="POST" action="/queue">
                                <input type="hidden" name="url" value="https://www.youtube.com/watch?v={{s.video_id}}" />
                                <input type="hidden" name="search" value="{{search}}" />
                                <button type="submit">⬇▶</button>
                            </form>
                        </span>
                    </li>
                % end
            % end
        </ul>

        <div class="centre top_spacing bottom_spacing">
            % if youtube_searched:
                <span>Includes search results from YouTube</span>
            % else:
                <a href="{{page_link_url(search, 1) + '&forceSearchYoutube=true'}}">Include search results from YouTube</a>
            % end
        </div>

        <div class="centre">
            % if current_page > 1:
                <a href="{{page_link_url(search, 1)}}">First</a>
                <a href="{{page_link_url(search, current_page - 1)}}">Prev</a>
            % end
            <span>Page {{current_page}} / {{total_pages}}</span>
            % if current_page < total_pages:
                <a href="{{page_link_url(search, current_page + 1)}}">Next</a>
                <a href="{{page_link_url(search, total_pages)}}">Last</a>
            %end
        </div>
    </body>
</html>