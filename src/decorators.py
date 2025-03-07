import nextcord
import pprint
import logging
import asyncio
from datetime import datetime
from functools import wraps
from tokens import *


logging.basicConfig(level=logging.INFO, format="%(message)s")

# Log function calls
def log_calls(func):
    # Enhanced helper function for formatting arguments in a human-readable way.
    def format_arg(arg):
        if isinstance(arg, nextcord.Interaction):
            user_info = f"user_id={arg.user.id}, user_name={arg.user.name}" if arg.user else "user=None"
            guild_info = f"guild_id={arg.guild.id}, guild_name={arg.guild.name}" if arg.guild else "guild=None"
            channel_info = f"channel_id={getattr(arg, 'channel_id', 'N/A')}"
            return f"Interaction({user_info}, {guild_info}, {channel_info})"
        elif isinstance(arg, nextcord.Guild):
            return f"Guild(id={arg.id}, name='{arg.name}', member_count={arg.member_count})"
        elif "lavalink.models.DefaultPlayer" in str(type(arg)):
            connected = getattr(arg, 'is_connected', 'N/A')
            playing = getattr(arg, 'is_playing', 'N/A')
            queue_length = len(arg.queue) if hasattr(arg, 'queue') else 'N/A'
            queue_info = None
            if hasattr(arg, 'queue') and arg.queue:
                # Show the titles of the first two tracks in the queue, if available.
                queue_info = [getattr(track, 'title', 'Unknown') for track in arg.queue[:2]]
            return (f"DefaultPlayer(connected={connected}, playing={playing}, "
                    f"queue_length={queue_length}, queue={queue_info})")
        elif isinstance(arg, (dict, list)):
            return pprint.pformat(arg, indent=2)
        elif hasattr(arg, "__dict__"):
            return pprint.pformat(arg.__dict__, indent=2)
        else:
            return repr(arg)

    # Create the logging message with a timestamp and expanded parameters.
    def log_execution(callback_name, args, kwargs):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Skip logging the first argument (usually 'self')
        relevant_args = args[1:] if args else args
        formatted_args = [format_arg(arg) for arg in relevant_args]
        formatted_kwargs = [f"{k}={format_arg(v)}" for k, v in kwargs.items()]
        params = formatted_args + formatted_kwargs
        log_message = f"\n-------------------------------------------------- {current_time}\nCalling: {callback_name}"
        for param in params:
            log_message += f"\n{param}"
        logging.info(log_message)

    # If this is a slash command (has a callback attribute), wrap that callback.
    if hasattr(func, "callback"):
        original_callback = func.callback

        @wraps(original_callback)
        async def async_callback_wrapper(*args, **kwargs):
            log_execution(original_callback.__name__, args, kwargs)
            return await original_callback(*args, **kwargs)

        func.callback = async_callback_wrapper
        return func
    else:
        # Otherwise, check whether the function is asynchronous or synchronous.
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                log_execution(func.__name__, args, kwargs)
                return await func(*args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                log_execution(func.__name__, args, kwargs)
                return func(*args, **kwargs)
            return sync_wrapper


def developer_only(func):
    # Get the original callback if it exists (for slash commands)
    original_callback = func.callback if hasattr(func, "callback") else func

    @wraps(original_callback)
    async def wrapper(*args, **kwargs):
        # Look for the Interaction object in args or kwargs
        interaction = None
        for arg in args:
            if isinstance(arg, nextcord.Interaction):
                interaction = arg
                break
        if not interaction and "interaction" in kwargs:
            interaction = kwargs["interaction"]
        if not interaction:
            raise RuntimeError("No interaction object found in command arguments.")

        # Check if the user is a developer
        if interaction.user.id not in tempo_developer_ids:
            return await interaction.response.send_message(
                "You do not have permission to use this command.", ephemeral=True
            )
        # Call the original callback
        return await original_callback(*args, **kwargs)

    # If the original function has a callback (as with slash commands), replace it
    if hasattr(func, "callback"):
        func.callback = wrapper
        return func
    else:
        return wrapper