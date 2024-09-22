<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8" >
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>Login - Home Music Player</title>
        <link href="static/styles.css" rel="stylesheet"></link>
    </head>

    <body>
        <h1>Login</h1>

        %if error_message is not None:
            <div id="error">{{error_message}}</div>
        %end
        
        <form method="POST" action="/login" class="simple_form">
            <label>
                Username
                <input name="username" />
            </label>

            <label>
                Password
                <input name="password" type="password" />
            </label>

            <button type="submit">Log in</button>
        </form>

        <a href="/">Back to Music Player</a>
    </body>
</html>