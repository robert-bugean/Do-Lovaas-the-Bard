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

    queue = []

    global cursor, loop
    cursor = 0
    loop = False
        
    youtube_base_url = 'https://www.youtube.com/'
    youtube_results_url = youtube_base_url + 'results?'
    youtube_watch_url = youtube_base_url + 'watch?v='
    yt_dl_options = {"format": "bestaudio/best"}
    ytdl = yt_dlp.YoutubeDL(yt_dl_options)

    ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn -filter:a "volume=0.25"'}

        
    @client.event
    async def on_ready():
        print(f'{client.user} is running')


    @client.command(name="play", aliases=["p"])
    async def play(ctx, *, link):
        global cursor
        
        # connect to the voice channel
        voice_channel = ctx.author.voice.channel if ctx.author.voice else None

        if not voice_channel:
            return await ctx.send("You are not in a voice channel!")

        if not ctx.voice_client:
            await voice_channel.connect()
            
            queue = []
            cursor = 0

        try:
            async with ctx.typing():
                # treat the user input as a search query if it's not a youtube link
                if youtube_base_url not in link:
                    query_string = urllib.parse.urlencode({'search_query': link})
                    content = urllib.request.urlopen(youtube_results_url + query_string)
                    search_results = re.findall(r'/watch\?v=(.{11})', content.read().decode())
                                     
                    link = youtube_watch_url + search_results[0]

                # add the song to the queue
                if link not in queue:
                    queue.append(link)

                if not ctx.voice_client.is_playing():
                    # extract the audio
                    event_loop = asyncio.get_event_loop()
                    data = await event_loop.run_in_executor(None, lambda: ytdl.extract_info(queue[cursor], download=False))
                    player = discord.FFmpegOpusAudio(data['url'], **ffmpeg_options)

                    # play the song
                    ctx.voice_client.play(player,
                        after=lambda e: asyncio.run_coroutine_threadsafe(loop_current(ctx), client.loop)
                    )
                    
                    await show_embed(ctx, data, link)
                else:
                    await ctx.send("Added to queue!")
        except Exception as e:
            print(e)


    async def loop_current(ctx):
        if loop:
            await play(ctx, link=queue[cursor])
        else:
            ctx.voice_client.stop()


    @client.command(name="previous")
    async def previous(ctx):
        global cursor
        
        if (cursor - 1) >= 0:
            cursor -= 1
        else:
            return

        try:
            ctx.voice_client.stop()
            await play(ctx, link=queue[cursor])
        except Exception as e:
            print(e)


    @client.command(name="next")
    async def next(ctx):
        global cursor
        
        if (cursor + 1) < len(queue):
            cursor += 1
        else:
            return
        
        try:
            ctx.voice_client.stop()
            await play(ctx, link=queue[cursor])
        except Exception as e:
            print(e)
            

    @client.command(name="pause")
    async def pause(ctx):
        try:
            if ctx.voice_client.is_playing():
                ctx.voice_client.pause()
            else:
                await ctx.send("Nothing to pause!")
        except Exception as e:
            print(e)


    @client.command(name="resume")
    async def resume(ctx):
        try:
            if not ctx.voice_client.is_playing():
                ctx.voice_client.resume()
            else:
                await ctx.send("Nothing to resume!")
        except Exception as e:
            print(e)


    @client.command(name="stop")
    async def stop(ctx):
        try:
            await ctx.voice_client.disconnect()
        except Exception as e:
            print(e)


    @client.command(name="loop")
    async def loop_toggle(ctx):
        global loop
        loop = not loop


    async def show_embed(ctx, data, link):
        with open("icon.png", "rb") as icon_file:
            icon = discord.File(icon_file, filename="icon.png")

        embed = discord.Embed(
            title=f"{data['title']}\n{link}",
            color=discord.Color.red()
        )
        
        embed.add_field(name="Duration", value=str(data['duration']) + " seconds")
        embed.add_field(name="Author", value=data.get('uploader', 'Unknown'))
        embed.set_thumbnail(url=data['thumbnail'])
    
        embed.set_author(
            name="Now playing...",
            icon_url="attachment://icon.png"
        )

        await ctx.send(embed=embed, view=EmbedButtons(ctx), file=icon)


    class EmbedButtons(discord.ui.View):
        def __init__(self, ctx):
            super().__init__(timeout=None)
            self.ctx = ctx


        @discord.ui.button(label='Prev.', style=discord.ButtonStyle.secondary)
        async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                await interaction.response.defer()
                await previous(self.ctx)

        @discord.ui.button(label='Pause', style=discord.ButtonStyle.secondary)
        async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                await interaction.response.defer()
                await pause(self.ctx)

        @discord.ui.button(label='Stop', style=discord.ButtonStyle.danger)
        async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                await interaction.response.defer()
                await stop(self.ctx)

        @discord.ui.button(label='Next', style=discord.ButtonStyle.secondary)
        async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                await interaction.response.defer()
                await next(self.ctx)

        @discord.ui.button(label='Loop', style=discord.ButtonStyle.secondary)
        async def loop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            global loop
            
            if interaction.user == self.ctx.author:
                await interaction.response.defer()
                await loop_toggle(self.ctx)

                button.style = discord.ButtonStyle.success if loop else discord.ButtonStyle.secondary
                await interaction.edit_original_response(view=self)


    client.run(TOKEN)
