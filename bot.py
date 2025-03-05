import os
import ffmpeg
import pandas
import discord
from discord.ext import commands

# —————————————————————————————————————— #

TOKEN = os.getenv('discord_token')

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix=".", intents=intents)

attachments_folder = f"{os.getcwd()}\\Attachments\\"
songs_folder = f"{os.getcwd()}\\Songs\\"

songbook_csv = f"{os.getcwd()}\\Songbook.csv"
songbook = pandas.read_csv(songbook_csv, delimiter=';') 

current_audio = None
loop = True

# —————————————————————————————————————— #

def run_bot():
    @client.event
    async def on_ready():
        print(f"{client.user} is running.")

    # JOIN
    @client.command(name="join", aliases=["j"])
    async def join(ctx):
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()

            await show_songbook(ctx)

    # PLAY
    @client.command(name="play", aliases=["p"])
    async def play(ctx, user_input: str):
        global current_audio
        vc = ctx.voice_client
        file_path = "";
        
        if not vc:
            await ctx.send("Hey! I'm not there yet!")
        else:
            # read songbook
            for index, row in songbook.iterrows():
                group = row.iloc[0];
                theme = row.iloc[1];
                file = row.iloc[2];

                if user_input.lower() == theme.lower():
                    file_path = file;

            # play audio
            if os.path.exists(file_path):
                current_audio = file_path
                
                play_audio(ctx, vc, file_path)
                await show_player(ctx)
            else:
                await ctx.send("Sorry, I can't find that in my songbook.")

    def play_audio(ctx, vc, file_path):
        vc.stop()
        vc.play(
            discord.FFmpegPCMAudio(file_path),
            after=lambda e: check_loop(ctx, vc)
        )

    def check_loop(ctx, vc):
        if loop:
            play_audio(ctx, vc, current_audio)

    # PAUSE
    @client.command(name="pause")
    async def pause(ctx):
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()

    # RESUME 
    @client.command(name="resume")
    async def resume(ctx):
        if not ctx.voice_client.is_playing():
            ctx.voice_client.resume()

    # DISCONNECT
    @client.command(name="disconnect", aliases=["d"])
    async def disconnect(ctx):
        await ctx.voice_client.disconnect()

    # LOOP
    @client.command(name="loop", aliases=["l"])
    async def toggle_loop(ctx):
        global loop
        loop = not loop

    # PLAYER VIEW
    async def show_player(ctx):
        song_title = current_audio.split("\\")[-1].split("(")[0].strip()
        song_category = current_audio.split("\\")[-2]
        song_author = "D&D Breakfast Club"
        song_duration = get_duration(current_audio)

        icon_path = f"{attachments_folder}\\icon.png"
        thumbnail_path = get_thumbnail(current_audio)

        # embed attachments
        files = []

        with open(icon_path, "rb") as icon_file:
            icon = discord.File(icon_file, filename="icon.png")
            files.append(icon)

        if thumbnail_path:
            with open(thumbnail_path, "rb") as thumbnail_file:
                thumbnail = discord.File(thumbnail_file, filename="cover.jpg")
                files.append(thumbnail)

        # embed structure
        embed = discord.Embed(
            title=song_title,
            description=song_category,
            color=discord.Color.red()
        )

        embed.set_author(
            name="Now playing...",
            icon_url="attachment://icon.png"
        )
        embed.set_thumbnail(url="attachment://cover.jpg")

        embed.add_field(name=" ", value=" ", inline=False)
        embed.add_field(name="Author", value=song_author, inline=True)
        embed.add_field(name=" ", value=" ", inline=True)
        embed.add_field(name="Duration", value=song_duration, inline=True)
        
        view=PlayerView(ctx)

        await ctx.send(embed=embed, view=view, files=files)

    class PlayerView(discord.ui.View):
        def __init__(self, ctx):
            super().__init__(timeout=None)
            self.ctx = ctx

        @discord.ui.button(label="Prev.", style=discord.ButtonStyle.secondary)
        async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                await interaction.response.defer()

        @discord.ui.button(label="Pause", style=discord.ButtonStyle.secondary)
        async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                await interaction.response.defer()

                if button.label == "Pause":
                    await pause(self.ctx)
                    button.label = "Resume"
                else:
                    await resume(self.ctx)
                    button.label = "Pause"

                await interaction.edit_original_response(view=self)

        @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
        async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                await interaction.response.defer()

        @discord.ui.button(label="Loop", style=discord.ButtonStyle.success)
        async def loop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                await interaction.response.defer()
                await toggle_loop(self.ctx)

                if loop:
                    button.style = discord.ButtonStyle.success
                else:
                    button.style = discord.ButtonStyle.secondary

                await interaction.edit_original_response(view=self)

    def get_duration(file_path):
        probe = ffmpeg.probe(file_path)
        duration = float(probe['format']['duration'])
        minutes = int(duration // 60)
        seconds = int(duration % 60)

        return f"{minutes}m {seconds:02d}s"

    def get_thumbnail(file_path):
        output_image = f"{attachments_folder}\\cover.jpg"

        # check the file's metadata for a video stream
        probe = ffmpeg.probe(file_path)
        video_streams = [stream for stream in probe['streams'] if stream['codec_type'] == 'video']

        if video_streams:
            (
                ffmpeg
                .input(file_path, ss=1)             # skip to 1 second
                .output(output_image, vframes=1)    # extract one frame only
                .run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
            )

            # return the path of the extracted image
            return output_image  
        else:
            return None

    # SONGBOOK VIEW
    @client.command(name="songbook", aliases=['b'])
    async def show_songbook(ctx):
        embed = discord.Embed(
            title="Do'Lovaas' songbook",
            description="This ancient book is filled with enchanted melodies\nand forgotten secrets, offering every bard the perfect\nsong for any adventure.",
            color=discord.Color.red()
        )

        view = SongbookClosedView(ctx)

        await ctx.send(embed=embed, view=view)

    class SongbookClosedView(discord.ui.View):
        def __init__(self, ctx):
            super().__init__(timeout=None)
            self.ctx = ctx

        @discord.ui.button(label="Open", style=discord.ButtonStyle.secondary)
        async def open(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                embed = discord.Embed(
                    title="Do'Lovaas' songbook",
                    color=discord.Color.red()
                )

                # read songbook
                for index, row in songbook.iterrows():
                    group = row.iloc[0];
                    theme = row.iloc[1];
                    file = row.iloc[2];

                    song_title = file.split("\\")[-1].split("(")[0].strip()

                    embed.add_field(name=theme, value=song_title, inline=False)

                embed.set_footer(text="Page 1/1")

                view=SongbookOpenedView(ctx=self.ctx)
                
                await interaction.response.edit_message(embed=embed, view=view)

    class SongbookOpenedView(discord.ui.View):
        def __init__(self, ctx):
            super().__init__(timeout=None)
            self.ctx = ctx

        @discord.ui.button(label="Prev.", style=discord.ButtonStyle.secondary)
        async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                await interaction.response.defer()

        @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
        async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                await interaction.response.defer()


    client.run(TOKEN)
