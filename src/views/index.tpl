%from song import DownloadState
%from playing_song import PlayingState
%from playlist import FilePlaylist

<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8" >
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>Home Music Player</title>

        <link href="static/styles.css" rel="stylesheet"></link>
        <script src="static/mp.js" type="text/javascript"></script>
    </head>

    <body>
        <div id="login">
            %if username is None:
                🔑 <a href="/login">Login</a>
            %else:
                🔑 {{username}}
            %end
        </div>

        <h1>Music Player</h1>

        <div id="queue">
            <h2>Queue</h2>
            <form id="queue_inputs" method="GET" action="/songs">
                <input id="queue_input" name="search" type="text" placeholder="Search for a song" />
                <button type="submit">🔍</button>
            </form>
        </div>

        <div id="playing">
            <h2>Currently Playing</h2>
            <img src="data:image/jpg;base64, {{song_queue.currently_playing.song.thumbnail_base64()}}" alt="{{song_queue.currently_playing.song.name}}" />
            <div>{{song_queue.currently_playing.song.name}}</div>
            <div>{{song_queue.currently_playing.current_elapsed_time_human_readable()}} / {{song_queue.currently_playing.song.length_human_readable()}}</div>
            <div id="playing_controls" class="controls">
                %if song_queue.currently_playing.playing_state == PlayingState.Playing:
                    <form method="POST" action="/pause">
                        <button type="submit">⏸</button>
                    </form>
                %else:
                    <form method="POST" action="/play">
                        <button type="submit">▶</button>
                    </form>
                %end

                <form method="POST" action="/skip">
                    <button type="submit">⏭</button>
                </form>

                <span>
                    %if current_volume == 0:
                        🔈
                    %elif current_volume < 0.4:
                        🔉
                    %else:
                        🔊
                    %end
                </span>
                <form id="volume_form" method="POST" action="/volume">
                    %(vol_min, vol_max, vol_step) = vol_min_max_step
                    <input type="range" name="volume" min="{{vol_min}}" max="{{vol_max}}" step="{{vol_step}}" value="{{current_volume}}">
                    <button type="submit">✔</button>
                </form>
            </div>

            %if username is not None:
                <div id="user_rating">
                    <form method="POST" action="/rateSong">
                        <input type="hidden" name="song_name" value="{{song_queue.currently_playing.song.name}}" />
                        <button type="submit" name="rating" value="1">{{"⭐" if rating and rating >= 1 else "☆"}}</button>
                        <button type="submit" name="rating" value="2">{{"⭐" if rating and rating >= 2 else "☆"}}</button>
                        <button type="submit" name="rating" value="3">{{"⭐" if rating and rating >= 3 else "☆"}}</button>
                        <button type="submit" name="rating" value="4">{{"⭐" if rating and rating >= 4 else "☆"}}</button>
                        <button type="submit" name="rating" value="5">{{"⭐" if rating and rating >= 5 else "☆"}}</button>
                    </form>
                </div>
            %end
        </div>

        <div id="upcoming">
            <h2>Upcoming</h2>
            %if len(song_queue.up_next) > 0:
                <ol>
                    %for s in song_queue.up_next:
                        <li>
                            <img src="data:image/jpg;base64, {{s.thumbnail_base64()}}" alt="{{s.name}}" />
                            <span>{{s.name}}</span>
                            %if s.downloading == DownloadState.Downloading:
                            <span>Downloading ({{s.download_percentage}}%)...</span>
                            %elif s.downloading == DownloadState.Error:
                            <span>Error downloading (See logs)</span>
                            %end
                        </li>
                    %end
                </ol>
            %else:
                <div>Nothing queued, playing songs from the playlist - go queue something!</div>
            %end
        </div>

        <div id="playlist">
            <h2>Playlist</h2>
            
            <form method="POST" action="/playlist">
                <label for="playlist_selector">Change playlist:</label>
                <select id="playlist_selector" name="playlist">
                    %for playlist in FilePlaylist.all_available_playlist_names():
                        %selected = "selected" if playlist == song_queue.playlist.name else ""
                        <option value="{{playlist}}" {{selected}}>{{playlist}}</option>
                    %end
                </select>
                
                <label for="playlist_shuffle">Shuffle</label>
                <input id="playlist_shuffle" name="shuffle" type="checkbox" {{"checked" if song_queue.playlist.shuffle else ""}} />

                <button type="submit">Change Playlist</button>
            </form>

            <form method="POST" action="createPlaylist">
                <label for="playlist_create_input">Create Playlist</label>
                <input id="playlist_create_input" name="url" placeholder="URL" />
                <button type="submit">Create Playlist</button>
            </form>
        </div>
    </body>
</html>