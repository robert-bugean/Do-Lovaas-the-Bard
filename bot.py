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

    queues = {}
    voice_channels = {}
    

    @client.event
    async def on_ready():
        print(f'{client.user} is running')


    async def play_next(ctx):
        if queues[ctx.guild.id] != []:
            link = queues[ctx.guild.id].pop(0)
            await play(ctx, link=link)


    @client.command(name="play", aliases=["p"])
    async def play(ctx, *, link):
        try:
            # connect to the voice channel
            voice_channel = await ctx.author.voice.channel.connect()
            voice_channels[voice_channel.guild.id] = voice_channel
        except Exception as e:
            print(e)

        try:
            # treat the user input as a search query, if it's not a youtube link
            if youtube_base_url not in link:
                query_string = urllib.parse.urlencode({'search_query': link})
                content = urllib.request.urlopen(youtube_results_url + query_string)
                search_results = re.findall(r'/watch\?v=(.{11})', content.read().decode())
                link = youtube_watch_url + search_results[0]

            # extract the audio
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))
            player = discord.FFmpegOpusAudio(data['url'], **ffmpeg_options)

            # play all the songs in queue
            voice_channels[ctx.guild.id].play(player,
                after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop)
            )
            
            await show_embed(ctx, data, link)
        except Exception as e:
            print(e)


    @client.command(name="pause")
    async def pause(ctx):
        try:
            voice_channels[ctx.guild.id].pause()
        except Exception as e:
            print(e)


    @client.command(name="resume")
    async def resume(ctx):
        try:
            voice_channels[ctx.guild.id].resume()
        except Exception as e:
            print(e)


    @client.command(name="stop")
    async def stop(ctx):
        try:
            voice_channels[ctx.guild.id].stop()
            
            await voice_channels[ctx.guild.id].disconnect()
            del voice_channels[ctx.guild.id]
        except Exception as e:
            print(e)

    
    @client.command(name="skip")
    async def skip(ctx):
        try:
            voice_channels[ctx.guild.id].stop()
            await play_next(ctx)
        except Exception as e:
            print(e)


    @client.command(name="queue", aliases=["q"])
    async def queue(ctx, *, url):
        if ctx.guild.id not in queues:
            queues[ctx.guild.id] = []
        
        queues[ctx.guild.id].append(url)
        await ctx.send("Added to queue!")


    @client.command(name="clear", aliases=["c"])
    async def clear_queue(ctx):
        if ctx.guild.id in queues:
            queues[ctx.guild.id].clear()
            await ctx.send("Queue cleared!")
        else:
            await ctx.send("There is no queue to clear")


    async def show_embed(ctx, data, link):
        embed = discord.Embed(title="Now Playing", description=f"[{data['title']}]({link})", color=0x5865f2)
        embed.add_field(name="Duration", value=str(data['duration']) + " seconds")
        embed.add_field(name="Author", value=data.get('uploader', 'Unknown'))
        embed.set_thumbnail(url=data['thumbnail'])

        view = EmbedButtons(ctx)
        await ctx.send(embed=embed, view=view)


    class EmbedButtons(discord.ui.View):
        def __init__(self, ctx):
            super().__init__(timeout=None)
            self.ctx = ctx

        @discord.ui.button(label='Pause', style=discord.ButtonStyle.secondary)
        async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                await interaction.response.defer()
                await pause(self.ctx)

        @discord.ui.button(label='Stop', style=discord.ButtonStyle.blurple)
        async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                await interaction.response.defer()
                await stop(self.ctx)

        @discord.ui.button(label='Skip', style=discord.ButtonStyle.secondary)
        async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                await interaction.response.defer()
                await skip(self.ctx)


    client.run(TOKEN)