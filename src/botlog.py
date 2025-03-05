from datetime import datetime
from functools import wraps
import nextcord
import logging


logging.basicConfig(level=logging.INFO, format="%(message)s")

# Log function calls
def log_calls(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Expand Interaction objects to log meaningful info
        def format_arg(arg):
            if isinstance(arg, nextcord.Interaction):
                user_info = f"user_id={arg.user.id}" if arg.user else "user=None"
                guild_info = f"guild_id={arg.guild.id}" if arg.guild else "guild=None"
                channel_info = f"channel_id={getattr(arg, 'channel_id', 'N/A')}"
                return f"Interaction({user_info}, {guild_info}, {channel_info})"
            elif isinstance(arg, nextcord.Guild):
                return f"Guild(id={arg.id}, name='{arg.name}', member_count={arg.member_count})"
            elif "lavalink.models.DefaultPlayer" in str(type(arg)):
                connected = getattr(arg, 'is_connected', 'N/A')
                playing = getattr(arg, 'is_playing', 'N/A')
                queue_length = len(arg.queue) if hasattr(arg, 'queue') else 'N/A'
                return f"DefaultPlayer(connected={connected}, playing={playing}, queue_length={queue_length})"
            else:
                return repr(arg)
        
        relevant_args = args[1:] if args else args # Skip logging 'self'
        formatted_args = [format_arg(arg) for arg in relevant_args]
        formatted_kwargs = [f"{k}={format_arg(v)}" for k, v in kwargs.items()]
        params = formatted_args + formatted_kwargs

        log_message = f"\n------------------------- {timestamp}\nCalling: {func.__name__}"
        for param in params:
            log_message += f"\n{param}"

        logging.info(log_message)

        result = func(*args, **kwargs)
        return result

    return wrapper

# Log slash command functions calls
def log_slash_command(func):
    original_callback = func.callback

    # Expand Interaction objects to log meaningful info
    def format_arg(arg):
        if isinstance(arg, nextcord.Interaction):
            user_info = f"user_id={arg.user.id}" if arg.user else "user=None"
            guild_info = f"guild_id={arg.guild.id}" if arg.guild else "guild=None"
            channel_info = f"channel_id={getattr(arg, 'channel_id', 'N/A')}"
            return f"Interaction({user_info}, {guild_info}, {channel_info})"
        return repr(arg)

    @wraps(original_callback)
    async def wrapper(*args, **kwargs):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        relevant_args = args[1:] if args else args # Skip logging 'self'
        formatted_args = [format_arg(arg) for arg in relevant_args]
        formatted_kwargs = [f"{k}={format_arg(v)}" for k, v in kwargs.items()]
        params = formatted_args + formatted_kwargs

        log_message = f"\n------------------------- {timestamp}\nCalling: {original_callback.__name__}"
        for param in params:
            log_message += f"\n{param}"
        
        logging.info(log_message)

        result = await original_callback(*args, **kwargs)
        return result

    func.callback = wrapper
    return func