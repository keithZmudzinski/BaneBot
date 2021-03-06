import datetime
import logging

import pymongo

import settings

logger = logging.getLogger('karma_handler')


class KarmaHandler:
    client = pymongo.MongoClient(settings.MONGO_URI)['banebot']
    karma_collection = client['karma']
    reaction_collection = client['reactions']

    @classmethod
    def is_karma_reaction(cls, emoji, guild_id):
        guild_doc = cls.reaction_collection.find_one({'guild': str(guild_id)})
        id_or_codepoint = str(emoji.id) if emoji.is_custom_emoji() else emoji.name
        return guild_doc is not None and id_or_codepoint in guild_doc.values()

    @classmethod
    def is_ignored_user(cls, user_id, guild_id):
        user_doc = cls.karma_collection.find_one({
            'guild': str(guild_id),
            'user': str(user_id)
        })
        try:
            return user_doc['ignored'] is not None and user_doc['ignored']
        except (AttributeError, KeyError, TypeError):
            return False

    @classmethod
    async def handle_reaction(cls, payload, client):
        # skip ignored users
        if cls.is_ignored_user(payload.user_id, payload.guild_id):
            return

        # find author of message
        channel = client.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        author_id = message.author.id

        # skip messages older than 24h
        if datetime.datetime.now() - datetime.timedelta(days=1) >= message.created_at:
            return

        # skip voting on bane
        if client.user.id == author_id:
            return

        # skip voting on self
        if payload.user_id == author_id:
            return

        # determine upvote/downvote
        guild_doc = cls.reaction_collection.find_one({'guild': str(payload.guild_id)})
        id_or_codepoint = str(payload.emoji.id) if payload.emoji.is_custom_emoji() else payload.emoji.name

        # already validated as karma reaction, so it must be in either upvote or downvote field
        vote_direction = 1 if guild_doc['upvote'] == id_or_codepoint else -1
        voted = 'upvote' if vote_direction == 1 else 'downvote'

        # flip direction if removing reaction
        if payload.event_type == 'REACTION_REMOVE':
            vote_direction *= -1
            voted = f'remove {voted}'

        # update author's karma
        cls.karma_collection.find_one_and_update(
            {'guild': str(payload.guild_id),
             'user': str(author_id)},
            {'$inc': {'karma': vote_direction}},
            upsert=True
        )

        # get names for logging
        user = client.get_user(payload.user_id)
        if user is None:
            user = await client.fetch_user(payload.user_id)
        author = client.get_user(author_id)
        if author is None:
            author = await client.fetch_user(author_id)
        guild = client.get_guild(payload.guild_id)
        if guild is None:
            guild = await client.fetch_guild(payload.guild_id)
        logger.info(f'{guild.name}: {user.name}#{user.discriminator} - {voted} - {author.name}#{author.discriminator}')

    @classmethod
    async def get_karma(cls, user_id, guild_id):
        user_doc = cls.karma_collection.find_one({
            'guild': str(guild_id),
            'user': str(user_id)
        })

        try:
            return user_doc['karma']
        except (AttributeError, KeyError, TypeError):
            return 0

    @classmethod
    async def toggle_ignore_user(cls, user, guild):
        user_doc = cls.karma_collection.find_one({
            'guild': str(guild.id),
            'user': str(user.id)
        })

        ignored = False
        try:
            ignored = user_doc['ignored']
        except (AttributeError, KeyError, TypeError):
            pass

        cls.karma_collection.find_one_and_update(
            {'guild': str(guild.id),
             'user': str(user.id)},
            {'$set': {'ignored': not ignored}},
            upsert=True
        )

        logger.info(f'{guild.name}: Toggled ignore of {user.name}#{user.discriminator}')

    @classmethod
    async def get_leaderboard(cls, message):
        karma_docs = cls.karma_collection.find({'guild': str(message.guild.id)})
        return sorted(karma_docs, key=lambda item: item['karma'], reverse=True)

    @classmethod
    async def set_reaction(cls, emoji, guild, vote_type):
        id_or_codepoint = str(emoji.id) if type(emoji) != str else emoji

        cls.reaction_collection.find_one_and_update(
            {'guild': str(guild.id)},
            {'$set': {vote_type: id_or_codepoint}},
            upsert=True
        )

        logger.info(f'{guild.name}: Set {vote_type} reaction as :{emoji.name}:')
