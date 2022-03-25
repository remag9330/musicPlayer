%from song import DownloadState

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
        <div id="queue">
            <form method="POST" action="/queue">
                <label id="queue_url_label">URL<input name="url" type="text" placeholder="URL to queue" /></label>
                <label id="queue_priority_label">Play Next<input name="priority" type="checkbox" /></label>
                <button id="queue_submit" type="submit">Queue</button>
            </form>
        </div>

        <div id="playing">
            <img src="data:image/jpg;base64, {{song_queue.currently_playing.song.thumbnail_base64()}}" alt="{{song_queue.currently_playing.song.name}}" />
            <div>{{song_queue.currently_playing.song.name}}</div>
            <div>{{song_queue.currently_playing.current_elapsed_time_human_readable()}} / {{song_queue.currently_playing.song.length_human_readable()}}</div>
            <div id="playing_controls">
                <form method="POST" action="/pause">
                    <button type="submit">Pause</button>
                </form>
                <form method="POST" action="/play">
                    <button type="submit">Play</button>
                </form>
                <form method="POST" action="/skip">
                    <button type="submit">Skip</button>
                </form>
                <form method="POST" action="/volume">
                    <button type="submit" name="direction" value="up">Vol. Up</button>
                </form>
                <form method="POST" action="/volume">
                    <button type="submit" name="direction" value="down">Vol. Down</button>
                </form>
                <span>Volume: {{current_volume}}%
            </div>
        </div>

        <div id="upcoming">
            %if len(song_queue.up_next) > 0:
                <span>Up next:</span>
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
                <span>Nothing queued, playing random songs - go queue something!</span>
            %end
        </div>
    </body>
</html>