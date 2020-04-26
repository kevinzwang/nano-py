# Nano
The beloved (citation needed) Discord bot, on its 3rd official version and now back to Python! 

## Quick Start
This bot needs Python 3.8+ to run.

First, install all the dependencies:
```
pip install -r requirements.txt
```

Then run the bot:
```
python bot.py
```

## Music
If you would like to run the bot's anime music features, you must first have a Lavalink server running. The best way to do that is to run the Lavalink Docker image using a different server than the one running Nano.

In `application.yml`, change the `server.address` to your Lavalink server IP address and the `lavalink.server.password` to whatever password you desire, then copy that file to the Lavalink server.

Start the server with:
```
docker run --rm --name lavalink -p 2333:2333 -v [absolute path to application.yml]:/opt/Lavalink/application.yml fredboat/lavalink:master-v3
```

After that, follow the quick start instructions to start the bot.