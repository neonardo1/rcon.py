import asyncio
from typing import List

from loguru import logger
from pydantic import ValidationError

from . import exceptions, models
from .client import Client


class Listener(Client):
    def __init__(self, ip, port, password):
        super().__init__(ip, port, password)

    def run(self):
        try:
            self._loop.run_until_complete(self.main())
        except KeyboardInterrupt:
            raise SystemExit

    async def main(self):
        await self.connect()
        tasks = [
            asyncio.create_task(self.server_event_loop()),
            asyncio.create_task(self.server_info_loop()),
        ]
        await asyncio.gather(*tasks)

    async def server_event_loop(self):
        event_handlers = {
            "player.onJoin": self._handle_player_on_join,
            "player.onAuthenticated": self._handle_player_on_auth,
            "player.onDisconnect": self._handle_player_on_disconnect,
            "player.onLeave": self._handle_player_on_leave,
            "player.onKill": self._handle_player_on_kill,
            # "player.onChat":
            # "player.onSquadChange"
            # "player.onTeamChange":
            # "punkBuster.onMessage":
            # "server.onMaxPlayerCountChange":
            # "server.onLevelLoaded":
            # "server.onRoundOver":
            # "server.onRoundOverPlayers":
            # "server.onRoundOverTeamScores":
        }
        while True:
            try:
                event = await self._protocol.listen()
                await event_handlers[event[0]](event)
            except asyncio.TimeoutError:
                pass
            except KeyError:
                # logger.error(f"{event} it's not a valid event {self.ip}:{self.port}")
                pass

    async def server_info_loop(self):
        while True:
            try:
                server_info = await self.send_command(["serverInfo"])  # noqa
                await asyncio.sleep(10)
            except exceptions.RCONException:
                await self.reconnect()

    async def _handle_player_on_join(self, event: List[str]):
        try:
            on_join = models.PlayerOnJoin(player_name=event[1], player_guid=event[2])
        except ValidationError:
            return

    async def _handle_player_on_auth(self, event: List[str]):
        try:
            on_auth = models.PlayerOnAuthenticated(player_name=event[1])
        except ValidationError:
            return

    async def _handle_player_on_disconnect(self, event: List[str]):
        try:
            on_disconnect = models.PlayerOnDisconnect(player_name=event[1], reason=event[2])
        except ValidationError:
            return

    async def _handle_player_on_leave(self, event: List[str]):
        try:
            on_leave = models.PlayerOnLeave()
        except ValidationError:
            return

    async def _handle_player_on_kill(self, event: List[str]):
        try:
            on_kill = models.PlayerOnKill(
                killer_name=event[1], victim_name=event[2], weapon_key=event[3], is_hs=event[4]
            )
        except ValidationError:
            return
