from __future__ import annotations

from aiohttp import web
from loguru import logger

from distrello.db.orm import Database

html = """
<!DOCTYPE html>
<html>
<head>
    <title>Distrello | OAuth Handler</title>
</head>
<body>
    <h2>Processing OAuth...</h2>
    <script>
        const hashParams = new URLSearchParams(window.location.hash.substring(1));
        const token = hashParams.get('token');

        const urlParams = new URLSearchParams(window.location.search);
        const serverId = urlParams.get('server_id');

        if (token && serverId) {
            fetch('/save_token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    server_id: serverId,
                    token: token
                })
            })
            .then(response => response.text())
            .then(data => {
                document.body.innerHTML = '<h2>' + data + '</h2>';
            })
            .catch(error => {
                document.body.innerHTML = '<h2>Error saving token: ' + error + '</h2>';
            });
        } else {
            document.body.innerHTML = '<h2>Error: Missing token or server ID</h2>';
        }
    </script>
</body>
</html>
"""


class TrelloOAuthCallbackHandler:
    def __init__(self) -> None:
        self.app = web.Application()
        self.app.router.add_get("/callback", self.handle_callback)
        self.app.router.add_post("/save_token", self.save_token_endpoint)

        self.db = Database()

    async def handle_callback(self, _: web.Request) -> web.Response:
        return web.Response(text=html, content_type="text/html")

    async def save_token_endpoint(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            token = data.get("token")
            server_id = data.get("server_id")

            if not token or not server_id:
                return web.Response(text="Missing token or server_id", status=400)

            await self.save_token(token, server_id)
            return web.Response(text="Authorization successful! You can close this tab now.")
        except Exception as e:
            logger.error(f"Error saving token: {e}")
            return web.Response(text=f"Error: {e}", status=500)

    async def save_token(self, token: str, server_id: str) -> None:
        server = await self.db.get_server(int(server_id))
        if server is None:
            msg = f"Server with ID {server_id!r} not found"
            raise ValueError(msg)

        server.api_token = token
        await self.db.update_server(server)

    async def run(self, port: int = 6721) -> None:
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", port)
        await site.start()
        logger.info(f"OAuth callback server running on http://localhost:{port}/callback")
