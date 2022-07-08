import nextcord as nxt
from nextcord.ext import commands as cmd

class Help(cmd.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Information/help menu commands
    @cmd.command(aliases=['h'])
    async def help(self, ctx, *, command=''):
        # Create embed and set border color
        help_menu = nxt.Embed(color=nxt.Color.from_rgb(134, 194, 50))
        
        # Default help menu
        if command == '':
            help_menu.description = (
                '**Standard Commands** \n'
                '`play`, `stop`, `pause`, `resume`, `skip`, `restart`, `seek`, `volume`, `song`, `queue`, `repeat`, `shuffle`, `remove`, `help`, `links` \n\n'

                '**Premium Commands** \n'
                '`search`, `lyrics`, `equalizer`, `prefix` \n\n'

                '**Command Details** \n'
                '`help <command name>` \n\n'
            )
        
        # Play command details/help menu
        elif command == 'play' or command == 'p':
            help_menu.description = (
                '**Command: Play** \n'
                'Play a song or, if a song is already playing, add to the queue. \n\n'

                '**Syntax** \n'
                '`play <song title and artist>` \n\n'

                '**Aliases** \n'
                '`play` \n'
                '`p` \n\n'
            )
        
        # Stop command details/help menu
        elif command == 'stop' or command == 'st':
            help_menu.description = (
                '**Command: Stop** \n'
                'Stop audio playback, clear queue and disconnect. \n\n'

                '**Aliases** \n'
                '`stop` \n'
                '`st` \n\n'
            )
        
        # Pause command details/help menu
        elif command == 'pause' or command == 'ps':
            help_menu.description = (
                '**Command: Pause** \n'
                'Pause audio playback. Use the `resume` command to continue playing. \n\n'

                '**Aliases** \n'
                '`pause` \n'
                '`ps` \n\n'
            )
        
        # Resume command details/help menu
        elif command == 'resume' or command == 'rs':
            help_menu.description = (
                '**Command: Resume** \n'
                'Resume audio playback after audio has been paused with the `pause` command. \n\n'

                '**Aliases** \n'
                '`resume` \n'
                '`rs` \n\n'
            )
        
        # Skip command details/help menu
        elif command == 'skip' or command == 'sk':
            help_menu.description = (
                '**Command: Skip** \n'
                'Skip the current song. \n\n'

                '**Aliases** \n'
                '`skip` \n'
                '`sk` \n\n'
            )

        # Restart command details/help menu
        elif command == 'restart' or command == 're':
            help_menu.description = (
                '**Command: Restart** \n'
                'Return to the beginning of the current song. \n\n'

                '**Aliases** \n'
                '`restart` \n'
                '`re` \n\n'
            )
        
        # Seek command details/help menu
        elif command == 'seek' or command == 'se':
            help_menu.description = (
                '**Command: Seek** \n'
                'Seek to position in song. \n\n'

                '**Syntax** \n'
                '`seek <position in seconds>`'

                '**Aliases** \n'
                '`seek` \n'
                '`se` \n\n'
            )
        
        # Song command details/help menu
        elif command == 'song' or command == 'sn':
            help_menu.description = (
                '**Command: Song** \n'
                'Get the title of the current song. \n\n'

                '**Aliases** \n'
                '`song` \n'
                '`sn` \n\n'
            )
        
        # Queue command details/help menu
        elif command == 'queue' or command == 'q':
            help_menu.description = (
                '**Command: Queue** \n'
                'Get a list of all songs currently in the queue. \n\n'

                '**Aliases** \n'
                '`queue` \n'
                '`q` \n\n'
            )

        # Repeat command details/help menu
        elif command == 'repeat' or command == 'rp':
            help_menu.description = (
                '**Command: Repeat** \n'
                'Turn repeat on or off. \n\n'

                '**Aliases** \n'
                '`repeat` \n'
                '`rp` \n\n'
            )

        # Shuffle command details/help menu
        elif command == 'shuffle' or command == 'sh':
            help_menu.description = (
                '**Command: Shuffle** \n'
                'Turn shuffle on or off. \n\n'

                '**Aliases** \n'
                '`shuffle` \n'
                '`sh` \n\n'
            )

        # Remove command details/help menu
        elif command == 'remove' or command == 'rm':
            help_menu.description = (
                '**Command: Remove** \n'
                'Remove a song from the queue. Use the `queue` command to see track numbers. \n\n'

                '**Syntax** \n'
                '`remove <track number>` \n\n'

                '**Aliases** \n'
                '`remove` \n'
                '`rm` \n\n'
            )

        # Help command details/help menu
        elif command == 'help' or command == 'h':
            help_menu.description = (
                '**Command: Help** \n'
                'Get a list of all available commands. \n\n'

                '**Aliases** \n'
                '`help` \n'
                '`h` \n\n'
            )
        
        # Links command details/help menu
        elif command == 'links' or command == 'ln':
            help_menu.description = (
                '**Command: Links** \n'
                'Get a list of active links. \n\n'

                '**Aliases** \n'
                '`links` \n'
                '`li` \n\n'
            )

        # Lyrics command details/help menu
        elif command == 'lyrics' or command == 'l':
            help_menu.description = (
                '**Command: Lyrics** \n'
                'Get the lyrics of any song. \n\n'

                '**Syntax** \n'
                '`lyrics <song title and artist>` \n\n'

                '**Aliases** \n'
                '`lyrics` \n'
                '`l` \n\n'
            )

        # Volume command details/help menu
        elif command == 'volume' or command == 'vol' or command == 'v':
            help_menu.description = (
                '**Command: Volume** \n'
                'Change audio playback volume by adjusting Tempo\'s input volume. This does not affect the output \'User Volume\' slider set by individual server members. \n\n'

                '**Syntax** \n'
                '`volume <0 - 100>` \n\n'

                '**Aliases** \n'
                '`volume` \n'
                '`vol` \n'
                '`v` \n\n'
            )

        # Interface command details/help menu
        elif command == 'interface' or command == 'if':
            help_menu.description = (
                '**Command: Interface** \n'
                'Get a GUI for the music player in chat. GUI contains pause, resume, skip and stop buttons. \n\n'

                '**Aliases** \n'
                '`interface` \n'
                '`if` \n\n'
            )
        
        # Search command details/help menu
        elif command == 'search' or command == 'sr':
            help_menu.description = (
                '**Command: Search** \n'
                'Get a list of songs and choose which one to play. \n\n'

                '**Syntax** \n'
                '`search <song title and artist>` \n\n'

                '**Aliases** \n'
                '`search` \n'
                '`sr` \n\n'
            )
        
        # Equalizer command details/help menu
        elif command == 'equalizer' or command == 'eq':
            help_menu.description = (
                '**Command: Equalizer** \n'
                'Choose from a list of equalizer presets for a unique listening experience. \n\n'

                '**Aliases** \n'
                '`equalizer` \n'
                '`eq` \n\n'
            )
        
        # Prefix command details/help menu
        elif command == 'prefix' or command == 'pf':
            help_menu.description = (
                '**Command: Prefix** \n'
                'Change the default command prefix from \'!\' to a custom character of your choice. Your custom prefix is limited to two characters in length and must be composed of standard keyboard characters. This command can only be used by the server admin. \n\n'

                '**Syntax** \n'
                '`prefix <custom characters>` \n\n'

                '**Aliases** \n'
                '`prefix` \n'
                '`pf` \n\n'
            )

        # Command help details/help menu
        else:
            help_menu.description = (
                f'**Unknown Command: {command}** \n'
                'Try `help play` for information on the `play` command. \n\n'

                '**Syntax** \n'
                '`help <command name>` \n\n'

                '**Aliases** \n'
                '`help` \n'
                '`h` \n\n'
            )
        
        # Send help message to text channel
        await ctx.channel.send(embed=help_menu)
        
# Add cog
def setup(bot):
    bot.add_cog(Help(bot))