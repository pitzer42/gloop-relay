import os
import aiohttp
import functools

from gloop.channels.redis import RedisChannel
from gloop.channels.web_socket import WebSocketChannel

DEFAULT_ROUTE = '/'

REDIS_ADDRESS_KEY = 'REDIS_ADDRESS'
DEFAULT_REDIS_ADDRESS = 'redis://localhost:6379'

WAITING_LIST_CHANNEL_NAME_KEY = 'WAITING_LIST_CHANNEL_NAME'
DEFAULT_WAITING_LIST_CHANNEL_NAME = 'waiting_list'

NEW_MATCHES_CHANNEL_NAME_KEY = 'NEW_MATCHES_CHANNEL_NAME'
DEFAULT_NEW_MATCHES_CHANNEL_NAME = 'new_matches'

DEFAULT_CHANNEL_FACTORY = RedisChannel
DEFAULT_CLIENT_CHANNEL_FACTORY = WebSocketChannel


async def DEFAULT_GAME_LOOP(match_channel, match_id, *player_ids):
    pass


def receive_player(
        waiting_list_channel_name: str,
        new_matches_channel_name: str,
        channel_factory,
        client_channel_factory,
        game_loop):

    async def _receive_player(request):

        ws = client_channel_factory(request)
        waiting_list_channel = channel_factory(waiting_list_channel_name)
        new_matches_channel = channel_factory(new_matches_channel_name)

        await ws.open()
        await waiting_list_channel.open()
        await new_matches_channel.open()

        ws_id = str(id(ws))
        await waiting_list_channel.send(ws_id)
        print(ws_id)

        new_match = str()
        while ws_id not in new_match:
            new_match = await new_matches_channel.receive()

        await ws.send(new_match)
        print(f'{ws_id} <- {new_match}')

        match_params = new_match.split(' ')
        match_channel_name = match_params[0]
        player_ids = match_params[1:]

        match = channel_factory(match_channel_name)
        await match.open()

        await game_loop(
            ws,
            match,
            *player_ids
        )

        return await ws.close()

    return _receive_player


if __name__ == '__main__':

    print(os.environ.get(REDIS_ADDRESS_KEY))

    REDIS_ADDRESS = os.environ.get(
        REDIS_ADDRESS_KEY,
        DEFAULT_REDIS_ADDRESS
    )

    _waiting_list_channel_name = os.environ.get(
        WAITING_LIST_CHANNEL_NAME_KEY,
        DEFAULT_WAITING_LIST_CHANNEL_NAME
    )

    _new_matches_channel_name = os.environ.get(
        NEW_MATCHES_CHANNEL_NAME_KEY,
        DEFAULT_NEW_MATCHES_CHANNEL_NAME
    )

    _channel_factory = functools.partial(
        DEFAULT_CHANNEL_FACTORY,
        address=REDIS_ADDRESS
    )

    _client_channel_factory = DEFAULT_CLIENT_CHANNEL_FACTORY

    _game_loop = DEFAULT_GAME_LOOP

    app = aiohttp.web.Application()
    app.router.add_get(
        DEFAULT_ROUTE,
        receive_player(
            _waiting_list_channel_name,
            _new_matches_channel_name,
            _channel_factory,
            _client_channel_factory,
            _game_loop
        )
    )
    aiohttp.web.run_app(app)
