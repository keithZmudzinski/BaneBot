import logging

import discord

import message_handler
import settings

logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s][%(name)s][%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger('bane')


def main():
    logger.info('Starting bot')
    client = discord.Client()

    @client.event
    async def on_ready():
        logger.info('Setting presence')
        await client.change_presence(
            activity=discord.Streaming(name='this plane', url='https://www.youtube.com/watch?v=LYQpJHmo8nE'))

        logger.info(f'Logged in as {client.user.name}, ID {client.user.id}')

    @client.event
    async def on_message(message):
        await handle_message(message)

    async def handle_message(message):
        if message.content.startswith(settings.PREFIX) and message.content != settings.PREFIX:
            cmd_split = message.content[len(settings.PREFIX):].split()

            await message_handler.handle_command(cmd_split[0].lower(), cmd_split[1:], message, client)

    client.run(settings.BOT_TOKEN)


if __name__ == "__main__":
    main()
