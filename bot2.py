import asyncio
import discord
import os
import urllib.parse, urllib.request, re
import yt_dlp
from discord.ext import commands
from dotenv import load_dotenv


def run_bot():
    load_dotenv()
    TOKEN = os.getenv('discord_token')
    intents = discord.Intents.default()
    intents.message_content = True
    client = commands.Bot(command_prefix=".", intents=intents)

    youtube_base_url = 'https://www.youtube.com/'
    youtube_results_url = youtube_base_url + 'results?'
    youtube_watch_url = youtube_base_url + 'watch?v='
    yt_dl_options = {"format": "bestaudio/best"}
    ytdl = yt_dlp.YoutubeDL(yt_dl_options)

    ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn -filter:a "volume=0.25"'}

    global voice_channel
    queue = []


    @client.event
    async def on_ready():
        print(f'{client.user} is running')


    @client.command(name="play", aliases=["p"])
    async def play(ctx, *, link):
        global voice_channel

        # connect to the voice channel
        voice_channel = ctx.author.voice.channel if ctx.author.voice else None

        if not voice_channel:
            return await ctx.send("You are not in a voice channel!")

        if not ctx.voice_client:
            voice_channel = await voice_channel.connect()

        try:
            # treat the user input as a search query, if it's not a youtube link
            if youtube_base_url not in link:
                query_string = urllib.parse.urlencode({'search_query': link})
                content = urllib.request.urlopen(youtube_results_url + query_string)
                search_results = re.findall(r'/watch\?v=(.{11})', content.read().decode())
                link = youtube_watch_url + search_results[0]

            # queue the song
            queue.append(link)

            if not ctx.voice_client.is_playing():
                link = queue.pop(0)
                
                # extract the audio
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))
                player = discord.FFmpegOpusAudio(data['url'], **ffmpeg_options)

                # play the song
                voice_channel.play(player,
                    after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop)
                )
            else:
                await ctx.send("Added to queue!")
        except Exception as e:
            print(e)


    async def play_next(ctx):
        if queue != []:
            link = queue.pop(0)
            await play(ctx, link=link)


    @client.command(name="pause")
    async def pause(ctx):
        try:
            voice_channel.pause()
        except Exception as e:
            print(e)


    @client.command(name="resume")
    async def resume(ctx):
        try:
            voice_channel.resume()
        except Exception as e:
            print(e)


    @client.command(name="stop")
    async def stop(ctx):
        try:
            voice_channel.stop()
            await voice_channel.disconnect()
        except Exception as e:
            print(e)


    client.run(TOKEN)